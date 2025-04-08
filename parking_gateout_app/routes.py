from flask import Blueprint, request, jsonify, current_app, render_template, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import jwt
import traceback
import uuid
from functools import wraps
from parking_gateout_app.models import (
    db, AspNetUsers, AspNetUserRoles, ParkingSpaces, Vehicles,
    ParkingTickets, ParkingTransactions, AccessTokens, ParkingRate, ActivityLog
)
import logging
from sqlalchemy import text
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprints for different route groups
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
parking_bp = Blueprint('parking', __name__, url_prefix='/api/parking-sessions')
payment_bp = Blueprint('payment', __name__, url_prefix='/api/payments')
management_bp = Blueprint('management', __name__, url_prefix='/api/management')
report_bp = Blueprint('report', __name__, url_prefix='/api/reports')
main_bp = Blueprint('main', __name__, url_prefix='/api/main')
health_bp = Blueprint('health', __name__, url_prefix='/api')

# Initialize rate limiter with fixed window and burst handling
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://"
)

# Define UserTokens class if it doesn't exist in models.py
class UserTokens(db.Model):
    __tablename__ = 'user_tokens'
    Id = db.Column(db.Integer, primary_key=True)
    Token = db.Column(db.String(500), unique=True)
    UserId = db.Column(db.String(36), db.ForeignKey('asp_net_users.Id'))
    ExpiresAt = db.Column(db.DateTime)

def create_token(user_id):
    """Create JWT token for user authentication"""
    token = jwt.encode(
        {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        },
        current_app.config['SECRET_KEY']
    )
    
    # Store token in database using dictionary unpacking
    access_token_data = {
        'Token': token,
        'UserId': user_id,
        'ExpiresAt': datetime.utcnow() + timedelta(hours=24)
    }
    access_token = AccessTokens(**access_token_data)
    db.session.add(access_token)
    db.session.commit()
    
    return token

def verify_token(token):
    """Verify JWT token"""
    try:
        # Check if token is revoked
        access_token = AccessTokens.query.filter_by(Token=token, IsRevoked=False).first()
        if not access_token:
            return None
        
        # Check if token is expired
        if access_token.ExpiresAt < datetime.utcnow():
            # Mark token as revoked
            access_token.IsRevoked = True
            db.session.commit()
            return None
        
        # Verify token
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        # Mark token as revoked if expired
        access_token = AccessTokens.query.filter_by(Token=token).first()
        if access_token:
            access_token.IsRevoked = True
            db.session.commit()
        return None
    except:
        return None

def token_required(f):
    """Decorator to require token authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or 'Bearer ' not in auth_header:
            return jsonify({'message': 'No token provided'}), 401
            
        token = auth_header.split(' ')[1]
        try:
            data = jwt.decode(token, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])
            # Look for the user in the database
            user = AspNetUsers.query.get(data.get('user_id'))
            if not user:
                return jsonify({'message': 'User not found'}), 401
                
            # We'll use the user object directly instead of UserTokens
            return f(user, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
            
    decorated.__name__ = f.__name__
    return decorated

# Auth routes
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute;30 per hour")
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'message': 'Username and password are required'}), 400
            
        # Validate credentials (implement your own logic)
        user = db.session.execute(
            text('SELECT * FROM AspNetUsers WHERE UserName = :username'),
            {'username': username}
        ).first()
        
        if not user:
            return jsonify({'message': 'Invalid credentials'}), 401
            
        # Generate token
        token = jwt.encode({
            'user_id': user.Id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, os.getenv('JWT_SECRET_KEY'), algorithm='HS256')
        
        # Store token
        user_token = UserTokens()
        user_token.Token = token
        user_token.UserId = user.Id
        user_token.ExpiresAt = datetime.utcnow() + timedelta(hours=24)
        
        db.session.add(user_token)
        db.session.commit()
        
        return jsonify({
            'token': token,
            'user': {
                'id': user.Id,
                'username': user.UserName,
                'email': user.Email
            }
        })
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500

@auth_bp.route('/logout', methods=['POST'])
@limiter.limit("10 per minute;60 per hour")
@token_required
def logout(current_user):
    try:
        # Get token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                'status': 'error',
                'message': 'No token provided',
                'code': 401
            }), 401
            
        token = auth_header.split(' ')[1]
        
        # Revoke token
        access_token = AccessTokens.query.filter_by(Token=token).first()
        if access_token:
            access_token.IsRevoked = True
            db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Successfully logged out'
        }), 200
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Logout failed',
            'code': 500
        }), 500

@auth_bp.route('/profile', methods=['GET'])
@limiter.limit("60 per minute;300 per hour")
@token_required
def profile(current_user):
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header:
            token = auth_header.split(' ')[1]
            user_id = verify_token(token)
            user = AspNetUsers.query.get(user_id)
            if user:
                user_role = AspNetUserRoles.query.filter_by(UserId=user_id).first()
                
                return jsonify({
                    'status': 'success',
                    'data': {
                        'fullName': user.FullName,
                        'email': user.Email,
                        'role': user_role.RoleId if user_role else None
                    }
                })
            
        return jsonify({
            'status': 'error',
            'message': 'User not found',
            'code': 404
        }), 404
    except Exception as e:
        current_app.logger.error(f"Profile error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get profile',
            'code': 500
        }), 500

@auth_bp.route('/logout_user')
def logout_user_route():
    """Handle exit request"""
    try:
        # Clear session and tokens
        session.clear()
        if 'token' in session:
            del session['token']
        
        # Redirect to login page
        return redirect(url_for('auth.login'))
    except Exception as e:
        print(f"Error during exit: {str(e)}")
        return redirect(url_for('auth.login'))

@auth_bp.route('/verify', methods=['GET'])
@limiter.limit("60 per minute;300 per hour")
@token_required
def verify(current_user):
    """Verify token endpoint"""
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'Invalid token'
        }), 401
        
    user_role = AspNetUserRoles.query.filter_by(UserId=current_user.Id).first()
    role_id = user_role.RoleId if user_role else None
        
    return jsonify({
        'status': 'success',
        'message': 'Token is valid',
        'user': {
            'id': current_user.Id,
            'username': current_user.UserName,
            'email': current_user.Email,
            'role': role_id
        }
    })

# Parking session routes
@parking_bp.route('/exit', methods=['PUT'])
@limiter.limit("50 per minute;150 per hour")  # Reduced for critical operation with burst allowance
@token_required
def process_exit(current_user):
    try:
        data = request.get_json()
        ticket_number = data.get('ticketNumber')
        
        ticket = ParkingTickets.query.filter_by(TicketNumber=ticket_number).first()
        if not ticket:
            return jsonify({
                'status': 'error',
                'message': 'Invalid ticket number'
            }), 404
        
        vehicle = Vehicles.query.get(ticket.VehicleId)
        if not vehicle or not vehicle.IsParked:
            return jsonify({
                'status': 'error',
                'message': 'Vehicle not found or already exited'
            }), 404
        
        # Calculate parking duration and fee
        exit_time = datetime.utcnow()
        duration = exit_time - vehicle.EntryTime
        hours = duration.total_seconds() / 3600
        
        space = ParkingSpaces.query.get(vehicle.ParkingSpaceId)
        hourly_rate = float(space.HourlyRate if space else current_app.config['DEFAULT_HOURLY_RATE'])
        total_fee = round(hours * hourly_rate, 2)
        
        # Update vehicle status
        vehicle.ExitTime = exit_time
        vehicle.IsParked = False
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'data': {
                'ticketNumber': ticket_number,
                'duration': f'{hours:.2f} hours',
                'fee': total_fee
            },
            'message': 'Exit processed successfully'
        })
    except Exception as e:
        current_app.logger.error(f"Exit error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'message': 'Internal server error',
            'error': str(e),
            'code': 500
        }), 500

@parking_bp.route('/active', methods=['GET'])
@limiter.limit("60 per minute;300 per hour")
@token_required
def get_active_sessions(current_user):
    try:
        sessions = ParkingTickets.query.filter_by(IsActive=True).all()
        return jsonify({
            'status': 'success',
            'data': [{
                'ticket_number': session.TicketNumber,
                'vehicle_plate': session.Vehicle.PlateNumber,
                'entry_time': session.EntryTime.isoformat(),
                'duration': str(datetime.utcnow() - session.EntryTime)
            } for session in sessions]
        })
    except Exception as e:
        current_app.logger.error(f"Active sessions error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get active sessions',
            'code': 500
        }), 500

# Payment routes
@payment_bp.route('/process', methods=['POST'])
@limiter.limit("50 per minute;150 per hour")  # Reduced for critical operation with burst allowance
@token_required
def process_payment(current_user):
    try:
        data = request.get_json()
        ticket_number = data.get('ticketNumber')
        payment_method = data.get('paymentMethod')
        
        ticket = ParkingTickets.query.filter_by(TicketNumber=ticket_number).first()
        if not ticket:
            return jsonify({
                'status': 'error',
                'message': 'Invalid ticket number'
            }), 404
        
        # Create payment transaction
        transaction_data = {
            'Id': str(uuid.uuid4()),
            'ticket_id': ticket.Id,
            'amount': ticket.Amount or 0,
            'payment_method': payment_method,
            'status': 'COMPLETED',
            'processed_by': current_user.Id,
            'transaction_number': f'TXN{datetime.now().strftime("%Y%m%d%H%M%S")}'
        }
        transaction = ParkingTransactions(**transaction_data)
        
        # Update ticket status
        ticket.IsPaid = True
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'data': {
                'transactionId': transaction.Id,
                'paymentStatus': transaction.status
            },
            'message': 'Payment processed successfully'
        })
    except Exception as e:
        current_app.logger.error(f"Payment error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'message': 'Internal server error',
            'error': str(e),
            'code': 500
        }), 500

@payment_bp.route('/record', methods=['POST'])
@limiter.limit("30 per minute")
@token_required
def record_payment(current_user):
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['ticketId', 'amount', 'paymentMethod']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
                
        # Create transaction record
        transaction_data = {
            'Id': str(uuid.uuid4()),
            'ticket_id': data['ticketId'],
            'amount': data['amount'],
            'payment_method': data['paymentMethod'],
            'status': data.get('status', 'completed'),
            'processed_by': current_user.Id,
            'transaction_number': f'TXN{datetime.now().strftime("%Y%m%d%H%M%S")}'
        }
        transaction = ParkingTransactions(**transaction_data)
        
        # Create activity log
        activity_data = {
            'Action': 'RECORD_PAYMENT',
            'Details': f'Payment recorded for ticket {data["ticketId"]}',
            'Status': 'success',
            'UserId': current_user.Id,
            'IpAddress': request.remote_addr,
            'IsRead': False
        }
        activity = ActivityLog(**activity_data)
        
        db.session.add(transaction)
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Payment recorded successfully',
            'data': {
                'transactionId': transaction.Id
            }
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Record payment error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to record payment: {str(e)}',
            'code': 500
        }), 500

# Management routes
@management_bp.route('/spaces', methods=['GET'])
@limiter.limit("200 per minute;1000 per hour")  # Increased for read-only with burst allowance
@token_required
def get_parking_spaces(current_user):
    try:
        spaces = ParkingSpaces.query.all()
        return jsonify({
            'status': 'success',
            'data': [{
                'spaceNumber': s.SpaceNumber,
                'isOccupied': s.IsOccupied,
                'hourlyRate': float(s.HourlyRate)
            } for s in spaces]
        })
    except Exception as e:
        current_app.logger.error(f"Parking spaces error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'message': 'Internal server error',
            'error': str(e),
            'code': 500
        }), 500

@management_bp.route('/operators', methods=['GET'])
@limiter.limit("200 per minute;1000 per hour")  # Increased for read-only with burst allowance
@token_required
def get_operators(current_user):
    try:
        operator_role_id = 'operator'  # Adjust based on your role system
        operators = db.session.query(AspNetUsers)\
            .join(AspNetUserRoles)\
            .filter(AspNetUserRoles.RoleId == operator_role_id)\
            .all()
        
        return jsonify({
            'status': 'success',
            'data': [{
                'fullName': op.FullName,
                'email': op.Email
            } for op in operators]
        })
    except Exception as e:
        current_app.logger.error(f"Operators error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'message': 'Internal server error',
            'error': str(e),
            'code': 500
        }), 500

# Report routes
@report_bp.route('/daily', methods=['GET'])
@limiter.limit("60 per minute;300 per hour")
@token_required
def get_daily_report(current_user):
    try:
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # Find all transactions for the date
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        next_date = date_obj + timedelta(days=1)
        
        transactions = ParkingTransactions.query\
            .filter(ParkingTransactions.created_at >= date_obj)\
            .filter(ParkingTransactions.created_at < next_date)\
            .all()
        
        total_amount = sum(float(t.amount or 0) for t in transactions)
        
        return jsonify({
            'status': 'success',
            'data': {
                'date': date,
                'totalTransactions': len(transactions),
                'totalRevenue': total_amount,
                'transactions': [{
                    'id': t.Id,
                    'amount': float(t.amount or 0),
                    'method': t.payment_method,
                    'processedAt': t.created_at.isoformat() if t.created_at else None
                } for t in transactions]
            }
        })
    except Exception as e:
        current_app.logger.error(f"Daily report error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get daily report',
            'code': 500
        }), 500

@report_bp.route('/weekly', methods=['GET'])
@limiter.limit("60 per minute;300 per hour")
@token_required
def get_weekly_report(current_user):
    try:
        # Get start and end date for the week
        end_date = request.args.get('end_date')
        if not end_date:
            end_date = datetime.now().date()
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
        start_date = end_date - timedelta(days=6)  # Last 7 days
        
        # Find all transactions for the date range
        transactions = ParkingTransactions.query\
            .filter(ParkingTransactions.created_at >= start_date)\
            .filter(ParkingTransactions.created_at < end_date + timedelta(days=1))\
            .all()
        
        # Group by day
        daily_totals = {}
        for t in transactions:
            day = t.created_at.date()
            if day not in daily_totals:
                daily_totals[day] = {'vehicles': 0, 'revenue': 0}
                
            daily_totals[day]['vehicles'] += 1
            daily_totals[day]['revenue'] += float(t.amount or 0)
            
        # Format for response
        daily_data = []
        current_date = start_date
        while current_date <= end_date:
            data = daily_totals.get(current_date, {'vehicles': 0, 'revenue': 0})
            daily_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'day': current_date.strftime('%A'),
                'vehicles': data['vehicles'],
                'revenue': data['revenue']
            })
            current_date += timedelta(days=1)
            
        return jsonify({
            'status': 'success',
            'data': {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'totalVehicles': sum(d['vehicles'] for d in daily_data),
                'totalRevenue': sum(d['revenue'] for d in daily_data),
                'dailyData': daily_data
            }
        })
    except Exception as e:
        current_app.logger.error(f"Weekly report error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get weekly report',
            'code': 500
        }), 500

@report_bp.route('/monthly', methods=['GET'])
@limiter.limit("60 per minute;300 per hour")
@token_required
def get_monthly_report(current_user):
    try:
        # Get month and year
        month_param = request.args.get('month')
        year_param = request.args.get('year')
        
        if not month_param or not year_param:
            now = datetime.now()
            month = month_param if month_param else now.month
            year = year_param if year_param else now.year
        else:
            month = int(month_param)
            year = int(year_param)
            
        # Calculate start and end date
        start_date = datetime(int(year), int(month), 1)
        if int(month) == 12:
            end_date = datetime(int(year) + 1, 1, 1)
        else:
            end_date = datetime(int(year), int(month) + 1, 1)
            
        # Find all transactions for the month
        transactions = ParkingTransactions.query\
            .filter(ParkingTransactions.created_at >= start_date)\
            .filter(ParkingTransactions.created_at < end_date)\
            .all()
        
        total_amount = sum(float(t.amount or 0) for t in transactions)
        
        # Format for response
        return jsonify({
            'status': 'success',
            'data': {
                'month': month,
                'year': year,
                'totalTransactions': len(transactions),
                'totalRevenue': total_amount,
                'transactions': [{
                    'id': t.Id,
                    'amount': float(t.amount or 0),
                    'method': t.payment_method,
                    'processedAt': t.created_at.isoformat() if t.created_at else None
                } for t in transactions]
            }
        })
    except Exception as e:
        current_app.logger.error(f"Monthly report error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get monthly report',
            'code': 500
        }), 500

@report_bp.route('/recent-transactions')
@limiter.limit("60 per minute")
@token_required
def get_recent_transactions(current_user):
    try:
        # Get recent transactions
        transactions = ParkingTransactions.query.order_by(
            ParkingTransactions.created_at.desc()
        ).limit(10).all()
        
        return jsonify({
            'status': 'success',
            'data': [{
                'id': t.Id,
                'ticket_id': t.ticket_id,
                'amount': float(t.amount) if t.amount else 0.0,
                'status': t.status,
                'payment_method': t.payment_method,
                'processed_by': t.processed_by,
                'created_at': t.created_at.isoformat() if t.created_at else None
            } for t in transactions]
        })
    except Exception as e:
        current_app.logger.error(f"Recent transactions error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get recent transactions',
            'code': 500
        }), 500
        
@report_bp.route('/transactions')
@limiter.limit("60 per minute")
@token_required
def get_transactions(current_user):
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Build query
        query = ParkingTransactions.query
        
        # Apply date filters
        if start_date:
            query = query.filter(ParkingTransactions.created_at >= start_date)
        if end_date:
            query = query.filter(ParkingTransactions.created_at < end_date)
            
        # Order by and paginate
        transactions = query.order_by(
            ParkingTransactions.created_at.desc()
        ).paginate(page=page, per_page=per_page)
        
        return jsonify({
            'status': 'success',
            'data': {
                'transactions': [{
                    'id': t.Id,
                    'ticket_id': t.ticket_id,
                    'amount': float(t.amount) if t.amount else 0.0,
                    'status': t.status,
                    'payment_method': t.payment_method,
                    'processed_by': t.processed_by,
                    'created_at': t.created_at.isoformat() if t.created_at else None
                } for t in transactions.items],
                'pagination': {
                    'total': transactions.total,
                    'pages': transactions.pages,
                    'page': transactions.page,
                    'per_page': transactions.per_page
                }
            }
        })
    except Exception as e:
        current_app.logger.error(f"Transactions error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get transactions',
            'code': 500
        }), 500

# Add route for login page
@auth_bp.route('/login-page', methods=['GET'])
def login_page():
    return render_template('login.html')

# Add route for root to redirect to login if not authenticated
@auth_bp.route('/', methods=['GET'])
def root():
    token = request.cookies.get('token')
    if not token or not verify_token(token):
        return redirect(url_for('auth.login_page'))
    return redirect(url_for('dashboard'))

@main_bp.route('/exit')
def exit():
    """Handle exit requests"""
    try:
        # Get ticket ID from query parameters
        ticket_id = request.args.get('ticket_id')
        if not ticket_id:
            return jsonify({'status': 'error', 'message': 'Ticket ID is required'}), 400

        # Find the parking ticket
        ticket = ParkingTickets.query.get(ticket_id)
        if not ticket:
            return jsonify({'status': 'error', 'message': 'Ticket not found'}), 404

        # Check if ticket is already processed
        if ticket.Status != 'active':
            return jsonify({'status': 'error', 'message': 'Ticket already processed'}), 400

        # Calculate parking duration and fee
        exit_time = datetime.utcnow()
        duration = exit_time - ticket.EntryTime
        hours = duration.total_seconds() / 3600

        # Get parking rate
        rate = ParkingRate.query.filter_by(
            VehicleType=ticket.VehicleType,
            DurationType='hourly'
        ).first()

        if not rate:
            return jsonify({'status': 'error', 'message': 'Parking rate not found'}), 404

        # Calculate fee
        base_fee = float(rate.BaseRate)
        additional_fee = float(rate.AdditionalRate) if rate.AdditionalRate else 0
        total_fee = base_fee + (max(0, hours - rate.BaseDuration) * additional_fee)

        # Create transaction
        transaction_data = {
            'Id': str(uuid.uuid4()),
            'ticket_id': ticket.Id,
            'amount': total_fee,
            'payment_method': 'CASH',
            'status': 'COMPLETED',
            'processed_by': current_user.Id,
            'transaction_number': f'TXN{datetime.now().strftime("%Y%m%d%H%M%S")}'
        }
        processed_txn = ParkingTransactions(**transaction_data)
        db.session.add(processed_txn)

        # Update ticket status
        ticket.ExitTime = exit_time
        ticket.Status = 'completed'
        ticket.Amount = total_fee

        # Update parking space
        space = ParkingSpaces.query.get(ticket.SpaceId)
        if space:
            space.IsOccupied = False

        # Log activity
        activity_data = {
            'Action': 'exit',
            'Details': f'Vehicle {ticket.PlateNumber} exited. Fee: {total_fee}',
            'Status': 'success'
        }
        activity = ActivityLog(**activity_data)
        db.session.add(activity)

        db.session.commit()

        return jsonify({
            'status': 'success',
            'data': {
                'ticket_id': ticket.Id,
                'plate_number': ticket.PlateNumber,
                'entry_time': ticket.EntryTime.isoformat(),
                'exit_time': exit_time.isoformat(),
                'duration_hours': round(hours, 2),
                'fee': total_fee
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Exit error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Health check endpoint
@health_bp.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint that doesn't require authentication"""
    try:
        # Check database connection
        db_health = {
            'status': 'healthy',
            'message': 'Database connection is active'
        }
        try:
            db.session.execute(text('SELECT 1'))
        except Exception as e:
            db_health = {
                'status': 'unhealthy',
                'message': str(e)
            }
            
        return jsonify({
            'status': 'success',
            'data': {
                'database': db_health
            }
        })
    except Exception as e:
        current_app.logger.error(f"Health check error: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500

# Register blueprints
current_app.register_blueprint(auth_bp)
current_app.register_blueprint(health_bp)

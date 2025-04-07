from flask import Blueprint, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import jwt
import traceback
import uuid
from functools import wraps
from models import (
    db, AspNetUsers, AspNetUserRoles, ParkingSpaces, Vehicles,
    ParkingTickets, ParkingTransactions, AccessTokens
)

# Create blueprints for different route groups
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
parking_bp = Blueprint('parking', __name__, url_prefix='/api/parking-sessions')
payment_bp = Blueprint('payment', __name__, url_prefix='/api/payments')
management_bp = Blueprint('management', __name__, url_prefix='/api/management')
report_bp = Blueprint('report', __name__, url_prefix='/api/reports')

# Initialize rate limiter with fixed window and burst handling
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://"
)

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                'message': 'No authorization header',
                'error': 'AuthenticationRequired',
                'code': 401
            }), 401
        
        try:
            token_type, token = auth_header.split(' ')
            if token_type.lower() != 'bearer':
                return jsonify({
                    'message': 'Invalid token type',
                    'error': 'AuthenticationRequired',
                    'code': 401
                }), 401
            
            # Verify token
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user = AspNetUsers.query.get(data['user_id'])
            if not user:
                return jsonify({
                    'message': 'User not found',
                    'error': 'AuthenticationRequired',
                    'code': 401
                }), 401
                
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({
                'message': 'Token has expired',
                'error': 'AuthenticationRequired',
                'code': 401
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'message': 'Invalid token',
                'error': 'AuthenticationRequired',
                'code': 401
            }), 401
    return decorated

def create_token(user_id):
    """Create JWT token for user authentication"""
    try:
        token = jwt.encode(
            {
                'user_id': user_id,
                'exp': datetime.utcnow() + timedelta(hours=24)
            },
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        
        # Store token in database
        access_token = AccessTokens(
            Id=str(uuid.uuid4()),
            Token=token,
            UserId=user_id,
            ExpiresAt=datetime.utcnow() + timedelta(hours=24)
        )
        db.session.add(access_token)
        db.session.commit()
        
        return token
    except Exception as e:
        current_app.logger.error(f"Error creating token: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        raise

# Auth routes
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("60 per minute;180 per hour")  # Reduced for security with burst allowance
def login():
    try:
        data = request.get_json()
        if not data:
            current_app.logger.error("No JSON data received")
            return jsonify({
                'message': 'No JSON data received',
                'error': 'InvalidRequest',
                'code': 400
            }), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            current_app.logger.error("Missing username or password")
            return jsonify({
                'message': 'Username and password are required',
                'error': 'ValidationError',
                'code': 400
            }), 400
        
        current_app.logger.info(f"Login attempt for username: {username}")
        
        # Try to find user by username or email
        user = AspNetUsers.query.filter(
            (AspNetUsers.UserName == username) | (AspNetUsers.Email == username)
        ).first()
        
        if not user:
            current_app.logger.warning(f"User not found: {username}")
            return jsonify({
                'message': 'Invalid credentials',
                'error': 'AuthenticationError',
                'code': 401
            }), 401
        
        if not user.check_password(password):
            current_app.logger.warning(f"Invalid password for user: {username}")
            return jsonify({
                'message': 'Invalid credentials',
                'error': 'AuthenticationError',
                'code': 401
            }), 401
        
        token = create_token(user.Id)
        
        # Get user role
        user_role = AspNetUserRoles.query.filter_by(UserId=user.Id).first()
        role_name = user_role.RoleId if user_role else None
        
        current_app.logger.info(f"Successful login for user: {username}")
        
        return jsonify({
            'token': token,
            'user': {
                'id': user.Id,
                'username': user.UserName,
                'role': role_name,
                'name': user.FullName
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'message': 'Internal server error',
            'error': str(e),
            'code': 500
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@limiter.limit("30 per minute;90 per hour")  # Reduced for security with burst allowance
@jwt_required
def logout():
    try:
        token = request.headers.get('Authorization').split(' ')[1]
        access_token = AccessTokens.query.filter_by(Token=token).first()
        if access_token:
            access_token.IsRevoked = True
            db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Logged out successfully'
        })
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'message': 'Internal server error',
            'error': str(e),
            'code': 500
        }), 500

@auth_bp.route('/profile', methods=['GET'])
@limiter.limit("200 per minute;1000 per hour")  # Increased for read-only with burst allowance
@jwt_required
def profile():
    try:
        user_role = AspNetUserRoles.query.filter_by(UserId=current_user.Id).first()
        return jsonify({
            'status': 'success',
            'data': {
                'fullName': current_user.FullName,
                'email': current_user.Email,
                'role': user_role.RoleId if user_role else None
            }
        })
    except Exception as e:
        current_app.logger.error(f"Profile error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'message': 'Internal server error',
            'error': str(e),
            'code': 500
        }), 500

# Parking session routes
@parking_bp.route('/exit', methods=['PUT'])
@limiter.limit("50 per minute;150 per hour")  # Reduced for critical operation with burst allowance
@jwt_required
def process_exit():
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
@limiter.limit("300 per minute;1500 per hour")  # Increased for read-only with burst allowance
@jwt_required
def get_active_vehicles():
    try:
        vehicles = Vehicles.query.filter_by(IsParked=True).all()
        return jsonify({
            'status': 'success',
            'data': [{
                'plateNumber': v.PlateNumber,
                'entryTime': v.EntryTime.isoformat(),
                'parkingSpaceId': v.ParkingSpaceId
            } for v in vehicles]
        })
    except Exception as e:
        current_app.logger.error(f"Active vehicles error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'message': 'Internal server error',
            'error': str(e),
            'code': 500
        }), 500

# Payment routes
@payment_bp.route('/process', methods=['POST'])
@limiter.limit("50 per minute;150 per hour")  # Reduced for critical operation with burst allowance
@jwt_required
def process_payment():
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
        transaction = ParkingTransactions(
            TicketId=ticket.Id,
            PaymentMethod=payment_method,
            PaymentStatus='COMPLETED',
            ProcessedBy=current_user.Id
        )
        
        # Update ticket status
        ticket.IsPaid = True
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'data': {
                'transactionId': transaction.Id,
                'paymentStatus': transaction.PaymentStatus
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

# Management routes
@management_bp.route('/spaces', methods=['GET'])
@limiter.limit("200 per minute;1000 per hour")  # Increased for read-only with burst allowance
@jwt_required
def get_parking_spaces():
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
@jwt_required
def get_operators():
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
@limiter.limit("150 per minute;750 per hour")  # Balanced for reporting with burst allowance
@jwt_required
def get_daily_report():
    try:
        date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
        date = datetime.strptime(date_str, '%Y-%m-%d')
        next_date = date + timedelta(days=1)
        
        transactions = ParkingTransactions.query\
            .filter(ParkingTransactions.ProcessedAt >= date)\
            .filter(ParkingTransactions.ProcessedAt < next_date)\
            .all()
        
        total_revenue = sum(float(t.PaymentAmount or 0) for t in transactions)
        
        return jsonify({
            'status': 'success',
            'data': {
                'date': date_str,
                'totalVehicles': len(transactions),
                'totalRevenue': total_revenue,
                'transactions': [{
                    'ticketId': t.TicketId,
                    'amount': float(t.PaymentAmount),
                    'method': t.PaymentMethod,
                    'processedAt': t.ProcessedAt.isoformat()
                } for t in transactions]
            }
        })
    except Exception as e:
        current_app.logger.error(f"Daily report error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'message': 'Internal server error',
            'error': str(e),
            'code': 500
        }), 500

@report_bp.route('/monthly', methods=['GET'])
@limiter.limit("150 per minute;750 per hour")  # Balanced for reporting with burst allowance
@jwt_required
def get_monthly_report():
    try:
        month = int(request.args.get('month', datetime.utcnow().month))
        year = int(request.args.get('year', datetime.utcnow().year))
        
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        transactions = ParkingTransactions.query\
            .filter(ParkingTransactions.ProcessedAt >= start_date)\
            .filter(ParkingTransactions.ProcessedAt < end_date)\
            .all()
        
        # Group by day
        daily_totals = {}
        for t in transactions:
            day = t.ProcessedAt.date()
            if day not in daily_totals:
                daily_totals[day] = {'vehicles': 0, 'revenue': 0}
            daily_totals[day]['vehicles'] += 1
            daily_totals[day]['revenue'] += float(t.PaymentAmount or 0)
        
        return jsonify({
            'status': 'success',
            'data': {
                'month': month,
                'year': year,
                'dailyTotals': [{
                    'date': day.isoformat(),
                    'vehicles': totals['vehicles'],
                    'revenue': totals['revenue']
                } for day, totals in sorted(daily_totals.items())]
            }
        })
    except Exception as e:
        current_app.logger.error(f"Monthly report error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'message': 'Internal server error',
            'error': str(e),
            'code': 500
        }), 500

@report_bp.route('/generate', methods=['POST'])
@limiter.limit("100 per minute;500 per hour")  # Standard for custom reports with burst allowance
@jwt_required
def generate_custom_report():
    try:
        data = request.get_json()
        start_date = datetime.fromisoformat(data.get('start_date'))
        end_date = datetime.fromisoformat(data.get('end_date'))
        
        transactions = ParkingTransactions.query\
            .filter(ParkingTransactions.ProcessedAt >= start_date)\
            .filter(ParkingTransactions.ProcessedAt < end_date)\
            .all()
        
        total_revenue = sum(float(t.PaymentAmount or 0) for t in transactions)
        
        return jsonify({
            'status': 'success',
            'data': {
                'startDate': start_date.isoformat(),
                'endDate': end_date.isoformat(),
                'totalVehicles': len(transactions),
                'totalRevenue': total_revenue,
                'transactions': [{
                    'ticketId': t.TicketId,
                    'amount': float(t.PaymentAmount),
                    'method': t.PaymentMethod,
                    'processedAt': t.ProcessedAt.isoformat()
                } for t in transactions]
            }
        })
    except Exception as e:
        current_app.logger.error(f"Custom report error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'message': 'Internal server error',
            'error': str(e),
            'code': 500
        }), 500

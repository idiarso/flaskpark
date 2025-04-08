from flask import Blueprint, jsonify, request, current_app, render_template
from datetime import datetime, timedelta
from sqlalchemy import func, and_, text, select
import uuid
from parking_gateout_app.models import (
    db, AspNetUsers, AspNetUserRoles, SystemConfig, ParkingRate,
    ActivityLog, HardwareStatus, Vehicles, ParkingTickets,
    ParkingTransactions, ParkingSpaces, Members, MemberCards,
    MemberRates, Staff, StaffAttendance, Shifts
)
from parking_gateout_app.routes import token_required, limiter
from flask_caching import Cache
import logging
from flask_login import login_required, current_user

# Initialize cache
cache = Cache(config={'CACHE_TYPE': 'simple'})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprints
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
api_dashboard_bp = Blueprint('api_dashboard', __name__, url_prefix='/api/dashboard')
api_stats_bp = Blueprint('api_stats', __name__, url_prefix='/api/stats')
api_activities_bp = Blueprint('api_activities', __name__, url_prefix='/api/activities')
api_vehicles_bp = Blueprint('api_vehicles', __name__, url_prefix='/api/vehicles')
api_rates_bp = Blueprint('api_rates', __name__, url_prefix='/api/parking-rates')

# Dashboard Pages
@dashboard_bp.route('/')
@token_required
def index():
    return render_template('dashboard/index.html')

# Parking Management Routes
@dashboard_bp.route('/parking/entry')
@token_required
def parking_entry():
    return render_template('dashboard/parking_entry.html')

@dashboard_bp.route('/parking/slots')
@token_required
def parking_slots():
    return render_template('dashboard/parking_slots.html')

@dashboard_bp.route('/parking/active')
@token_required
def active_sessions():
    return render_template('dashboard/active_sessions.html')

@dashboard_bp.route('/parking-sessions')
@token_required
def parking_sessions():
    return render_template('dashboard/parking_sessions.html')

# Membership Management Routes
@dashboard_bp.route('/members')
@token_required
def members():
    return render_template('dashboard/members.html')

@dashboard_bp.route('/members/cards')
@token_required
def member_cards():
    return render_template('dashboard/member_cards.html')

@dashboard_bp.route('/members/rates')
@token_required
def member_rates():
    return render_template('dashboard/member_rates.html')

# Staff Management Routes
@dashboard_bp.route('/staff')
@token_required
def staff():
    return render_template('dashboard/staff.html')

@dashboard_bp.route('/staff/attendance')
@token_required
def staff_attendance():
    return render_template('dashboard/staff_attendance.html')

@dashboard_bp.route('/staff/shifts')
@token_required
def shifts():
    return render_template('dashboard/shifts.html')

# Reports Routes
@dashboard_bp.route('/reports/financial')
@token_required
def financial_reports():
    return render_template('dashboard/financial_reports.html')

@dashboard_bp.route('/reports/usage')
@token_required
def usage_stats():
    return render_template('dashboard/usage_stats.html')

@dashboard_bp.route('/reports/activities')
@token_required
def activity_logs():
    return render_template('dashboard/activity_logs.html')

# Settings Routes
@dashboard_bp.route('/settings/rates')
@token_required
def parking_rates():
    return render_template('dashboard/parking_rates.html')

@dashboard_bp.route('/settings/hardware')
@token_required
def hardware():
    return render_template('dashboard/hardware.html')

@dashboard_bp.route('/settings/users')
@token_required
def users():
    return render_template('dashboard/users.html')

@dashboard_bp.route('/settings/system')
@token_required
def system_settings():
    return render_template('dashboard/system_settings.html')

@dashboard_bp.route('/profile')
@token_required
def profile():
    return render_template('dashboard/profile.html')

# API Routes for Dashboard Stats
@api_dashboard_bp.route('/stats/overview', methods=['GET'])
@token_required
def get_overview_stats(current_user):
    try:
        # Get total parking spaces
        total_spaces = ParkingSpaces.query.count()
        
        # Get occupied spaces
        occupied_spaces = ParkingTickets.query.filter_by(IsActive=True).count()
        
        # Get available spaces
        available_spaces = total_spaces - occupied_spaces
        
        # Get active sessions
        active_sessions = ParkingTickets.query.filter_by(IsActive=True).count()
        
        return jsonify({
            'success': True,
            'message': 'Overview stats retrieved successfully',
            'data': {
                'total_spaces': total_spaces,
                'occupied_spaces': occupied_spaces,
                'available_spaces': available_spaces,
                'active_sessions': active_sessions
            }
        })
    except Exception as e:
        logger.error(f'Error getting overview stats: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Error retrieving overview stats',
            'error': 'STATS_ERROR'
        }), 500

# API Routes for Activities
@api_activities_bp.route('', methods=['GET'])
@token_required
def get_activities_list(current_user):
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # Get activities with pagination
        activities = ActivityLog.query.order_by(ActivityLog.CreatedAt.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format activities
        formatted_activities = [{
            'id': activity.id,
            'action': activity.Action,
            'details': activity.Details,
            'status': activity.Status,
            'created_at': activity.CreatedAt.isoformat(),
            'user_id': activity.UserId
        } for activity in activities.items]
        
        return jsonify({
            'success': True,
            'message': 'Activities retrieved successfully',
            'data': {
                'activities': formatted_activities,
                'pagination': {
                    'page': activities.page,
                    'per_page': activities.per_page,
                    'total': activities.total,
                    'pages': activities.pages
                }
            }
        })
    except Exception as e:
        logger.error(f'Error getting activities: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Error retrieving activities',
            'error': 'ACTIVITIES_ERROR'
        }), 500

# API Routes for Parking Sessions
@api_dashboard_bp.route('/parking-sessions/active')
@limiter.limit("60 per minute")
@token_required
def get_active_sessions():
    try:
        active_sessions = ParkingTickets.query\
            .filter_by(Status='active')\
            .order_by(ParkingTickets.EntryTime.desc())\
            .all()
        
        return jsonify({
            'status': 'success',
            'data': [{
                'ticket_number': session.TicketNumber,
                'vehicle_plate': session.Vehicle.plate_number if session.Vehicle else 'Unknown',
                'entry_time': session.EntryTime.isoformat(),
                'duration': (datetime.utcnow() - session.EntryTime).total_seconds()
            } for session in active_sessions]
        })
    except Exception as e:
        current_app.logger.error(f"Active sessions error: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to get active sessions', 'code': 500}), 500

# API Routes for Daily Reports
@api_dashboard_bp.route('/reports/daily')
@limiter.limit("60 per minute")
@token_required
def get_daily_report():
    try:
        today = datetime.now().date()
        
        # Get daily transactions
        transactions = ParkingTransactions.query\
            .filter(func.date(ParkingTransactions.created_at) == today)\
            .all()
        
        total_revenue = sum(t.amount for t in transactions)
        
        return jsonify({
            'status': 'success',
            'data': {
                'date': today.isoformat(),
                'total_revenue': float(total_revenue),
                'transaction_count': len(transactions)
            }
        })
    except Exception as e:
        current_app.logger.error(f"Daily report error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

# API Routes for Vehicles
@api_vehicles_bp.route('')
@limiter.limit("60 per minute")
@token_required
def get_vehicles():
    try:
        vehicles = Vehicles.query.all()
        return jsonify({
            'status': 'success',
            'data': {
                'total': len(vehicles),
                'vehicles': [{
                    'id': vehicle.Id,
                    'plate_number': vehicle.plate_number,
                    'vehicle_type': vehicle.vehicle_type,
                    'is_parked': vehicle.IsParked
                } for vehicle in vehicles]
            }
        })
    except Exception as e:
        current_app.logger.error(f"Vehicles error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

# API Routes
@api_dashboard_bp.route('')
@limiter.limit("60 per minute")
@token_required
def get_dashboard():
    try:
        # Get overview statistics
        total_spaces = ParkingSpaces.query.count()
        occupied_spaces = ParkingSpaces.query.filter_by(IsOccupied=True).count()
        total_vehicles = Vehicles.query.count()
        active_sessions = ParkingTickets.query.filter_by(Status='active').count()
        
        # Get recent activities
        recent_activities = ActivityLog.query\
            .order_by(ActivityLog.CreatedAt.desc())\
            .limit(5)\
            .all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'overview': {
                    'total_spaces': total_spaces,
                    'occupied_spaces': occupied_spaces,
                    'total_vehicles': total_vehicles,
                    'active_sessions': active_sessions
                },
                'recent_activities': [{
                    'id': activity.id,
                    'action': activity.Action,
                    'details': activity.Details,
                    'created_at': activity.CreatedAt.isoformat(),
                    'status': activity.Status
                } for activity in recent_activities]
            }
        })
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

# Stats API
@api_stats_bp.route('', methods=['GET'])
@limiter.limit("120 per minute")
@token_required
def get_realtime_stats():
    try:
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        
        # Get hourly statistics
        hourly_entries = ParkingTickets.query\
            .filter(ParkingTickets.EntryTime >= hour_ago)\
            .count()
            
        hourly_exits = ParkingTickets.query\
            .filter(ParkingTickets.ExitTime >= hour_ago)\
            .count()
            
        hourly_revenue = db.session.query(func.sum(ParkingTransactions.amount))\
            .filter(ParkingTransactions.created_at >= hour_ago)\
            .scalar() or 0
        
        # Get space utilization
        total_spaces = ParkingSpaces.query.count()
        occupied_spaces = ParkingSpaces.query.filter(
            ParkingSpaces.Status != 'available'
        ).count()
        
        return jsonify({
            'status': 'success',
            'data': {
                'hourly': {
                    'entries': hourly_entries,
                    'exits': hourly_exits,
                    'revenue': float(hourly_revenue)
                },
                'spaces': {
                    'total': total_spaces,
                    'occupied': occupied_spaces,
                    'available': total_spaces - occupied_spaces
                }
            }
        })
    except Exception as e:
        current_app.logger.error(f"Stats error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

@api_vehicles_bp.route('/<vehicle_id>', methods=['GET'])
@limiter.limit("60 per minute")
@token_required
def get_vehicle_details(vehicle_id):
    try:
        vehicle = Vehicles.query.get_or_404(vehicle_id)
        
        # Get parking history
        parking_history = ParkingTickets.query\
            .filter_by(VehicleId=vehicle_id)\
            .order_by(ParkingTickets.EntryTime.desc())\
            .limit(10)\
            .all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'vehicle': {
                    'id': vehicle.Id,
                    'plate_number': vehicle.plate_number,
                    'vehicle_type': vehicle.vehicle_type,
                    'is_parked': vehicle.IsParked,
                    'entry_time': vehicle.EntryTime.isoformat() if vehicle.EntryTime else None,
                    'parking_history': [{
                        'ticket_number': ticket.TicketNumber,
                        'entry_time': ticket.EntryTime.isoformat(),
                        'exit_time': ticket.ExitTime.isoformat() if ticket.ExitTime else None,
                        'status': ticket.Status
                    } for ticket in parking_history]
                }
            }
        })
    except Exception as e:
        current_app.logger.error(f"Vehicle details error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

# API Routes for Parking Rates
@api_rates_bp.route('', methods=['GET'])
@limiter.limit("60 per minute")
@token_required
def get_parking_rates():
    try:
        rates = ParkingRate.query.all()
        return jsonify({
            'Status': 'success',
            'Data': {
                'Rates': [{
                    'Id': rate.Id,
                    'VehicleType': rate.VehicleType,
                    'DurationType': rate.DurationType,
                    'BaseDuration': rate.BaseDuration,
                    'BaseRate': float(rate.BaseRate),
                    'AdditionalRate': float(rate.AdditionalRate) if rate.AdditionalRate else None,
                    'MaxDailyRate': float(rate.MaxDailyRate) if rate.MaxDailyRate else None,
                    'IsActive': rate.IsActive,
                    'CreatedAt': rate.CreatedAt.isoformat() if rate.CreatedAt else None,
                    'UpdatedAt': rate.UpdatedAt.isoformat() if rate.UpdatedAt else None
                } for rate in rates]
            }
        })
    except Exception as e:
        current_app.logger.error(f"Parking rates error: {str(e)}")
        return jsonify({'Message': str(e), 'Error': 'InternalError', 'Code': 500}), 500

@api_rates_bp.route('/<rate_id>', methods=['GET'])
@limiter.limit("60 per minute")
@token_required
def get_parking_rate(rate_id):
    try:
        rate = ParkingRate.query.get_or_404(rate_id)
        return jsonify({
            'status': 'success',
            'data': {
                'rate': {
                    'id': rate.Id,
                    'vehicle_type': rate.VehicleType,
                    'duration_type': rate.DurationType,
                    'base_duration': rate.BaseDuration,
                    'base_rate': float(rate.BaseRate),
                    'additional_rate': float(rate.AdditionalRate) if rate.AdditionalRate else None,
                    'max_daily_rate': float(rate.MaxDailyRate) if rate.MaxDailyRate else None,
                    'is_active': rate.IsActive
                }
            }
        })
    except Exception as e:
        current_app.logger.error(f"Parking rate error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

@api_rates_bp.route('', methods=['POST'])
@limiter.limit("30 per minute")
@token_required
def create_parking_rate():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['VehicleType', 'DurationType', 'BaseDuration', 'BaseRate']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'Message': f'Missing required field: {field}',
                    'Error': 'ValidationError',
                    'Code': 400
                }), 400
        
        # Create new rate
        rate_data = {
            'VehicleType': data['VehicleType'],
            'DurationType': data['DurationType'],
            'BaseDuration': data['BaseDuration'],
            'BaseRate': data['BaseRate'],
            'AdditionalRate': data.get('AdditionalRate'),
            'MaxDailyRate': data.get('MaxDailyRate'),
            'IsActive': data.get('IsActive', True)
        }
        new_rate = ParkingRate(**rate_data)
        db.session.add(new_rate)
        db.session.commit()

        # Log activity
        activity_data = {
            'Action': 'CREATE_RATE',
            'Details': f'Created new parking rate for {new_rate.VehicleType}',
            'UserId': current_user.Id,
            'IpAddress': request.remote_addr,
            'IsRead': False,
            'Status': 'success'
        }
        activity = ActivityLog(**activity_data)
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            'Status': 'success',
            'Data': {
                'Rate': {
                    'Id': new_rate.Id,
                    'VehicleType': new_rate.VehicleType,
                    'DurationType': new_rate.DurationType,
                    'BaseDuration': new_rate.BaseDuration,
                    'BaseRate': float(new_rate.BaseRate),
                    'AdditionalRate': float(new_rate.AdditionalRate) if new_rate.AdditionalRate else None,
                    'MaxDailyRate': float(new_rate.MaxDailyRate) if new_rate.MaxDailyRate else None,
                    'IsActive': new_rate.IsActive,
                    'CreatedAt': new_rate.CreatedAt.isoformat() if new_rate.CreatedAt else None,
                    'UpdatedAt': new_rate.UpdatedAt.isoformat() if new_rate.UpdatedAt else None
                }
            }
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create parking rate error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

@api_rates_bp.route('/<rate_id>', methods=['PUT'])
@limiter.limit("30 per minute")
@token_required
def update_parking_rate(rate_id):
    try:
        rate = ParkingRate.query.get_or_404(rate_id)
        data = request.get_json()
        
        # Update fields
        rate.VehicleType = data['vehicle_type']
        rate.DurationType = data['duration_type']
        rate.BaseDuration = data['base_duration']
        rate.BaseRate = data['base_rate']
        rate.AdditionalRate = data.get('additional_rate')
        rate.MaxDailyRate = data.get('max_daily_rate')
        rate.IsActive = data.get('is_active', True)
        
        db.session.commit()
        
        # Log activity
        activity_data = {
            'Action': 'UPDATE_RATE',
            'Details': f'Updated parking rate for {data["vehicle_type"]}',
            'UserId': current_user.Id,
            'IpAddress': request.remote_addr,
            'IsRead': False
        }
        activity = ActivityLog(**activity_data)
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'data': {
                'rate': {
                    'id': rate.Id,
                    'vehicle_type': rate.VehicleType,
                    'duration_type': rate.DurationType,
                    'base_duration': rate.BaseDuration,
                    'base_rate': float(rate.BaseRate),
                    'additional_rate': float(rate.AdditionalRate) if rate.AdditionalRate else None,
                    'max_daily_rate': float(rate.MaxDailyRate) if rate.MaxDailyRate else None,
                    'is_active': rate.IsActive
                }
            }
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update parking rate error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

@api_rates_bp.route('/<rate_id>', methods=['DELETE'])
@limiter.limit("30 per minute")
@token_required
def delete_parking_rate(rate_id):
    try:
        rate = ParkingRate.query.get_or_404(rate_id)
        
        # Log activity before deletion
        activity_data = {
            'Action': 'DELETE_RATE',
            'Details': f'Deleted parking rate for {rate.VehicleType}',
            'UserId': current_user.Id,
            'IpAddress': request.remote_addr,
            'IsRead': False
        }
        activity = ActivityLog(**activity_data)
        
        db.session.delete(rate)
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Parking rate deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete parking rate error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

# New API endpoints for enhanced dashboard
@api_dashboard_bp.route('/health')
@limiter.limit("60 per minute")
@token_required
def get_system_health():
    try:
        # Get database health
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

        # Get server health
        server_health = {
            'status': 'healthy',
            'memory': 0.8,  # Example value
            'cpu': 0.3      # Example value
        }

        # Get hardware status
        hardware_status = HardwareStatus.query.first()
        hardware_health = {
            'gates': {
                'status': hardware_status.GateStatus if hardware_status else 'unknown',
                'details': []
            },
            'printers': {
                'status': hardware_status.PrinterStatus if hardware_status else 'unknown',
                'details': []
            }
        }

        return jsonify({
            'status': 'success',
            'data': {
                'status': 'healthy' if all([
                    db_health['status'] == 'healthy',
                    server_health['status'] == 'healthy',
                    hardware_health['gates']['status'] == 'online',
                    hardware_health['printers']['status'] == 'online'
                ]) else 'unhealthy',
                'components': {
                    'database': db_health,
                    'server': server_health,
                    'hardware': hardware_health
                }
            }
        })
    except Exception as e:
        current_app.logger.error(f"System health error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

@api_dashboard_bp.route('/notifications')
@limiter.limit("60 per minute")
@token_required
def get_notifications():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        read = request.args.get('read', None)
        
        query = ActivityLog.query
        if read is not None:
            query = query.filter_by(IsRead=read == 'true')
            
        notifications = query\
            .order_by(ActivityLog.CreatedAt.desc())\
            .paginate(page=page, per_page=per_page)
            
        unread_count = ActivityLog.query.filter_by(IsRead=False).count()
        
        return jsonify({
            'status': 'success',
            'data': {
                'notifications': [{
                    'id': notification.Id,
                    'type': notification.Action,
                    'message': notification.Details,
                    'read': notification.IsRead,
                    'timestamp': notification.CreatedAt.isoformat()
                } for notification in notifications.items],
                'unread_count': unread_count,
                'pagination': {
                    'total': notifications.total,
                    'pages': notifications.pages,
                    'current_page': notifications.page,
                    'per_page': notifications.per_page
                }
            }
        })
    except Exception as e:
        current_app.logger.error(f"Notifications error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

@api_dashboard_bp.route('/alerts')
@limiter.limit("60 per minute")
@token_required
def get_alerts():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        severity = request.args.get('severity', None)
        status = request.args.get('status', None)
        
        query = ActivityLog.query.filter(ActivityLog.Action.in_(['error', 'warning']))
        if severity:
            query = query.filter_by(Severity=severity)
        if status:
            query = query.filter_by(Status=status)
            
        alerts = query\
            .order_by(ActivityLog.CreatedAt.desc())\
            .paginate(page=page, per_page=per_page)
            
        active_count = ActivityLog.query\
            .filter(ActivityLog.Action.in_(['error', 'warning']))\
            .filter_by(Status='active')\
            .count()
        
        return jsonify({
            'status': 'success',
            'data': {
                'alerts': [{
                    'id': alert.id,
                    'severity': alert.Severity,
                    'type': alert.Action,
                    'message': alert.Details,
                    'status': alert.Status,
                    'timestamp': alert.CreatedAt.isoformat()
                } for alert in alerts.items],
                'total': alerts.total,
                'active_count': active_count
            }
        })
    except Exception as e:
        current_app.logger.error(f"Alerts error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

@api_dashboard_bp.route('/audit')
@limiter.limit("60 per minute")
@token_required
def get_audit_logs():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        user_id = request.args.get('user_id', None)
        action = request.args.get('action', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        
        query = ActivityLog.query
        if user_id:
            query = query.filter_by(UserId=user_id)
        if action:
            query = query.filter_by(Action=action)
        if start_date:
            query = query.filter(ActivityLog.CreatedAt >= start_date)
        if end_date:
            query = query.filter(ActivityLog.CreatedAt <= end_date)
            
        audit_logs = query\
            .order_by(ActivityLog.CreatedAt.desc())\
            .paginate(page=page, per_page=per_page)
        
        return jsonify({
            'status': 'success',
            'data': {
                'entries': [{
                    'id': log.id,
                    'user_id': log.UserId,
                    'username': log.UserName,
                    'action': log.Action,
                    'resource': log.Resource,
                    'resource_id': log.ResourceId,
                    'details': log.Details,
                    'timestamp': log.CreatedAt.isoformat(),
                    'ip_address': log.IpAddress
                } for log in audit_logs.items],
                'total': audit_logs.total
            }
        })
    except Exception as e:
        current_app.logger.error(f"Audit logs error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

@api_dashboard_bp.route('/activities')
@limiter.limit("60 per minute")
@token_required
def get_dashboard_activities():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5, type=int)
        
        activities = ActivityLog.query\
            .order_by(ActivityLog.CreatedAt.desc())\
            .paginate(page=page, per_page=per_page)
        
        return jsonify({
            'status': 'success',
            'data': {
                'activities': [{
                    'id': activity.id,
                    'action': activity.Action,
                    'details': activity.Details,
                    'status': activity.Status,
                    'created_at': activity.CreatedAt.isoformat()
                } for activity in activities.items],
                'pagination': {
                    'page': activities.page,
                    'pages': activities.pages,
                    'total': activities.total
                }
            }
        })
    except Exception as e:
        current_app.logger.error(f"Activities error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

@api_dashboard_bp.route('/parking-spaces/available')
@token_required
def get_available_spaces():
    try:
        spaces = ParkingSpaces.query.filter_by(IsOccupied=False).all()
        return jsonify({
            'status': 'success',
            'data': [{
                'id': space.Id,
                'number': space.SpaceNumber,
                'type': space.Type
            } for space in spaces]
        })
    except Exception as e:
        current_app.logger.error(f"Available spaces error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get available spaces',
            'code': 500
        }), 500

@api_dashboard_bp.route('/parking-sessions/recent')
@token_required
def get_recent_sessions():
    try:
        sessions = ParkingTickets.query.order_by(ParkingTickets.EntryTime.desc()).limit(10).all()
        return jsonify({
            'status': 'success',
            'data': [{
                'ticket_number': session.TicketNumber,
                'vehicle_plate': session.Vehicle.plate_number if session.Vehicle else 'Unknown',
                'entry_time': session.EntryTime.isoformat(),
                'exit_time': session.ExitTime.isoformat() if session.ExitTime else None,
                'duration': (session.ExitTime - session.EntryTime).total_seconds() if session.ExitTime else (datetime.utcnow() - session.EntryTime).total_seconds(),
                'amount': float(session.Amount) if session.Amount else 0,
                'status': 'completed' if session.ExitTime else 'active'
            } for session in sessions]
        })
    except Exception as e:
        current_app.logger.error(f"Recent sessions error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get recent sessions',
            'code': 500
        }), 500

@api_dashboard_bp.route('/parking-sessions', methods=['POST'])
@limiter.limit("60 per minute")
@token_required
def create_session(current_user):
    try:
        data = request.get_json()
        vehicle_id = data.get('vehicleId')
        parking_space_id = data.get('parkingSpaceId')

        # Validate required fields
        if not vehicle_id or not parking_space_id:
            return jsonify({
                'status': 'error',
                'message': 'Vehicle ID and parking space ID are required'
            }), 400

        # Check if vehicle exists and is not already parked
        vehicle = Vehicles.query.get(vehicle_id)
        if not vehicle:
            return jsonify({
                'status': 'error',
                'message': 'Vehicle not found'
            }), 404

        # Check if parking space exists and is not occupied
        space = ParkingSpaces.query.get(parking_space_id)
        if not space:
            return jsonify({
                'status': 'error',
                'message': 'Parking space not found'
            }), 404
        if space.IsOccupied:
            return jsonify({
                'status': 'error',
                'message': 'Parking space is already occupied'
            }), 400

        # Create new session using setattr
        session = ParkingTickets()
        setattr(session, 'TicketNumber', str(uuid.uuid4())[:8].upper())
        setattr(session, 'VehicleId', vehicle_id)
        setattr(session, 'SpaceId', parking_space_id)
        setattr(session, 'EntryTime', datetime.utcnow())
        setattr(session, 'Status', 'active')
        setattr(session, 'CreatedBy', current_user.Id)

        try:
            # Update parking space status
            space.IsOccupied = True
            
            db.session.add(session)
            db.session.commit()

            return jsonify({
                'status': 'success',
                'data': {
                    'ticket_number': session.TicketNumber,
                    'vehicle_id': session.VehicleId,
                    'space_id': session.SpaceId,
                    'entry_time': session.EntryTime.isoformat()
                },
                'message': 'Session created successfully'
            })
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating session: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to create session'
            }), 500

    except Exception as e:
        logger.error(f"Error in create_session: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@api_dashboard_bp.route('/parking-sessions/<ticket_number>/end', methods=['POST'])
@token_required
def end_session(ticket_number):
    try:
        session = ParkingTickets.query.filter_by(TicketNumber=ticket_number).first()
        if not session:
            return jsonify({
                'status': 'error',
                'message': 'Session not found',
                'code': 404
            }), 404
            
        if not session.IsActive:
            return jsonify({
                'status': 'error',
                'message': 'Session is already ended',
                'code': 400
            }), 400
            
        # Calculate duration and amount
        exit_time = datetime.utcnow()
        duration = exit_time - session.EntryTime
        hours = duration.total_seconds() / 3600
        
        # Get parking rate
        vehicle = Vehicles.query.get(session.VehicleId)
        if not vehicle:
            return jsonify({
                'status': 'error',
                'message': 'Vehicle not found',
                'code': 404
            }), 404
            
        rate = ParkingRate.query.filter_by(
            vehicle_type=vehicle.vehicle_type,
            is_active=True
        ).first()
        
        if not rate:
            # Use default rate if no specific rate found
            amount = 10000  # Default amount (e.g., 10,000 IDR)
        else:
            # Calculate amount
            base_fee = float(rate.BaseRate)
            additional_fee = float(rate.AdditionalRate) if rate.AdditionalRate else 0
            amount = base_fee + (max(0, hours - rate.BaseDuration) * additional_fee)
        
        # Update session
        session.ExitTime = exit_time
        session.IsActive = False
        session.Amount = amount
        
        # Update parking space
        space = ParkingSpaces.query.get(session.SpaceId)
        if space:
            space.IsOccupied = False
            
        # Update vehicle status
        if vehicle:
            vehicle.IsParked = False
            
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'data': {
                'ticket_number': session.TicketNumber,
                'exit_time': session.ExitTime.isoformat(),
                'duration': duration.total_seconds(),
                'amount': amount
            },
            'message': 'Session ended successfully'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"End session error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to end session',
            'code': 500
        }), 500

@api_dashboard_bp.route('/recent-vehicles', methods=['GET'])
@limiter.limit("60 per minute")
@token_required
def get_recent_vehicles():
    try:
        vehicles = Vehicles.query.order_by(Vehicles.created_at.desc()).limit(5).all()
        vehicle_list = []
        for vehicle in vehicles:
            if vehicle is not None:
                vehicle_list.append({
                    'id': vehicle.Id,
                    'plateNumber': vehicle.plate_number,
                    'vehicleType': vehicle.vehicle_type,
                    'status': vehicle.status,
                    'createdAt': vehicle.created_at.isoformat() if vehicle.created_at else None
                })
        return jsonify({'vehicles': vehicle_list}), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching recent vehicles: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_dashboard_bp.route('/recent-transactions', methods=['GET'])
@limiter.limit("60 per minute")
@token_required
def get_recent_transactions():
    try:
        transactions = ParkingTransactions.query.order_by(ParkingTransactions.created_at.desc()).limit(5).all()
        transaction_list = []
        for transaction in transactions:
            if transaction is not None:
                transaction_list.append({
                    'id': transaction.Id,
                    'ticketId': transaction.ticket_id,
                    'transactionNumber': transaction.transaction_number,
                    'amount': float(transaction.amount) if transaction.amount else 0.0,
                    'paymentMethod': transaction.payment_method,
                    'status': transaction.status,
                    'processedBy': transaction.processed_by,
                    'createdAt': transaction.created_at.isoformat() if transaction.created_at else None
                })
        return jsonify({'transactions': transaction_list}), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching recent transactions: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_dashboard_bp.route('/rate-settings', methods=['POST'])
@limiter.limit("60 per minute")
@token_required
def update_rate_settings(current_user):
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = {'vehicle_type', 'duration_type', 'base_duration', 'base_rate', 'additional_rate', 'max_daily_rate'}
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        # Validate duration type
        valid_duration_types = {'hourly', 'daily', 'monthly'}
        duration_type = data['duration_type'].lower()
        if duration_type not in valid_duration_types:
            return jsonify({'error': f'Invalid duration type. Must be one of: {", ".join(valid_duration_types)}'}), 400

        # Validate and convert numeric values
        try:
            base_duration = int(data['base_duration'])
            base_rate = float(data['base_rate'])
            additional_rate = float(data['additional_rate'])
            max_daily_rate = float(data['max_daily_rate'])
            
            if base_duration <= 0:
                return jsonify({'error': 'Base duration must be positive'}), 400
            if base_rate < 0:
                return jsonify({'error': 'Base rate cannot be negative'}), 400
            if additional_rate < 0:
                return jsonify({'error': 'Additional rate cannot be negative'}), 400
            if max_daily_rate < 0:
                return jsonify({'error': 'Max daily rate cannot be negative'}), 400
            if max_daily_rate < base_rate:
                return jsonify({'error': 'Max daily rate must be greater than or equal to base rate'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid numeric values provided'}), 400

        # Check for existing rate
        rate = ParkingRate.query.filter_by(
            vehicle_type=data['vehicle_type'],
            duration_type=duration_type
        ).first()

        # Update or create rate
        if rate:
            rate.BaseDuration = base_duration
            rate.BaseRate = base_rate
            rate.AdditionalRate = additional_rate
            rate.MaxDailyRate = max_daily_rate
            rate.IsActive = True
            action = 'Updated'
        else:
            rate_data = {
                'VehicleType': data['vehicle_type'],
                'DurationType': duration_type,
                'BaseDuration': base_duration,
                'BaseRate': base_rate,
                'AdditionalRate': additional_rate,
                'MaxDailyRate': max_daily_rate,
                'IsActive': True
            }
            rate = ParkingRate(**rate_data)
            db.session.add(rate)
            action = 'Created'

        # Log activity
        activity_data = {
            'Action': f'{action} Rate Setting',
            'Details': f"{action} rate setting for {data['vehicle_type']} - {duration_type}",
            'Status': 'success',
            'UserId': current_user.Id,
            'IpAddress': request.remote_addr,
            'IsRead': False
        }
        activity_log = ActivityLog(**activity_data)
        db.session.add(activity_log)

        # Commit transaction
        db.session.commit()
        return jsonify({
            'message': f'Rate settings {action.lower()} successfully',
            'rate': {
                'id': rate.Id,
                'vehicle_type': rate.VehicleType,
                'duration_type': rate.DurationType,
                'base_duration': rate.BaseDuration,
                'base_rate': float(rate.BaseRate),
                'additional_rate': float(rate.AdditionalRate),
                'max_daily_rate': float(rate.MaxDailyRate),
                'is_active': rate.IsActive,
                'createdAt': rate.CreatedAt.isoformat() if rate.CreatedAt else None,
                'updatedAt': rate.UpdatedAt.isoformat() if rate.UpdatedAt else None
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating rate settings: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_dashboard_bp.route('/rate-settings', methods=['GET'])
@limiter.limit("60 per minute")
@token_required
@cache.cached(timeout=300, query_string=True)
def get_rate_settings():
    """
    Retrieve active parking rate settings with filtering, sorting, pagination, and search.
    
    Query Parameters:
        - vehicle_type (str): Filter by vehicle type
        - duration_type (str): Filter by duration type
        - search (str): Search term for vehicle type or duration type (case-insensitive)
        - page (int): Page number (default: 1)
        - per_page (int): Items per page (default: 10)
        - sort_by (str): Field to sort by (default: 'created_at')
        - sort_order (str): Sort direction ('asc' or 'desc', default: 'asc')
    
    Returns:
        - rates: List of rate settings
        - pagination: {
            - total: Total number of rates
            - pages: Total number of pages
            - current_page: Current page number
            - per_page: Items per page
        }
    """
    try:
        # Get query parameters
        vehicle_type = request.args.get('vehicle_type')
        duration_type = request.args.get('duration_type')
        search = request.args.get('search')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'asc')
        
        # Log received parameters
        current_app.logger.info(
            f"Rate settings request - params: {dict(request.args)}"
        )
        
        # Validate sort parameters
        valid_sort_fields = {
            'vehicle_type': ParkingRate.VehicleType,
            'base_rate': ParkingRate.BaseRate,
            'created_at': ParkingRate.CreatedAt,
            'updated_at': ParkingRate.UpdatedAt
        }
        
        if sort_by not in valid_sort_fields:
            current_app.logger.warning(
                f"Invalid sort field requested: {sort_by}"
            )
            return jsonify({
                'error': f'Invalid sort field. Must be one of: {", ".join(valid_sort_fields.keys())}'
            }), 400
            
        if sort_order not in ['asc', 'desc']:
            current_app.logger.warning(
                f"Invalid sort order requested: {sort_order}"
            )
            return jsonify({
                'error': 'Invalid sort order. Must be either "asc" or "desc"'
            }), 400
        
        # Build base query
        query = ParkingRate.query.filter_by(IsActive=True)
        
        # Apply filters
        if vehicle_type:
            query = query.filter_by(VehicleType=vehicle_type)
        if duration_type:
            query = query.filter_by(DurationType=duration_type.lower())
        
        # Apply search if provided
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                db.or_(
                    ParkingRate.VehicleType.ilike(search_term),
                    ParkingRate.DurationType.ilike(search_term)
                )
            )
            current_app.logger.info(
                f"Applied search filter with term: {search}"
            )
        
        # Apply sorting
        sort_field = valid_sort_fields[sort_by]
        if sort_order == 'desc':
            sort_field = sort_field.desc()
        query = query.order_by(sort_field)
        
        # Apply pagination
        rates = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Log response details
        current_app.logger.info(
            f"Returning {len(rates.items)} rates (page {page} of {rates.pages})"
        )
        
        return jsonify({
            'rates': [{
                'id': rate.Id,
                'vehicle_type': rate.VehicleType,
                'duration_type': rate.DurationType,
                'base_duration': rate.BaseDuration,
                'base_rate': float(rate.BaseRate),
                'additional_rate': float(rate.AdditionalRate),
                'max_daily_rate': float(rate.MaxDailyRate),
                'is_active': rate.IsActive,
                'createdAt': rate.CreatedAt.isoformat() if rate.CreatedAt else None,
                'updatedAt': rate.UpdatedAt.isoformat() if rate.UpdatedAt else None
            } for rate in rates.items],
            'pagination': {
                'total': rates.total,
                'pages': rates.pages,
                'current_page': rates.page,
                'per_page': rates.per_page
            }
        }), 200
        
    except ValueError as e:
        current_app.logger.error(f"Validation error in get_rate_settings: {str(e)}")
        return jsonify({'error': 'Invalid parameter value'}), 400
    except Exception as e:
        current_app.logger.error(f"Error fetching rate settings: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_dashboard_bp.route('/rate-settings/<int:rate_id>', methods=['DELETE'])
@limiter.limit("60 per minute")
@token_required
def delete_rate_setting(current_user, rate_id):
    try:
        rate = ParkingRate.query.get_or_404(rate_id)
        
        if not rate.IsActive:
            return jsonify({'error': 'Rate setting is already inactive'}), 400
            
        rate.IsActive = False
        
        activity_data = {
            'Action': 'Delete Rate Setting',
            'Details': f"Deleted rate setting for {rate.VehicleType} - {rate.DurationType}",
            'Status': 'success',
            'UserId': current_user.Id,
            'IpAddress': request.remote_addr,
            'IsRead': False
        }
        activity_log = ActivityLog(**activity_data)
        db.session.add(activity_log)
        
        db.session.commit()
        return jsonify({'message': 'Rate setting deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting rate setting: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Register blueprints
def init_app(app):
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_dashboard_bp)
    app.register_blueprint(api_activities_bp)
    app.register_blueprint(api_stats_bp)

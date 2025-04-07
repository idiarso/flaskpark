from flask import Blueprint, jsonify, request, current_app, render_template
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from models import (
    db, AspNetUsers, AspNetUserRoles, SystemConfig, ParkingRate,
    ActivityLog, HardwareStatus, Vehicles, ParkingTickets,
    ParkingTransactions, ParkingSpaces, Members, MemberCards,
    MemberRates, Staff, StaffAttendance, Shifts
)
from routes import jwt_required, limiter

# Create blueprints
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
api_dashboard_bp = Blueprint('api_dashboard', __name__, url_prefix='/api/dashboard')
api_stats_bp = Blueprint('api_stats', __name__, url_prefix='/api/stats')
api_activities_bp = Blueprint('api_activities', __name__, url_prefix='/api/activities')
api_vehicles_bp = Blueprint('api_vehicles', __name__, url_prefix='/api/vehicles')
api_rates_bp = Blueprint('api_rates', __name__, url_prefix='/api/parking-rates')

# Dashboard Pages
@dashboard_bp.route('/')
@jwt_required
def index():
    return render_template('dashboard/index.html')

# Parking Management Routes
@dashboard_bp.route('/parking/entry')
@jwt_required
def parking_entry():
    return render_template('dashboard/parking_entry.html')

@dashboard_bp.route('/parking/slots')
@jwt_required
def parking_slots():
    return render_template('dashboard/parking_slots.html')

@dashboard_bp.route('/parking/active')
@jwt_required
def active_sessions():
    return render_template('dashboard/active_sessions.html')

# Membership Management Routes
@dashboard_bp.route('/members')
@jwt_required
def members():
    return render_template('dashboard/members.html')

@dashboard_bp.route('/members/cards')
@jwt_required
def member_cards():
    return render_template('dashboard/member_cards.html')

@dashboard_bp.route('/members/rates')
@jwt_required
def member_rates():
    return render_template('dashboard/member_rates.html')

# Staff Management Routes
@dashboard_bp.route('/staff')
@jwt_required
def staff():
    return render_template('dashboard/staff.html')

@dashboard_bp.route('/staff/attendance')
@jwt_required
def staff_attendance():
    return render_template('dashboard/staff_attendance.html')

@dashboard_bp.route('/staff/shifts')
@jwt_required
def shifts():
    return render_template('dashboard/shifts.html')

# Reports Routes
@dashboard_bp.route('/reports/financial')
@jwt_required
def financial_reports():
    return render_template('dashboard/financial_reports.html')

@dashboard_bp.route('/reports/usage')
@jwt_required
def usage_stats():
    return render_template('dashboard/usage_stats.html')

@dashboard_bp.route('/reports/activities')
@jwt_required
def activity_logs():
    return render_template('dashboard/activity_logs.html')

# Settings Routes
@dashboard_bp.route('/settings/rates')
@jwt_required
def parking_rates():
    return render_template('dashboard/parking_rates.html')

@dashboard_bp.route('/settings/hardware')
@jwt_required
def hardware():
    return render_template('dashboard/hardware.html')

@dashboard_bp.route('/settings/users')
@jwt_required
def users():
    return render_template('dashboard/users.html')

@dashboard_bp.route('/settings/system')
@jwt_required
def system_settings():
    return render_template('dashboard/system_settings.html')

@dashboard_bp.route('/profile')
@jwt_required
def profile():
    return render_template('dashboard/profile.html')

# API Routes for Dashboard Stats
@api_dashboard_bp.route('/stats/overview')
@limiter.limit("60 per minute")
@jwt_required
def get_overview_stats():
    try:
        # Get current stats
        active_sessions = ParkingTickets.query.filter_by(ExitTime=None).count()
        total_spaces = ParkingSpaces.query.count()
        available_spaces = ParkingSpaces.query.filter_by(IsOccupied=False).count()
        
        # Get today's revenue
        today = datetime.now().date()
        today_revenue = db.session.query(func.sum(ParkingTransactions.Amount))\
            .filter(func.date(ParkingTransactions.CreatedAt) == today)\
            .scalar() or 0
        
        return jsonify({
            'status': 'success',
            'data': {
                'active_sessions': active_sessions,
                'total_spaces': total_spaces,
                'available_spaces': available_spaces,
                'occupancy_rate': round((total_spaces - available_spaces) / total_spaces * 100 if total_spaces > 0 else 0, 2),
                'today_revenue': float(today_revenue)
            }
        })
    except Exception as e:
        current_app.logger.error(f"Dashboard stats error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

# API Routes for Activities
@api_activities_bp.route('')
@limiter.limit("60 per minute")
@jwt_required
def get_activities():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        activities = ActivityLog.query\
            .order_by(ActivityLog.CreatedAt.desc())\
            .paginate(page=page, per_page=per_page)
        
        return jsonify({
            'status': 'success',
            'data': {
                'activities': [{
                    'id': activity.Id,
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

# API Routes
@api_dashboard_bp.route('', methods=['GET'])
@limiter.limit("60 per minute")
@jwt_required
def get_dashboard_data():
    try:
        # Get current statistics
        active_sessions = ParkingTickets.query.filter_by(Status='active').count()
        total_vehicles = Vehicles.query.count()
        available_spaces = ParkingSpaces.query.filter_by(Status='available').count()
        
        # Get today's revenue
        today = datetime.utcnow().date()
        today_revenue = db.session.query(func.sum(ParkingTransactions.Amount))\
            .filter(func.date(ParkingTransactions.ProcessedAt) == today)\
            .scalar() or 0
        
        # Get hardware status
        hardware_status = HardwareStatus.query\
            .filter(HardwareStatus.LastPing >= datetime.utcnow() - timedelta(minutes=5))\
            .all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'active_sessions': active_sessions,
                'total_vehicles': total_vehicles,
                'available_spaces': available_spaces,
                'today_revenue': float(today_revenue),
                'hardware_status': [{
                    'device_type': h.DeviceType,
                    'device_id': h.DeviceId,
                    'status': h.Status,
                    'location': h.Location,
                    'last_ping': h.LastPing.isoformat() if h.LastPing else None
                } for h in hardware_status]
            }
        })
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

# Stats API
@api_stats_bp.route('', methods=['GET'])
@limiter.limit("120 per minute")
@jwt_required
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
            
        hourly_revenue = db.session.query(func.sum(ParkingTransactions.Amount))\
            .filter(ParkingTransactions.ProcessedAt >= hour_ago)\
            .scalar() or 0
        
        # Get space utilization
        total_spaces = ParkingSpaces.query.count()
        occupied_spaces = ParkingSpaces.query.filter(
            ParkingSpaces.Status != 'available'
        ).count()
        
        return jsonify({
            'status': 'success',
            'data': {
                'hourly_stats': {
                    'entries': hourly_entries,
                    'exits': hourly_exits,
                    'revenue': float(hourly_revenue)
                },
                'space_utilization': {
                    'total': total_spaces,
                    'occupied': occupied_spaces,
                    'available': total_spaces - occupied_spaces,
                    'utilization_rate': (occupied_spaces / total_spaces * 100) if total_spaces > 0 else 0
                }
            }
        })
    except Exception as e:
        current_app.logger.error(f"Stats error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

# Activities API
@api_activities_bp.route('', methods=['GET'])
@limiter.limit("60 per minute")
@jwt_required
def get_recent_activities():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        activities = ActivityLog.query\
            .order_by(ActivityLog.CreatedAt.desc())\
            .paginate(page=page, per_page=per_page)
        
        return jsonify({
            'status': 'success',
            'data': {
                'activities': [{
                    'id': activity.Id,
                    'action': activity.Action,
                    'details': activity.Details,
                    'created_at': activity.CreatedAt.isoformat(),
                    'status': activity.Status
                } for activity in activities.items],
                'pagination': {
                    'total': activities.total,
                    'pages': activities.pages,
                    'current_page': activities.page,
                    'per_page': activities.per_page
                }
            }
        })
    except Exception as e:
        current_app.logger.error(f"Activities error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

# Vehicles API
@api_vehicles_bp.route('', methods=['GET'])
@limiter.limit("60 per minute")
@jwt_required
def get_vehicles():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        
        query = Vehicles.query
        if status:
            query = query.filter_by(IsParked=(status == 'parked'))
        
        vehicles = query.paginate(page=page, per_page=per_page)
        
        return jsonify({
            'status': 'success',
            'data': {
                'vehicles': [{
                    'id': vehicle.Id,
                    'plate_number': vehicle.PlateNumber,
                    'vehicle_type': vehicle.VehicleType,
                    'is_parked': vehicle.IsParked,
                    'entry_time': vehicle.EntryTime.isoformat() if vehicle.EntryTime else None
                } for vehicle in vehicles.items],
                'pagination': {
                    'total': vehicles.total,
                    'pages': vehicles.pages,
                    'current_page': vehicles.page,
                    'per_page': vehicles.per_page
                }
            }
        })
    except Exception as e:
        current_app.logger.error(f"Vehicles error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

@api_vehicles_bp.route('/<vehicle_id>', methods=['GET'])
@limiter.limit("60 per minute")
@jwt_required
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
                    'plate_number': vehicle.PlateNumber,
                    'vehicle_type': vehicle.VehicleType,
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
@jwt_required
def get_parking_rates():
    try:
        rates = ParkingRate.query.all()
        return jsonify({
            'status': 'success',
            'data': {
                'rates': [{
                    'id': rate.Id,
                    'vehicle_type': rate.VehicleType,
                    'duration_type': rate.DurationType,
                    'base_duration': rate.BaseDuration,
                    'base_rate': float(rate.BaseRate),
                    'additional_rate': float(rate.AdditionalRate) if rate.AdditionalRate else None,
                    'max_daily_rate': float(rate.MaxDailyRate) if rate.MaxDailyRate else None,
                    'is_active': rate.IsActive
                } for rate in rates]
            }
        })
    except Exception as e:
        current_app.logger.error(f"Parking rates error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

@api_rates_bp.route('/<rate_id>', methods=['GET'])
@limiter.limit("60 per minute")
@jwt_required
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
@jwt_required
def create_parking_rate():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['vehicle_type', 'duration_type', 'base_duration', 'base_rate']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'message': f'Missing required field: {field}',
                    'error': 'ValidationError',
                    'code': 400
                }), 400
        
        # Create new rate
        rate = ParkingRate(
            VehicleType=data['vehicle_type'],
            DurationType=data['duration_type'],
            BaseDuration=data['base_duration'],
            BaseRate=data['base_rate'],
            AdditionalRate=data.get('additional_rate'),
            MaxDailyRate=data.get('max_daily_rate'),
            IsActive=data.get('is_active', True)
        )
        
        db.session.add(rate)
        db.session.commit()
        
        # Log activity
        activity = ActivityLog(
            Action='create_parking_rate',
            Details=f"Created {data['duration_type']} rate for {data['vehicle_type']}",
            Status='success'
        )
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
        current_app.logger.error(f"Create parking rate error: {str(e)}")
        return jsonify({'message': str(e), 'error': 'InternalError', 'code': 500}), 500

@api_rates_bp.route('/<rate_id>', methods=['PUT'])
@limiter.limit("30 per minute")
@jwt_required
def update_parking_rate(rate_id):
    try:
        rate = ParkingRate.query.get_or_404(rate_id)
        data = request.get_json()
        
        # Update fields
        rate.VehicleType = data.get('vehicle_type', rate.VehicleType)
        rate.DurationType = data.get('duration_type', rate.DurationType)
        rate.BaseDuration = data.get('base_duration', rate.BaseDuration)
        rate.BaseRate = data.get('base_rate', rate.BaseRate)
        rate.AdditionalRate = data.get('additional_rate', rate.AdditionalRate)
        rate.MaxDailyRate = data.get('max_daily_rate', rate.MaxDailyRate)
        rate.IsActive = data.get('is_active', rate.IsActive)
        
        db.session.commit()
        
        # Log activity
        activity = ActivityLog(
            Action='update_parking_rate',
            Details=f"Updated {rate.DurationType} rate for {rate.VehicleType}",
            Status='success'
        )
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
@jwt_required
def delete_parking_rate(rate_id):
    try:
        rate = ParkingRate.query.get_or_404(rate_id)
        
        # Log activity before deletion
        activity = ActivityLog(
            Action='delete_parking_rate',
            Details=f"Deleted {rate.DurationType} rate for {rate.VehicleType}",
            Status='success'
        )
        
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

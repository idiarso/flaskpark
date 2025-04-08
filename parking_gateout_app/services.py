from datetime import datetime, timedelta
import uuid
from typing import Dict, Optional, Tuple, Any, List

from .models import ParkingTickets, ParkingTransactions, ParkingRate, ActivityLog, db

class ParkingService:
    @staticmethod
    def calculate_parking_fee(entry_time: datetime, exit_time: datetime, vehicle_type: str) -> float:
        """
        Calculate parking fee based on duration and vehicle type
        
        Args:
            entry_time: When the vehicle entered
            exit_time: When the vehicle is exiting
            vehicle_type: The type of vehicle
            
        Returns:
            float: The calculated parking fee
        """
        # Get the rate for this vehicle type
        rate = ParkingRate.query.filter_by(VehicleType=vehicle_type).first()
        if not rate:
            # Default rate if not found
            base_rate = 5.0
            hourly_rate = 2.0
        else:
            base_rate = float(rate.BaseRate)
            hourly_rate = float(rate.AdditionalRate or 2.0)
        
        # Calculate duration in hours
        duration = exit_time - entry_time
        hours = duration.total_seconds() / 3600
        
        # Calculate fee (base rate + hourly rate * hours)
        # First hour is covered by base rate
        if hours <= 1:
            fee = base_rate
        else:
            additional_hours = hours - 1
            fee = base_rate + (hourly_rate * additional_hours)
            
        return round(fee, 2)
    
    @staticmethod
    def get_active_ticket(ticket_id: Optional[str] = None, plate_number: Optional[str] = None) -> Optional[ParkingTickets]:
        """
        Get an active parking ticket by ID or plate number
        
        Args:
            ticket_id: The ticket ID
            plate_number: The vehicle plate number
            
        Returns:
            ParkingTickets or None: The active ticket if found
        """
        query = ParkingTickets.query.filter_by(Status='active')
        
        if ticket_id:
            return query.filter_by(TicketNumber=ticket_id).first()
        
        if plate_number:
            return query.filter(ParkingTickets.VehicleId.has(plate_number=plate_number)).first()
            
        return None
    
    @staticmethod
    def create_transaction(ticket: ParkingTickets, amount: float) -> ParkingTransactions:
        """
        Create a new parking transaction
        
        Args:
            ticket: The parking ticket
            amount: The transaction amount
            
        Returns:
            ParkingTransactions: The newly created transaction
        """
        transaction_data = {
            'Id': str(uuid.uuid4()),
            'ticket_id': str(ticket.Id),
            'transaction_number': f"TX-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'amount': amount,
            'payment_method': 'cash',  # Default method
            'status': 'completed'
        }
        
        transaction = ParkingTransactions(**transaction_data)
        db.session.add(transaction)
        db.session.commit()
        
        return transaction
    
    @staticmethod
    def log_activity(action: str, details: str, status: str = 'success') -> ActivityLog:
        """
        Log system activity
        
        Args:
            action: The action performed
            details: Details about the action
            status: Status of the action
            
        Returns:
            ActivityLog: The created log entry
        """
        activity_data = {
            'Action': action,
            'Details': details,
            'Status': status,
            'CreatedAt': datetime.now()
        }
        
        activity = ActivityLog(**activity_data)
        db.session.add(activity)
        db.session.commit()
        
        return activity
    
    @staticmethod
    def get_parking_statistics(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get parking statistics for a date range
        
        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            dict: Statistics including total vehicles, revenue, etc.
        """
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now()
            
        # Get completed transactions
        transactions = ParkingTransactions.query.filter(
            ParkingTransactions.created_at.between(start_date, end_date),
            ParkingTransactions.status == 'completed'
        ).all()
        
        # Calculate statistics
        total_revenue = sum(float(t.amount) for t in transactions)
        total_vehicles = len(transactions)
        
        # Get statistics by vehicle type
        vehicle_stats = {}
        tickets = ParkingTickets.query.filter(
            ParkingTickets.ExitTime.between(start_date, end_date),
            ParkingTickets.Status == 'completed'
        ).all()
        
        for ticket in tickets:
            # Use the related vehicle to get vehicle_type
            vehicle_type = ticket.VehicleId.vehicle_type if ticket.VehicleId else "Unknown"
            if vehicle_type not in vehicle_stats:
                vehicle_stats[vehicle_type] = {
                    'count': 0,
                    'revenue': 0
                }
            
            vehicle_stats[vehicle_type]['count'] += 1
            vehicle_trans = next((t for t in transactions if t.ticket_id == str(ticket.Id)), None)
            if vehicle_trans:
                vehicle_stats[vehicle_type]['revenue'] += float(vehicle_trans.amount)
                
        return {
            'total_vehicles': total_vehicles,
            'total_revenue': total_revenue,
            'vehicle_stats': vehicle_stats,
            'start_date': start_date,
            'end_date': end_date
        } 
        
    @staticmethod
    def validate_ticket(ticket_number: str) -> Tuple[bool, Optional[ParkingTickets], str]:
        """
        Validate a parking ticket for exit
        
        Args:
            ticket_number: The ticket number to validate
            
        Returns:
            Tuple: (is_valid, ticket_object, message)
        """
        ticket = ParkingTickets.query.filter_by(TicketNumber=ticket_number).first()
        
        if not ticket:
            return False, None, "Ticket not found"
            
        if ticket.Status != 'active':
            return False, ticket, f"Invalid ticket status: {ticket.Status}"
            
        if ticket.ExitTime:
            return False, ticket, "Ticket has already been used for exit"
            
        return True, ticket, "Ticket is valid"
        
    @staticmethod
    def process_vehicle_exit(ticket_number: str, payment_method: str = 'cash') -> Dict[str, Any]:
        """
        Process a vehicle exit using a ticket
        
        Args:
            ticket_number: The ticket number
            payment_method: Payment method used (cash, card, etc)
            
        Returns:
            Dict: Result of the exit operation
        """
        is_valid, ticket, message = ParkingService.validate_ticket(ticket_number)
        
        if not is_valid:
            ParkingService.log_activity(
                action="VEHICLE_EXIT_FAILED",
                details=f"Failed exit attempt: {message} for ticket {ticket_number}",
                status="failed"
            )
            ticket_dict = None
            if ticket:
                ticket_dict = {
                    'id': ticket.Id,
                    'ticket_number': ticket.TicketNumber,
                    'status': ticket.Status
                }
            return {
                'success': False,
                'message': message,
                'ticket': ticket_dict
            }
            
        # Calculate parking fee
        exit_time = datetime.now()
        vehicle_type = "Standard"
        if ticket and ticket.VehicleId:
            # Get the vehicle type from the related Vehicle object
            from .models import Vehicles
            vehicle = Vehicles.query.get(ticket.VehicleId)
            if vehicle:
                vehicle_type = vehicle.vehicle_type
        
        if ticket:  # Add null check before accessing ticket attributes
            fee = ParkingService.calculate_parking_fee(
                ticket.EntryTime, 
                exit_time, 
                vehicle_type
            )
            
            # Update ticket
            ticket.ExitTime = exit_time
            ticket.Status = 'completed'
            ticket.Amount = fee
            
            # Create transaction
            transaction = ParkingService.create_transaction(ticket, fee)
            transaction.payment_method = payment_method
            
            # Save changes
            db.session.commit()
            
            # Log activity
            ParkingService.log_activity(
                action="VEHICLE_EXIT",
                details=f"Vehicle exit processed: {ticket.TicketNumber}, Fee: {fee}",
                status="success"
            )
            
            ticket_dict = {
                'id': ticket.Id,
                'ticket_number': ticket.TicketNumber,
                'entry_time': ticket.EntryTime,
                'exit_time': ticket.ExitTime,
                'status': ticket.Status,
                'fee': ticket.Amount
            }
            
            transaction_dict = {
                'id': transaction.Id,
                'amount': transaction.amount,
                'payment_method': transaction.payment_method,
                'timestamp': transaction.created_at
            }
            
            return {
                'success': True,
                'message': "Exit processed successfully",
                'ticket': ticket_dict,
                'fee': fee,
                'transaction': transaction_dict
            }
        
        return {
            'success': False,
            'message': "Failed to process exit: Invalid ticket",
            'ticket': None
        }
        
    @staticmethod
    def search_tickets(search_term: str, limit: int = 10) -> List[ParkingTickets]:
        """
        Search for parking tickets by ticket number or license plate
        
        Args:
            search_term: Search term (ticket number or plate)
            limit: Maximum results to return
            
        Returns:
            List[ParkingTickets]: Matching tickets
        """
        search_term = search_term.strip().upper()
        
        # Search by ticket number
        tickets = ParkingTickets.query.filter(
            ParkingTickets.TicketNumber.like(f"%{search_term}%")
        ).limit(limit).all()
        
        # If no results, try by license plate
        if not tickets:
            from .models import Vehicles
            vehicles = Vehicles.query.filter(
                Vehicles.plate_number.like(f"%{search_term}%")
            ).all()
            
            if vehicles:
                vehicle_ids = [v.Id for v in vehicles]
                tickets = ParkingTickets.query.filter(
                    ParkingTickets.VehicleId.in_(vehicle_ids)
                ).limit(limit).all()
                
        return tickets
        
    @staticmethod
    def get_daily_report(report_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate a daily report of parking operations
        
        Args:
            report_date: The date for the report (defaults to today)
            
        Returns:
            Dict: Report data
        """
        if not report_date:
            report_date = datetime.now()
            
        start_date = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1) - timedelta(microseconds=1)
        
        # Get basic statistics
        stats = ParkingService.get_parking_statistics(start_date, end_date)
        
        # Get hourly breakdown
        hourly_data = {}
        for hour in range(24):
            hour_start = start_date + timedelta(hours=hour)
            hour_end = hour_start + timedelta(hours=1) - timedelta(microseconds=1)
            
            tickets = ParkingTickets.query.filter(
                ParkingTickets.EntryTime.between(hour_start, hour_end)
            ).all()
            
            hourly_data[hour] = len(tickets)
            
        # Get peak hour
        peak_hour = None
        if hourly_data:
            peak_hour = max(hourly_data.items(), key=lambda x: x[1])[0]
        
        # Add activity logs
        activity_logs = ActivityLog.query.filter(
            ActivityLog.CreatedAt.between(start_date, end_date)
        ).all()
        
        # Count issues/errors
        issues = [log for log in activity_logs if log.Status == 'failed']
        
        return {
            **stats,
            'hourly_breakdown': hourly_data,
            'peak_hour': peak_hour,
            'activity_count': len(activity_logs),
            'issue_count': len(issues),
            'report_date': report_date.strftime('%Y-%m-%d')
        } 
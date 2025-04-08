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
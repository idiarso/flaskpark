import random
import string
from datetime import datetime, timedelta
import qrcode
from io import BytesIO
import base64
from typing import Optional, Dict, Any, Tuple


def generate_ticket_number() -> str:
    """
    Generate a unique ticket number for new parking tickets
    
    Returns:
        str: A unique ticket number (e.g., 'TKT-20230415-ABCD')
    """
    date_part = datetime.now().strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"TKT-{date_part}-{random_part}"


def generate_qr_code(data: str) -> str:
    """
    Generate a QR code as a base64 encoded image
    
    Args:
        data: The data to encode in the QR code
        
    Returns:
        str: Base64 encoded QR code image
    """
    qr = qrcode.make(data)
    
    # Convert to base64
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def format_currency(amount: float) -> str:
    """
    Format a number as currency
    
    Args:
        amount: The amount to format
        
    Returns:
        str: Formatted currency string
    """
    return f"${amount:.2f}"


def calculate_duration(start_time: datetime, end_time: datetime) -> str:
    """
    Calculate and format the duration between two datetime objects
    
    Args:
        start_time: The start time
        end_time: The end time
        
    Returns:
        str: Formatted duration string (e.g., "2 hours 30 minutes")
    """
    duration = end_time - start_time
    total_seconds = int(duration.total_seconds())
    
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
    else:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"


def validate_license_plate(plate_number: str) -> bool:
    """
    Validate the format of a license plate number
    
    Args:
        plate_number: The license plate to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Basic validation - can be customized based on regional formats
    if not plate_number or len(plate_number) < 3 or len(plate_number) > 10:
        return False
    
    # Remove spaces for validation
    plate_number = plate_number.replace(" ", "")
    
    # Check that it contains at least one letter and one number
    has_letter = any(c.isalpha() for c in plate_number)
    has_digit = any(c.isdigit() for c in plate_number)
    
    return has_letter and has_digit


def parse_datetime(date_str: Optional[str], format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """
    Parse a string into a datetime object
    
    Args:
        date_str: The date string to parse
        format_str: The format string (default: "%Y-%m-%d %H:%M:%S")
        
    Returns:
        datetime or None: The parsed datetime or None if parsing fails
    """
    if not date_str:
        return None
        
    try:
        return datetime.strptime(date_str, format_str)
    except ValueError:
        return None


def get_date_range(period: str) -> Tuple[datetime, datetime]:
    """
    Get the start and end dates based on a specified time period
    
    Args:
        period: The time period ('today', 'week', 'month', 'year')
        
    Returns:
        tuple: (start_date, end_date)
    """
    now = datetime.now()
    end_date = now
    
    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        # Start of the current week (Monday)
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'month':
        # Start of the current month
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'year':
        # Start of the current year
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        # Default to today
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
    return start_date, end_date 


def format_timestamp(dt: Optional[datetime]) -> str:
    """
    Format a datetime object as a human-readable timestamp
    
    Args:
        dt: The datetime to format
        
    Returns:
        str: Formatted timestamp string or empty string if None
    """
    if not dt:
        return ""
    return dt.strftime("%b %d, %Y %I:%M %p")


def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent security issues
    
    Args:
        text: The text to sanitize
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Remove potentially dangerous characters
    sanitized = ''.join(c for c in text if c.isalnum() or c in ' -_.,')
    return sanitized.strip()


def generate_transaction_id() -> str:
    """
    Generate a unique transaction ID
    
    Returns:
        str: A unique transaction ID
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"TRX-{timestamp}-{random_part}"


def calculate_overstay_fee(exit_time: datetime, expected_exit_time: datetime, hourly_rate: float) -> float:
    """
    Calculate overstay fee if a vehicle stays beyond expected time
    
    Args:
        exit_time: The actual exit time
        expected_exit_time: The expected exit time
        hourly_rate: The hourly rate for overstay
        
    Returns:
        float: The calculated overstay fee
    """
    if exit_time <= expected_exit_time:
        return 0.0
    
    # Calculate hours overstayed
    overstay_duration = exit_time - expected_exit_time
    overstay_hours = overstay_duration.total_seconds() / 3600
    
    # Round up to nearest hour
    overstay_hours = int(overstay_hours) + (1 if overstay_hours % 1 > 0 else 0)
    
    return round(overstay_hours * hourly_rate, 2)


def is_business_hours() -> bool:
    """
    Check if current time is within business hours (8 AM to 8 PM)
    
    Returns:
        bool: True if within business hours, False otherwise
    """
    now = datetime.now()
    hour = now.hour
    
    # Check if between 8 AM and 8 PM (20:00)
    return 8 <= hour < 20


def get_day_name(date: datetime) -> str:
    """
    Get the name of the day for a given date
    
    Args:
        date: The date to get the day name for
        
    Returns:
        str: The name of the day (e.g., 'Monday')
    """
    return date.strftime("%A")


def truncate_string(text: str, max_length: int = 50) -> str:
    """
    Truncate a string to the specified length and add ellipsis if needed
    
    Args:
        text: The text to truncate
        max_length: Maximum length of the string
        
    Returns:
        str: Truncated string
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..." 
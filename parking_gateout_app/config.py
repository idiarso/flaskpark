import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    PORT = int(os.getenv('PORT', '3001'))
    
    # Database configuration - use SQLite for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///parking.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Parking configuration
    PARKING_RATES = {
        'MOTOR': float(os.getenv('PARKING_RATE_MOTOR', '2000')),
        'MOBIL': float(os.getenv('PARKING_RATE_MOBIL', '5000')),
        'TRUK': float(os.getenv('PARKING_RATE_TRUK', '10000')),
        'BUS': float(os.getenv('PARKING_RATE_BUS', '15000'))
    }
    MAX_PARKING_HOURS = int(os.getenv('MAX_PARKING_HOURS', '24'))
    
    # API Configuration
    RATE_LIMIT = '100 per minute'
    REQUEST_TIMEOUT = 30  # seconds

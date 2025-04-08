import os
import logging
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # SQLite configuration
    basedir = os.getenv('basedir', os.path.abspath(os.path.dirname(__file__)))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'parking.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = int(os.getenv('SESSION_LIFETIME', '3600'))  # 1 hour
    
    # JWT configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Parking configuration
    DEFAULT_HOURLY_RATE = float(os.getenv('DEFAULT_HOURLY_RATE', '5000'))  # Default rate in IDR
    
    # Parking configuration
    PARKING_RATES = {
        'MOTOR': float(os.getenv('PARKING_RATE_MOTOR', '2000')),
        'MOBIL': float(os.getenv('PARKING_RATE_MOBIL', '5000')),
        'TRUK': float(os.getenv('PARKING_RATE_TRUK', '10000')),
        'BUS': float(os.getenv('PARKING_RATE_BUS', '15000'))
    }
    MAX_PARKING_HOURS = int(os.getenv('MAX_PARKING_HOURS', '24'))
    
    # API Configuration
    RATE_LIMIT = os.getenv('RATE_LIMIT', '100 per minute')
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))  # seconds
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.path.join(basedir, 'logs', 'app.log')
    
    # Error tracking configuration
    PROPAGATE_EXCEPTIONS = True
    ERROR_INCLUDE_MESSAGE = True
    
    @staticmethod
    def init_logging():
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(Config.LOG_FILE)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format=Config.LOG_FORMAT,
            handlers=[
                logging.FileHandler(Config.LOG_FILE),
                logging.StreamHandler()
            ]
        )

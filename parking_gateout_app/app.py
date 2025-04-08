from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from datetime import timedelta

# Initialize extensions
db = SQLAlchemy()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('parking_gateout_app.config.Config')
    
    # Initialize extensions with app
    db.init_app(app)
    CORS(app)
    limiter.init_app(app)
    
    with app.app_context():
        # Import blueprints here to avoid circular imports
        from parking_gateout_app.routes import (
            auth_bp, parking_bp, payment_bp, management_bp,
            report_bp, main_bp, health_bp
        )
        from parking_gateout_app.dashboard_routes import (
            dashboard_bp, api_dashboard_bp, api_stats_bp,
            api_activities_bp, api_vehicles_bp, api_rates_bp
        )
        
        # Register blueprints from dashboard_routes.py first
        app.register_blueprint(dashboard_bp, name='dashboard')
        app.register_blueprint(api_dashboard_bp, name='api_dashboard')
        app.register_blueprint(api_stats_bp, name='api_stats')
        app.register_blueprint(api_activities_bp, name='api_activities')
        app.register_blueprint(api_vehicles_bp, name='api_vehicles')
        app.register_blueprint(api_rates_bp, name='api_rates')
        
        # Register blueprints from routes.py
        app.register_blueprint(auth_bp, name='auth_api')
        app.register_blueprint(parking_bp, name='parking_api')
        app.register_blueprint(payment_bp, name='payment_api')
        app.register_blueprint(management_bp, name='management_api')
        app.register_blueprint(report_bp, name='report_api')
        app.register_blueprint(main_bp, name='main_api')
        app.register_blueprint(health_bp, name='health_api')
        
        # Create database tables
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)

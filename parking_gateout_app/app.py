from flask import Flask, render_template, request, jsonify
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import db, AspNetUsers
from routes import auth_bp, parking_bp, payment_bp, management_bp, report_bp, limiter
from dashboard_routes import (
    dashboard_bp, api_dashboard_bp, api_stats_bp,
    api_activities_bp, api_vehicles_bp
)
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Initialize rate limiter
    limiter.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return AspNetUsers.query.get(user_id)
    
    @login_manager.unauthorized_handler
    def unauthorized():
        if request.blueprint and request.blueprint.startswith('api'):
            return jsonify({
                'message': 'Unauthorized',
                'error': 'AuthenticationRequired',
                'code': 401
            }), 401
        return 'Unauthorized', 401
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(parking_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(management_bp)
    app.register_blueprint(report_bp)
    
    # Register dashboard blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_dashboard_bp)
    app.register_blueprint(api_stats_bp)
    app.register_blueprint(api_activities_bp)
    app.register_blueprint(api_vehicles_bp)
    
    # Basic route for home page
    @app.route('/')
    def index():
        return render_template('dashboard/index.html')
    
    # Global error handler for consistent error responses
    @app.errorhandler(Exception)
    def handle_error(error):
        return {
            'message': str(error),
            'error': error.__class__.__name__,
            'code': getattr(error, 'code', 500)
        }, getattr(error, 'code', 500)
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = app.config.get('PORT', 3001)  # Get port from config, default to 3001
    app.run(host='0.0.0.0', port=port, debug=True)

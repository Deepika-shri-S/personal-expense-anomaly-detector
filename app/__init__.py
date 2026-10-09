import os
from flask import Flask, jsonify
from config import config_by_name
from app.extensions import db, cors
from app.routes import register_routes
from app.services.bill_scheduler import init_bill_scheduler


def create_app(config_name: str = "default") -> Flask:
    """
    Application factory pattern initializing database, CORS, route blueprints,
    and background bill reminder scheduler.
    """
    app = Flask(__name__)

    # Select configuration
    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # Create tables automatically if they do not exist
    with app.app_context():
        from app.models import User, SpendingProfile, Transaction, Bill, Alert  # noqa: F401
        db.create_all()

    # Register API routes
    register_routes(app)

    # Global JSON error handlers so frontend always receives structured JSON
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "details": str(error)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found", "details": str(error)}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed", "details": str(error)}), 405

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({"error": "Internal server error", "details": "An unexpected error occurred."}), 500

    # Start APScheduler for recurring bill due reminders if enabled
    if not app.config.get("TESTING", False):
        init_bill_scheduler(app)

    return app

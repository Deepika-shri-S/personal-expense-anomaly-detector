from flask import Flask

from app.routes.auth import auth_bp
from app.routes.health import health_bp
from app.routes.profiles import profiles_bp
from app.routes.transactions import transactions_bp
from app.routes.anomalies import anomalies_bp
from app.routes.analytics import analytics_bp
from app.routes.bills import bills_bp
from app.routes.alerts import alerts_bp
from app.routes.chatbot import chatbot_bp
from app.routes.import_data import import_bp


def register_routes(app: Flask) -> None:
    """Register all API route blueprints with the Flask application."""
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profiles_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(anomalies_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(bills_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(import_bp)

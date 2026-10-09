from datetime import datetime, timezone
from flask import Blueprint, jsonify, current_app
from app.extensions import db, scheduler

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.route("/health", methods=["GET"])
def health_check():
    """System health check endpoint verifying database connectivity and services."""
    db_status = "healthy"
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return jsonify({
        "status": "online",
        "service": "Personal Expense Anomaly Detector API",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "scheduler_running": scheduler.running if scheduler else False,
        "environment": current_app.config.get("ENV", "development"),
    }), 200

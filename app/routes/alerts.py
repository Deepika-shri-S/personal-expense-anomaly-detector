from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models.alert import Alert
from app.routes.auth import auth_required

alerts_bp = Blueprint("alerts", __name__, url_prefix="/api/alerts")


@alerts_bp.route("", methods=["GET"])
@auth_required
def list_alerts():
    """List in-app alerts with filter options."""
    query = Alert.query.filter_by(user_id=g.current_user.id)

    is_read = request.args.get("is_read")
    if is_read is not None:
        val = is_read.lower() in ("true", "1", "yes")
        query = query.filter_by(is_read=val)

    is_resolved = request.args.get("is_resolved")
    if is_resolved is not None:
        val = is_resolved.lower() in ("true", "1", "yes")
        query = query.filter_by(is_resolved=val)

    severity = request.args.get("severity")
    if severity:
        query = query.filter_by(severity=severity.lower())

    alert_type = request.args.get("alert_type")
    if alert_type:
        query = query.filter_by(alert_type=alert_type.lower())

    alerts = query.order_by(Alert.created_at.desc()).all()
    unread_count = Alert.query.filter_by(user_id=g.current_user.id, is_read=False).count()

    return jsonify({
        "count": len(alerts),
        "unread_count": unread_count,
        "alerts": [a.to_dict() for a in alerts],
    }), 200


@alerts_bp.route("/<int:alert_id>/read", methods=["PATCH"])
@auth_required
def mark_read(alert_id: int):
    """Mark a single alert as read."""
    alert = Alert.query.filter_by(id=alert_id, user_id=g.current_user.id).first()
    if not alert:
        return jsonify({"error": "Alert not found."}), 404

    alert.is_read = True
    db.session.commit()
    return jsonify({"message": "Alert marked as read.", "alert": alert.to_dict()}), 200


@alerts_bp.route("/<int:alert_id>/resolve", methods=["PATCH"])
@auth_required
def mark_resolved(alert_id: int):
    """Mark a single alert as resolved."""
    alert = Alert.query.filter_by(id=alert_id, user_id=g.current_user.id).first()
    if not alert:
        return jsonify({"error": "Alert not found."}), 404

    alert.is_resolved = True
    alert.is_read = True
    db.session.commit()
    return jsonify({"message": "Alert resolved.", "alert": alert.to_dict()}), 200


@alerts_bp.route("/mark-all-read", methods=["POST"])
@auth_required
def mark_all_read():
    """Mark all unread alerts for this user as read."""
    Alert.query.filter_by(user_id=g.current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"message": "All alerts marked as read."}), 200

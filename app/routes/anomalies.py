from flask import Blueprint, request, jsonify, g
from app.routes.auth import auth_required
from app.models.transaction import Transaction
from app.models.profile import SpendingProfile
from app.services.anomaly_service import AnomalyService
from app.services.analytics_service import AnalyticsService

anomalies_bp = Blueprint("anomalies", __name__, url_prefix="/api/anomalies")


@anomalies_bp.route("", methods=["GET"])
@auth_required
def list_anomalies():
    """Retrieve all flagged unusual transactions for the user."""
    profile_id = request.args.get("profile_id", type=int)
    severity = request.args.get("severity")
    status = request.args.get("status")

    query = Transaction.query.filter_by(user_id=g.current_user.id, anomaly_status=True)

    if profile_id:
        query = query.filter_by(profile_id=profile_id)
    if severity:
        query = query.filter_by(anomaly_severity=severity.lower())
    if status:
        query = query.filter_by(user_confirmation_status=status.lower())

    anomalies = query.order_by(Transaction.transaction_date.desc()).all()
    return jsonify({
        "count": len(anomalies),
        "anomalies": [a.to_dict() for a in anomalies],
    }), 200


@anomalies_bp.route("/stats", methods=["GET"])
@auth_required
def anomaly_stats():
    """Summary of anomalies broken down by severity and review status."""
    profile_id = request.args.get("profile_id", type=int)
    filters = {"profile_id": profile_id} if profile_id else {}
    stats = AnalyticsService.get_anomalies_summary(g.current_user.id, filters)
    return jsonify(stats), 200


@anomalies_bp.route("/retrain/<int:profile_id>", methods=["POST"])
@auth_required
def retrain_model(profile_id: int):
    """Trigger retraining of the Isolation Forest model for a specific spending profile."""
    profile = SpendingProfile.query.filter_by(id=profile_id, user_id=g.current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    res = AnomalyService.retrain_profile(profile_id, g.current_user.id)
    if not res.get("success"):
        return jsonify(res), 400

    return jsonify({
        "message": "Model retraining executed.",
        "details": res,
    }), 200


@anomalies_bp.route("/batch-recalculate/<int:profile_id>", methods=["POST"])
@auth_required
def batch_recalculate(profile_id: int):
    """Recalculate anomaly scores and explanations for all transactions in a profile."""
    profile = SpendingProfile.query.filter_by(id=profile_id, user_id=g.current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    res = AnomalyService.batch_recalculate_profile(profile_id, g.current_user.id)
    if not res.get("success"):
        return jsonify(res), 400

    return jsonify({
        "message": "Batch anomaly recalculation completed.",
        "details": res,
    }), 200

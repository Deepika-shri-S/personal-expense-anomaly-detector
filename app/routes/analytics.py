from flask import Blueprint, request, jsonify, g
from app.routes.auth import auth_required
from app.services.analytics_service import AnalyticsService

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


def extract_common_filters():
    return {
        "profile_id": request.args.get("profile_id"),
        "category": request.args.get("category"),
        "start_date": request.args.get("start_date"),
        "end_date": request.args.get("end_date"),
    }


@analytics_bp.route("/summary", methods=["GET"])
@auth_required
def get_summary():
    """Retrieve high-level spending summary KPI metrics."""
    filters = extract_common_filters()
    summary = AnalyticsService.get_summary(g.current_user.id, filters)
    return jsonify(summary), 200


@analytics_bp.route("/spending-trend", methods=["GET"])
@auth_required
def get_spending_trend():
    """
    Time series spending trend for charting libraries.
    Query parameters:
    - period: 'day' | 'week' | 'month' (default: 'day')
    - fill_zeros: 'true' | 'false' (default: 'true')
    - profile_id: int
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    """
    period = request.args.get("period", "day").lower()
    if period not in ["day", "week", "month"]:
        period = "day"

    fill_zeros = request.args.get("fill_zeros", "true").lower() in ("true", "1", "yes")
    filters = extract_common_filters()

    trend = AnalyticsService.get_spending_trend(
        user_id=g.current_user.id,
        filters=filters,
        period=period,
        fill_zeros=fill_zeros,
    )
    return jsonify(trend), 200


@analytics_bp.route("/category-breakdown", methods=["GET"])
@auth_required
def get_category_breakdown():
    """Category-wise spending distribution with percentages and counts."""
    filters = extract_common_filters()
    breakdown = AnalyticsService.get_category_breakdown(g.current_user.id, filters)
    return jsonify(breakdown), 200


@analytics_bp.route("/payment-channel-breakdown", methods=["GET"])
@auth_required
def get_payment_channel_breakdown():
    """Online versus offline spending comparison."""
    filters = extract_common_filters()
    breakdown = AnalyticsService.get_payment_channel_breakdown(g.current_user.id, filters)
    return jsonify(breakdown), 200


@analytics_bp.route("/payment-method-breakdown", methods=["GET"])
@auth_required
def get_payment_method_breakdown():
    """Distribution of payment methods (UPI, cash, card, net banking, other)."""
    filters = extract_common_filters()
    breakdown = AnalyticsService.get_payment_method_breakdown(g.current_user.id, filters)
    return jsonify(breakdown), 200


@analytics_bp.route("/profile-comparison", methods=["GET"])
@auth_required
def get_profile_comparison():
    """Compare spending patterns across profiles (e.g. College vs Home vs Travel)."""
    filters = extract_common_filters()
    comparison = AnalyticsService.get_profile_comparison(g.current_user.id, filters)
    return jsonify(comparison), 200


@analytics_bp.route("/anomalies-summary", methods=["GET"])
@auth_required
def get_anomalies_summary():
    """Summary of flagged anomalies by severity and review status."""
    filters = extract_common_filters()
    summary = AnalyticsService.get_anomalies_summary(g.current_user.id, filters)
    return jsonify(summary), 200

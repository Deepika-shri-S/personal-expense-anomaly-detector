from flask import Blueprint, request, jsonify, g
from app.routes.auth import auth_required
from app.services.bill_service import BillService

bills_bp = Blueprint("bills", __name__, url_prefix="/api/bills")


@bills_bp.route("", methods=["GET"])
@auth_required
def list_bills():
    """List bills with optional profile and payment status filtering."""
    profile_id = request.args.get("profile_id", type=int)
    status = request.args.get("status")
    bills = BillService.get_bills(g.current_user.id, profile_id=profile_id, status=status)
    return jsonify({"count": len(bills), "bills": bills}), 200


@bills_bp.route("", methods=["POST"])
@auth_required
def create_bill():
    """Create a new bill with reminder days schedule."""
    data = request.get_json() or {}
    success, res = BillService.create_bill(g.current_user.id, data)
    if not success:
        return jsonify(res), 400
    return jsonify({"message": "Bill created successfully.", "bill": res}), 201


@bills_bp.route("/upcoming", methods=["GET"])
@auth_required
def get_upcoming():
    """Retrieve unpaid bills due within the next N days (default 30)."""
    days = request.args.get("days", 30, type=int)
    bills = BillService.get_upcoming_bills(g.current_user.id, days_ahead=days)
    return jsonify({"count": len(bills), "bills": bills}), 200


@bills_bp.route("/overdue", methods=["GET"])
@auth_required
def get_overdue():
    """Retrieve unpaid bills past their due date."""
    bills = BillService.get_overdue_bills(g.current_user.id)
    return jsonify({"count": len(bills), "bills": bills}), 200


@bills_bp.route("/<int:bill_id>", methods=["GET"])
@auth_required
def get_bill(bill_id: int):
    """Retrieve single bill details."""
    bills = BillService.get_bills(g.current_user.id)
    match = next((b for b in bills if b["id"] == bill_id), None)
    if not match:
        return jsonify({"error": "Bill not found."}), 404
    return jsonify({"bill": match}), 200


@bills_bp.route("/<int:bill_id>", methods=["PUT"])
@auth_required
def update_bill(bill_id: int):
    """Update bill amount, due date, or reminder configuration."""
    data = request.get_json() or {}
    success, res = BillService.update_bill(bill_id, g.current_user.id, data)
    if not success:
        return jsonify(res), 400
    return jsonify({"message": "Bill updated.", "bill": res}), 200


@bills_bp.route("/<int:bill_id>", methods=["DELETE"])
@auth_required
def delete_bill(bill_id: int):
    """Delete a bill."""
    success, res = BillService.delete_bill(bill_id, g.current_user.id)
    if not success:
        return jsonify(res), 404
    return jsonify(res), 200


@bills_bp.route("/<int:bill_id>/pay", methods=["POST"])
@auth_required
def pay_bill(bill_id: int):
    """Mark bill as paid. If recurring (e.g. monthly), advances to the next due cycle."""
    success, res = BillService.mark_bill_paid(bill_id, g.current_user.id)
    if not success:
        return jsonify(res), 400
    return jsonify(res), 200


@bills_bp.route("/trigger-reminders", methods=["POST"])
@auth_required
def trigger_reminders():
    """Manual trigger to evaluate due dates and generate alert notifications."""
    alerts = BillService.check_and_create_due_reminders()
    return jsonify({
        "message": f"Processed bill due date reminders. Generated {len(alerts)} alerts.",
        "alerts_generated": alerts,
    }), 200

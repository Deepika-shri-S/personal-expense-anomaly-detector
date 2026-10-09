from flask import Blueprint, request, jsonify, g
from app.routes.auth import auth_required
from app.services.transaction_service import TransactionService

transactions_bp = Blueprint("transactions", __name__, url_prefix="/api/transactions")


@transactions_bp.route("", methods=["GET"])
@auth_required
def get_transactions():
    """
    Query transactions with flexible filtering and pagination.
    Query parameters:
    - profile_id: int
    - category: string
    - merchant: string
    - payment_method: upi | cash | card | net banking | other
    - payment_channel: online | offline
    - anomaly_status: true | false
    - anomaly_severity: high | medium | low
    - user_confirmation_status: pending | recognized_legitimate | unexpected_legitimate | not_recognized
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - search: string (matches merchant, category, description, location)
    - page: int (default 1)
    - per_page: int (default 20, max 100)
    """
    filters = {
        "profile_id": request.args.get("profile_id"),
        "category": request.args.get("category"),
        "merchant": request.args.get("merchant"),
        "payment_method": request.args.get("payment_method"),
        "payment_channel": request.args.get("payment_channel"),
        "anomaly_status": request.args.get("anomaly_status"),
        "anomaly_severity": request.args.get("anomaly_severity"),
        "user_confirmation_status": request.args.get("user_confirmation_status"),
        "start_date": request.args.get("start_date"),
        "end_date": request.args.get("end_date"),
        "search": request.args.get("search"),
    }

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    result = TransactionService.get_transactions(
        user_id=g.current_user.id,
        filters=filters,
        page=page,
        per_page=per_page,
    )
    return jsonify(result), 200


@transactions_bp.route("", methods=["POST"])
@auth_required
def create_transaction():
    """
    Record a new expense. Runs the anomaly detector, creates alerts if unusual,
    and stores the record.
    """
    data = request.get_json() or {}
    success, res = TransactionService.create_transaction(g.current_user.id, data)
    if not success:
        return jsonify(res), 400

    return jsonify({
        "message": "Transaction recorded successfully.",
        "transaction": res,
    }), 201


@transactions_bp.route("/<int:transaction_id>", methods=["GET"])
@auth_required
def get_transaction(transaction_id: int):
    """Retrieve details for a single transaction."""
    tx = TransactionService.get_transaction_by_id(transaction_id, g.current_user.id)
    if not tx:
        return jsonify({"error": "Transaction not found."}), 404
    return jsonify({"transaction": tx.to_dict()}), 200


@transactions_bp.route("/<int:transaction_id>", methods=["PUT"])
@auth_required
def update_transaction(transaction_id: int):
    """Update fields of an existing transaction."""
    data = request.get_json() or {}
    success, res = TransactionService.update_transaction(transaction_id, g.current_user.id, data)
    if not success:
        return jsonify(res), 400
    return jsonify({
        "message": "Transaction updated successfully.",
        "transaction": res,
    }), 200


@transactions_bp.route("/<int:transaction_id>", methods=["DELETE"])
@auth_required
def delete_transaction(transaction_id: int):
    """Delete a transaction."""
    success, res = TransactionService.delete_transaction(transaction_id, g.current_user.id)
    if not success:
        return jsonify(res), 404
    return jsonify(res), 200


@transactions_bp.route("/<int:transaction_id>/confirm", methods=["POST"])
@auth_required
def confirm_transaction(transaction_id: int):
    """
    Submit user feedback on an anomaly.
    Payload:
    {
      "status": "recognized_legitimate" | "unexpected_legitimate" | "not_recognized" | "incorrectly_categorized",
      "notes": "optional comment"
    }
    """
    data = request.get_json() or {}
    status = data.get("status")
    if not status:
        return jsonify({"error": "Field 'status' is required."}), 400

    notes = data.get("notes")
    success, res = TransactionService.confirm_transaction(
        tx_id=transaction_id,
        user_id=g.current_user.id,
        status=status,
        notes=notes,
    )
    if not success:
        return jsonify(res), 400

    return jsonify({
        "message": "Feedback recorded. Thank you for helping refine the detection baseline.",
        "transaction": res,
    }), 200

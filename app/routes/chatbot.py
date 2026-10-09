from flask import Blueprint, request, jsonify, g
from app.routes.auth import auth_required
from app.services.chatbot_service import chatbot_service

chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/api/chatbot")


@chatbot_bp.route("/message", methods=["POST"])
@auth_required
def post_message():
    """
    Submit a conversational natural-language question about expenses.
    Queries the database deterministically without hallucination.
    """
    data = request.get_json() or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Field 'message' cannot be empty."}), 400

    profile_id = data.get("profile_id")
    if profile_id:
        try:
            profile_id = int(profile_id)
        except ValueError:
            profile_id = None

    response = chatbot_service.process_message(
        user_id=g.current_user.id,
        message=message,
        profile_id=profile_id,
    )
    return jsonify(response), 200


@chatbot_bp.route("/suggestions", methods=["GET"])
@auth_required
def get_suggestions():
    """Suggested starter questions for the user interface."""
    return jsonify({
        "suggestions": [
            "Why was my latest transaction flagged?",
            "How much did I spend this week?",
            "How much did I spend this month?",
            "Which category accounts for the most spending?",
            "How much did I spend online?",
            "What are my upcoming bills?",
            "What should I review in my recent spending?",
            "How does my college spending differ from my home spending?",
            "Is my latest unusual transaction fraudulent?",
        ]
    }), 200

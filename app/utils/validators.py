from datetime import datetime
from typing import Tuple, Optional, Dict, Any

VALID_PAYMENT_METHODS = {"upi", "cash", "card", "net banking", "other"}
VALID_PAYMENT_CHANNELS = {"online", "offline"}
VALID_CONFIRMATION_STATUSES = {
    "pending",
    "recognized_legitimate",
    "unexpected_legitimate",
    "not_recognized",
    "incorrectly_categorized",
}
VALID_RECURRENCE_TYPES = {"one_time", "monthly", "quarterly", "yearly", "weekly"}


def validate_transaction_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate transaction creation and update payloads.
    Returns (is_valid, error_message).
    """
    if not isinstance(data, dict):
        return False, "Request body must be a valid JSON object."

    # Profile ID
    if "profile_id" not in data or data["profile_id"] is None:
        return False, "Field 'profile_id' is required."
    try:
        int(data["profile_id"])
    except (ValueError, TypeError):
        return False, "'profile_id' must be an integer."

    # Amount
    if "amount" not in data or data["amount"] is None:
        return False, "Field 'amount' is required."
    try:
        amount = float(data["amount"])
        if amount <= 0:
            return False, "'amount' must be a strictly positive number (> 0)."
    except (ValueError, TypeError):
        return False, "'amount' must be a valid numeric value."

    # Category
    category = str(data.get("category", "")).strip()
    if not category:
        return False, "Field 'category' is required and cannot be empty."

    # Merchant
    merchant = str(data.get("merchant", "")).strip()
    if not merchant:
        return False, "Field 'merchant' is required and cannot be empty."

    # Transaction Date
    tx_date_raw = data.get("transaction_date")
    if not tx_date_raw:
        return False, "Field 'transaction_date' is required."

    # Payment Method
    method = str(data.get("payment_method", "")).strip().lower()
    if not method:
        return False, f"Field 'payment_method' is required. Allowed: {list(VALID_PAYMENT_METHODS)}"
    if method not in VALID_PAYMENT_METHODS:
        return False, f"Invalid 'payment_method': '{method}'. Allowed values: {list(VALID_PAYMENT_METHODS)}"

    # Payment Channel
    channel = str(data.get("payment_channel", "")).strip().lower()
    if not channel:
        return False, f"Field 'payment_channel' is required. Allowed: {list(VALID_PAYMENT_CHANNELS)}"
    if channel not in VALID_PAYMENT_CHANNELS:
        return False, f"Invalid 'payment_channel': '{channel}'. Allowed values: {list(VALID_PAYMENT_CHANNELS)}"

    # Optional confirmation status validation if provided
    if "user_confirmation_status" in data and data["user_confirmation_status"]:
        status = str(data["user_confirmation_status"]).strip().lower()
        if status not in VALID_CONFIRMATION_STATUSES:
            return False, f"Invalid 'user_confirmation_status'. Allowed: {list(VALID_CONFIRMATION_STATUSES)}"

    return True, None


def validate_profile_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate profile creation payload."""
    if not isinstance(data, dict):
        return False, "Request body must be a valid JSON object."

    name = str(data.get("name", "")).strip()
    if not name:
        return False, "Field 'name' is required and cannot be empty."

    currency = str(data.get("currency", "INR")).strip().upper()
    if len(currency) < 2 or len(currency) > 6:
        return False, "'currency' must be 2 to 6 characters (e.g. INR, USD, EUR)."

    return True, None


def validate_bill_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate bill creation payload."""
    if not isinstance(data, dict):
        return False, "Request body must be a valid JSON object."

    if "profile_id" not in data or data["profile_id"] is None:
        return False, "Field 'profile_id' is required."

    bill_name = str(data.get("bill_name", "")).strip()
    if not bill_name:
        return False, "Field 'bill_name' is required."

    category = str(data.get("category", "")).strip()
    if not category:
        return False, "Field 'category' is required."

    if "amount" not in data or data["amount"] is None:
        return False, "Field 'amount' is required."
    try:
        amount = float(data["amount"])
        if amount <= 0:
            return False, "'amount' must be positive (> 0)."
    except (ValueError, TypeError):
        return False, "'amount' must be a valid number."

    if "due_date" not in data or not data["due_date"]:
        return False, "Field 'due_date' is required."

    recurrence = str(data.get("recurrence_type", "one_time")).strip().lower()
    if recurrence not in VALID_RECURRENCE_TYPES:
        return False, f"Invalid 'recurrence_type'. Allowed values: {list(VALID_RECURRENCE_TYPES)}"

    return True, None


def validate_user_registration(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate user registration inputs."""
    if not isinstance(data, dict):
        return False, "Request body must be a valid JSON object."

    username = str(data.get("username", "")).strip()
    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters."

    email = str(data.get("email", "")).strip()
    if not email or "@" not in email:
        return False, "A valid email address is required."

    password = str(data.get("password", "")).strip()
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters."

    display_name = str(data.get("display_name", "")).strip()
    if not display_name:
        return False, "Display name is required."

    return True, None

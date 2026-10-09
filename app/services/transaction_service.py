from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List
from flask import current_app
from sqlalchemy import or_

from app.extensions import db
from app.models.transaction import Transaction
from app.models.profile import SpendingProfile
from app.models.alert import Alert
from app.utils.validators import validate_transaction_payload
from app.utils.date_utils import parse_datetime, parse_date, get_start_of_day, get_end_of_day
from app.services.anomaly_service import AnomalyService
from app.services.notification_service import notification_manager


class TransactionService:
    """Business logic for transaction management and anomaly dispatching."""

    @staticmethod
    def create_transaction(user_id: int, data: Dict[str, Any]) -> Tuple[bool, Any]:
        is_valid, err = validate_transaction_payload(data)
        if not is_valid:
            return False, {"error": err}

        profile_id = int(data["profile_id"])
        profile = SpendingProfile.query.filter_by(id=profile_id, user_id=user_id).first()
        if not profile:
            return False, {"error": f"Spending profile ID {profile_id} not found or does not belong to you."}

        tx_date = parse_datetime(data["transaction_date"])
        if not tx_date:
            return False, {"error": "Invalid transaction_date format."}

        amount = float(data["amount"])
        category = str(data["category"]).strip()
        merchant = str(data["merchant"]).strip()
        payment_method = str(data["payment_method"]).strip().lower()
        payment_channel = str(data["payment_channel"]).strip().lower()
        location_label = data.get("location_label")
        description = data.get("description")
        source = data.get("source", "manual")
        user_notes = data.get("user_notes")
        confirmation_status = data.get("user_confirmation_status", "pending")

        # Create model instance
        tx = Transaction(
            user_id=user_id,
            profile_id=profile_id,
            amount=amount,
            category=category,
            merchant=merchant,
            transaction_date=tx_date,
            payment_method=payment_method,
            payment_channel=payment_channel,
            location_label=location_label,
            description=description,
            source=source,
            user_confirmation_status=confirmation_status,
            user_notes=user_notes,
        )

        # Run Anomaly Detector
        prediction = AnomalyService.evaluate_new_transaction(data, profile)
        tx.anomaly_status = prediction.is_anomaly
        tx.anomaly_severity = prediction.severity
        tx.anomaly_score = prediction.anomaly_score
        tx.anomaly_explanation = prediction.reasons
        tx.recommended_action = prediction.recommended_action

        db.session.add(tx)
        db.session.flush() # Flush to get tx.id

        # Dispatch Alert Policy
        if prediction.is_anomaly:
            curr = profile.currency or "INR"
            if prediction.severity == "high":
                msg = (
                    f"High Priority Alert: An unusual transaction of {curr} {amount:,.2f} in '{category}' "
                    f"at '{merchant}' was flagged. Action required."
                )
                alert_type = "anomaly_high"
            elif prediction.severity == "medium":
                msg = (
                    f"Review Notice: Moderate spending anomaly of {curr} {amount:,.2f} at '{merchant}' "
                    f"in profile '{profile.name}'."
                )
                alert_type = "anomaly_medium"
            else:
                msg = f"Spending Notice: Mild deviation detected for {curr} {amount:,.2f} in '{category}'."
                alert_type = "anomaly_low"

            notification_manager.dispatch({
                "user_id": user_id,
                "transaction_id": tx.id,
                "alert_type": alert_type,
                "severity": prediction.severity or "medium",
                "message": msg,
                "metadata": {
                    "anomaly_score": prediction.anomaly_score,
                    "reasons": prediction.reasons,
                    "profile_name": profile.name,
                }
            })

        db.session.commit()
        return True, tx.to_dict()

    @staticmethod
    def get_transactions(
        user_id: int, 
        filters: Dict[str, Any], 
        page: int = 1, 
        per_page: int = 20
    ) -> Dict[str, Any]:
        query = Transaction.query.filter_by(user_id=user_id)

        # Filters
        if filters.get("profile_id"):
            query = query.filter_by(profile_id=int(filters["profile_id"]))

        if filters.get("category"):
            query = query.filter(Transaction.category.ilike(f"%{filters['category'].strip()}%"))

        if filters.get("merchant"):
            query = query.filter(Transaction.merchant.ilike(f"%{filters['merchant'].strip()}%"))

        if filters.get("payment_method"):
            query = query.filter_by(payment_method=filters["payment_method"].strip().lower())

        if filters.get("payment_channel"):
            query = query.filter_by(payment_channel=filters["payment_channel"].strip().lower())

        if filters.get("anomaly_status") is not None:
            is_anomaly = str(filters["anomaly_status"]).lower() in ("true", "1", "yes")
            query = query.filter_by(anomaly_status=is_anomaly)

        if filters.get("anomaly_severity"):
            query = query.filter_by(anomaly_severity=filters["anomaly_severity"].strip().lower())

        if filters.get("user_confirmation_status"):
            query = query.filter_by(user_confirmation_status=filters["user_confirmation_status"].strip().lower())

        # Date Range Filter
        if filters.get("start_date"):
            start_d = parse_date(filters["start_date"])
            if start_d:
                query = query.filter(Transaction.transaction_date >= get_start_of_day(start_d))

        if filters.get("end_date"):
            end_d = parse_date(filters["end_date"])
            if end_d:
                query = query.filter(Transaction.transaction_date <= get_end_of_day(end_d))

        # Full-text search on description, merchant, or location_label
        search = filters.get("search")
        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Transaction.merchant.ilike(s),
                    Transaction.category.ilike(s),
                    Transaction.description.ilike(s),
                    Transaction.location_label.ilike(s),
                )
            )

        # Order chronologically descending
        query = query.order_by(Transaction.transaction_date.desc())

        # Pagination
        per_page = min(max(1, per_page), 100)
        page = max(1, page)
        total_items = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        total_pages = max(1, (total_items + per_page - 1) // per_page)

        return {
            "total_items": total_items,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "items": [item.to_dict() for item in items],
        }

    @staticmethod
    def get_transaction_by_id(tx_id: int, user_id: int) -> Optional[Transaction]:
        return Transaction.query.filter_by(id=tx_id, user_id=user_id).first()

    @staticmethod
    def update_transaction(tx_id: int, user_id: int, data: Dict[str, Any]) -> Tuple[bool, Any]:
        tx = TransactionService.get_transaction_by_id(tx_id, user_id)
        if not tx:
            return False, {"error": "Transaction not found."}

        # Check editable fields
        re_evaluate = False
        if "amount" in data:
            try:
                new_amt = float(data["amount"])
                if new_amt <= 0:
                    return False, {"error": "'amount' must be positive (> 0)."}
                if new_amt != tx.amount:
                    tx.amount = new_amt
                    re_evaluate = True
            except (ValueError, TypeError):
                return False, {"error": "Invalid 'amount'."}

        if "category" in data and data["category"]:
            new_cat = str(data["category"]).strip()
            if new_cat != tx.category:
                tx.category = new_cat
                re_evaluate = True

        if "merchant" in data and data["merchant"]:
            tx.merchant = str(data["merchant"]).strip()

        if "transaction_date" in data and data["transaction_date"]:
            tx_dt = parse_datetime(data["transaction_date"])
            if tx_dt:
                tx.transaction_date = tx_dt

        if "payment_method" in data and data["payment_method"]:
            tx.payment_method = str(data["payment_method"]).strip().lower()

        if "payment_channel" in data and data["payment_channel"]:
            tx.payment_channel = str(data["payment_channel"]).strip().lower()

        if "location_label" in data:
            tx.location_label = data["location_label"]

        if "description" in data:
            tx.description = data["description"]

        if "user_notes" in data:
            tx.user_notes = data["user_notes"]

        if "user_confirmation_status" in data and data["user_confirmation_status"]:
            tx.user_confirmation_status = str(data["user_confirmation_status"]).strip().lower()

        if re_evaluate:
            profile = SpendingProfile.query.get(tx.profile_id)
            if profile:
                pred = AnomalyService.evaluate_new_transaction(tx.to_dict(), profile)
                tx.anomaly_status = pred.is_anomaly
                tx.anomaly_severity = pred.severity
                tx.anomaly_score = pred.anomaly_score
                tx.anomaly_explanation = pred.reasons
                tx.recommended_action = pred.recommended_action

        db.session.commit()
        return True, tx.to_dict()

    @staticmethod
    def delete_transaction(tx_id: int, user_id: int) -> Tuple[bool, Any]:
        tx = TransactionService.get_transaction_by_id(tx_id, user_id)
        if not tx:
            return False, {"error": "Transaction not found."}

        db.session.delete(tx)
        db.session.commit()
        return True, {"message": f"Transaction {tx_id} deleted successfully."}

    @staticmethod
    def confirm_transaction(
        tx_id: int, 
        user_id: int, 
        status: str, 
        notes: Optional[str] = None
    ) -> Tuple[bool, Any]:
        tx = TransactionService.get_transaction_by_id(tx_id, user_id)
        if not tx:
            return False, {"error": "Transaction not found."}

        valid_statuses = [
            "recognized_legitimate",
            "unexpected_legitimate",
            "not_recognized",
            "incorrectly_categorized",
        ]
        status_clean = str(status).strip().lower()
        if status_clean not in valid_statuses:
            return False, {"error": f"Invalid status. Allowed: {valid_statuses}"}

        tx.user_confirmation_status = status_clean
        if notes:
            tx.user_notes = notes

        # If user recognized it, mark associated alerts as resolved
        if status_clean in ["recognized_legitimate", "unexpected_legitimate"]:
            alerts = Alert.query.filter_by(transaction_id=tx.id, user_id=user_id).all()
            for a in alerts:
                a.is_resolved = True
                a.is_read = True

        db.session.commit()
        return True, tx.to_dict()

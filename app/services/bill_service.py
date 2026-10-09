from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from app.extensions import db
from app.models.bill import Bill
from app.models.profile import SpendingProfile
from app.models.alert import Alert
from app.utils.validators import validate_bill_payload
from app.utils.date_utils import parse_date
from app.services.notification_service import notification_manager


def advance_bill_due_date(current_due: date, recurrence_type: str) -> date:
    """Calculate the next due date for recurring bills."""
    rec = recurrence_type.lower()
    if rec == "weekly":
        return current_due + timedelta(days=7)
    elif rec == "monthly":
        # Add one month handling month lengths
        year = current_due.year + (1 if current_due.month == 12 else 0)
        month = 1 if current_due.month == 12 else current_due.month + 1
        day = min(current_due.day, 28) # Safe day clamping
        return date(year, month, day)
    elif rec == "quarterly":
        month = current_due.month + 3
        year = current_due.year
        if month > 12:
            month -= 12
            year += 1
        day = min(current_due.day, 28)
        return date(year, month, day)
    elif rec == "yearly":
        return date(current_due.year + 1, current_due.month, min(current_due.day, 28))
    return current_due


class BillService:
    """Business logic for bill tracking, recurring cycles, and reminder alerts."""

    @staticmethod
    def create_bill(user_id: int, data: Dict[str, Any]) -> Tuple[bool, Any]:
        is_valid, err = validate_bill_payload(data)
        if not is_valid:
            return False, {"error": err}

        profile_id = int(data["profile_id"])
        profile = SpendingProfile.query.filter_by(id=profile_id, user_id=user_id).first()
        if not profile:
            return False, {"error": "Profile not found or access denied."}

        due_date = parse_date(data["due_date"])
        if not due_date:
            return False, {"error": "Invalid due_date format."}

        bill = Bill(
            user_id=user_id,
            profile_id=profile_id,
            bill_name=str(data["bill_name"]).strip(),
            category=str(data["category"]).strip(),
            amount=float(data["amount"]),
            due_date=due_date,
            recurrence_type=str(data.get("recurrence_type", "one_time")).strip().lower(),
            payment_status="unpaid",
        )

        if "reminder_days" in data and isinstance(data["reminder_days"], list):
            bill.reminder_days = data["reminder_days"]

        db.session.add(bill)
        db.session.commit()
        return True, bill.to_dict()

    @staticmethod
    def get_bills(user_id: int, profile_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        query = Bill.query.filter_by(user_id=user_id)
        if profile_id:
            query = query.filter_by(profile_id=profile_id)
        if status:
            query = query.filter_by(payment_status=status.lower())

        bills = query.order_by(Bill.due_date.asc()).all()
        return [b.to_dict() for b in bills]

    @staticmethod
    def get_upcoming_bills(user_id: int, days_ahead: int = 30) -> List[Dict[str, Any]]:
        today = date.today()
        future_limit = today + timedelta(days=days_ahead)
        bills = Bill.query.filter(
            Bill.user_id == user_id,
            Bill.payment_status == "unpaid",
            Bill.due_date >= today,
            Bill.due_date <= future_limit,
        ).order_by(Bill.due_date.asc()).all()
        return [b.to_dict() for b in bills]

    @staticmethod
    def get_overdue_bills(user_id: int) -> List[Dict[str, Any]]:
        today = date.today()
        bills = Bill.query.filter(
            Bill.user_id == user_id,
            Bill.payment_status == "unpaid",
            Bill.due_date < today,
        ).order_by(Bill.due_date.asc()).all()
        return [b.to_dict() for b in bills]

    @staticmethod
    def update_bill(bill_id: int, user_id: int, data: Dict[str, Any]) -> Tuple[bool, Any]:
        bill = Bill.query.filter_by(id=bill_id, user_id=user_id).first()
        if not bill:
            return False, {"error": "Bill not found."}

        if "bill_name" in data and data["bill_name"]:
            bill.bill_name = str(data["bill_name"]).strip()
        if "category" in data and data["category"]:
            bill.category = str(data["category"]).strip()
        if "amount" in data:
            try:
                amt = float(data["amount"])
                if amt <= 0:
                    return False, {"error": "'amount' must be positive."}
                bill.amount = amt
            except (ValueError, TypeError):
                return False, {"error": "Invalid amount."}
        if "due_date" in data:
            d = parse_date(data["due_date"])
            if d:
                bill.due_date = d
        if "recurrence_type" in data:
            bill.recurrence_type = str(data["recurrence_type"]).strip().lower()
        if "reminder_days" in data and isinstance(data["reminder_days"], list):
            bill.reminder_days = data["reminder_days"]
        if "payment_status" in data:
            bill.payment_status = str(data["payment_status"]).strip().lower()

        db.session.commit()
        return True, bill.to_dict()

    @staticmethod
    def delete_bill(bill_id: int, user_id: int) -> Tuple[bool, Any]:
        bill = Bill.query.filter_by(id=bill_id, user_id=user_id).first()
        if not bill:
            return False, {"error": "Bill not found."}

        db.session.delete(bill)
        db.session.commit()
        return True, {"message": f"Bill {bill_id} deleted."}

    @staticmethod
    def mark_bill_paid(bill_id: int, user_id: int) -> Tuple[bool, Any]:
        bill = Bill.query.filter_by(id=bill_id, user_id=user_id).first()
        if not bill:
            return False, {"error": "Bill not found."}

        now_utc = datetime.now(timezone.utc)
        bill.last_paid_date = now_utc

        if bill.recurrence_type and bill.recurrence_type != "one_time":
            # Advance due date for next cycle
            next_due = advance_bill_due_date(bill.due_date, bill.recurrence_type)
            bill.due_date = next_due
            bill.payment_status = "unpaid" # Active for next cycle
            msg = f"Bill '{bill.bill_name}' marked as paid. Next cycle due date set to {next_due.isoformat()}."
        else:
            bill.payment_status = "paid"
            msg = f"Bill '{bill.bill_name}' marked as paid."

        # Mark all pending alerts for this bill as resolved
        alerts = Alert.query.filter_by(bill_id=bill.id, user_id=user_id, is_resolved=False).all()
        for a in alerts:
            a.is_resolved = True
            a.is_read = True

        db.session.commit()
        return True, {"message": msg, "bill": bill.to_dict()}

    @staticmethod
    def check_and_create_due_reminders(reference_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Pure calculation function callable independently from scheduler or testing.
        Checks all unpaid bills and generates non-duplicate alerts.
        """
        ref_d = reference_date or date.today()
        unpaid_bills = Bill.query.filter(Bill.payment_status != "paid").all()
        generated_alerts = []

        for bill in unpaid_bills:
            days_until_due = (bill.due_date - ref_d).days
            reminder_schedule = bill.reminder_days # e.g. [7, 3, 1, 0]

            # 1. Overdue Check
            if days_until_due < 0:
                overdue_alert_type = f"bill_overdue_{bill.due_date.isoformat()}"
                exists = Alert.query.filter_by(
                    user_id=bill.user_id,
                    bill_id=bill.id,
                    alert_type=overdue_alert_type
                ).first()
                if not exists:
                    msg = (
                        f"🚨 OVERDUE BILL: '{bill.bill_name}' of {bill.profile.currency} {bill.amount:,.2f} "
                        f"was due on {bill.due_date.isoformat()} ({abs(days_until_due)} days ago)."
                    )
                    alert_data = {
                        "user_id": bill.user_id,
                        "bill_id": bill.id,
                        "alert_type": overdue_alert_type,
                        "severity": "high",
                        "message": msg,
                        "metadata": {"bill_id": bill.id, "days_overdue": abs(days_until_due)},
                    }
                    notification_manager.dispatch(alert_data)
                    generated_alerts.append(alert_data)

            # 2. Upcoming Reminder Trigger Check
            elif days_until_due in reminder_schedule:
                alert_type = f"bill_due_{days_until_due}d_{bill.due_date.isoformat()}"
                exists = Alert.query.filter_by(
                    user_id=bill.user_id,
                    bill_id=bill.id,
                    alert_type=alert_type
                ).first()

                if not exists:
                    if days_until_due == 0:
                        msg = f"⏰ DUE TODAY: '{bill.bill_name}' of {bill.profile.currency} {bill.amount:,.2f} is due today!"
                        severity = "high"
                    elif days_until_due == 1:
                        msg = f"⚠️ Due Tomorrow: '{bill.bill_name}' of {bill.profile.currency} {bill.amount:,.2f} is due tomorrow."
                        severity = "medium"
                    else:
                        msg = f"Upcoming Bill: '{bill.bill_name}' of {bill.profile.currency} {bill.amount:,.2f} is due in {days_until_due} days."
                        severity = "low"

                    alert_data = {
                        "user_id": bill.user_id,
                        "bill_id": bill.id,
                        "alert_type": alert_type,
                        "severity": severity,
                        "message": msg,
                        "metadata": {"bill_id": bill.id, "days_remaining": days_until_due},
                    }
                    notification_manager.dispatch(alert_data)
                    generated_alerts.append(alert_data)

        db.session.commit()
        return generated_alerts

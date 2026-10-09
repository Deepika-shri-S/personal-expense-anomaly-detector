import json
from datetime import datetime, timezone, date
from app.extensions import db


class Bill(db.Model):
    """
    Upcoming or recurring bill and reminder entity.
    """
    __tablename__ = "bills"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    profile_id = db.Column(
        db.Integer, 
        db.ForeignKey("spending_profiles.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )

    bill_name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False, index=True)
    
    # Recurrence: one_time, monthly, quarterly, yearly, weekly
    recurrence_type = db.Column(db.String(20), default="one_time", nullable=False)
    
    # Reminder days before due date stored as JSON string (e.g., "[7, 3, 1, 0]")
    reminder_days_json = db.Column(db.String(100), default="[7, 3, 1, 0]", nullable=False)
    
    # Payment status: unpaid, paid, overdue
    payment_status = db.Column(db.String(20), default="unpaid", nullable=False, index=True)
    last_paid_date = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relationships
    alerts = db.relationship(
        "Alert", 
        backref="bill", 
        lazy="select", 
        cascade="all, delete-orphan"
    )

    @property
    def reminder_days(self) -> list:
        if not self.reminder_days_json:
            return [7, 3, 1, 0]
        try:
            return json.loads(self.reminder_days_json)
        except (ValueError, TypeError):
            return [7, 3, 1, 0]

    @reminder_days.setter
    def reminder_days(self, value) -> None:
        if isinstance(value, list):
            self.reminder_days_json = json.dumps(value)
        elif isinstance(value, (int, str)):
            self.reminder_days_json = json.dumps([int(value)])
        else:
            self.reminder_days_json = json.dumps([7, 3, 1, 0])

    def to_dict(self) -> dict:
        today = date.today()
        # Dynamically evaluate if unpaid and overdue
        effective_status = self.payment_status
        if self.payment_status == "unpaid" and self.due_date and self.due_date < today:
            effective_status = "overdue"

        days_remaining = (self.due_date - today).days if self.due_date else None

        return {
            "id": self.id,
            "user_id": self.user_id,
            "profile_id": self.profile_id,
            "profile_name": self.profile.name if self.profile else None,
            "currency": self.profile.currency if self.profile else "INR",
            "bill_name": self.bill_name,
            "category": self.category,
            "amount": round(self.amount, 2),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "days_remaining": days_remaining,
            "recurrence_type": self.recurrence_type,
            "reminder_days": self.reminder_days,
            "payment_status": effective_status,
            "last_paid_date": self.last_paid_date.isoformat() if self.last_paid_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

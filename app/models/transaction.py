import json
from datetime import datetime, timezone
from app.extensions import db


class Transaction(db.Model):
    """
    Transaction record with distinct payment method and payment channel,
    scoped to a user and spending profile.
    """
    __tablename__ = "transactions"

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

    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    merchant = db.Column(db.String(120), nullable=False, index=True)
    transaction_date = db.Column(db.DateTime, nullable=False, index=True)

    # Distinct method & channel
    payment_method = db.Column(db.String(30), nullable=False, index=True)  # UPI, cash, card, net banking, other
    payment_channel = db.Column(db.String(20), nullable=False, index=True) # online, offline

    location_label = db.Column(db.String(100), nullable=True) # Optional user-provided label, not GPS
    description = db.Column(db.String(255), nullable=True)
    source = db.Column(db.String(30), default="manual", nullable=False) # manual, csv_import, etc.

    # User review and feedback status
    # Options: pending, recognized_legitimate, unexpected_legitimate, not_recognized, incorrectly_categorized
    user_confirmation_status = db.Column(db.String(30), default="pending", nullable=False, index=True)
    user_notes = db.Column(db.String(255), nullable=True)

    # Anomaly detection results
    anomaly_status = db.Column(db.Boolean, default=False, nullable=False, index=True)
    anomaly_severity = db.Column(db.String(20), nullable=True, index=True) # low, medium, high
    anomaly_score = db.Column(db.Float, nullable=True) # Normalized 0.0 - 1.0
    anomaly_explanation_json = db.Column(db.Text, nullable=True) # JSON serialized list of reason strings
    recommended_action = db.Column(db.String(255), nullable=True)

    created_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relationships
    alerts = db.relationship(
        "Alert", 
        backref="transaction", 
        lazy="select", 
        cascade="all, delete-orphan"
    )

    @property
    def anomaly_explanation(self) -> list:
        """Parse JSON explanation array safely."""
        if not self.anomaly_explanation_json:
            return []
        try:
            return json.loads(self.anomaly_explanation_json)
        except (ValueError, TypeError):
            return [self.anomaly_explanation_json]

    @anomaly_explanation.setter
    def anomaly_explanation(self, value) -> None:
        """Serialize explanation list into JSON string."""
        if isinstance(value, list):
            self.anomaly_explanation_json = json.dumps(value)
        elif isinstance(value, str):
            self.anomaly_explanation_json = json.dumps([value])
        else:
            self.anomaly_explanation_json = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "profile_id": self.profile_id,
            "profile_name": self.profile.name if self.profile else None,
            "currency": self.profile.currency if self.profile else "INR",
            "amount": round(self.amount, 2),
            "category": self.category,
            "merchant": self.merchant,
            "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
            "payment_method": self.payment_method,
            "payment_channel": self.payment_channel,
            "location_label": self.location_label,
            "description": self.description,
            "source": self.source,
            "user_confirmation_status": self.user_confirmation_status,
            "user_notes": self.user_notes,
            "anomaly_status": self.anomaly_status,
            "anomaly_severity": self.anomaly_severity,
            "anomaly_score": round(self.anomaly_score, 4) if self.anomaly_score is not None else None,
            "anomaly_explanation": self.anomaly_explanation,
            "recommended_action": self.recommended_action,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

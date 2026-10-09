import json
from datetime import datetime, timezone
from app.extensions import db


class Alert(db.Model):
    """
    In-app alert entity for anomalies, due dates, and spending alerts.
    """
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    transaction_id = db.Column(
        db.Integer, 
        db.ForeignKey("transactions.id", ondelete="CASCADE"), 
        nullable=True, 
        index=True
    )
    bill_id = db.Column(
        db.Integer, 
        db.ForeignKey("bills.id", ondelete="CASCADE"), 
        nullable=True, 
        index=True
    )

    # alert_type: anomaly_high, anomaly_medium, anomaly_low, bill_due, bill_overdue, general
    alert_type = db.Column(db.String(30), nullable=False, index=True)
    
    # severity: high, medium, low, info
    severity = db.Column(db.String(20), default="medium", nullable=False, index=True)
    
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_resolved = db.Column(db.Boolean, default=False, nullable=False, index=True)
    metadata_json = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False,
        index=True
    )

    @property
    def alert_metadata(self) -> dict:
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except (ValueError, TypeError):
            return {}

    @alert_metadata.setter
    def alert_metadata(self, val: dict) -> None:
        if val is not None:
            self.metadata_json = json.dumps(val)
        else:
            self.metadata_json = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "transaction_id": self.transaction_id,
            "bill_id": self.bill_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "is_read": self.is_read,
            "is_resolved": self.is_resolved,
            "metadata": self.alert_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

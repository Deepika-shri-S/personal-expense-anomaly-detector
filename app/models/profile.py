from datetime import datetime, timezone
from app.extensions import db


class SpendingProfile(db.Model):
    """
    Independent spending profile / context for a user.
    Examples: College, Home, Hostel, Travel, Vacation.
    Each profile maintains its own spending baseline, statistics, and anomaly rules.
    """
    __tablename__ = "spending_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    currency = db.Column(db.String(10), default="INR", nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relationships
    transactions = db.relationship(
        "Transaction", 
        backref="profile", 
        lazy="select", 
        cascade="all, delete-orphan"
    )
    bills = db.relationship(
        "Bill", 
        backref="profile", 
        lazy="select", 
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_user_profile_name"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "currency": self.currency,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "transaction_count": len(self.transactions) if self.transactions else 0,
        }

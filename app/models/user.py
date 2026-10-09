from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    """User account entity with secure password hashing."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relationships with cascading deletes
    profiles = db.relationship(
        "SpendingProfile", 
        backref="user", 
        lazy="select", 
        cascade="all, delete-orphan"
    )
    transactions = db.relationship(
        "Transaction", 
        backref="user", 
        lazy="select", 
        cascade="all, delete-orphan"
    )
    bills = db.relationship(
        "Bill", 
        backref="user", 
        lazy="select", 
        cascade="all, delete-orphan"
    )
    alerts = db.relationship(
        "Alert", 
        backref="user", 
        lazy="select", 
        cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        """Hash and store user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify candidate password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.extensions import db
from app.models.alert import Alert


class BaseNotificationChannel(ABC):
    """Abstract base notification channel."""

    @abstractmethod
    def send(self, alert_data: Dict[str, Any]) -> bool:
        pass


class DatabaseNotificationChannel(BaseNotificationChannel):
    """
    In-App Notification Channel: persists alerts to SQLite.
    Note: Storing alerts in SQLite makes them queryable via APIs.
    Real-time push delivery (e.g. Firebase Cloud Messaging, Web Push)
    or external SMS/Email requires active external worker gateways.
    """

    def send(self, alert_data: Dict[str, Any]) -> bool:
        user_id = alert_data.get("user_id")
        if not user_id:
            return False

        # Deduplication check for transactions
        tx_id = alert_data.get("transaction_id")
        if tx_id:
            existing = Alert.query.filter_by(
                user_id=user_id,
                transaction_id=tx_id,
                alert_type=alert_data.get("alert_type", "anomaly")
            ).first()
            if existing:
                return True # Already recorded, avoid duplicate notifications

        alert = Alert(
            user_id=user_id,
            transaction_id=tx_id,
            bill_id=alert_data.get("bill_id"),
            alert_type=alert_data.get("alert_type", "general"),
            severity=alert_data.get("severity", "medium"),
            message=alert_data.get("message", ""),
            is_read=False,
            is_resolved=False,
        )
        if "metadata" in alert_data:
            alert.alert_metadata = alert_data["metadata"]

        db.session.add(alert)
        return True


class NotificationManager:
    """Manages dispatching alerts to configured notification channels."""

    def __init__(self):
        self.channels = [
            DatabaseNotificationChannel()
        ]

    def dispatch(self, alert_data: Dict[str, Any]) -> None:
        for channel in self.channels:
            try:
                channel.send(alert_data)
            except Exception as e:
                # Fallback logging to prevent transaction rollback
                print(f"[NotificationManager Error] Channel {channel.__class__.__name__} failed: {e}")


notification_manager = NotificationManager()

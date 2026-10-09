import pytest
from datetime import datetime, date, timedelta, timezone
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.profile import SpendingProfile
from app.models.transaction import Transaction
from app.models.bill import Bill
from app.routes.auth import generate_auth_token


@pytest.fixture
def app():
    """Create Flask application configured for isolated testing."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def seed_data(app):
    """Seed test user, profiles, transactions, and bills."""
    with app.app_context():
        user = User(
            username="test_student",
            email="test@student.edu",
            display_name="Test Student",
        )
        user.set_password("pass123")
        db.session.add(user)
        db.session.flush()

        # Profiles
        p_college = SpendingProfile(
            user_id=user.id,
            name="College",
            description="College profile",
            currency="INR",
            is_default=True,
        )
        p_home = SpendingProfile(
            user_id=user.id,
            name="Home",
            description="Home profile",
            currency="INR",
            is_default=False,
        )
        db.session.add_all([p_college, p_home])
        db.session.flush()

        # Seed 20 historical transactions for College so ML baseline has data
        base_dt = datetime.now(timezone.utc) - timedelta(days=20)
        for i in range(20):
            t = Transaction(
                user_id=user.id,
                profile_id=p_college.id,
                amount=150.0 + (i % 5) * 10.0, # 150 to 190
                category="Food",
                merchant="Campus Canteen",
                transaction_date=base_dt + timedelta(days=i),
                payment_method="upi",
                payment_channel="offline",
                source="test",
                user_confirmation_status="recognized_legitimate",
                anomaly_status=False,
                anomaly_score=0.1,
            )
            db.session.add(t)

        # Seed a test bill
        today = date.today()
        bill = Bill(
            user_id=user.id,
            profile_id=p_college.id,
            bill_name="Mess Fee",
            category="Utilities",
            amount=1500.0,
            due_date=today + timedelta(days=3),
            recurrence_type="monthly",
            reminder_days=[7, 3, 1, 0],
            payment_status="unpaid",
        )
        db.session.add(bill)
        db.session.commit()

        token = generate_auth_token(user.id)

        return {
            "user_id": user.id,
            "token": token,
            "headers": {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            "college_profile_id": p_college.id,
            "home_profile_id": p_home.id,
        }

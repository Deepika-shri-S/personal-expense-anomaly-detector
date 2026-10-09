import os
import sys
from pathlib import Path
from datetime import datetime, date, timedelta, timezone

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.profile import SpendingProfile
from app.models.transaction import Transaction
from app.models.bill import Bill
from app.services.anomaly_service import AnomalyService
from app.services.bill_service import BillService


def seed_database():
    app = create_app("development")

    with app.app_context():
        print("[1/5] Recreating database schema in instance/expense_detector.db ...")
        db.drop_all()
        db.create_all()

        print("[2/5] Creating demo user account ...")
        user = User(
            username="student_user",
            email="student@college.edu",
            display_name="Deepika (Student Developer)",
        )
        user.set_password("student123")
        db.session.add(user)
        db.session.flush()

        print("[3/5] Creating spending profiles: College, Home, Travel ...")
        p_college = SpendingProfile(
            user_id=user.id,
            name="College",
            description="Daily campus canteen, textbooks, local transit, and hostel expenses",
            currency="INR",
            is_default=True,
        )
        p_home = SpendingProfile(
            user_id=user.id,
            name="Home",
            description="Family groceries, home utility bills, and neighborhood markets",
            currency="INR",
            is_default=False,
        )
        p_travel = SpendingProfile(
            user_id=user.id,
            name="Travel",
            description="Vacation, flights, outstation lodging, and holiday trips",
            currency="INR",
            is_default=False,
        )
        db.session.add_all([p_college, p_home, p_travel])
        db.session.flush()

        print("[4/5] Populating realistic spending history and test anomalies ...")
        base_time = datetime.now(timezone.utc) - timedelta(days=30)

        # Baseline College Transactions
        college_normal_items = [
            (120.0, "Food", "Campus Canteen", "upi", "offline", "Hostel Block A", "Breakfast idli and tea", 0),
            (180.0, "Food", "Campus Canteen", "upi", "offline", "Campus Canteen", "Lunch thali", 0),
            (50.0, "Travel", "City Metro", "card", "offline", "Metro Station", "Daily metro token", 1),
            (250.0, "Books", "College Book Depot", "cash", "offline", "Gate 2", "Notebooks & pens", 1),
            (150.0, "Food", "Campus Canteen", "upi", "offline", "Campus Canteen", "Lunch", 2),
            (80.0, "Food", "Tea Stall", "cash", "offline", "Near Library", "Evening chai", 2),
            (160.0, "Food", "Campus Canteen", "upi", "offline", "Campus Canteen", "Lunch", 3),
            (210.0, "Food", "Green Bowl Cafe", "upi", "offline", "College Road", "Team project lunch", 4),
            (450.0, "Books", "Standard Academic Books", "card", "online", "Online", "Operating Systems textbook", 5),
            (130.0, "Food", "Campus Canteen", "upi", "offline", "Campus Canteen", "Breakfast", 6),
            (170.0, "Food", "Campus Canteen", "upi", "offline", "Campus Canteen", "Lunch", 6),
            (60.0, "Travel", "City Bus", "cash", "offline", "Bus Stand", "Commute", 7),
            (190.0, "Food", "Campus Canteen", "upi", "offline", "Campus Canteen", "Lunch", 8),
            (140.0, "Food", "Campus Canteen", "upi", "offline", "Campus Canteen", "Lunch", 9),
            (90.0, "Food", "Campus Juice Corner", "upi", "offline", "Grounds", "Fresh orange juice", 10),
            (160.0, "Food", "Campus Canteen", "upi", "offline", "Campus Canteen", "Lunch", 11),
            (280.0, "Food", "Rolls Express", "upi", "offline", "Market", "Dinner", 12),
            (115.0, "Food", "Campus Canteen", "upi", "offline", "Campus Canteen", "Breakfast", 13),
            (175.0, "Food", "Campus Canteen", "upi", "offline", "Campus Canteen", "Lunch", 14),
            (350.0, "Stationery", "Print & Xerox World", "upi", "offline", "Campus", "Report spiral binding", 15),
            (150.0, "Food", "Campus Canteen", "upi", "offline", "Campus Canteen", "Lunch", 16),
            (180.0, "Food", "Campus Canteen", "upi", "offline", "Campus Canteen", "Lunch", 17),
            (155.0, "Food", "Campus Canteen", "upi", "offline", "Campus Canteen", "Lunch", 18),
            (170.0, "Food", "Campus Canteen", "upi", "offline", "Campus Canteen", "Lunch", 19),
        ]

        for amt, cat, merch, method, chan, loc, desc, day_offset in college_normal_items:
            tx = Transaction(
                user_id=user.id,
                profile_id=p_college.id,
                amount=amt,
                category=cat,
                merchant=merch,
                transaction_date=base_time + timedelta(days=day_offset, hours=12),
                payment_method=method,
                payment_channel=chan,
                location_label=loc,
                description=desc,
                source="initial_seed",
                user_confirmation_status="recognized_legitimate",
                anomaly_status=False,
                anomaly_score=0.12,
                anomaly_explanation=["Within normal college spending parameters."],
            )
            db.session.add(tx)

        # High Anomaly: Midnight electronics purchase
        tx_anomaly1 = Transaction(
            user_id=user.id,
            profile_id=p_college.id,
            amount=4800.0,
            category="Electronics",
            merchant="GadgetWorld Electronics",
            transaction_date=base_time + timedelta(days=22, hours=2, minutes=30), # 02:30 AM
            payment_method="card",
            payment_channel="online",
            location_label="Online Portal",
            description="Smartwatch midnight order",
            source="manual",
            user_confirmation_status="pending",
            anomaly_status=True,
            anomaly_severity="high",
            anomaly_score=0.88,
            anomaly_explanation=[
                "Amount INR 4,800.00 is substantially higher than typical profile median (INR 160.00).",
                "Transaction occurred at 02:30 AM, outside usual daytime spending hours.",
                "First recorded purchase at merchant 'GadgetWorld Electronics'."
            ],
            recommended_action="Review this transaction immediately and confirm whether you recognize and authorized it.",
        )
        # Medium Anomaly: 18x normal food expense at luxury restaurant
        tx_anomaly2 = Transaction(
            user_id=user.id,
            profile_id=p_college.id,
            amount=3200.0,
            category="Food",
            merchant="Luxury Fine Dining Bistro",
            transaction_date=base_time + timedelta(days=25, hours=20, minutes=15),
            payment_method="card",
            payment_channel="offline",
            location_label="Downtown District",
            description="Celebration dinner with classmates",
            source="manual",
            user_confirmation_status="pending",
            anomaly_status=True,
            anomaly_severity="medium",
            anomaly_score=0.74,
            anomaly_explanation=[
                "Amount INR 3,200.00 is 19.4x higher than your usual median spending (INR 165.00) in 'Food'.",
                "Unfamiliar merchant with high transaction value."
            ],
            recommended_action="Review this expense in your daily summary and verify the amount.",
        )
        db.session.add_all([tx_anomaly1, tx_anomaly2])

        # Home Profile Transactions
        home_items = [
            (1200.0, "Groceries", "BigBazaar Supermarket", "card", "offline", "City Mall", "Monthly grocery staples", 2),
            (350.0, "Groceries", "Local Dairy", "cash", "offline", "Home Street", "Milk and curd", 4),
            (1850.0, "Utilities", "State Electricity Board", "net banking", "online", "Online Portal", "Home power bill", 8),
            (799.0, "Utilities", "FiberNet Broadband", "upi", "online", "Online App", "Home Wi-Fi monthly", 10),
            (650.0, "Groceries", "Fresh Fruit Market", "cash", "offline", "Main Road", "Weekly fruits", 12),
            (1450.0, "Groceries", "BigBazaar Supermarket", "card", "offline", "City Mall", "Pantry refill", 16),
            (2200.0, "Medical", "Apollo Pharmacy", "upi", "offline", "Corner Clinic", "Prescription medicines", 18),
            (400.0, "Groceries", "Local Dairy", "cash", "offline", "Home Street", "Weekly dairy", 20),
            (950.0, "Utilities", "City Gas LPG", "net banking", "online", "Gas Agency", "LPG cylinder refill", 22),
            (1100.0, "Groceries", "Organic Greens", "upi", "offline", "Subzi Mandi", "Vegetables and pantry", 24),
            (500.0, "Entertainment", "City Cinema", "card", "offline", "Theatre Plaza", "Family movie tickets", 26),
        ]

        for amt, cat, merch, method, chan, loc, desc, day_offset in home_items:
            tx = Transaction(
                user_id=user.id,
                profile_id=p_home.id,
                amount=amt,
                category=cat,
                merchant=merch,
                transaction_date=base_time + timedelta(days=day_offset, hours=17),
                payment_method=method,
                payment_channel=chan,
                location_label=loc,
                description=desc,
                source="initial_seed",
                user_confirmation_status="recognized_legitimate",
                anomaly_status=False,
                anomaly_score=0.15,
                anomaly_explanation=["Within normal home spending baseline."],
            )
            db.session.add(tx)

        # Seed Bills
        today = date.today()
        bills = [
            Bill(
                user_id=user.id,
                profile_id=p_college.id,
                bill_name="Hostel Electricity Bill",
                category="Utilities",
                amount=650.0,
                due_date=today + timedelta(days=3),
                recurrence_type="monthly",
                reminder_days=[7, 3, 1, 0],
                payment_status="unpaid",
            ),
            Bill(
                user_id=user.id,
                profile_id=p_college.id,
                bill_name="Mobile Phone Recharge",
                category="Utilities",
                amount=299.0,
                due_date=today + timedelta(days=1),
                recurrence_type="monthly",
                reminder_days=[7, 3, 1, 0],
                payment_status="unpaid",
            ),
            Bill(
                user_id=user.id,
                profile_id=p_college.id,
                bill_name="Semester Library Book Fee",
                category="Fees",
                amount=150.0,
                due_date=today - timedelta(days=2), # Overdue for testing
                recurrence_type="one_time",
                reminder_days=[7, 3, 1, 0],
                payment_status="unpaid",
            ),
            Bill(
                user_id=user.id,
                profile_id=p_home.id,
                bill_name="Home Broadband Wi-Fi",
                category="Utilities",
                amount=799.0,
                due_date=today + timedelta(days=12),
                recurrence_type="monthly",
                reminder_days=[7, 3, 1, 0],
                payment_status="unpaid",
            ),
        ]
        db.session.add_all(bills)
        db.session.commit()

        print("[5/5] Training ML Isolation Forest models and computing initial reminders ...")
        AnomalyService.retrain_profile(p_college.id, user.id)
        AnomalyService.retrain_profile(p_home.id, user.id)
        BillService.check_and_create_due_reminders()

        print("\n" + "=" * 65)
        print(" Database Initialization Complete!")
        print("=" * 65)
        print(" Demo User Credentials:")
        print("   Username : student_user")
        print("   Password : student123")
        print(" Profiles Seeded:")
        print(f"   1. College (ID: {p_college.id}) - {len(college_normal_items) + 2} transactions (2 flagged anomalies)")
        print(f"   2. Home    (ID: {p_home.id}) - {len(home_items)} transactions")
        print(f"   3. Travel  (ID: {p_travel.id}) - 0 transactions (new profile)")
        print(" Bills Seeded:")
        print("   4 sample bills (including 1 overdue and 1 due tomorrow)")
        print("=" * 65 + "\n")


if __name__ == "__main__":
    seed_database()

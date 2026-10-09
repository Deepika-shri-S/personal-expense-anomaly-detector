import json
from datetime import date, timedelta
from app.services.bill_service import BillService


def test_create_and_list_bills(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]
    today = date.today()

    payload = {
        "profile_id": pid,
        "bill_name": "Wi-Fi Router Fee",
        "category": "Utilities",
        "amount": 499.0,
        "due_date": (today + timedelta(days=5)).isoformat(),
        "recurrence_type": "monthly",
        "reminder_days": [7, 3, 1, 0],
    }
    create_res = client.post("/api/bills", data=json.dumps(payload), headers=headers)
    assert create_res.status_code == 201

    list_res = client.get("/api/bills", headers=headers)
    assert list_res.status_code == 200
    assert list_res.get_json()["count"] >= 2


def test_mark_bill_paid_advances_recurring(client, seed_data):
    headers = seed_data["headers"]
    # Get seeded bill
    bills_res = client.get("/api/bills", headers=headers)
    bill = bills_res.get_json()["bills"][0]
    bill_id = bill["id"]
    old_due = bill["due_date"]

    pay_res = client.post(f"/api/bills/{bill_id}/pay", headers=headers)
    assert pay_res.status_code == 200
    updated = pay_res.get_json()["bill"]
    if updated["recurrence_type"] == "monthly":
        assert updated["due_date"] != old_due
        assert updated["payment_status"] == "unpaid" # Reset for next cycle


def test_pure_reminder_calculation_without_waiting(app, seed_data):
    """Verify that due date reminder calculations can be tested on synthetic reference dates."""
    today = date.today()
    alerts = BillService.check_and_create_due_reminders(reference_date=today)
    assert isinstance(alerts, list)

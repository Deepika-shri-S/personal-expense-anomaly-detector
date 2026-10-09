import json
from datetime import datetime, timezone


def test_high_anomaly_detection(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]

    # In College profile, normal food is ~170. An amount of 4,500 is >25x normal!
    payload = {
        "profile_id": pid,
        "amount": 4500.0,
        "category": "Food",
        "merchant": "Luxury Palace Dining",
        "transaction_date": datetime.now(timezone.utc).isoformat(),
        "payment_method": "card",
        "payment_channel": "offline",
        "description": "Massive dinner party",
    }
    res = client.post("/api/transactions", data=json.dumps(payload), headers=headers)
    assert res.status_code == 201
    tx = res.get_json()["transaction"]
    assert tx["anomaly_status"] is True
    assert tx["anomaly_severity"] in ["high", "medium"]
    assert len(tx["anomaly_explanation"]) > 0
    # Check that explanation mentions higher spending or category
    reasons_str = " ".join(tx["anomaly_explanation"])
    assert "higher" in reasons_str.lower() or "median" in reasons_str.lower()


def test_user_confirmation_feedback(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]

    # Create an anomalous transaction
    payload = {
        "profile_id": pid,
        "amount": 3500.0,
        "category": "Food",
        "merchant": "Fine Dine",
        "transaction_date": datetime.now(timezone.utc).isoformat(),
        "payment_method": "card",
        "payment_channel": "offline",
    }
    create_res = client.post("/api/transactions", data=json.dumps(payload), headers=headers)
    tx_id = create_res.get_json()["transaction"]["id"]

    # Submit feedback: recognized_legitimate
    confirm_payload = {
        "status": "recognized_legitimate",
        "notes": "Yes, treated my study group after exams.",
    }
    confirm_res = client.post(f"/api/transactions/{tx_id}/confirm", data=json.dumps(confirm_payload), headers=headers)
    assert confirm_res.status_code == 200
    updated_tx = confirm_res.get_json()["transaction"]
    assert updated_tx["user_confirmation_status"] == "recognized_legitimate"
    assert updated_tx["user_notes"] == "Yes, treated my study group after exams."


def test_retrain_profile_model(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]

    res = client.post(f"/api/anomalies/retrain/{pid}", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["details"]["success"] is True

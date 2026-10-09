import json
from datetime import datetime, timezone


def test_create_valid_transaction(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]

    payload = {
        "profile_id": pid,
        "amount": 160.0,
        "category": "Food",
        "merchant": "Campus Canteen",
        "transaction_date": datetime.now(timezone.utc).isoformat(),
        "payment_method": "upi",
        "payment_channel": "offline",
        "location_label": "Canteen Floor 1",
        "description": "Lunch with lab partners",
    }
    res = client.post("/api/transactions", data=json.dumps(payload), headers=headers)
    assert res.status_code == 201
    data = res.get_json()
    assert data["transaction"]["amount"] == 160.0
    assert data["transaction"]["payment_method"] == "upi"
    assert data["transaction"]["payment_channel"] == "offline"
    assert data["transaction"]["anomaly_status"] is False


def test_transaction_validation_errors(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]

    # Negative amount
    bad_payload = {
        "profile_id": pid,
        "amount": -50.0,
        "category": "Food",
        "merchant": "Campus Canteen",
        "transaction_date": "2026-10-01T12:00:00",
        "payment_method": "upi",
        "payment_channel": "offline",
    }
    res = client.post("/api/transactions", data=json.dumps(bad_payload), headers=headers)
    assert res.status_code == 400
    assert "positive" in res.get_json()["error"]

    # Invalid payment channel
    bad_channel = {
        "profile_id": pid,
        "amount": 100.0,
        "category": "Food",
        "merchant": "Store",
        "transaction_date": "2026-10-01T12:00:00",
        "payment_method": "upi",
        "payment_channel": "quantum_teleportation",
    }
    res = client.post("/api/transactions", data=json.dumps(bad_channel), headers=headers)
    assert res.status_code == 400
    assert "payment_channel" in res.get_json()["error"]


def test_get_transactions_with_filters(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]

    res = client.get(f"/api/transactions?profile_id={pid}&category=Food", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_items"] >= 20
    assert len(data["items"]) <= 20 # pagination limit default


def test_delete_transaction(client, seed_data):
    headers = seed_data["headers"]
    # Get a transaction ID
    list_res = client.get("/api/transactions", headers=headers)
    tx_id = list_res.get_json()["items"][0]["id"]

    del_res = client.delete(f"/api/transactions/{tx_id}", headers=headers)
    assert del_res.status_code == 200

    check_res = client.get(f"/api/transactions/{tx_id}", headers=headers)
    assert check_res.status_code == 404

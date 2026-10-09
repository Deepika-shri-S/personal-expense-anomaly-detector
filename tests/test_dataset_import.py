import json


SAMPLE_CSV = """Date,Amount,Store,Category
2026-09-01 10:00:00,120.00,Campus Store,Books
2026-09-02 11:30:00,180.00,Canteen,Food
2026-09-03 14:00:00,50.00,Bus,Travel
"""


def test_preview_csv(client, seed_data):
    headers = seed_data["headers"]
    payload = {"csv_content": SAMPLE_CSV}
    res = client.post("/api/import/preview", data=json.dumps(payload), headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "Amount" in data["total_columns"]
    assert "Date" in data["total_columns"]
    # Check inferred mapping
    mapping = data["suggested_mapping"]
    assert mapping["amount"] == "Amount"
    assert mapping["date"] == "Date"


def test_import_csv(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]
    payload = {
        "csv_content": SAMPLE_CSV,
        "profile_id": pid,
        "mapping": {
            "amount": "Amount",
            "date": "Date",
            "merchant": "Store",
            "category": "Category",
        }
    }
    res = client.post("/api/import/csv", data=json.dumps(payload), headers=headers)
    assert res.status_code == 201
    data = res.get_json()
    assert data["details"]["imported_count"] == 3
    assert data["details"]["error_count"] == 0

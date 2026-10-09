import json


def test_list_profiles(client, seed_data):
    headers = seed_data["headers"]
    res = client.get("/api/profiles", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["count"] == 2
    names = [p["name"] for p in data["profiles"]]
    assert "College" in names
    assert "Home" in names


def test_create_profile(client, seed_data):
    headers = seed_data["headers"]
    payload = {
        "name": "Hostel",
        "description": "Hostel room essentials",
        "currency": "INR",
        "is_default": False,
    }
    res = client.post("/api/profiles", data=json.dumps(payload), headers=headers)
    assert res.status_code == 201
    data = res.get_json()
    assert data["profile"]["name"] == "Hostel"
    assert data["profile"]["currency"] == "INR"


def test_create_duplicate_profile_prevented(client, seed_data):
    headers = seed_data["headers"]
    payload = {
        "name": "College",
        "description": "Duplicate profile",
    }
    res = client.post("/api/profiles", data=json.dumps(payload), headers=headers)
    assert res.status_code == 409
    data = res.get_json()
    assert "already exists" in data["error"]


def test_update_profile(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]
    payload = {
        "name": "Campus & Canteen",
        "description": "Updated description",
    }
    res = client.put(f"/api/profiles/{pid}", data=json.dumps(payload), headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["profile"]["name"] == "Campus & Canteen"

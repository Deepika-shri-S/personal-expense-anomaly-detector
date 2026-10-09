import json


def test_chatbot_spend_this_week(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]

    payload = {
        "message": "How much did I spend this week?",
        "profile_id": pid,
    }
    res = client.post("/api/chatbot/message", data=json.dumps(payload), headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["intent"] == "spending_this_week"
    assert "INR" in data["reply"]
    assert len(data["suggested_questions"]) > 0


def test_chatbot_top_category(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]

    payload = {
        "message": "Which category accounts for the most spending?",
        "profile_id": pid,
    }
    res = client.post("/api/chatbot/message", data=json.dumps(payload), headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["intent"] == "top_category"
    assert "Food" in data["reply"]


def test_chatbot_fraud_inquiry(client, seed_data):
    headers = seed_data["headers"]

    payload = {
        "message": "Is this transaction fraudulent or a scam?",
    }
    res = client.post("/api/chatbot/message", data=json.dumps(payload), headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["intent"] == "fraud_inquiry"
    # Verify that it explains that unusual spending is not automatically fraud
    assert "not automatically fraudulent" in data["reply"]


def test_chatbot_suggestions(client, seed_data):
    headers = seed_data["headers"]
    res = client.get("/api/chatbot/suggestions", headers=headers)
    assert res.status_code == 200
    assert len(res.get_json()["suggestions"]) > 0

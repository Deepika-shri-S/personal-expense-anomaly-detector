def test_analytics_summary(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]

    res = client.get(f"/api/analytics/summary?profile_id={pid}", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_spending"] > 0
    assert data["transaction_count"] >= 20
    assert data["currency"] == "INR"
    assert data["top_category"] == "Food"


def test_spending_trend_with_continuous_dates(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]

    res = client.get(f"/api/analytics/spending-trend?period=day&profile_id={pid}", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["period"] == "day"
    assert len(data["data"]) > 0
    assert "period_start" in data["data"][0]
    assert "total_spending" in data["data"][0]


def test_category_breakdown(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]

    res = client.get(f"/api/analytics/category-breakdown?profile_id={pid}", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["breakdown"]) > 0
    assert data["breakdown"][0]["category"] == "Food"
    assert data["breakdown"][0]["percentage"] > 0


def test_payment_channel_breakdown(client, seed_data):
    headers = seed_data["headers"]
    pid = seed_data["college_profile_id"]

    res = client.get(f"/api/analytics/payment-channel-breakdown?profile_id={pid}", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    channels = {c["channel"]: c for c in data["channels"]}
    assert "offline" in channels
    assert channels["offline"]["total_spending"] > 0


def test_profile_comparison(client, seed_data):
    headers = seed_data["headers"]

    res = client.get("/api/analytics/profile-comparison", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["profiles_count"] == 2

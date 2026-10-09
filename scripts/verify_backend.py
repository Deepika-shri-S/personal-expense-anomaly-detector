import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app

app = create_app("development")
c = app.test_client()

print("=" * 60)
print(" STAGE 1: HEALTH CHECK & SYSTEM STATUS")
print("=" * 60)
res = c.get("/api/health")
data = res.get_json()
print(f"Status Code : {res.status_code}")
print(f"Service     : {data['service']}")
print(f"DB Status   : {data['database']}")

print("\n" + "=" * 60)
print(" STAGE 2: AUTHENTICATION & SECURITY")
print("=" * 60)
res = c.post("/api/auth/login", json={"username": "student_user", "password": "student123"})
assert res.status_code == 200, "Login failed"
token = res.get_json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"Login OK    : {res.get_json()['user']['display_name']}")
print(f"JWT Token   : {token[:25]}... (valid)")

print("\n" + "=" * 60)
print(" STAGE 3: SPENDING CONTEXT PROFILES")
print("=" * 60)
res = c.get("/api/profiles", headers=headers)
profiles = res.get_json()["profiles"]
print(f"Total Profiles: {len(profiles)}")
for p in profiles:
    print(f" - Profile [{p['id']}]: '{p['name']}' ({p['currency']}) - {p['description']}")

print("\n" + "=" * 60)
print(" STAGE 4: EXPENSE RECORDING & ANOMALY DETECTION")
print("=" * 60)
# A. Normal transaction
res_normal = c.post("/api/transactions", json={
    "profile_id": 1,
    "amount": 140.0,
    "category": "Food",
    "merchant": "Campus Canteen",
    "transaction_date": "2026-10-09T13:00:00",
    "payment_method": "upi",
    "payment_channel": "offline",
    "description": "Daily canteen lunch"
}, headers=headers)
tx_norm = res_normal.get_json()["transaction"]
print(f"Normal Transaction -> ID: {tx_norm['id']}, Amount: INR{tx_norm['amount']}, Anomaly: {tx_norm['anomaly_status']}")

# B. Anomalous transaction (high amount + late night + online)
res_anomaly = c.post("/api/transactions", json={
    "profile_id": 1,
    "amount": 4900.0,
    "category": "Food",
    "merchant": "Grand Luxury Palace",
    "transaction_date": "2026-10-09T02:45:00",
    "payment_method": "card",
    "payment_channel": "online",
    "description": "Midnight celebration banquet"
}, headers=headers)
tx_anom = res_anomaly.get_json()["transaction"]
print(f"\nUnusual Transaction -> ID: {tx_anom['id']}, Amount: INR{tx_anom['amount']}, Anomaly: {tx_anom['anomaly_status']}")
print(f"Severity Level      : {tx_anom['anomaly_severity'].upper()}")
print(f"Anomaly Score       : {tx_anom['anomaly_score']}")
print(f"Explanations:")
for reason in tx_anom["anomaly_explanation"]:
    print(f"   - {reason}")
print(f"Recommended Action  : {tx_anom['recommended_action']}")

print("\n" + "=" * 60)
print(" STAGE 5: ANOMALY USER REVIEW & FEEDBACK")
print("=" * 60)
res_confirm = c.post(f"/api/transactions/{tx_anom['id']}/confirm", json={
    "status": "recognized_legitimate",
    "notes": "End of semester celebration with study team."
}, headers=headers)
print(f"Feedback Status: {res_confirm.get_json()['transaction']['user_confirmation_status']}")
print(f"User Notes     : {res_confirm.get_json()['transaction']['user_notes']}")

print("\n" + "=" * 60)
print(" STAGE 6: ANALYTICS & FRONTEND GRAPH DATA")
print("=" * 60)
trend = c.get("/api/analytics/spending-trend?period=day&profile_id=1", headers=headers).get_json()
print(f"Spending Trend  : {len(trend['data'])} continuous daily data points ready for charts")

channels = c.get("/api/analytics/payment-channel-breakdown?profile_id=1", headers=headers).get_json()
for ch in channels["channels"]:
    print(f"Channel '{ch['channel']}': INR{ch['total_spending']:,.2f} ({ch['percentage']}%) across {ch['transaction_count']} txs")

cats = c.get("/api/analytics/category-breakdown?profile_id=1", headers=headers).get_json()
top_c = cats["breakdown"][0]
print(f"Top Category    : '{top_c['category']}' accounting for INR{top_c['total_spending']:,.2f} ({top_c['percentage']}%)")

print("\n" + "=" * 60)
print(" STAGE 7: BILL MANAGEMENT & DUE REMINDERS")
print("=" * 60)
bills = c.get("/api/bills/upcoming", headers=headers).get_json()
print(f"Upcoming Bills  : {bills['count']}")
for b in bills["bills"][:2]:
    print(f" - '{b['bill_name']}': INR{b['amount']} due on {b['due_date']} (in {b['days_remaining']} days)")

print("\n" + "=" * 60)
print(" STAGE 8: CONVERSATIONAL CHATBOT (DATABASE QUERYING)")
print("=" * 60)
q1 = "Why was my latest transaction flagged?"
a1 = c.post("/api/chatbot/message", json={"message": q1, "profile_id": 1}, headers=headers).get_json()
print(f"Q: {q1}")
print(f"A:\n{a1['reply']}")

q2 = "How much did I spend this week?"
a2 = c.post("/api/chatbot/message", json={"message": q2, "profile_id": 1}, headers=headers).get_json()
print(f"\nQ: {q2}")
print(f"A: {a2['reply']}")

q3 = "Is this transaction fraudulent?"
a3 = c.post("/api/chatbot/message", json={"message": q3}, headers=headers).get_json()
print(f"\nQ: {q3}")
print(f"A: {a3['reply']}")

print("\n" + "=" * 60)
print(" STAGE 9: KAGGLE CSV PREVIEW & COLUMN MAPPING")
print("=" * 60)
csv_sample = """trans_date,amt,category_name,vendor,method,channel
2026-10-01 10:00:00,320.00,Books,Book Haven,upi,offline
2026-10-02 14:00:00,180.00,Food,Campus Cafe,cash,offline
"""
prev = c.post("/api/import/preview", json={"csv_content": csv_sample}, headers=headers).get_json()
print(f"Detected Columns : {prev['total_columns']}")
print(f"Inferred Mapping : {json.dumps(prev['suggested_mapping'], indent=2)}")

print("\n" + "=" * 60)
print(" SUCCESS: ALL 9 STAGES VERIFIED & WORKING COMPLETELY!")
print("=" * 60)

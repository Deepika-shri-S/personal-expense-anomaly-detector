import os
from app import create_app

env_name = os.getenv("FLASK_ENV", "development")
app = create_app(env_name)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print("=" * 65)
    print(" Personal Expense Anomaly Detector - Backend Service")
    print("=" * 65)
    print(f" Environment : {env_name}")
    print(f" API Server  : http://localhost:{port}")
    print(f" Health Check: http://localhost:{port}/api/health")
    print(f" Database    : SQLite in instance/expense_detector.db")
    print(" Ready for frontend team API requests.")
    print("=" * 65)
    app.run(host="0.0.0.0", port=port, debug=True)
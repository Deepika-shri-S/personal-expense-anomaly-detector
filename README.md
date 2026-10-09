# Personal Expense Anomaly Detector with AI-Assisted Expense Analysis

A modular, production-ready Python backend designed for second-year CSE students and full-stack project teams. The system learns individual spending patterns, detects potentially unusual transactions using a hybrid Machine Learning & Statistical approach, explains why transactions were flagged, manages upcoming bills, and provides conversational chatbot analysis of personal finances.

---

## 🌟 Key Features

1. **Multi-Context Spending Profiles**:
   - Distinct profiles (e.g., `College`, `Home`, `Travel`, `Hostel`).
   - Completely isolated baselines: Higher spending during travel or college will never contaminate home spending patterns.
   - Independent currencies (`INR`, `USD`, `EUR`).

2. **Hybrid Anomaly Detection Pipeline**:
   - **Robust Statistical Baseline**: Uses Interquartile Range (IQR) and Median (resistant to historical outlier distortion).
   - **Machine Learning Scoring**: Scikit-Learn `IsolationForest` calibrated with multi-feature engineering (amount, time of day, day of week, merchant frequency, category distance).
   - **Contextual Rules**: Late-night spending (00:00 - 05:00), first-time merchants, and high-value online transactions.
   - **Explainable AI**: Returns structured, human-readable explanations and recommended actions rather than arbitrary confidence percentages.
   - **Feedback Learning Loop**: Allows users to mark transactions as *Recognized*, *Unexpected but legitimate*, or *Not recognized* (suspicious) to iteratively refine future models.

3. **Frontend-Ready Chart Analytics**:
   - Pre-aggregated JSON datasets designed for Chart.js, Recharts, or Plotly.
   - Continuous time series trend (fills zero-spending gaps).
   - Category distribution, Payment method breakdown (UPI, Cash, Card, Net Banking), and Online vs. Offline channel comparisons.

4. **Bill Tracking & Due-Date Reminders**:
   - Automatic recurrence management (`monthly`, `quarterly`, `yearly`, `weekly`).
   - Configurable reminder schedules (`[7, 3, 1, 0]` days before due date).
   - Background scheduling powered by `APScheduler` with process-safe guards.

5. **Financial Chatbot**:
   - Direct database querying with zero hallucination.
   - Answers questions regarding weekly/monthly spending, flagged transactions, category leaders, and profile comparisons.
   - Explains the difference between statistical anomalies and fraudulent charges.

6. **Flexible Kaggle CSV Ingestion**:
   - Configurable column mapping for external CSVs.
   - Automatic preview, amount cleaning, date parsing, duplicate detection, and row-level error reporting.

---

## 🛠️ Technology Stack

- **Language**: Python 3.10+ (tested on Python 3.14)
- **Framework**: Flask, Flask-CORS
- **Database**: SQLite with SQLAlchemy ORM (Flask-SQLAlchemy)
- **Machine Learning**: Scikit-Learn (Isolation Forest), NumPy, Pandas, Joblib
- **Scheduler**: APScheduler
- **Testing**: Pytest
- **Authentication**: PyJWT, Werkzeug Security (pbkdf2:sha256 password hashing)

---

## 📂 Project Directory Structure

```text
Personal expense anomaly detector/
│
├── app.py                      # Application entry point & local dev server
├── config.py                   # Environment configuration (Dev, Test, Prod)
├── requirements.txt            # Pinned dependencies
├── pytest.ini                  # Pytest runner configuration
├── .env.example                # Example environment variables
├── .gitignore                  # Git ignore rules for venv, DB, models
├── README.md                   # Complete system documentation
│
├── instance/                   # Runtime files (SQLite DB, Joblib model artifacts)
│   ├── expense_detector.db     # SQLite database file
│   └── models/                 # Saved IsolationForest model checkpoints
│
├── app/                        # Application package
│   ├── __init__.py             # Application factory (create_app) & error handlers
│   ├── extensions.py           # SQLAlchemy, CORS, APScheduler instances
│   │
│   ├── models/                 # Database ORM models
│   │   ├── __init__.py
│   │   ├── user.py             # User accounts & secure password hashing
│   │   ├── profile.py          # Spending context profiles (College, Home, etc.)
│   │   ├── transaction.py      # Expense transactions & anomaly fields
│   │   ├── bill.py             # Upcoming/recurring bills & reminders
│   │   └── alert.py            # In-app notification alerts
│   │
│   ├── routes/                 # RESTful API Blueprints
│   │   ├── __init__.py         # Blueprint registration
│   │   ├── auth.py             # Register, Login, Token verification
│   │   ├── health.py           # System status & DB connectivity
│   │   ├── profiles.py         # CRUD spending profiles
│   │   ├── transactions.py     # CRUD transactions, filters, feedback
│   │   ├── anomalies.py        # Anomaly inspection & model retraining
│   │   ├── analytics.py        # Aggregated chart JSON endpoints
│   │   ├── bills.py            # Bill CRUD, mark as paid, reminder triggers
│   │   ├── alerts.py           # In-app notifications & read/resolve status
│   │   ├── chatbot.py          # Conversational assistant endpoint
│   │   └── import_data.py      # CSV preview, upload, and ML evaluation
│   │
│   ├── services/               # Business logic & Domain layer
│   │   ├── __init__.py
│   │   ├── transaction_service.py
│   │   ├── anomaly_service.py
│   │   ├── analytics_service.py
│   │   ├── bill_service.py
│   │   ├── bill_scheduler.py
│   │   ├── dataset_service.py
│   │   ├── chatbot_service.py
│   │   └── notification_service.py
│   │
│   ├── ml/                     # Machine Learning Pipeline
│   │   ├── __init__.py
│   │   ├── feature_engineering.py   # Baseline extractor & feature transformation
│   │   ├── train_model.py           # Isolation Forest training & Joblib serialization
│   │   ├── predict_anomaly.py       # Hybrid predictor & explanation generator
│   │   └── evaluate_model.py        # Supervised & feedback evaluation metrics
│   │
│   └── utils/                  # Helper utilities
│       ├── __init__.py
│       ├── validators.py       # Input validation logic
│       └── date_utils.py       # Calendar bounds & date parsing
│
├── data/                       # Datasets & synthetic testing data
│   ├── README.md               # Kaggle mapping & privacy guide
│   └── sample_transactions.csv # 30+ synthetic student transactions with anomalies
│
├── scripts/                    # Management scripts
│   ├── initialize_db.py        # Schema setup, demo user, & sample transactions
│   └── import_dataset.py       # CLI importer for external Kaggle CSVs
│
└── tests/                      # Pytest test suite (25 test cases)
    ├── conftest.py             # In-memory SQLite fixtures & mock tokens
    ├── test_profiles.py
    ├── test_transactions.py
    ├── test_anomalies.py
    ├── test_analytics.py
    ├── test_bills.py
    ├── test_chatbot.py
    └── test_dataset_import.py
```

---

## 🚀 Setup & Execution Guide

### 1. Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14 installed.
- Git (optional).

### 2. Virtual Environment Setup
Open PowerShell or your preferred terminal in the project directory:

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# (On Linux / macOS)
# source venv/bin/activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Initialize Database and Seed Data
Run the seeding script to create database tables, create the demo student user, populate sample transactions with realistic anomalies, and train the initial ML models:

```powershell
python scripts/initialize_db.py
```

**Default Demo Credentials:**
- **Username**: `student_user`
- **Password**: `student123`

### 5. Run the Backend Server
```powershell
python app.py
```

The server will start at `http://localhost:5000`.
- Health check: `http://localhost:5000/api/health`

---

## 🧪 Running Automated Tests

Run the complete test suite with verbose output:

```powershell
pytest -v
```

All 25 unit and integration tests run against an isolated in-memory SQLite database.

---

## 🧠 Machine Learning & Anomaly Detection Details

### Hybrid Detection Architecture

```text
[Incoming Transaction]
         │
         ├───► 1. Robust Statistical Baseline (Median, IQR, Category Deviation)
         │
         ├───► 2. Feature Engineering (Log Amount, Hour, Channel, Merchant Frequency)
         │              │
         │              ▼
         │        Isolation Forest Scoring (sklearn)
         │
         ├───► 3. Contextual Rule Engine (Midnight Spend, Unseen Merchant, High Multiplier)
         │
         ▼
[Blended Anomaly Score (0.0 to 1.0) & Severity (Low / Medium / High)]
         │
         ▼
[Human-Readable Explanations + Recommended Actions + In-App Alerts]
```

1. **Cold-Start Handling**: If a profile has fewer than 15 historical transactions, the system uses an explainable statistical baseline with `is_preliminary: true` to prevent overfitting on tiny samples.
2. **Robust Statistics**: Uses median and IQR instead of mean and standard deviation so that a single large purchase (e.g. college fees or laptop) does not artificially distort the regular food/transit baseline.
3. **User Feedback Integration**: Flagged transactions confirmed as `not_recognized` are excluded from the legitimate baseline.

---

## 📡 REST API Reference

All protected endpoints require an authorization token in the header:
```http
Authorization: Bearer <your_jwt_token>
```
*(For rapid frontend development testing, you can also pass `X-User-Id: 1`)*

### 1. Authentication (`/api/auth`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register new user (auto-creates default profiles) |
| `POST` | `/api/auth/login` | Login and obtain JWT token |
| `GET` | `/api/auth/me` | Get authenticated user info & profiles |

#### Login Request:
```json
{
  "username": "student_user",
  "password": "student123"
}
```
#### Response:
```json
{
  "message": "Login successful.",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "student_user",
    "display_name": "Deepika (Student Developer)"
  }
}
```

---

### 2. Spending Profiles (`/api/profiles`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/profiles` | List all profiles for user |
| `POST` | `/api/profiles` | Create new profile (`name`, `currency`, `description`) |
| `GET` | `/api/profiles/<id>` | View single profile |
| `PUT` | `/api/profiles/<id>` | Update profile |
| `DELETE` | `/api/profiles/<id>` | Delete profile |

---

### 3. Transactions (`/api/transactions`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/transactions` | Query transactions (filters: `profile_id`, `category`, `merchant`, `payment_method`, `payment_channel`, `anomaly_status`, `start_date`, `end_date`, `page`, `per_page`) |
| `POST` | `/api/transactions` | Record transaction (runs anomaly detection & creates alert) |
| `GET` | `/api/transactions/<id>` | View individual transaction |
| `PUT` | `/api/transactions/<id>` | Edit transaction |
| `DELETE` | `/api/transactions/<id>` | Delete transaction |
| `POST` | `/api/transactions/<id>/confirm` | User review feedback (`status`: `recognized_legitimate`, `unexpected_legitimate`, `not_recognized`) |

#### Adding a Transaction:
```json
POST /api/transactions
{
  "profile_id": 1,
  "amount": 3200.00,
  "category": "Food",
  "merchant": "Luxury Bistro",
  "transaction_date": "2026-10-09T20:30:00",
  "payment_method": "card",
  "payment_channel": "offline",
  "location_label": "Downtown",
  "description": "Celebration dinner"
}
```
#### Response with Anomaly Evaluation:
```json
{
  "message": "Transaction recorded successfully.",
  "transaction": {
    "id": 105,
    "amount": 3200.0,
    "category": "Food",
    "merchant": "Luxury Bistro",
    "payment_method": "card",
    "payment_channel": "offline",
    "anomaly_status": true,
    "anomaly_severity": "medium",
    "anomaly_score": 0.74,
    "anomaly_explanation": [
      "The amount (INR 3,200.00) is 19.4x higher than your usual median spending (INR 165.00) in 'Food'.",
      "This is your first recorded transaction with merchant 'Luxury Bistro'."
    ],
    "recommended_action": "Review this expense in your daily summary and verify the amount."
  }
}
```

---

### 4. Spending Analytics (`/api/analytics`)

Pre-formatted JSON endpoints for frontend graphs:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/analytics/summary` | KPI cards (total spent, count, anomalies, average) |
| `GET` | `/api/analytics/spending-trend?period=week` | Continuous time-series trend (periods: `day`, `week`, `month`) |
| `GET` | `/api/analytics/category-breakdown` | Category spending & percentages |
| `GET` | `/api/analytics/payment-channel-breakdown` | Online vs. Offline comparison |
| `GET` | `/api/analytics/payment-method-breakdown` | UPI, Cash, Card, Net Banking distribution |
| `GET` | `/api/analytics/profile-comparison` | Compare spending across College vs. Home vs. Travel |
| `GET` | `/api/analytics/anomalies-summary` | Breakdown of anomalies by severity & review status |

#### Trend Response Example:
```json
GET /api/analytics/spending-trend?period=week&profile_id=1
{
  "currency": "INR",
  "period": "week",
  "data": [
    { "period_start": "2026-09-01", "total_spending": 850.00, "transaction_count": 5 },
    { "period_start": "2026-09-08", "total_spending": 1200.00, "transaction_count": 7 }
  ]
}
```

---

### 5. Bills & Reminders (`/api/bills`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/bills` | List bills |
| `POST` | `/api/bills` | Create bill (`due_date`, `recurrence_type`, `reminder_days`) |
| `GET` | `/api/bills/upcoming` | Bills due within N days (default 30) |
| `GET` | `/api/bills/overdue` | Unpaid bills past due date |
| `POST` | `/api/bills/<id>/pay` | Mark as paid (automatically advances recurring due dates!) |
| `POST` | `/api/bills/trigger-reminders` | Manually run due date check & generate alert notifications |

---

### 6. Conversational Chatbot (`/api/chatbot`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/chatbot/message` | Natural-language query about spending, bills, or anomalies |
| `GET` | `/api/chatbot/suggestions` | Suggested prompt questions for UI quick-buttons |

#### Example Query:
```json
POST /api/chatbot/message
{
  "message": "Why was my latest transaction flagged?",
  "profile_id": 1
}
```
#### Response:
```json
{
  "reply": "Your transaction of INR 3,200.00 at 'Luxury Fine Dining Bistro' was flagged with MEDIUM severity.\n\nReasons:\n• Amount INR 3,200.00 is 19.4x higher than your usual median spending (INR 165.00) in 'Food'.\n\nRecommended action: Review this expense in your daily summary and verify the amount.",
  "intent": "why_flagged_latest",
  "related_transactions": [26],
  "suggested_questions": [
    "What should I review in my recent spending?",
    "How much did I spend this month?",
    "Which category accounts for the most spending?"
  ]
}
```

---

### 7. Dataset Ingestion & Evaluation (`/api/import`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/import/preview` | Upload or pass CSV string to preview columns & inferred mappings |
| `POST` | `/api/import/csv` | Import CSV with custom mapping, amount cleaning, & duplicate skipping |
| `POST` | `/api/import/evaluate` | Evaluates model with ground truth (Precision/Recall/F1/Confusion Matrix) or user review feedback rates |

#### CLI Importer Tool:
```powershell
python scripts/import_dataset.py --csv data/sample_transactions.csv --preview
python scripts/import_dataset.py --csv data/sample_transactions.csv --profile College
```

---

## 🎨 Note for Frontend Teammates

- **CORS is enabled**: All `/api/*` endpoints allow Cross-Origin Resource Sharing from any local development frontend port (e.g., `localhost:3000`, `localhost:5173`, etc.).
- **Chart-Ready JSON**: All analytics endpoints return formatted objects with numbers, labels, and percentages so you can pass them directly to Chart.js, Recharts, or ApexCharts without custom data munging.
- **Error Format**: All errors return standard JSON: `{"error": "Description of error"}` with standard HTTP status codes (`400`, `401`, `404`, `409`, `500`).

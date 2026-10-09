# Dataset Integration & Guidance

## Overview

This project is designed to bridge the gap between **public machine learning datasets** (such as Kaggle credit card/fraud datasets) and **real-world personalized spending habits**.

---

## 1. Why Personal Expense Anomaly Detection Differs from Public Fraud Datasets

| Public Fraud Datasets (e.g., Kaggle) | Personal Expense Anomaly Detection |
| :--- | :--- |
| Focus on binary fraud (stolen credit cards, unauthorized charges). | Focus on personal spending deviations (unusual amounts, first-time merchants, lifestyle changes). |
| Aggregated across thousands of anonymous users with PCA-anonymized features (`V1-V28`). | Scoped to **individual user profiles** (e.g., "College", "Home", "Travel"). |
| Payment channels and location contexts are usually masked or unavailable. | Distinguishes distinct **payment methods** (UPI, Cash, Card) and **payment channels** (Online vs Offline). |
| Static labels ("Class 1 = Fraud"). | User feedback (`recognized_legitimate`, `unexpected_legitimate`, `not_recognized`) continuously informs baselines. |

---

## 2. Supported Kaggle Dataset Mapping

When downloading a CSV from Kaggle, use our flexible `/api/import/csv` or `scripts/import_dataset.py` pipeline.

The importer accepts custom mappings:

```json
{
  "amount": "Amount",
  "date": "Time",
  "category": "Category",
  "merchant": "Merchant",
  "payment_method": "Payment_Type",
  "payment_channel": "Channel"
}
```

If columns are omitted in the Kaggle CSV:
- **Missing Category**: Defaults to `"General"`.
- **Missing Merchant**: Defaults to `"Imported Merchant"`.
- **Missing Payment Channel**: Inferred as `"offline"` for cash and `"online"` for cards/UPI.

---

## 3. Privacy & Synthetic Data Rules

1. **Do not commit actual personal bank statements or credit card numbers.**
2. `sample_transactions.csv` contains purely synthetic, realistic college student expenses for local development and testing.
3. Keep user database files (`instance/*.db`) in `.gitignore`.

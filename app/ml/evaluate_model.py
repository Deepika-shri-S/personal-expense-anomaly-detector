from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from app.ml.train_model import train_profile_model
from app.ml.predict_anomaly import predict_transaction_anomaly
from pathlib import Path


def evaluate_with_ground_truth(
    df: pd.DataFrame,
    label_col: str,
    models_dir: Path,
    profile_id: int = 1,
    test_ratio: float = 0.20,
) -> Dict[str, Any]:
    """
    Chronological train/test split evaluation for datasets containing known anomaly/fraud labels.
    Calculates Precision, Recall, F1-score, Confusion Matrix, and False Positive Rate.
    Avoids train/test data leakage.
    """
    if df.empty or label_col not in df.columns:
        return {
            "error": f"Dataset is empty or label column '{label_col}' is missing.",
            "metrics_available": False,
        }

    # Sort chronologically if transaction_date or date column exists
    date_col = next((c for c in ["transaction_date", "date", "Date", "timestamp"] if c in df.columns), None)
    if date_col:
        df_sorted = df.sort_values(by=date_col).copy()
    else:
        df_sorted = df.copy()

    total_samples = len(df_sorted)
    if total_samples < 20:
        return {
            "error": "Dataset too small for reliable train/test evaluation (minimum 20 samples required).",
            "metrics_available": False,
        }

    split_idx = int(total_samples * (1.0 - test_ratio))
    train_df = df_sorted.iloc[:split_idx].copy()
    test_df = df_sorted.iloc[split_idx:].copy()

    # Train model on train set only
    bundle, train_meta = train_profile_model(
        profile_id=profile_id,
        transactions_df=train_df,
        models_dir=models_dir,
        min_samples=10,
    )

    # Evaluate on test set
    y_true = (test_df[label_col].astype(int) > 0).astype(int).values
    y_pred = []

    for _, row in test_df.iterrows():
        tx_dict = row.to_dict()
        res = predict_transaction_anomaly(tx_dict, bundle)
        y_pred.append(1 if res.is_anomaly else 0)

    y_pred = np.array(y_pred)

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    # cm layout: [[TN, FP], [FN, TP]]
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

    return {
        "evaluation_type": "chronological_supervised",
        "metrics_available": True,
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "metrics": {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "false_positive_rate": round(fpr, 4),
        },
        "confusion_matrix": {
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
        },
        "notes": (
            "Model was evaluated on the final chronological 20% of the dataset to simulate real-world arrival. "
            "Note that general fraud dataset patterns may differ from an individual's personal spending habits."
        ),
    }


def evaluate_unlabelled_feedback(
    transactions_list: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluation method for unlabelled personal transactions based on user review feedback
    and statistical alert rates.
    """
    total = len(transactions_list)
    if total == 0:
        return {
            "evaluation_type": "unlabelled_feedback",
            "metrics_available": False,
            "message": "No transactions available for feedback evaluation.",
        }

    flagged = [t for t in transactions_list if t.get("anomaly_status")]
    flagged_count = len(flagged)
    reviewed_count = 0
    confirmed_legitimate = 0
    confirmed_unexpected = 0
    confirmed_suspicious = 0

    for t in flagged:
        status = t.get("user_confirmation_status", "pending")
        if status != "pending":
            reviewed_count += 1
            if status == "recognized_legitimate":
                confirmed_legitimate += 1
            elif status == "unexpected_legitimate":
                confirmed_unexpected += 1
            elif status == "not_recognized":
                confirmed_suspicious += 1

    feedback_rate = (reviewed_count / flagged_count) if flagged_count > 0 else 0.0
    false_alert_rate = (confirmed_legitimate / reviewed_count) if reviewed_count > 0 else 0.0

    return {
        "evaluation_type": "user_feedback_and_alert_rate",
        "metrics_available": True,
        "total_transactions": total,
        "flagged_anomalies": flagged_count,
        "anomaly_rate": round(flagged_count / total, 4) if total > 0 else 0.0,
        "reviewed_by_user": reviewed_count,
        "feedback_coverage": round(feedback_rate, 4),
        "feedback_breakdown": {
            "recognized_legitimate": confirmed_legitimate,
            "unexpected_but_legitimate": confirmed_unexpected,
            "not_recognized_suspicious": confirmed_suspicious,
            "pending_review": flagged_count - reviewed_count,
        },
        "false_alert_rate_of_reviewed": round(false_alert_rate, 4),
        "explanation": (
            "Because personal expense tracking lacks synthetic ground-truth fraud labels, "
            "the system measures alert volume, user feedback distribution, and false-alert rates "
            "from actual user confirmations."
        ),
    }

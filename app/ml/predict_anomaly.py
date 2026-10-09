import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.ml.train_model import ProfileModelBundle
from app.utils.date_utils import parse_datetime


class AnomalyPredictionResult:
    """Structured result of anomaly prediction."""

    def __init__(
        self,
        is_anomaly: bool,
        severity: Optional[str],
        anomaly_score: float,
        reasons: List[str],
        recommended_action: str,
        is_preliminary: bool = False,
        metrics: Optional[Dict[str, Any]] = None,
    ):
        self.is_anomaly = is_anomaly
        self.severity = severity
        self.anomaly_score = round(anomaly_score, 4)
        self.reasons = reasons
        self.recommended_action = recommended_action
        self.is_preliminary = is_preliminary
        self.metrics = metrics or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_anomaly": self.is_anomaly,
            "severity": self.severity,
            "anomaly_score": self.anomaly_score,
            "reasons": self.reasons,
            "recommended_action": self.recommended_action,
            "is_preliminary": self.is_preliminary,
            "metrics": self.metrics,
        }


def predict_transaction_anomaly(
    tx_dict: Dict[str, Any],
    bundle: Optional[ProfileModelBundle],
    currency: str = "INR",
) -> AnomalyPredictionResult:
    """
    Perform hybrid anomaly detection:
    1. Statistical baseline analysis (robust median, IQR)
    2. Machine learning scoring via Isolation Forest (if available)
    3. Rule-based severity and context assessment
    4. Human-readable explanation generation
    """
    amount = float(tx_dict.get("amount", 0.0))
    category = str(tx_dict.get("category", "")).strip()
    merchant = str(tx_dict.get("merchant", "")).strip()
    channel = str(tx_dict.get("payment_channel", "offline")).strip().lower()
    tx_dt = parse_datetime(tx_dict.get("transaction_date")) or datetime.utcnow()
    hour = tx_dt.hour

    reasons: List[str] = []
    is_preliminary = False
    ml_score = 0.0
    stat_score = 0.0

    # Fallback when no bundle exists at all (e.g., brand new profile with 0 history)
    if bundle is None or not bundle.extractor:
        is_preliminary = True
        # Cold start heuristic
        is_high = amount > 10000.0
        reasons.append(
            f"Your spending profile is newly created. This transaction is being evaluated against general baseline rules."
        )
        if is_high:
            reasons.append(f"Amount {currency} {amount:,.2f} is relatively high for an initial transaction.")
            return AnomalyPredictionResult(
                is_anomaly=True,
                severity="medium",
                anomaly_score=0.55,
                reasons=reasons,
                recommended_action="Confirm that this amount is correct for your new profile.",
                is_preliminary=True,
            )
        return AnomalyPredictionResult(
            is_anomaly=False,
            severity=None,
            anomaly_score=0.15,
            reasons=["Spending is within normal parameters for an initial transaction."],
            recommended_action="No action required.",
            is_preliminary=True,
        )

    extractor = bundle.extractor
    cat_stats = extractor.category_stats.get(category)
    prof_stats = extractor.profile_stats

    # Check merchant familiarity
    merchant_key = merchant.lower()
    merchant_freq = extractor.merchant_frequencies.get(merchant_key, 0.0)
    is_new_merchant = merchant_freq == 0.0

    # 1. Statistical Baseline Assessment
    cat_median = cat_stats["median"] if cat_stats else prof_stats.get("median", 100.0)
    cat_iqr = cat_stats["iqr"] if cat_stats else prof_stats.get("iqr", 50.0)
    ratio = amount / max(cat_median, 1.0)
    iqr_distance = (amount - cat_median) / max(cat_iqr, 1.0)

    # Statistical score mapped between 0.0 and 1.0
    if iqr_distance > 0:
        stat_score = min(1.0, iqr_distance / 4.0)
    else:
        stat_score = 0.1

    # 2. Machine Learning Scoring
    if bundle.is_ml_active and bundle.model is not None:
        try:
            feat_vec = extractor.extract_features_single(tx_dict).reshape(1, -1)
            raw_decision = float(bundle.model.decision_function(feat_vec)[0])
            # Sklearn decision_function: negative for anomalies, positive for inliers
            # Logistic conversion: score in [0.0, 1.0]
            ml_score = 1.0 / (1.0 + np.exp(raw_decision * 6.0))
        except Exception:
            ml_score = stat_score
    else:
        is_preliminary = True
        ml_score = stat_score

    # Blended anomaly score: 60% ML + 40% statistical baseline (or 100% stat if preliminary)
    if is_preliminary:
        combined_score = stat_score
    else:
        combined_score = 0.60 * ml_score + 0.40 * stat_score

    # 3. Contextual Rule Checks & Explanations
    # Amount check
    if ratio >= 3.0:
        reasons.append(
            f"The amount ({currency} {amount:,.2f}) is {ratio:.1f}x higher than your usual median spending "
            f"({currency} {cat_median:,.2f}) in '{category}'."
        )
    elif ratio >= 1.8 and amount > 500:
        reasons.append(
            f"The amount ({currency} {amount:,.2f}) is noticeably higher than your category typical spending "
            f"({currency} {cat_median:,.2f})."
        )

    # Merchant check
    if is_new_merchant and extractor.total_transactions >= 5:
        if amount > cat_median:
            reasons.append(f"This is your first recorded transaction with merchant '{merchant}'.")

    # Time of day check (midnight to 5 AM)
    if hour in [0, 1, 2, 3, 4] and amount >= 500:
        reasons.append(
            f"The transaction occurred at {hour:02d}:{tx_dt.minute:02d}, outside your usual daytime hours."
        )

    # Channel check
    if channel == "online" and cat_stats and amount > 2.0 * cat_median:
        reasons.append("High-value online transaction compared to your typical category payments.")

    # 4. Severity Assessment
    severity: Optional[str] = None
    is_anomaly = False

    if combined_score >= 0.70 or ratio >= 3.5:
        is_anomaly = True
        severity = "high"
        recommended_action = "Review this transaction immediately and confirm whether you recognize and authorized it."
    elif combined_score >= 0.48 or ratio >= 2.0 or (is_new_merchant and ratio >= 1.8):
        is_anomaly = True
        severity = "medium"
        recommended_action = "Review this expense in your daily summary and verify the amount."
    elif combined_score >= 0.35 and (ratio >= 1.4 or is_new_merchant):
        is_anomaly = True
        severity = "low"
        recommended_action = "Keep track of this expense in your regular budget review."
    else:
        is_anomaly = False
        severity = None
        recommended_action = "No action required. Spending aligns with your normal profile patterns."
        if not reasons:
            reasons.append("Spending aligns with your established profile pattern.")

    if is_preliminary and is_anomaly:
        reasons.append(
            f"Note: This profile has {extractor.total_transactions} transactions. "
            f"Detection is currently using statistical baseline comparison."
        )

    metrics = {
        "ratio_to_median": round(ratio, 2),
        "iqr_distance": round(iqr_distance, 2),
        "category_median": round(cat_median, 2),
        "ml_score": round(ml_score, 4),
        "stat_score": round(stat_score, 4),
    }

    return AnomalyPredictionResult(
        is_anomaly=is_anomaly,
        severity=severity,
        anomaly_score=combined_score,
        reasons=reasons,
        recommended_action=recommended_action,
        is_preliminary=is_preliminary,
        metrics=metrics,
    )

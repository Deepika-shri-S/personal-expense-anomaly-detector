import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.utils.date_utils import parse_datetime


class ExpenseFeatureExtractor:
    """
    Feature engineering pipeline for personal expense transactions.
    Extracts statistical baseline comparisons, temporal signals, and categorical frequencies
    while strictly preventing data leakage of IDs.
    """

    def __init__(self, historical_df: Optional[pd.DataFrame] = None):
        """
        historical_df: DataFrame of historical transactions for a SPECIFIC profile.
        Columns expected: amount, category, merchant, transaction_date, payment_channel, payment_method, user_confirmation_status
        """
        self.category_stats: Dict[str, Dict[str, float]] = {}
        self.profile_stats: Dict[str, float] = {}
        self.merchant_frequencies: Dict[str, float] = {}
        self.known_categories: List[str] = []
        self.total_transactions: int = 0

        if historical_df is not None and not historical_df.empty:
            self.fit(historical_df)

    def fit(self, df: pd.DataFrame) -> "ExpenseFeatureExtractor":
        """Compute robust baseline statistics from historical profile transactions."""
        if df.empty:
            return self

        # Exclude confirmed fraudulent / unrecognized transactions from baseline calculations
        valid_history = df[df["user_confirmation_status"] != "not_recognized"].copy()
        if valid_history.empty:
            valid_history = df.copy()

        self.total_transactions = len(valid_history)

        # Profile-level robust statistics (Median and Interquartile Range)
        amounts = valid_history["amount"].astype(float).values
        p25, p50, p75 = np.percentile(amounts, [25, 50, 75])
        iqr = max(p75 - p25, 1.0)
        self.profile_stats = {
            "median": float(p50),
            "p25": float(p25),
            "p75": float(p75),
            "iqr": float(iqr),
            "mean": float(np.mean(amounts)),
            "std": float(np.std(amounts)) if len(amounts) > 1 else 1.0,
            "max": float(np.max(amounts)),
        }

        # Category-level robust statistics
        self.category_stats = {}
        for category, group in valid_history.groupby("category"):
            c_amounts = group["amount"].astype(float).values
            if len(c_amounts) >= 3:
                c25, c50, c75 = np.percentile(c_amounts, [25, 50, 75])
                c_iqr = max(c75 - c25, 1.0)
            else:
                c25 = float(np.min(c_amounts))
                c50 = float(np.median(c_amounts))
                c75 = float(np.max(c_amounts))
                c_iqr = max(c75 - c25, 1.0)

            self.category_stats[str(category)] = {
                "count": len(c_amounts),
                "median": float(c50),
                "p25": float(c25),
                "p75": float(c75),
                "iqr": float(c_iqr),
                "mean": float(np.mean(c_amounts)),
                "std": float(np.std(c_amounts)) if len(c_amounts) > 1 else 1.0,
            }

        # Merchant frequency distribution
        merchant_counts = valid_history["merchant"].astype(str).str.lower().value_counts()
        self.merchant_frequencies = {
            m: count / self.total_transactions 
            for m, count in merchant_counts.items()
        }

        self.known_categories = list(self.category_stats.keys())
        return self

    def extract_features_single(self, tx_dict: Dict[str, Any]) -> np.ndarray:
        """
        Extract numerical feature vector for a single transaction.
        Feature vector:
        0: amount
        1: log_amount
        2: hour of day (0-23)
        3: day of week (0-6)
        4: is_weekend (0 or 1)
        5: payment_channel_online (1 if online, 0 if offline)
        6: merchant_frequency (0.0 to 1.0)
        7: ratio_to_category_median
        8: category_iqr_distance ((amount - median) / iqr)
        9: ratio_to_profile_median
        10: is_first_time_merchant (1 if never seen before, 0 otherwise)
        """
        amount = float(tx_dict.get("amount", 0.0))
        log_amount = float(np.log1p(max(0.0, amount)))

        tx_dt = parse_datetime(tx_dict.get("transaction_date")) or datetime.utcnow()
        hour = float(tx_dt.hour)
        day_of_week = float(tx_dt.weekday())
        is_weekend = 1.0 if day_of_week >= 5 else 0.0

        channel = str(tx_dict.get("payment_channel", "offline")).strip().lower()
        channel_online = 1.0 if channel == "online" else 0.0

        merchant = str(tx_dict.get("merchant", "")).strip().lower()
        merchant_freq = float(self.merchant_frequencies.get(merchant, 0.0))
        is_new_merchant = 1.0 if merchant_freq == 0.0 else 0.0

        category = str(tx_dict.get("category", "")).strip()
        cat_stats = self.category_stats.get(category)

        if cat_stats:
            cat_median = max(cat_stats["median"], 1.0)
            ratio_cat = amount / cat_median
            iqr_dist = (amount - cat_stats["median"]) / max(cat_stats["iqr"], 1.0)
        else:
            # Unseen category fallback to profile baseline
            prof_median = max(self.profile_stats.get("median", 100.0), 1.0)
            ratio_cat = amount / prof_median
            iqr_dist = (amount - prof_median) / max(self.profile_stats.get("iqr", 50.0), 1.0)

        prof_median = max(self.profile_stats.get("median", 100.0), 1.0)
        ratio_prof = amount / prof_median

        return np.array([
            amount,
            log_amount,
            hour,
            day_of_week,
            is_weekend,
            channel_online,
            merchant_freq,
            ratio_cat,
            iqr_dist,
            ratio_prof,
            is_new_merchant
        ], dtype=np.float64)

    def extract_features_df(self, df: pd.DataFrame) -> np.ndarray:
        """Extract feature matrix for multiple transactions."""
        rows = [self.extract_features_single(row.to_dict()) for _, row in df.iterrows()]
        if not rows:
            return np.empty((0, 11), dtype=np.float64)
        return np.vstack(rows)

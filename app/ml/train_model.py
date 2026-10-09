import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from app.ml.feature_engineering import ExpenseFeatureExtractor


class ProfileModelBundle:
    """Encapsulates the trained ML model, feature extractor, and training metadata."""

    def __init__(
        self,
        profile_id: int,
        model: Optional[IsolationForest],
        extractor: ExpenseFeatureExtractor,
        training_samples: int,
        contamination: float,
        trained_at: str,
        is_ml_active: bool = False,
    ):
        self.profile_id = profile_id
        self.model = model
        self.extractor = extractor
        self.training_samples = training_samples
        self.contamination = contamination
        self.trained_at = trained_at
        self.is_ml_active = is_ml_active


def train_profile_model(
    profile_id: int,
    transactions_df: pd.DataFrame,
    models_dir: Path,
    min_samples: int = 15,
    contamination: float = 0.08,
) -> Tuple[ProfileModelBundle, Dict[str, Any]]:
    """
    Train an IsolationForest model for a specific spending profile.
    If sample count is below min_samples, creates a statistical baseline bundle.
    """
    models_dir = Path(models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / f"model_profile_{profile_id}.joblib"

    sample_count = len(transactions_df)
    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).isoformat()

    # Step 1: Fit Feature Extractor baseline
    extractor = ExpenseFeatureExtractor(transactions_df)

    # Step 2: Check sample threshold
    if sample_count < min_samples:
        bundle = ProfileModelBundle(
            profile_id=profile_id,
            model=None,
            extractor=extractor,
            training_samples=sample_count,
            contamination=contamination,
            trained_at=now_str,
            is_ml_active=False,
        )
        # Save baseline bundle
        joblib.dump(bundle, model_path)
        return bundle, {
            "status": "baseline_only",
            "message": f"Profile has {sample_count} transactions (minimum {min_samples} needed for ML). Statistical baseline active.",
            "training_samples": sample_count,
            "is_ml_active": False,
        }

    # Step 3: Extract feature matrix
    X = extractor.extract_features_df(transactions_df)

    # Step 4: Fit Isolation Forest
    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X)

    bundle = ProfileModelBundle(
        profile_id=profile_id,
        model=model,
        extractor=extractor,
        training_samples=sample_count,
        contamination=contamination,
        trained_at=now_str,
        is_ml_active=True,
    )

    joblib.dump(bundle, model_path)

    return bundle, {
        "status": "success",
        "message": f"Isolation Forest trained successfully on {sample_count} transactions.",
        "training_samples": sample_count,
        "is_ml_active": True,
        "trained_at": now_str,
    }


def load_profile_model(profile_id: int, models_dir: Path) -> Optional[ProfileModelBundle]:
    """Load cached model bundle from disk if available."""
    model_path = Path(models_dir) / f"model_profile_{profile_id}.joblib"
    if not model_path.exists():
        return None
    try:
        bundle = joblib.load(model_path)
        return bundle
    except Exception:
        return None

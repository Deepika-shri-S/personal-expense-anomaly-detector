from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import pandas as pd
from flask import current_app
from app.extensions import db
from app.models.transaction import Transaction
from app.models.profile import SpendingProfile
from app.ml.train_model import train_profile_model, load_profile_model, ProfileModelBundle
from app.ml.predict_anomaly import predict_transaction_anomaly, AnomalyPredictionResult


class AnomalyService:
    """Service orchestrating machine learning anomaly detection and model lifecycle per profile."""

    @staticmethod
    def get_models_dir() -> Path:
        return Path(current_app.config.get("ML_MODELS_DIR", "instance/models"))

    @staticmethod
    def get_profile_bundle(profile_id: int, user_id: int) -> Optional[ProfileModelBundle]:
        """Load trained model bundle for profile, or create an initial baseline if none exists."""
        models_dir = AnomalyService.get_models_dir()
        bundle = load_profile_model(profile_id, models_dir)

        if bundle is not None:
            return bundle

        # Build initial baseline from existing transactions if available
        tx_query = Transaction.query.filter_by(profile_id=profile_id, user_id=user_id).all()
        if tx_query:
            data = [t.to_dict() for t in tx_query]
            df = pd.DataFrame(data)
            bundle, _ = train_profile_model(
                profile_id=profile_id,
                transactions_df=df,
                models_dir=models_dir,
                min_samples=current_app.config.get("MIN_TRANSACTIONS_FOR_ML", 15),
                contamination=current_app.config.get("CONTAMINATION_RATE", 0.08),
            )
            return bundle

        return None

    @staticmethod
    def evaluate_new_transaction(
        tx_dict: Dict[str, Any], 
        profile: SpendingProfile
    ) -> AnomalyPredictionResult:
        """Evaluate a single transaction against its profile baseline and ML model."""
        bundle = AnomalyService.get_profile_bundle(profile.id, profile.user_id)
        return predict_transaction_anomaly(
            tx_dict=tx_dict,
            bundle=bundle,
            currency=profile.currency or "INR"
        )

    @staticmethod
    def retrain_profile(profile_id: int, user_id: int) -> Dict[str, Any]:
        """Retrain the profile model using all verified transactions."""
        profile = SpendingProfile.query.filter_by(id=profile_id, user_id=user_id).first()
        if not profile:
            return {"success": False, "error": "Profile not found."}

        tx_list = Transaction.query.filter_by(profile_id=profile_id, user_id=user_id).all()
        if not tx_list:
            return {"success": False, "error": "No transactions found for this profile."}

        data = [t.to_dict() for t in tx_list]
        df = pd.DataFrame(data)

        models_dir = AnomalyService.get_models_dir()
        bundle, meta = train_profile_model(
            profile_id=profile_id,
            transactions_df=df,
            models_dir=models_dir,
            min_samples=current_app.config.get("MIN_TRANSACTIONS_FOR_ML", 15),
            contamination=current_app.config.get("CONTAMINATION_RATE", 0.08),
        )

        return {
            "success": True,
            "profile_id": profile_id,
            "profile_name": profile.name,
            "metadata": meta,
        }

    @staticmethod
    def batch_recalculate_profile(profile_id: int, user_id: int) -> Dict[str, Any]:
        """Recalculate anomaly scores and explanations for all transactions in a profile."""
        profile = SpendingProfile.query.filter_by(id=profile_id, user_id=user_id).first()
        if not profile:
            return {"success": False, "error": "Profile not found."}

        # First retrain baseline/model
        retrain_res = AnomalyService.retrain_profile(profile_id, user_id)
        if not retrain_res.get("success"):
            return retrain_res

        bundle = AnomalyService.get_profile_bundle(profile_id, user_id)
        tx_list = Transaction.query.filter_by(profile_id=profile_id, user_id=user_id).all()

        updated_count = 0
        anomaly_count = 0

        for tx in tx_list:
            pred = predict_transaction_anomaly(
                tx.to_dict(), 
                bundle, 
                currency=profile.currency
            )
            tx.anomaly_status = pred.is_anomaly
            tx.anomaly_severity = pred.severity
            tx.anomaly_score = pred.anomaly_score
            tx.anomaly_explanation = pred.reasons
            tx.recommended_action = pred.recommended_action
            if pred.is_anomaly:
                anomaly_count += 1
            updated_count += 1

        db.session.commit()

        return {
            "success": True,
            "total_transactions": updated_count,
            "flagged_anomalies": anomaly_count,
            "profile_id": profile_id,
        }

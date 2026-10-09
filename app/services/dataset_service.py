import re
from io import StringIO
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone
import pandas as pd

from app.extensions import db
from app.models.transaction import Transaction
from app.models.profile import SpendingProfile
from app.utils.date_utils import parse_datetime
from app.services.anomaly_service import AnomalyService

# Common column name synonym heuristics for automatic mapping detection
COLUMN_SYNONYMS = {
    "amount": ["amount", "cost", "trans_amount", "transaction_amount", "value", "price", "amt", "spending"],
    "category": ["category", "trans_category", "expense_category", "category_name", "type", "expense_type"],
    "merchant": ["merchant", "store", "vendor", "payee", "merchant_name", "shop", "description", "name"],
    "date": ["date", "trans_date", "transaction_date", "timestamp", "trans_date_trans_time", "datetime", "time"],
    "payment_method": ["payment_method", "method", "card_type", "payment_mode", "mode", "payment_type"],
    "payment_channel": ["payment_channel", "channel", "online_offline", "channel_type", "pos_type"],
    "label": ["is_fraud", "fraud", "is_anomaly", "anomaly", "label", "target", "class"],
}


class DatasetService:
    """Service handling configurable CSV dataset inspection, cleaning, and ingestion."""

    @staticmethod
    def infer_column_mapping(columns: List[str]) -> Dict[str, Optional[str]]:
        """Suggest mapping between user CSV columns and required fields."""
        mapping = {}
        clean_cols = {c.strip().lower().replace(" ", "_"): c for c in columns}

        for target_field, synonyms in COLUMN_SYNONYMS.items():
            matched = None
            for syn in synonyms:
                if syn in clean_cols:
                    matched = clean_cols[syn]
                    break
            mapping[target_field] = matched

        return mapping

    @staticmethod
    def preview_csv(file_content: str, max_rows: int = 5) -> Dict[str, Any]:
        """
        Inspect the uploaded CSV and generate preview rows and suggested mappings.
        """
        try:
            df = pd.read_csv(StringIO(file_content), nrows=max_rows)
        except Exception as e:
            return {"success": False, "error": f"Failed to parse CSV format: {str(e)}"}

        columns = list(df.columns)
        suggested_mapping = DatasetService.infer_column_mapping(columns)

        # Sanitize NaN values for JSON output
        sample_rows = df.fillna("").to_dict(orient="records")

        return {
            "success": True,
            "total_columns": columns,
            "suggested_mapping": suggested_mapping,
            "sample_rows": sample_rows,
            "preview_count": len(sample_rows),
        }

    @staticmethod
    def clean_amount(raw_val: Any) -> Optional[float]:
        """Clean currency strings, commas, symbols into a positive float."""
        if pd.isna(raw_val) or raw_val is None:
            return None
        val_str = str(raw_val).strip()
        # Remove currency symbols ($, Rs, ₹, commas)
        cleaned = re.sub(r"[^\d.-]", "", val_str)
        try:
            amt = float(cleaned)
            return amt if amt > 0 else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def import_csv(
        user_id: int,
        profile_id: int,
        file_content: str,
        column_mapping: Dict[str, str],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute full import with validation, duplicate detection, cleaning, and error reporting.
        """
        profile = SpendingProfile.query.filter_by(id=profile_id, user_id=user_id).first()
        if not profile:
            return {"success": False, "error": "Profile not found or access denied."}

        try:
            df = pd.read_csv(StringIO(file_content))
        except Exception as e:
            return {"success": False, "error": f"CSV parse error: {str(e)}"}

        total_rows = len(df)
        if total_rows == 0:
            return {"success": False, "error": "CSV file contains no data rows."}

        # Validate required target mappings
        amount_col = column_mapping.get("amount")
        date_col = column_mapping.get("date")

        if not amount_col or amount_col not in df.columns:
            return {"success": False, "error": f"Mapped amount column '{amount_col}' is missing in CSV."}

        if not date_col or date_col not in df.columns:
            return {"success": False, "error": f"Mapped date column '{date_col}' is missing in CSV."}

        cat_col = column_mapping.get("category")
        merch_col = column_mapping.get("merchant")
        method_col = column_mapping.get("payment_method")
        chan_col = column_mapping.get("payment_channel")

        imported_records = []
        errors = []
        duplicate_count = 0

        # Pre-fetch existing signatures for duplicate detection
        existing_txs = Transaction.query.filter_by(user_id=user_id, profile_id=profile_id).all()
        existing_signatures = {
            (
                t.transaction_date.strftime("%Y-%m-%d %H:%M"),
                round(t.amount, 2),
                t.merchant.lower(),
            )
            for t in existing_txs
        }

        # Model bundle for anomaly scoring during import
        bundle = AnomalyService.get_profile_bundle(profile_id, user_id)

        for idx, row in df.iterrows():
            row_num = idx + 2 # 1-based index accounting for CSV header row

            # 1. Clean Amount
            amount = DatasetService.clean_amount(row.get(amount_col))
            if amount is None:
                errors.append({
                    "row": row_num,
                    "field": "amount",
                    "reason": f"Invalid or non-positive amount value: '{row.get(amount_col)}'",
                })
                continue

            # 2. Parse Date
            dt_raw = row.get(date_col)
            tx_dt = parse_datetime(dt_raw)
            if tx_dt is None:
                errors.append({
                    "row": row_num,
                    "field": "date",
                    "reason": f"Unable to parse transaction date: '{dt_raw}'",
                })
                continue

            # 3. Categoricals & Defaults
            category = str(row.get(cat_col, "General")).strip() if cat_col and pd.notna(row.get(cat_col)) else "General"
            merchant = str(row.get(merch_col, "Imported Merchant")).strip() if merch_col and pd.notna(row.get(merch_col)) else "Imported Merchant"
            
            # Payment Method
            raw_method = str(row.get(method_col, "other")).strip().lower() if method_col and pd.notna(row.get(method_col)) else "other"
            if raw_method in ["card", "credit card", "debit card", "visa", "mastercard"]:
                payment_method = "card"
            elif raw_method in ["upi", "gpay", "phonepe", "paytm"]:
                payment_method = "upi"
            elif raw_method in ["cash"]:
                payment_method = "cash"
            elif raw_method in ["net banking", "netbanking", "bank transfer"]:
                payment_method = "net banking"
            else:
                payment_method = "other"

            # Payment Channel
            if chan_col and pd.notna(row.get(chan_col)):
                raw_chan = str(row.get(chan_col)).strip().lower()
                payment_channel = "online" if "online" in raw_chan or "web" in raw_chan else "offline"
            else:
                # Inferred sensible default
                payment_channel = "offline" if payment_method == "cash" else "online"

            # 4. Duplicate Check
            sig = (tx_dt.strftime("%Y-%m-%d %H:%M"), round(amount, 2), merchant.lower())
            if sig in existing_signatures:
                duplicate_count += 1
                continue

            existing_signatures.add(sig)

            # 5. Build Transaction Entity
            tx = Transaction(
                user_id=user_id,
                profile_id=profile_id,
                amount=amount,
                category=category,
                merchant=merchant,
                transaction_date=tx_dt,
                payment_method=payment_method,
                payment_channel=payment_channel,
                source="csv_import",
                user_confirmation_status="pending",
                description=f"Imported from dataset row {row_num}",
            )

            # Evaluate against current baseline
            pred = AnomalyService.evaluate_new_transaction(tx.to_dict(), profile)
            tx.anomaly_status = pred.is_anomaly
            tx.anomaly_severity = pred.severity
            tx.anomaly_score = pred.anomaly_score
            tx.anomaly_explanation = pred.reasons
            tx.recommended_action = pred.recommended_action

            db.session.add(tx)
            imported_records.append(tx)

        db.session.commit()

        # Retrain profile model now that new data is available
        if imported_records:
            AnomalyService.retrain_profile(profile_id, user_id)

        return {
            "success": True,
            "total_rows_processed": total_rows,
            "imported_count": len(imported_records),
            "duplicate_count": duplicate_count,
            "error_count": len(errors),
            "errors": errors[:50], # Return first 50 error rows for diagnostic inspectability
            "profile_id": profile_id,
            "profile_name": profile.name,
        }

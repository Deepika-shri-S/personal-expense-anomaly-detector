import json
from flask import Blueprint, request, jsonify, g, current_app
import pandas as pd
from io import StringIO
from app.routes.auth import auth_required
from app.services.dataset_service import DatasetService
from app.services.anomaly_service import AnomalyService
from app.ml.evaluate_model import evaluate_with_ground_truth, evaluate_unlabelled_feedback
from app.models.transaction import Transaction

import_bp = Blueprint("import_data", __name__, url_prefix="/api/import")


def get_csv_content_from_request():
    """Extract CSV text from file upload or raw string payload."""
    if "file" in request.files:
        f = request.files["file"]
        return f.read().decode("utf-8", errors="replace")

    data = request.get_json(silent=True)
    if data and "csv_content" in data:
        return data["csv_content"]

    return None


@import_bp.route("/preview", methods=["POST"])
@auth_required
def preview_csv():
    """
    Upload CSV to preview columns, sample rows, and suggested mappings
    before committing to import.
    """
    csv_text = get_csv_content_from_request()
    if not csv_text:
        return jsonify({"error": "No CSV file or 'csv_content' string provided."}), 400

    max_rows = request.args.get("max_rows", 5, type=int)
    preview = DatasetService.preview_csv(csv_text, max_rows=max_rows)
    if not preview.get("success"):
        return jsonify(preview), 400

    return jsonify(preview), 200


@import_bp.route("/csv", methods=["POST"])
@auth_required
def import_csv():
    """
    Import transactions from CSV with user-defined or inferred column mappings.
    Multipart form-data:
      - file: CSV file
      - profile_id: integer
      - mapping: JSON string e.g. '{"amount": "amt", "date": "Date", "merchant": "Merchant"}'
    OR JSON payload:
      - csv_content: string
      - profile_id: integer
      - mapping: dict
    """
    csv_text = get_csv_content_from_request()
    if not csv_text:
        return jsonify({"error": "No CSV data provided."}), 400

    profile_id = request.form.get("profile_id") or (request.get_json(silent=True) or {}).get("profile_id")
    if not profile_id:
        return jsonify({"error": "Field 'profile_id' is required."}), 400
    try:
        profile_id = int(profile_id)
    except ValueError:
        return jsonify({"error": "'profile_id' must be an integer."}), 400

    mapping_raw = request.form.get("mapping") or (request.get_json(silent=True) or {}).get("mapping")
    if isinstance(mapping_raw, str):
        try:
            mapping = json.loads(mapping_raw)
        except Exception:
            mapping = {}
    elif isinstance(mapping_raw, dict):
        mapping = mapping_raw
    else:
        # Fallback to automatic synonym inference
        preview = DatasetService.preview_csv(csv_text, max_rows=1)
        mapping = preview.get("suggested_mapping", {})

    result = DatasetService.import_csv(
        user_id=g.current_user.id,
        profile_id=profile_id,
        file_content=csv_text,
        column_mapping=mapping,
    )

    if not result.get("success"):
        return jsonify(result), 400

    return jsonify({
        "message": f"Successfully imported {result['imported_count']} transactions.",
        "details": result,
    }), 201


@import_bp.route("/evaluate", methods=["POST"])
@auth_required
def evaluate_dataset():
    """
    Evaluate ML model performance.
    If CSV has ground-truth labels (e.g. Kaggle 'is_fraud' column):
      calculates Precision, Recall, F1, Confusion Matrix, and False Positive Rate.
    If no labels exist:
      returns user feedback confirmation metrics and false-alert rates.
    """
    csv_text = get_csv_content_from_request()
    models_dir = AnomalyService.get_models_dir()

    if csv_text:
        try:
            df = pd.read_csv(StringIO(csv_text))
        except Exception as e:
            return jsonify({"error": f"Failed to read CSV: {e}"}), 400

        label_col = request.form.get("label_col") or (request.get_json(silent=True) or {}).get("label_col", "is_fraud")

        if label_col in df.columns:
            results = evaluate_with_ground_truth(
                df=df,
                label_col=label_col,
                models_dir=models_dir,
                profile_id=1,
            )
            return jsonify(results), 200
        else:
            return jsonify({
                "message": f"Label column '{label_col}' not found in dataset.",
                "available_columns": list(df.columns),
                "unlabelled_evaluation": (
                    "When evaluating unlabelled personal expenses, standard supervised metrics "
                    "(precision/recall) cannot be manufactured. Use system feedback review metrics instead."
                )
            }), 200

    # Fallback to evaluating user's existing recorded transactions
    tx_query = Transaction.query.filter_by(user_id=g.current_user.id).all()
    tx_dicts = [t.to_dict() for t in tx_query]
    feedback_eval = evaluate_unlabelled_feedback(tx_dicts)
    return jsonify(feedback_eval), 200

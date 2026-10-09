import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.models.user import User
from app.models.profile import SpendingProfile
from app.services.dataset_service import DatasetService


def main():
    parser = argparse.ArgumentParser(description="Import Kaggle or external CSV dataset into Personal Expense Detector.")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--username", default="student_user", help="Target username (default: student_user)")
    parser.add_argument("--profile", default="College", help="Target spending profile name (default: College)")
    parser.add_argument("--mapping", help="Optional JSON string of column mappings e.g. '{\"amount\": \"Amount\", \"date\": \"Time\"}'")
    parser.add_argument("--preview", action="store_true", help="Preview rows and inferred mappings without importing")

    args = parser.parse_args()
    csv_path = Path(args.csv)

    if not csv_path.exists():
        print(f"Error: File not found at {csv_path}")
        sys.exit(1)

    content = csv_path.read_text(encoding="utf-8", errors="replace")
    app = create_app("development")

    with app.app_context():
        user = User.query.filter_by(username=args.username).first()
        if not user:
            print(f"Error: User '{args.username}' not found. Run scripts/initialize_db.py first.")
            sys.exit(1)

        profile = SpendingProfile.query.filter_by(user_id=user.id, name=args.profile).first()
        if not profile:
            print(f"Error: Profile '{args.profile}' not found for user '{args.username}'.")
            sys.exit(1)

        if args.preview:
            preview = DatasetService.preview_csv(content, max_rows=5)
            print("\n" + "=" * 50)
            print(f" Preview for: {csv_path.name}")
            print("=" * 50)
            print("Detected Columns:", preview.get("total_columns"))
            print("Suggested Mapping:", json.dumps(preview.get("suggested_mapping"), indent=2))
            print(f"Sample Rows (First {preview.get('preview_count')}):")
            for r in preview.get("sample_rows", []):
                print(r)
            return

        # Prepare mapping
        if args.mapping:
            mapping = json.loads(args.mapping)
        else:
            preview = DatasetService.preview_csv(content, max_rows=1)
            mapping = preview.get("suggested_mapping", {})
            print(f"Using inferred mapping: {mapping}")

        print(f"Importing transactions into user '{user.username}', profile '{profile.name}' ...")
        res = DatasetService.import_csv(
            user_id=user.id,
            profile_id=profile.id,
            file_content=content,
            column_mapping=mapping,
        )

        if not res.get("success"):
            print("Import Failed:", res.get("error"))
            sys.exit(1)

        print("\n" + "=" * 50)
        print(" Import Completed Successfully!")
        print("=" * 50)
        print(f" Total Rows in CSV : {res['total_rows_processed']}")
        print(f" Imported Records  : {res['imported_count']}")
        print(f" Duplicates Skipped: {res['duplicate_count']}")
        print(f" Errors Encountered: {res['error_count']}")
        if res['errors']:
            print("Sample Errors:")
            for err in res['errors'][:5]:
                print(f"  Row {err['row']}: {err['reason']}")
        print("=" * 50 + "\n")


if __name__ == "__main__":
    main()

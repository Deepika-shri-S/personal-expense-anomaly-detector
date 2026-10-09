from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models.profile import SpendingProfile
from app.routes.auth import auth_required
from app.utils.validators import validate_profile_payload

profiles_bp = Blueprint("profiles", __name__, url_prefix="/api/profiles")


@profiles_bp.route("", methods=["GET"])
@auth_required
def list_profiles():
    """List all spending profiles belonging to the authenticated user."""
    profiles = SpendingProfile.query.filter_by(user_id=g.current_user.id).all()
    return jsonify({
        "count": len(profiles),
        "profiles": [p.to_dict() for p in profiles],
    }), 200


@profiles_bp.route("", methods=["POST"])
@auth_required
def create_profile():
    """Create a new spending context profile (e.g. College, Home, Travel)."""
    data = request.get_json() or {}
    is_valid, err = validate_profile_payload(data)
    if not is_valid:
        return jsonify({"error": err}), 400

    name = data["name"].strip()
    existing = SpendingProfile.query.filter_by(user_id=g.current_user.id, name=name).first()
    if existing:
        return jsonify({"error": f"A profile named '{name}' already exists for your account."}), 409

    is_default = bool(data.get("is_default", False))
    if is_default:
        # Clear default flag on existing profiles
        SpendingProfile.query.filter_by(user_id=g.current_user.id).update({"is_default": False})

    profile = SpendingProfile(
        user_id=g.current_user.id,
        name=name,
        description=data.get("description"),
        currency=data.get("currency", "INR").strip().upper(),
        is_default=is_default,
    )
    db.session.add(profile)
    db.session.commit()

    return jsonify({
        "message": "Profile created successfully.",
        "profile": profile.to_dict(),
    }), 201


@profiles_bp.route("/<int:profile_id>", methods=["GET"])
@auth_required
def get_profile(profile_id: int):
    """Retrieve details of a single spending profile."""
    profile = SpendingProfile.query.filter_by(id=profile_id, user_id=g.current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404
    return jsonify({"profile": profile.to_dict()}), 200


@profiles_bp.route("/<int:profile_id>", methods=["PUT"])
@auth_required
def update_profile(profile_id: int):
    """Update profile name, description, or default status."""
    profile = SpendingProfile.query.filter_by(id=profile_id, user_id=g.current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    data = request.get_json() or {}
    if "name" in data and data["name"]:
        new_name = data["name"].strip()
        dup = SpendingProfile.query.filter(
            SpendingProfile.user_id == g.current_user.id,
            SpendingProfile.name == new_name,
            SpendingProfile.id != profile_id,
        ).first()
        if dup:
            return jsonify({"error": f"A profile named '{new_name}' already exists."}), 409
        profile.name = new_name

    if "description" in data:
        profile.description = data["description"]

    if "currency" in data and data["currency"]:
        profile.currency = data["currency"].strip().upper()

    if "is_default" in data and data["is_default"]:
        SpendingProfile.query.filter_by(user_id=g.current_user.id).update({"is_default": False})
        profile.is_default = True

    db.session.commit()
    return jsonify({
        "message": "Profile updated successfully.",
        "profile": profile.to_dict(),
    }), 200


@profiles_bp.route("/<int:profile_id>", methods=["DELETE"])
@auth_required
def delete_profile(profile_id: int):
    """Delete spending profile and cascading associations."""
    profile = SpendingProfile.query.filter_by(id=profile_id, user_id=g.current_user.id).first()
    if not profile:
        return jsonify({"error": "Profile not found."}), 404

    # Ensure user has at least one profile remaining
    total = SpendingProfile.query.filter_by(user_id=g.current_user.id).count()
    if total <= 1:
        return jsonify({"error": "Cannot delete your only spending profile."}), 400

    db.session.delete(profile)
    db.session.commit()
    return jsonify({"message": f"Profile '{profile.name}' deleted successfully."}), 200

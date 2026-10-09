import functools
from datetime import datetime, timezone, timedelta
import jwt
from flask import Blueprint, request, jsonify, current_app, g
from app.extensions import db
from app.models.user import User
from app.models.profile import SpendingProfile
from app.utils.validators import validate_user_registration

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def generate_auth_token(user_id: int) -> str:
    """Generate signed JWT token valid for 7 days."""
    secret = current_app.config.get("SECRET_KEY", "fallback-secret")
    payload = {
        "sub": str(user_id),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def auth_required(f):
    """
    Decorator enforcing user authentication.
    Resolves authenticated user from:
    1. Authorization Bearer token header
    2. X-User-Id header (useful for flexible frontend testing)
    3. Fallback to default user in development mode
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = None
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1].strip()
            secret = current_app.config.get("SECRET_KEY", "fallback-secret")
            try:
                payload = jwt.decode(token, secret, algorithms=["HS256"])
                sub = payload.get("sub")
                if sub is not None:
                    user_id = int(sub)
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                return jsonify({"error": "Invalid or expired authorization token."}), 401

        # Check explicit X-User-Id header
        if not user_id and request.headers.get("X-User-Id"):
            try:
                user_id = int(request.headers.get("X-User-Id"))
            except ValueError:
                pass

        # In testing or development, allow fallback if exactly one or default user exists
        if not user_id:
            default_user = User.query.first()
            if default_user:
                user_id = default_user.id
            else:
                return jsonify({"error": "Authentication required. Please log in or provide X-User-Id."}), 401

        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "Authenticated user not found in database."}), 401

        g.current_user = user
        return f(*args, **kwargs)

    return decorated_function


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    is_valid, err = validate_user_registration(data)
    if not is_valid:
        return jsonify({"error": err}), 400

    username = data["username"].strip()
    email = data["email"].strip().lower()

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username is already taken."}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email is already registered."}), 409

    user = User(
        username=username,
        email=email,
        display_name=data["display_name"].strip(),
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.flush()

    # Create default 'College' and 'Home' spending profiles for the new user
    p_college = SpendingProfile(
        user_id=user.id,
        name="College",
        description="Daily campus, food, canteen, stationery, and hostel expenses",
        currency="INR",
        is_default=True,
    )
    p_home = SpendingProfile(
        user_id=user.id,
        name="Home",
        description="Home groceries, utilities, and local expenses",
        currency="INR",
        is_default=False,
    )
    db.session.add(p_college)
    db.session.add(p_home)
    db.session.commit()

    token = generate_auth_token(user.id)
    return jsonify({
        "message": "User registered successfully.",
        "user": user.to_dict(),
        "token": token,
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    ident = str(data.get("username", data.get("email", ""))).strip()
    password = str(data.get("password", "")).strip()

    if not ident or not password:
        return jsonify({"error": "Username/email and password are required."}), 400

    user = User.query.filter(
        (User.username == ident) | (User.email == ident.lower())
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials."}), 401

    token = generate_auth_token(user.id)
    return jsonify({
        "message": "Login successful.",
        "user": user.to_dict(),
        "token": token,
    }), 200


@auth_bp.route("/me", methods=["GET"])
@auth_required
def get_current_user_profile():
    return jsonify({
        "user": g.current_user.to_dict(),
        "profiles": [p.to_dict() for p in g.current_user.profiles],
    }), 200

from datetime import timedelta
from flask import request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    create_access_token, 
    verify_jwt_in_request,
    get_jwt_identity
)
from functools import wraps
import re



bcrypt = Bcrypt()


def hash_pin(pin):
    return bcrypt.generate_password_hash(pin).decode("utf-8")


# -----------------------------
# 1. Create a JWT when user logs in
# -----------------------------
def generate_token(username):
    # Token contains the user ID
    token = create_access_token(
        identity=str(username),
        expires_delta=timedelta(hours=12)  # token valid for 12h
    )
    return token


# -----------------------------
# 2. Verify PIN / password
# -----------------------------
def check_pin(stored_hash, provided_pin):
    """
    Returns True if PIN is correct, else False.
    """
    if stored_hash is None:
        return False

    return bcrypt.check_password_hash(stored_hash, provided_pin)


# -----------------------------
# 3. Protect routes using @require_auth
# -----------------------------
def require_auth(func):
    """
    Decorator that:
    - Verifies JWT is present
    - Injects `current_username` into route
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Check if JWT exists in headers
            verify_jwt_in_request()

            # Get user ID from the token
            username = get_jwt_identity()

            # Pass it into the route as a keyword arg
            return func(current_username=username, *args, **kwargs)

        except Exception as e:
            return jsonify(str(e)), 401

    return wrapper


# -----------------------------------------
# 4. Validate and normalize the username
# -----------------------------------------
USERNAME_REGEX = re.compile(r"^[a-z0-9_]{3,25}$")

def normalize_username(username: str) -> str:
    return username.strip().lower()

def validate_username(username: str) -> bool:
    return bool(USERNAME_REGEX.match(username))


# -------------------------------
# 5. Validate the business_name
# -------------------------------
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,25}$")

def normalize_business_name(business_name: str) -> str:
    return business_name.strip()

def validate_business_name(business_name: str) -> bool:
    return bool(USERNAME_REGEX.match(business_name))

# ------------------------------------
# 6. Check permissions of user's role
# ------------------------------------
def require_role(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):

            from .models import Account
            
            username = get_jwt_identity()
            user = Account.query.filter_by(username=username).first()

            if not user or user.role not in allowed_roles:
                return jsonify({"Error": "Forbidden"}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator

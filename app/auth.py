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
def generate_token(account_id):
    # Token contains the user ID
    token = create_access_token(
        identity=str(account_id),
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
    - Injects `current_user_id` into route
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Check if JWT exists in headers
            verify_jwt_in_request()

            # Get user ID from the token
            user_id = get_jwt_identity()

            # Pass it into the route as a keyword arg
            return func(current_user_id=user_id, *args, **kwargs)

        except Exception as e:
            return jsonify(str(e)), 401

    return wrapper

# -----------------------------
# 4. Validate the username
# -----------------------------
USERNAME_REGEX = re.compile(r"^[a-z0-9_]{3,20}$")

def normalize_username(username: str) -> str:
    return username.strip().lower()

def validate_username(username: str) -> bool:
    return bool(USERNAME_REGEX.match(username))
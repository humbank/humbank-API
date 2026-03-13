from datetime import timedelta
from flask import jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    create_access_token, 
    verify_jwt_in_request,
    get_jwt_identity,
    get_jwt
)
from functools import wraps
import re
from .error import APIError
from app.db.connection import username_exists
import secrets


bcrypt = Bcrypt()


ROLES = ["admin", "user", "business_owner"]


def hash_pin(pin):
    return bcrypt.generate_password_hash(pin).decode("utf-8")


# -----------------------------
# 1. Create a JWT when user logs in
# -----------------------------
def generate_token(idty, addi_claims):
    # Token contains the user ID
    token = create_access_token(
        identity=str(idty),
        additional_claims=addi_claims,
        expires_delta=timedelta(minutes=30)  # token valid for 30 min
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

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Check if JWT exists in headers
            verify_jwt_in_request()

            # Get user ID from the token
            username = get_jwt_identity()
            claims = get_jwt()

            if not username_exists(username):
                raise APIError(message="User not found", status_code=404)
            
            if claims["deleted"]:
                raise APIError(message="User disabled", status_code=401)
            
            if claims["banned"]:
                raise APIError(message="User is banned", status_code=403)

            # Pass it into the route as a keyword arg
            return func(current_username=username, *args, **kwargs)

        except APIError as e:
            return jsonify(e.to_dict()), e.status_code

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
    for role in allowed_roles:
        if role not in ROLES:
            raise APIError(message="Unknown role", status_code=400)
    
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()

            
                #username = get_jwt_identity()
                claims = get_jwt()
                
                if claims["role"] not in allowed_roles:
                    raise APIError(message="Entry forbidden", status_code=403)

                return fn(*args, **kwargs)
            
            except APIError as e:
                return jsonify(e.to_dict()), e.status_code
        return wrapper
    return decorator


# -----------------------------------
# 7. CREATE TOKEN FOR TRANSACTIONS
# -----------------------------------
def create_token_for_trans():
    return "req_" + secrets.token_urlsafe(16)
    

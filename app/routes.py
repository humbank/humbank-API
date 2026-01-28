from flask import Blueprint, request, jsonify, send_from_directory
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.exc import IntegrityError
from .models import Account, BusinessAccount, BusinessMember
from .auth import check_pin, generate_token, require_auth, normalize_username, validate_username, normalize_business_name, validate_business_name, require_role
from .db_raw import get_business_balance, get_user_balance, execute_transfer, get_todays_transactions, transactions_amount, username_exists, business_name_exists, get_user_id_by_username
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import os

api = Blueprint("api", __name__)


# -------------------------
#        TIMEZONE HELPER    
# -------------------------
GERMAN_TZ = ZoneInfo("Europe/Berlin")

def isoformat_german(dt):
    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(GERMAN_TZ).isoformat()


# -------------------------
#        LOGIN
# -------------------------
@api.route("/login", methods=["POST"])
def login():
    print("test")
    try:
        data = request.get_json()

        if not data or "username" not in data or "pin" not in data:
            return jsonify("Missing Username or PIN"), 400

        username = data["username"].lower().strip()
        pin = data["pin"]

        # Fetch user via SQLAlchemy model and username
        user = Account.query.filter_by(username=username).first()
        
        if not user:
            return jsonify("User not found"), 404
        
        if not user.pin_hash:
            return jsonify("User has no PIN set"), 400


        # Verify PIN hash
        if not check_pin(user.pin_hash, pin):
            return jsonify("Invalid PIN"), 401
        
        #user_id = user.id

        # Create token
        token = generate_token(username)

        return jsonify({"token": token, "username": username}), 200

    except Exception as e:
        return jsonify(str(e)), 520


# -------------------------
#       GET USER BALANCE
# -------------------------
@api.route("/get_user_balance", methods=["GET"])
@require_auth
def get_user_balance_route(current_username):
    try:
        balance = get_user_balance(current_username)
        return jsonify(balance), 200
    except Exception as e:
        return jsonify(str(e)), 520
    
# -------------------------
#       GET USER ACCOUNT
# -------------------------
@api.route("/get_user_account", methods=["GET"])
@require_auth
def get_user_account_route(current_username):
    try:
        user = Account.query.filter_by(username=current_username).first()

        if not user:
            return jsonify("User not found"), 404
        
        
        return jsonify({"user_id": user.id, 
                        "username": user.username, 
                        "balance": user.balance, 
                        "role": user.role,  
                        "updated_at": isoformat_german(user.updated_at), 
                        "full_name": user.full_name()}
                    ), 200
    
    except Exception as e:
        return jsonify(str(e)), 520
    
# -----------------------------
#       GET ALL USER ACCOUNTS
# -----------------------------
@api.route("/get_all_users", methods=["GET"])
@require_auth
def get_all_users_route(current_username):
    users = Account.query.filter(Account.deleted_at.is_(None)).all()

    return jsonify([
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "balance": float(u.balance),
            "deleted_at": u.deleted_at,
            "updated_at": isoformat_german(u.updated_at),
            "full_name": u.full_name(),
        }
        for u in users
    ]), 200

# ------------------------------
#       GET BUSINESS BALANCE
# ------------------------------
@api.route("/get_business_balance", methods=["GET"])
@require_auth
def get_business_balance_route(current_username):
    try:
        balance = get_business_balance(current_username)
        return jsonify(balance), 200
    except Exception as e:
        return jsonify(str(e)), 520

# -------------------------
#       CREATE USER
# -------------------------
@api.route("/create_user", methods=["POST"])
@require_auth
@require_role("admin")
def create_user_route(current_username):
    try:
        data = request.get_json() or {}

        first_name = data.get("first_name")
        last_name = data.get("last_name")
        pin = data.get("pin")
        username = data.get("username")
        role = data.get("role")

        if not first_name or not last_name or not pin or not username or not role:
            return jsonify("Missing fields"), 400
        
        pin = str(pin)
        username = normalize_username(username=username)
        
        if not validate_username(username=username):
            return jsonify("Username must be 3-25 characters, lowercase letters, "
            "underscores or numbers only"), 400
        
        start_balance = 100
        
        new_account = Account(
            first_name=first_name,
            last_name=last_name,
            balance=start_balance,
            username = username,
            role = role,
        )
        new_account.set_pin(pin)

        from . import db
        db.session.add(new_account)
        db.session.commit()

        return jsonify({"message": "User created", "id": new_account.id, "username": username}), 201


    except Exception as e:
        return jsonify(str(e)), 520


# -------------------------
#       CREATE BUSINESS
# -------------------------
@api.route("/create_business", methods=["POST"])
@require_auth
@require_role("admin")
def create_business_route(current_username):
    from . import db
    try:
        data = request.get_json() or {}

        business_name = data.get("business_name")
        pin = data.get("pin")
        owner_username = data.get("owner_username")
        description = data.get("description") or "We will greet you in person!"

        if not business_name or not pin or not owner_username:
            return jsonify("Missing fields"), 400
        
        pin = str(pin)
        business_name = normalize_business_name(business_name=business_name)
        
        if not validate_business_name(business_name=business_name):
            return jsonify("Business name must be 3-25 characters, "
            "underscores or numbers only"), 400
        
        if not business_name_exists(business_name):
            return jsonify("Business name already taken"), 400



        if not username_exists(owner_username):
            return jsonify("User not found"), 404
        
        if not can_create_business(owner_username, limit=1):
            return jsonify("Owner already has maximum businesses"), 403
        
        owner_id = get_user_id_by_username(owner_username)
        
        START_BALANCE = 0
        
        new_business_account = BusinessAccount(
            business_name = business_name,
            owner_id = owner_id,
            owner_username = owner_username,
            balance=START_BALANCE,
        )
        new_business_account.set_pin(pin)

        
        
        db.session.add(new_business_account)
        db.session.flush()

        #add description to description file
        descr_file = "business_descr.json"
        deleted_file = "business_deleted.json"
        data = {}
        if os.path.exists(descr_file):
            with open(descr_file, "r") as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    data = {}

        is_deleted = False
        with open(deleted_file, "r") as file:
            try:
                contents = json.load(file)
                if str(new_business_account.id) in contents:
                    is_deleted = True
                
            except Exception as e:
                return jsonify(str(e)), 520
            
        if is_deleted:
            raise Exception("Business is disabled")


        # Add new business
        data[new_business_account.id] = description

        # Write back
        with open(descr_file, "w") as file:
            json.dump(data, file)

        membership = BusinessMember(
            user_id=owner_id,
            username = owner_username,
            business_id=new_business_account.id,
            role="owner"
        )
        db.session.add(membership)

        db.session.commit()

        return jsonify({"message": "Business created", "id": new_business_account.id}), 201
    
    except IntegrityError as e:
        db.session.rollback()
        return jsonify("Business name already exists"), 400
    

    except Exception as e:
        db.session.rollback()
        return jsonify(str(e)), 520
    
# --------------------------------
#     BUSINESS CREATION HELPER
# --------------------------------
def can_create_business(username, limit=1):
    active_count = BusinessAccount.query.filter(BusinessAccount.owner_username==username, BusinessAccount.deleted_at.is_(None)).count()
    return active_count < limit

# --------------------------------
#     DISABLE BUSINESS
# --------------------------------
@api.route("/disable_business", methods=["POST"])
@require_auth
@require_role("admin")
def disable_business_route(current_username):
    from . import db
    try:
        data = request.get_json() or {}

        business_id = data.get("business_id")

        
        business = BusinessAccount.query.get(business_id)
        if not business or business.deleted_at is not None:
            return jsonify("Business not found"), 404

        business.deleted_at = db.func.now()
        db.session.commit()

        deleted_file = "business_deleted.json"
        data = {}
        if os.path.exists(deleted_file):
            with open(deleted_file, "r") as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    data = {}

        # Add new business
        data[business_id] = "disabled"

        # Write back
        with open(deleted_file, "w") as file:
            json.dump(data, file)

        return jsonify("Business disabled"), 200

    except Exception as e:
        db.session.rollback()
        return jsonify(str(e)), 520


# ---------------------
#     DISABLE USER
# ---------------------

@api.route("/disable_user", methods=["POST"])
@require_auth
@require_role("admin")
def disable_user_route(current_username):

    try:
        data = request.get_json() or {}

        user_id = data.get("user_id")

        user = Account.query.get(user_id)

        if not user:
            return jsonify("User not found"), 404
    
        from . import db

        user.deleted_at = db.func.now()
        db.session.commit()

        return jsonify("User is disabled"), 200
    
    except Exception as e:
        return jsonify(str(e)), 520



# -------------------------
#     EXECUTE TRANSFER
# -------------------------
@api.route("/execute_transfer", methods=["POST"])
@require_auth
def execute_transfer_route(current_username):
    try:
        data = request.get_json() or {}

        payer_username = current_username
        issuer_username = data.get("issuer_username")
        amount = data.get("amount")
        transaction_id = data.get("transaction_id")
        description = data.get("description")

        if not issuer_username or not amount or not transaction_id or not description:
            return jsonify("Missing fields"), 400

        result = execute_transfer(payer_username, issuer_username, amount, transaction_id, description)

        if result is True:
            return jsonify("Transfer completed"), 200
        else:
            return "", 400

    except Exception as e:
        return jsonify(str(e)), 520


# -------------------------
#  TODAY'S TRANSACTIONS
# -------------------------
@api.route("/get_todays_transactions", methods=["GET"])
@require_auth
def todays_transactions_route(current_username):
    try:
        now = datetime.now()
        start = datetime.combine(now.date(), datetime.min.time())

        results = get_todays_transactions(current_username, start, now)
        return jsonify(results), 200

    except Exception as e:
        return jsonify(str(e)), 520

# ----------------------------
#  TODAY'S TRANSACTION AMOUNT
# ----------------------------
@api.route("/transactions_amount", methods=["GET"])
@require_auth
def transactions_amount_route(current_username):
    try:
        results = transactions_amount(current_username)
        return jsonify(results), 200
    
    except Exception as e:
        return jsonify(str(e)), 520



# ----------------------------
#  CHECK TOKEN VALIDITY
# ----------------------------
@api.route("/check_token_validity", methods=["GET"])
@require_auth
def check_token_validity_route(current_user_id):
	return "", 200


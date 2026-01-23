from flask import Blueprint, request, jsonify, send_from_directory
from flask_jwt_extended import get_jwt_identity
from .models import Account, BusinessAccount, BusinessMember
from .auth import check_pin, generate_token, require_auth, normalize_username, validate_username, normalize_business_name, validate_business_name, require_role
from .db_raw import get_balance, execute_transfer, get_todays_transactions, transactions_amount, get_user_by_id, get_user_id_by_username
from datetime import datetime
import json
import os

api = Blueprint("api", __name__)


# -------------------------
#        LOGIN
# -------------------------
@api.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()

        if not data or "username" not in data or "pin" not in data:
            return jsonify("Missing Username or PIN"), 400

        username = data["username"].lower().strip()
        pin = data["pin"]

        # Fetch user via SQLAlchemy model and username
        user = Account.query.filter_by(username = username).first()
        
        if not user:
            return jsonify("User not found"), 404


        # Verify PIN hash
        if not check_pin(user.pin_hash, pin):
            return jsonify("Invalid PIN"), 401
        
        user_id = user.id

        # Create token
        token = generate_token(user_id)
        return jsonify(token, user_id), 200

    except Exception as e:
        return jsonify(str(e)), 520


# -------------------------
#       GET BALANCE
# -------------------------
@api.route("/get_balance", methods=["GET"])
@require_auth
def get_balance_route(current_user_id):
    try:
        balance = get_balance(current_user_id)
        return jsonify(balance), 200
    except Exception as e:
        return jsonify(str(e)), 520


# -------------------------
#       CREATE USER
# -------------------------
@api.route("/create_user", methods=["POST"])
@require_auth
@require_role("admin")
def create_user_route(current_user_id):
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

        return jsonify({"message": "User created", "id": new_account.id}), 201


    except Exception as e:
        return jsonify(str(e)), 520


# -------------------------
#       CREATE BUSINESS
# -------------------------
@api.route("/create_business", methods=["POST"])
@require_auth
@require_role("admin")
def create_business_route(current_user_id):
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
        
        owner_id = get_user_id_by_username(owner_username)

        if not owner_id:
            return jsonify("User not found"), 404

        if not can_create_business(owner_id, limit=1):
            return jsonify("Owner already has maximum businesses"), 403
        
        start_balance = 0
        
        new_business_account = BusinessAccount(
            business_name = business_name,
            owner_id = owner_id,
            balance=start_balance,
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
            business_id=new_business_account.id,
            role="owner"
        )
        db.session.add(membership)

        db.session.commit()

        return jsonify({"message": "Business created", "id": new_business_account.id}), 201
    

    except Exception as e:
        db.session.rollback()
        return jsonify(str(e)), 520
    
# --------------------------------
#     BUSINESS CREATION HELPER
# --------------------------------
def can_create_business(user_id, limit=1):
    active_count = BusinessAccount.query.filter(BusinessAccount.owner_id==user_id, BusinessAccount.deleted_at.is_(None)).count()
    return active_count < limit

# --------------------------------
#     DISABLE BUSINESS
# --------------------------------
@api.route("/disable_business", methods=["POST"])
@require_auth
@require_role("admin")
def disable_business_route(current_user_id):
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
def disable_user_route(current_user_id):

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
def execute_transfer_route(current_user_id):
    try:
        data = request.get_json() or {}

        payer_id = current_user_id  # The user sending money
        issuer_id = data.get("issuer_id")
        amount = data.get("amount")
        transaction_id = data.get("transaction_id")

        if not issuer_id or not amount or not transaction_id:
            return jsonify("Missing fields"), 400

        result = execute_transfer(payer_id, issuer_id, amount, transaction_id)

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
def todays_transactions_route(current_user_id):
    try:
        now = datetime.now()
        start = datetime.combine(now.date(), datetime.min.time())

        results = get_todays_transactions(current_user_id, start, now)
        return jsonify(results), 200

    except Exception as e:
        return jsonify(str(e)), 520

# ----------------------------
#  TODAY'S TRANSACTION AMOUNT
# ----------------------------
@api.route("/transactions_amount", methods=["GET"])
@require_auth
def transactions_amount(current_user_id):
    try:
        now = datetime.now()
        start = datetime.combine(now.date(), datetime.min.time())

        results = transactions_amount(current_user_id, start, now)
        return jsonify(results), 200
    
    except Exception as e:
        return jsonify(str(e)), 520

# -------------------------
#       GET USER BY ID
# -------------------------
@api.route("/get_user_by_id", methods=["POST"])
@require_auth
def get_user_by_id_route(current_user_id):
    try:
        data = request.get_json() or {}

        user_id = data["id"]

        if not user_id:
            return jsonify("Missing id"), 400

        result = get_user_by_id(user_id=user_id)

        if not result:
            return jsonify("User not found"), 404

        return jsonify(result), 200


    
    except Exception as e:
        return jsonify(str(e)), 520


@api.route("/check_token_validity", methods=["GET"])
@require_auth
def check_token_validity_route(current_user_id):
	return "", 200


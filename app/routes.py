from flask import Blueprint, request, jsonify, send_from_directory
from sqlalchemy.exc import IntegrityError
from .models import Account, BusinessAccount, BusinessMember
from .auth import (check_pin, generate_token, require_auth, normalize_username, validate_username, 
                   normalize_business_name, validate_business_name, require_role)
from .db_raw import (get_business_balance, get_user_balance, execute_transfer, get_todays_transactions, transactions_amount, 
                     username_exists, business_name_exists, get_user_id_by_username, execute_transfer_to_business,
                     get_updated_accounts_after_time, todays_transaction_amount
                    )
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import os
from .error import APIError

api = Blueprint("api", __name__)

BANK_FEE = 0.05

TAXES = {"Status1": 0.02, "Status2": 0.03, "Status3": 0.05}


# -----------------------------
#       GERMAN TIMEZONE HELPER     
# -----------------------------
GERMAN_TZ = ZoneInfo("Europe/Berlin")

def isoformat_german(dt):
    if dt is None:
        return None
    
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace(" ", "T"))
        except ValueError:
            return dt 

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(GERMAN_TZ).isoformat()


# ------------------------------
#       BRITISH TIMEZONE HELPER     
# ------------------------------
BRITISH_TZ = ZoneInfo("Europe/London")

def isoformat_britain(dt):
    if dt is None:
        return None

    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace(" ", "T"))
        except ValueError:
            return dt

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(BRITISH_TZ).isoformat()


# -------------------------
#        LOGIN
# -------------------------
@api.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()

        if not data:
            raise APIError(message="Inputs are missing", status_code=400)
        
        if "username" not in data:
            raise APIError(message="Username missing", status_code=400)
        
        if "pin" not in data:
            raise APIError(message="Pin missing", status_code=400)

        username = data["username"].lower().strip()
        pin = data["pin"]

        # Fetch user via SQLAlchemy model and username
        user = Account.query.filter_by(username=username).first()
        
        if not user:
            raise APIError(message="User not found", status_code=404)
        
        if not user.pin_hash:
            raise APIError(message="User has no Pin set", status_code=400)
        
        if user.deleted_at is not None:
            raise APIError(message="User is deleted", status_code=401)
        
        if user.banned_at is not None:
            raise APIError(message="User is banned", status_code=401)


        # Verify PIN hash
        if not check_pin(user.pin_hash, pin):
            raise APIError(message="Pin is incorrect", status_code=401)
        
        additional_claims = {
            "role": user.role,
            "deleted": user.deleted_at is not None,
            "banned": user.banned_at is not None
        }
        
        # Create token
        token = generate_token(
            idty=user.username,
            addi_claims= additional_claims
        )

        return jsonify({"token": token, "username": username}), 200

    except APIError as e:
        return jsonify(e.to_dict()), e.status_code


# -------------------------
#       GET USER BALANCE
# -------------------------
@api.route("/get_user_balance", methods=["GET"])
@require_auth
def get_user_balance_route(current_username):
    try:
        balance = get_user_balance(current_username)
        return jsonify(balance), 200
    
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    
# -------------------------
#       GET USER ACCOUNT
# -------------------------
@api.route("/get_user_account", methods=["GET"])
@require_auth
def get_user_account_route(current_username):
    try:
        user = Account.query.filter_by(username=current_username).first()

        if not user:
            raise APIError(message="User not found", status_code=404)
        
        
        return jsonify({"username": user.username, 
                        "balance": user.balance, 
                        "role": user.role,  
                        "updated_at": isoformat_german(user.updated_at), 
                        "full_name": user.full_name()}
                    ), 200
    
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    
# -----------------------------
#       GET ALL USER ACCOUNTS
# -----------------------------
@api.route("/get_all_users", methods=["GET"])
@require_auth
def get_all_users_route(current_username):
    try:
        users = Account.query.all()

        if not users:
            raise APIError(message="Users not found", status_code=404)

        return jsonify([
            {
                "username": u.username,
                "role": u.role,
                "updated_at": isoformat_german(u.updated_at),
                "full_name": u.full_name(),
                "deleted_at": u.deleted_at,
                "banned_at": u.banned_at,
            }
            for u in users
        ]), 200
    
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code

# ------------------------------
#       GET BUSINESS BALANCE
# ------------------------------
@api.route("/get_business_balance", methods=["GET"])
@require_auth
def get_business_balance_route(current_username):
    try:
        balance = get_business_balance(current_username)
        return jsonify(balance), 200
    
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code

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
        
        if not first_name:
            raise APIError(message="First Name is missing", status_code=400)
        
        if not last_name:
            raise APIError(message="Last Name is missing", status_code=400)
        
        if not pin:
            raise APIError(message="Pin is missing", status_code=400)
        
        if not username:
            raise APIError(message="Username is missing", status_code=400)
        
        if not role:
            raise APIError(message="Role is missing", status_code=400)
        
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


    except APIError as e:
        return jsonify(e.to_dict()), e.status_code


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

        if not business_name:
            raise APIError(message="Business Name is missing", status_code=400)
        
        if not description:
            raise APIError(message="Describtion is missing", status_code=400)
        
        if not pin:
            raise APIError(message="Pin is missing", status_code=400)
        
        if not owner_username:
            raise APIError(message="Owner Username is missing", status_code=400)
        
        pin = str(pin)
        business_name = normalize_business_name(business_name=business_name)
        
        if not validate_business_name(business_name=business_name):
            raise APIError(message="Business name must be 3-25 characters, "
            "underscores or numbers only", status_code=400)
        
        if business_name_exists(business_name):
            raise APIError(message="Business Name already taken", status_code=403)

        if not username_exists(owner_username):
            raise APIError(message="User not found", status_code=404)
        
        if not can_create_business(owner_username, limit=1):
            raise APIError(message="Owner reached business limit", status_code=403)
        
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
            with open(descr_file, "r", encoding="utf-8") as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    data = {}

        is_deleted = False
        with open(deleted_file, "r", encoding="utf-8") as file:
            try:
                contents = json.load(file)
                if str(new_business_account.id) in contents:
                    is_deleted = True
                
            except Exception as e:
                return jsonify(str(e)), 520
            
        if is_deleted:
            raise APIError(message="Business is disabled", status_code=401)


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
        return jsonify({"Error":"Business name already exists"}), 400
    

    except APIError as e:
        db.session.rollback()
        return jsonify(e.to_dict()), e.status_code
    
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
        
        if not business:
            raise APIError(message="Business not found", status_code=404)
        
        if not business_id:
            raise APIError(message="Business Id missing", status_code=400)
        
        if business.deleted_at is not None:
            raise APIError(message="Business already disabled", status_code=422)

        business.deleted_at = db.func.now(timezone.utc)
        db.session.commit()

        deleted_file = "business_deleted.json"
        data = {}
        if os.path.exists(deleted_file):
            with open(deleted_file, "r", encoding="utf-8") as file:
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

    except APIError as e:
        db.session.rollback()
        return jsonify(e.to_dict()), e.status_code


# ---------------------
#     DISABLE USER
# ---------------------
@api.route("/disable_user", methods=["POST"])
@require_auth
@require_role("admin")
def disable_user_route(current_username):

    try:
        data = request.get_json() or {}

        username = data.get("username")

        if not username:
            raise APIError(message="Username missing", status_code=400)

        user = Account.query.filter_by(username=username).first()

        if not user:
            raise APIError(message="User not found", status_code=404)
    
        from . import db

        user.deleted_at = db.func.now(timezone.utc)
        db.session.commit()

        return jsonify("User is disabled"), 200
    
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    
# ---------------------
#     BAN USERS
# ---------------------
@api.route("/ban_users", methods=["POST"])
@require_auth
@require_role("admin")
def ban_users_route(current_username):
    try:
        data = request.get_json() or {}

        usernames = data.get("users")

        if not usernames or len(usernames) == 0:
            raise APIError(message="Usernames missing", status_code=400)
        
        for username in usernames:
            if not username_exists(username):
                raise APIError(message="Username not found", status_code=404)
        
        users = []

        for username in usernames:
            user = Account.query.filter_by(username=username).first()

            if not user:
                raise APIError(message="User not found", status_code=404)
            
            users.append(user)
    
        from . import db

        for user in users:
            if user.role == "admin":
                raise APIError(message="Tried to ban admin", status_code=403)
            
            user.banned_at = db.func.now(timezone.utc)
            db.session.commit()

        return jsonify("Users are banned"), 200
    
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    
# ---------------------
#     DEBAN USERS
# ---------------------
@api.route("/deban_users", methods=["POST"])
@require_auth
@require_role("admin")
def deban_users_route(current_username):
    try:
        data = request.get_json() or {}

        usernames = data.get("users")

        if not usernames or usernames.len() == 0:
            raise APIError(message="Usernames missing", status_code=400)
        
        for username in usernames:
            if not username_exists(username):
                raise APIError(message=f"Username {username} not found", status_code=404)
        
        users = []

        for username in usernames:
            user = Account.query.filter(username=username)

            if not user:
                raise APIError(message="User not found", status_code=404)
    
        from . import db

        for user in users:
            user.banned_at = None
            db.session.commit()

        return jsonify("Users are debanned"), 200
    
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code



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
        absolute_amount = data.get("amount")
        transaction_id = data.get("transaction_id")
        description = data.get("description")
        
        if not issuer_username:
            raise APIError(message="Issuer username missing", status_code=400)
        
        if not absolute_amount:
            raise APIError(message="Amount is missing", status_code=400)
        
        if not transaction_id:
            raise APIError(message="Transaction Id missing", status_code=400)
        
        if not description:
            raise APIError(message="Description missing", status_code=400)

        if not username_exists(issuer_username):
            raise APIError(message="User not found", status_code=404)
        
        result = execute_transfer(payer_username, issuer_username, absolute_amount, transaction_id, description, BANK_FEE, TAXES["Status3"])
        
        #fee_result = pay_fee(issuer_username, absolute_amount*BANK_FEE)
        
        #if fee_result is not True:
        #    raise APIError(message="Transfer went wrong, apparent server error", status_code=500)

        
        if result is True:
            return jsonify("Transfer completed"), 200
        else:
            raise APIError(message="Transfer went wrong", status_code=500)

    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    

# ----------------------------------
#     EXECUTE TRANSFER TO BUSINESS
# ----------------------------------
@api.route("/execute_transfer_to_business", methods=["POST"])
@require_auth
def execute_transfer_to_business_route(current_username):
    try:
        data = request.get_json() or {}

        payer_username = current_username
        issuer_business_name = data.get("issuer_business_name")
        amount = data.get("amount")
        transaction_id = data.get("transaction_id")
        description = data.get("description")
        
        if not issuer_business_name:
            raise APIError(message="Business Name missing", status_code=400)
        
        if not amount:
            raise APIError(message="Amount is missing", status_code=400)
        
        if not transaction_id:
            raise APIError(message="Transaction Id missing", status_code=400)
        
        if not description:
            raise APIError(message="Description missing", status_code=400)

        if not business_name_exists(issuer_business_name):
            raise APIError(message="Business not found", status_code=404)

        result = execute_transfer_to_business(payer_username, issuer_business_name, amount, transaction_id, description)

        if result is True:
            return jsonify("Transfer completed"), 200
        else:
            raise APIError(message="Transfer went wrong", status_code=500)

    except APIError as e:
        return jsonify(e.to_dict()), e.status_code


# -------------------------
#  TODAY'S TRANSACTIONS
# -------------------------
@api.route("/get_todays_transactions", methods=["GET"])
@require_auth
def todays_transactions_route(current_username):
    try:
        now = datetime.now(timezone.utc)
        start = datetime.combine(now.date(), datetime.min.time())

        results = get_todays_transactions(current_username, start, now)

        for entry in results:
            results[results.index(entry)]["transaction_date"] = isoformat_german(results[results.index(entry)]["transaction_date"])

        return jsonify(results), 200

    except APIError as e:
        return jsonify(e.to_dict()), e.status_code

# ----------------------------
#      TRANSACTION AMOUNT
# ----------------------------
@api.route("/transactions_amount", methods=["GET"])
@require_auth
def transactions_amount_route(current_username):
    try:
        results = transactions_amount(current_username)
        return jsonify(results), 200
    
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    
# --------------------------------
#      TODAY`S TRANSACTION AMOUNT
# --------------------------------
@api.route("/todays_transactions_amount", methods=["GET"])
@require_auth
def todays_transaction_amount_route(current_username):
    try:
        now = datetime.now(timezone.utc)
        start = datetime.combine(now.date(), datetime.min.time())

        result = todays_transaction_amount(current_username, start, now)

        return jsonify(result), 200

    except APIError as e:
        return jsonify(e.to_dict()), e.status_code

# ----------------------------------
#  GET UPDATED ACCOUNTS AFTER TIME
# ----------------------------------
@api.route("/get_updated_accounts_after_time", methods=["POST"])
@require_auth
def get_updated_accounts_after_time_route(current_username):
    try:
        data = request.get_json() or {}
        time_input = data.get("time")

        if not time_input:
            raise APIError(message="Time parameter missing", status_code=400)
        formatted_search_time = isoformat_britain(time_input)

        results = get_updated_accounts_after_time(current_username, formatted_search_time)


        return jsonify([
            {
                "username": u["username"],
                "role": u["role"],
                "updated_at": isoformat_german(u["updated_at"]),
                "full_name": u["full_name"],
                "deleted_at": u["deleted_at"],
                "banned_at": u["banned_at"],
                
            }
            for u in results
        ]), 200

    except APIError as e:
        return jsonify(e.to_dict()), e.status_code





# ----------------------------
#  CHECK TOKEN VALIDITY
# ----------------------------
@api.route("/check_token_validity", methods=["GET"])
@require_auth
def check_token_validity_route(current_username):
	return "", 200


from flask import Blueprint, request, jsonify
from app.db.account import (get_user_account, get_user_balance, get_all_user_accounts, create_new_user_account, disable_user, ban_users, deban_users,
                            get_updated_accounts_after_time, execute_transfer, get_todays_transactions, transactions_amount, 
                            todays_transaction_amount, change_user_role, create_payment_request, payment_request, fulfill_payment_request)
from app.db.business import (get_business_balance, execute_transfer_to_business, create_business, disable_business)
from app.db.connection import (username_exists, business_name_exists, get_full_name)
from .auth import (check_pin, generate_token, require_auth, normalize_username, validate_username, 
                   normalize_business_name, validate_business_name, require_role, create_token_for_trans, ROLES)
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from .error import APIError
import secrets
import string


api = Blueprint("api", __name__)

BANK_FEE = 0.05

TAXES = {"Status1": 0.02, "Status2": 0.03, "Status3": 0.05}


# -----------------------------
#     RANDOM TX_ID GENERATOR     
# -----------------------------
def generate_tx_id():
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(12))
    return f"tx_{random_part}"


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

        if not username_exists(username):
            raise APIError(message="User not found", status_code=404)

        # Fetch user via SQLAlchemy model and username
        user = get_user_account(username)
        
        if not user or len(user) == 0:
            raise APIError(message="User not found", status_code=404)
        
        if not user["pin_hash"]:
            raise APIError(message="User has no Pin set", status_code=400)
        
        if user["deleted_at"] is not None:
            raise APIError(message="User is deleted", status_code=401)
        
        if user["banned_at"] is not None:
            raise APIError(message="User is banned", status_code=401)


        # Verify PIN hash
        if not check_pin(user["pin_hash"], pin):
            raise APIError(message="Pin is incorrect", status_code=401)
        
        additional_claims = {
            "role": user["role"],
            "deleted": user["deleted_at"] is not None,
            "banned": user["banned_at"] is not None
        }
        
        # Create token
        token = generate_token(
            idty=user["username"],
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
        user = get_user_account(current_username)

        if not user:
            raise APIError(message="User not found", status_code=404)
        
        
        return jsonify({"username": user["username"], 
                        "balance": user["balance"], 
                        "role": user["role"],  
                        "updated_at": isoformat_german(user["updated_at"]), 
                        "full_name": user["full_name"]}
                    ), 200
    
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    
# -----------------------------
#       GET ALL USERS
# -----------------------------
@api.route("/get_all_users", methods=["GET"])
@require_auth
def get_all_users_route(current_username):
    try:
        users = get_all_user_accounts()

        if not users:
            raise APIError(message="Users not found", status_code=404)

        return jsonify([
            {
                "username": u["username"],
                "role": u["role"],
                "updated_at": isoformat_german(u["updated_at"]),
                "full_name": u["full_name"],
                "deleted_at": u["deleted_at"],
                "banned_at": u["banned_at"],
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

        if username_exists(username):
            raise APIError(message="User already in place", status_code=403)
        
        if not validate_username(username=username):
            return jsonify("Username must be 3-25 characters, lowercase letters, "
            "underscores or numbers only"), 400
        
        start_balance = 100
        
        id = create_new_user_account(
            first_name=first_name,
            last_name=last_name,
            balance=start_balance,
            username=username,
            role=role,
            pin=pin,
        )

        return jsonify({"message": "User created", "id": id, "username": username}), 201


    except APIError as e:
        return jsonify(e.to_dict()), e.status_code


# -------------------------
#       CREATE BUSINESS
# -------------------------
@api.route("/create_business", methods=["POST"])
@require_auth
@require_role("admin")
def create_business_route(current_username):
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
        
        
        START_BALANCE = 0
        
        business_id = create_business(owner_username, START_BALANCE, business_name, pin, description, "owner")

        return jsonify({"message": "Business created", "id": business_id}), 201
    
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    


# --------------------------------
#     DISABLE BUSINESS
# --------------------------------
@api.route("/disable_business", methods=["POST"])
@require_auth
@require_role("admin")
def disable_business_route(current_username):
    try:
        data = request.get_json() or {}

        owner_username = data.get("owner_username")
        
        if not owner_username:
            raise APIError(message="Owner username missing", status_code=400)
        
        disable_business(owner_username)

        return jsonify("Business disabled"), 200

    except APIError as e:
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
        
        if not username_exists(username):
            raise APIError(message="Username not existing", status_code=400)

        user = get_user_account()

        if not user:
            raise APIError(message="User not found", status_code=404)
    
        disable_user(username)

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
        
        ban_users(usernames)


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
        
        deban_users(usernames)

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

        result = execute_transfer_to_business(payer_username, issuer_business_name, amount, transaction_id, description, BANK_FEE, TAXES["Status3"])

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
            entry["transaction_date"] = isoformat_german(entry["transaction_date"])

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

        results = get_updated_accounts_after_time(formatted_search_time, )


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


# -------------------------
#       CHANGE USER ROLE
# -------------------------
@api.route("/change_user_role", methods=["POST"])
@require_auth
@require_role("admin")
def change_user_role_route(current_username):
    try:
        data = request.get_json() or {}
        new_role = data.get("new_role")

        if not new_role:
            raise APIError(message="New role parameter missing", status_code=400)

        if new_role not in ROLES:
            raise APIError(message="Unknown role", status_code=400)
        
        result = change_user_role(current_username, new_role)

        if not result:
            raise APIError(message="Couldn´t change role, please alert devs", status_code=500)
    
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code



# -----------------------------
#       CREATE PAYMENT REQUEST
# -----------------------------
@api.route("/create_payment_request", methods=["POST"])
@require_auth
def create_payment_request_route(current_username):
    try:
        data = request.get_json() or {}

        amount = data.get("amount")
        description = data.get("description")

        
        if not amount:
            raise APIError(message="Amount is missing", status_code=400)
        
        if not description:
            raise APIError(message="Description is missing", status_code=400)
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        token = create_token_for_trans()
        
        response = create_payment_request(token, current_username, amount, expires_at, description)
        
        if not response:
            raise APIError(message="Payment Request creation failed. Please alert devs", status_code=500)

        return jsonify({"token": token, "expires_at" : expires_at}), 200


    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    

# -----------------------------
#       PAYMENT REQUEST
# -----------------------------
@api.route("/payment_request/<token>", methods=["GET"])
@require_auth
def payment_request_route(current_username, token):
    try:
        now = datetime.now(timezone.utc)

        response = payment_request(token, now)
        
        if len(response) <= 0:
            raise APIError(message="Token probably expired.", status_code=410)

        print(response)
        
        response["token"] = token
        response["requester_full_name"] = get_full_name(current_username)[0]

        return jsonify(response), 200


    except APIError as e:
        return jsonify(e.to_dict()), e.status_code


# -----------------------------
#    FULFILL PAYMENT REQUEST
# -----------------------------
@api.route("/fulfill_payment_request", methods=["POST"])
@require_auth
def fulfill_payment_request_route(current_username):
    try:
        now = datetime.now(timezone.utc)

        data = request.get_json() or {}

        payment_data = payment_request(data.get("token"), now)

        if len(data) <= 0:
            raise APIError(message="Token probably expired.", status_code=410)
        
        result = execute_transfer(current_username, payment_data["requester_username"], float(payment_data["amount"]), generate_tx_id(), payment_data["description"], BANK_FEE, TAXES["Status3"])
        if result is True:
            fulfill_payment_request(now, data.get("token"))
            return jsonify("Transfer completed"), 200
        else:
            raise APIError(message="Transfer went wrong", status_code=500)
        
        
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code




# ----------------------------
#  CHECK TOKEN VALIDITY
# ----------------------------
@api.route("/check_token_validity", methods=["GET"])
@require_auth
def check_token_validity_route(current_username):
	return "", 200


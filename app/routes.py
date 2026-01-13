from flask import Blueprint, request, jsonify, send_from_directory
from flask_jwt_extended import get_jwt_identity
from .models import Account
from .auth import check_pin, generate_token, require_auth, normalize_username, validate_username
from .db_raw import get_balance, execute_transfer, get_todays_transactions, transactions_amount, get_user_by_id
from datetime import datetime

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
def create_user_route():
    try:
        data = request.get_json() or {}

        first_name = data.get("first_name")
        last_name = data.get("last_name")
        pin = data.get("pin")
        username = data.get("username")

        if not first_name or not last_name or not pin or not username:
            return jsonify("Missing fields"), 400
        
        pin = str(pin)
        username = normalize_username(username=username)
        
        if not validate_username(username=username):
            return jsonify("Username must be 3-25 charakters, lowercase letters, "
            "underscores or numbers only"), 400
        
        new_account = Account(
            first_name=first_name,
            last_name=last_name,
            balance=0,
            username = username,
        )
        new_account.set_pin(pin)

        from . import db
        db.session.add(new_account)
        db.session.commit()

        return jsonify({"message": "User created", "id": new_account.id}), 201
    
    except IntegrityError:
        return jsonify("Username already taken"), 400

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
        results = transactions_amount(current_user_id)
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


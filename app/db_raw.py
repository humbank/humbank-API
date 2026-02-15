import mysql.connector
from flask import current_app
from .error import APIError

# Create a fresh MySQL connection using credentials from config
def getBank():
    return mysql.connector.connect(
        host=current_app.config["MYSQL_HOST"],
        user=current_app.config["MYSQL_USER"],
        password=current_app.config["MYSQL_PASS"],
        database=current_app.config["MYSQL_DB"],
        charset="utf8mb4",
        autocommit=False  # IMPORTANT: we control commits manually
    )

def id_exists(id):
    conn = getBank()
    cursor = conn.cursor()
    cursor.execute("select id from accounts where id = %s;", (id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result is not None

def username_exists(username):
    conn = getBank()
    cursor = conn.cursor()
    cursor.execute("select username from accounts where username = %s;", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result is not None

def business_name_exists(business_name):
    conn = getBank()
    cursor = conn.cursor()
    cursor.execute("select business_name from business_accounts where business_name = %s;", (business_name,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result is None


def get_user_balance(username):
    try:
        if not (username and username_exists(username)):
            raise APIError(message="Username not found", status_code=404)
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = "select balance from accounts where username = %s;"

        cursor.execute(sql, (username,))
        results = cursor.fetchone()

        return results["balance"]

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if cursor: conn.close()




# ----------------------------------------
#       EXECUTE TRANSFER WITH FEE AND TAX
# ----------------------------------------
def execute_transfer(payer_username, issuer_username, amount, transaction_id, description, fee, taxes):

    conn = getBank()
    cursor = conn.cursor(dictionary=True)

    try:
        netto_amount = round(amount - (amount * fee) - (amount * taxes), 2)
        
        # Start transaction
        conn.start_transaction()

        # Lock payer
        cursor.execute(
            "select balance from accounts where username = %s for update",
            (payer_username,)
        )

        payer = cursor.fetchone()

        if not payer:
            raise APIError(message="Payer not found", status_code=404)

        if payer["balance"] < amount:
            raise APIError(message="Insufficient funds", status_code=403)

        # Lock issuer
        cursor.execute(
            "select balance from accounts where username = %s for update",
            (issuer_username,)
        )

        issuer = cursor.fetchone()

        if not issuer:
            raise APIError(message="Issuer not found", status_code=404)
        
        cursor.execute(
            "select balance from business_accounts where business_name = %s for update",
            ("Bank",)
        )

        bank = cursor.fetchone()

        if not issuer:
            raise APIError(message="Bank not found, Important", status_code=404)

        # Update balances
        cursor.execute(
            "update accounts set balance = balance - %s where username = %s",
            (amount, payer_username)
        )
        cursor.execute(
            "update accounts set balance = balance + %s where username = %s",
            (netto_amount, issuer_username)
        )
        cursor.execute(
            "update business_accounts set balance = balance + %s where business_name = %s",
            (amount * fee, "Bank")
        )

        # Insert transaction
        cursor.execute(
            "insert into transactions (transaction_id, payer_username, issuer_username, amount, netto_amount, description, bank_fee, trans_tax) values (%s, %s, %s, %s, %s, %s, %s, %s)",
            (transaction_id, payer_username, issuer_username, amount, netto_amount, description, fee, taxes)
        )

        conn.commit()
        return True

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        conn.close()


# ------------------------------------
#       EXECUTE TRANSFER TO BUSINESS
# ------------------------------------
def execute_transfer_to_business(payer_username, issuer_business_name, amount, transaction_id, description):

    conn = getBank()
    cursor = conn.cursor(dictionary=True)

    try:
        # Start transaction
        conn.start_transaction()

        # Lock payer
        cursor.execute(
            "select balance from accounts where username = %s for update",
            (payer_username,)
        )

        payer = cursor.fetchone()
        if not payer:
            raise APIError(message="Payer not found", status_code=404)

        if payer["balance"] < amount:
            raise APIError(message="Insufficient funds", status_code=403)

        # Lock issuer
        cursor.execute(
            "select balance from business_accounts where business_name = %s for update",
            (issuer_business_name,)
        )

        issuer = cursor.fetchone()
        if not issuer:
            raise APIError(message="Issuer not found", status_code=404)

        # Update balances
        cursor.execute(
            "update accounts set balance = balance - %s where username = %s",
            (amount, payer_username)
        )
        cursor.execute(
            "update business_accounts set balance = balance + %s where business_name = %s",
            (amount, issuer_business_name)
        )

        # Insert transaction
        cursor.execute(
            "insert into transactions (transaction_id, payer_username, issuer_username, amount, description) values (%s, %s, %s, %s, %s)",
            (transaction_id, payer_username, issuer_business_name, amount, description)
        )

        conn.commit()
        return True

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        conn.close()


# ---------------------------------------
#       GET TRANSACTIONS FROM DATE
# ---------------------------------------
def get_todays_transactions(username, start_of_day, now):
    try:
        if not (username and username_exists(username)):
            raise APIError(message="User not found", status_code=404)
        
        if not(now and start_of_day):
            raise APIError(message="Dates are missing", status_code=400)
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT * from transactions
            WHERE (payer_username = %s OR issuer_username = %s)
            AND transaction_date between %s AND %s
            ORDER BY transaction_date DESC
        """

        cursor.execute(sql, (username, username, start_of_day, now))
        results = cursor.fetchall()

        return results
    
    except APIError:
        conn.rollback()
        raise
        
    finally:
        if cursor: cursor.close()
        conn.close()

# --------------------------------------
#       GET AMOUNT OF ALL TRANSACTIONS
# --------------------------------------
def transactions_amount(username):
    try:
        if not (username and username_exists(username)):
            raise APIError(message="User not found", status_code=404)
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT COUNT(*) as trans_amount from transactions
            WHERE (payer_username = %s OR issuer_username = %s)
        """

        cursor.execute(sql, (username, username))
        results = cursor.fetchone()

        return results

    except APIError:
        conn.rollback()
        raise
        
    finally:
        if cursor: cursor.close()
        conn.close()



# ------------------------------------------------
#       GET USER ID BY USERNAME (for business)
# ------------------------------------------------
def get_user_id_by_username(username):
    try:
        if not (username and username_exists(username)):
            raise APIError(message="User not found", status_code=404)
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = """
                select id from accounts
                where username = %s;"""
        
        cursor.execute(sql, (username,))
        results = cursor.fetchone()

        return results["id"]
    
    except APIError:
        conn.rollback()
        raise
    
    finally:
        if cursor: cursor.close()
        conn.close()


# -----------------------------------
#       GET BUSINESS ID BY USERNAME
# -----------------------------------
def get_business_id_by_username(username):
    try:
        if not (username and username_exists(username)):
            raise APIError(message="User not found", status_code=404)
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)
        
        sql = "select id from business_accounts where owner_username = %s;"

        cursor.execute(sql, (username, ))

        business_id = cursor.fetchone()

        return business_id["id"]

    except APIError:
        conn.rollback()
        raise
    
    finally:
        if cursor: cursor.close()
        conn.close()

# ---------------------------------
#       GET BUSINESS BALANCE
# ---------------------------------
def get_business_balance(username):
    try:
        if not (username and username_exists(username)):
            raise APIError(message="User not found", status_code=404)
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = "select balance from business_accounts where owner_username = %s;"

        cursor.execute(sql, (username,))

        row = cursor.fetchone()

        if not row:
            raise APIError(message="Balance missing. Alert devs", status_code=500)

        return {
            "balance": float(row["balance"])
        }

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if cursor: conn.close()

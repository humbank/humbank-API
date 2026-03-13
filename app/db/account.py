from .connection import (getBank, id_exists, username_exists, business_name_exists)
from app.error import APIError
from app.auth import hash_pin




# ----------------------------------------
#       GET USER BALANCE
# ----------------------------------------
def get_user_balance(username):
    try:
       
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
        if conn: conn.close()


# ----------------------------------------
#       GET USER ACCOUNT
# ----------------------------------------
def get_user_account(username):
    try:
        if not (username and username_exists(username)):
            raise APIError(message="Username not found", status_code=404)
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = "select * from accounts where username = %s"

        cursor.execute(sql, (username,))

        results = cursor.fetchall()[0]

        full_name = f"{results["first_name"]} {results["last_name"]}"

        results["full_name"] = full_name

        return results

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ----------------------------------------
#       GET ALL USER ACCOUNTS
# ----------------------------------------
def get_all_user_accounts():
    try:
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = "select * from accounts"

        cursor.execute(sql)

        results = cursor.fetchall()

        return results

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ----------------------------------------
#       CREATE NEW USER ACCOUNT
# ----------------------------------------
def create_new_user_account(first_name, last_name, balance, username, role, pin):
    try:
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        pin_hash = hash_pin(pin)
        full_name = f"{str(first_name)} {str(last_name)}"

        sql = "insert into accounts (first_name, last_name, full_name, balance, username, role, pin_hash) values(%s, %s, %s, %s, %s, %s, %s)"

        cursor.execute(sql, (first_name, last_name, full_name, balance, username, role, pin_hash))

        user_id = cursor.lastrowid

        conn.commit()

        return user_id

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ----------------------------------------
#       DISABLE USER ACCOUNT
# ----------------------------------------
def disable_user(username):
    try:
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = "update accounts set deleted_at = now() where username = %s;"

        cursor.execute(sql, (username, ))

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ----------------------------------------
#       BAN USER ACCOUNTS
# ----------------------------------------
def ban_users(users_dict):
    try:
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        for username in users_dict:
            sql = "update accounts set banned_at = now() where username = %s and not role = 'admin';"
            cursor.execute(sql, (username, ))

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ----------------------------------------
#       DEBAN USER ACCOUNTS
# ----------------------------------------
def deban_users(users_dict):
    try:
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        for username in users_dict:
            sql = "update accounts set banned_at = null where username = %s;"
            cursor.execute(sql, (username, ))

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()





# ---------------------------------------
#       GET UPDATED ACCOUNTS AFTER TIME
# ---------------------------------------
def get_updated_accounts_after_time(time):
    try:   
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = """
                select 
                    username, 
                    role, 
                    updated_at, 
                    deleted_at,
                    banned_at,
                    concat(first_name, ' ', last_name) AS full_name
                from accounts
                where updated_at >= %s;
            """
        cursor.execute(sql, (time, ))
        results = cursor.fetchall()

        return results
    
    except APIError:
        conn.rollback()
        raise
        
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ----------------------------------------
#       EXECUTE TRANSFER WITH FEE AND TAX
# ----------------------------------------
def execute_transfer(payer_username, issuer_username, amount, transaction_id, description, fee, taxes):

    conn = getBank()
    cursor = conn.cursor()

    try:
        netto_amount = round(amount - (amount * fee) - (amount * taxes), 2)
        fee_amount = amount - netto_amount
        
        # Start transaction
        conn.start_transaction()

        #update the balance of payer
        cursor.execute(
            "update accounts set balance = balance - %s where username = %s and balance >= %s;",
            (amount, payer_username, amount)
        )

        if cursor.rowcount <= 0:
            raise APIError(message="Insufficient funds", status_code=403)

        #update the balance of issuer
        cursor.execute(
            "update accounts set balance = balance + %s where username = %s;",
            (netto_amount, issuer_username)
        )

        #pay fee to bank
        cursor.execute(
            "update business_accounts set balance = balance + %s where business_name ='Bank';",
            (fee_amount, )
        )

        if cursor.rowcount <= 0:
            raise APIError(message="Bank not found, Important", status_code=404)


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
        if conn: conn.close()


# ---------------------------------------
#       GET TODAYS TRANSACTIONS 
# ---------------------------------------
def get_todays_transactions(username, start_of_day, now):
    try:   
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
        if conn: conn.close()

# --------------------------------------
#       GET AMOUNT OF ALL TRANSACTIONS
# --------------------------------------
def transactions_amount(username):
    try:
        
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
        if conn: conn.close()

# ---------------------------------------
#       GET TODAYS TRANSACTION AMOUNT
# ---------------------------------------
def todays_transaction_amount(username, start_of_day, now):
    try:
        if not(now and start_of_day):
            raise APIError(message="Dates are missing", status_code=400)
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT COUNT(transaction_id) as todays_trans_amount from transactions
            WHERE (payer_username = %s OR issuer_username = %s)
            AND transaction_date between %s AND %s
            ORDER BY transaction_date DESC
        """

        cursor.execute(sql, (username, username, start_of_day, now))
        result = cursor.fetchone()

        return result
    
    except APIError:
        conn.rollback()
        raise
        
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# ----------------------------------------
#       CHANGE USER ROLE
# ----------------------------------------
def change_user_role(username, role):
    try:
        conn = getBank()
        cursor = conn.cursor()

        sql = "update accounts set role = %s where username = %s;"

        cursor.execute(sql, (username, role))

        conn.commit()

        return True

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()



# ----------------------------------------
#       CREATE PAYMENT REQUEST
# ----------------------------------------
def create_payment_request(token, requester_username, amount, expires_at, description):

    conn = getBank()
    cursor = conn.cursor()

    try:     

        # Insert request
        cursor.execute(
            "insert into payment_requests (token, requester_username, amount, expires_at, description) values (%s, %s, %s, %s, %s)",
            (token, requester_username, amount, expires_at, description)
        )

        conn.commit()

        return True

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ----------------------------------------
#       PAYMENT REQUEST
# ----------------------------------------
def payment_request(token, now):

    conn = getBank()
    cursor = conn.cursor(dictionary=True)

    try:     
        # Insert request
        cursor.execute(
            "select requester_username, amount, description, expires_at, fulfilled_at from payment_requests where token = %s and expires_at > %s;",
            (token, now)
        )

        results = cursor.fetchone()

        return results

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ----------------------------------------
#        FULFILL PAYMENT REQUEST
# ----------------------------------------

def fulfill_payment_request(current_time, request_token):

    conn = getBank()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "update payment_requests set fulfilled_at=%s where token=%s;",
            (current_time, request_token)
        )
        conn.commit()

        return True
    
    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
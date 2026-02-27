from .connection import (getBank, id_exists, username_exists, business_name_exists)
from app.error import APIError
from app.auth import hash_pin




# ----------------------------------------
#       GET USER BALANCE
# ----------------------------------------
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
        if cursor: conn.close()


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

        return results

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if cursor: conn.close()

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
        if cursor: conn.close()


# ----------------------------------------
#       CREATE NEW USER ACCOUNT
# ----------------------------------------
def create_new_user_account(first_name, last_name, balance, username, role, pin):
    try:
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        if username_exists(username):
            raise APIError(message="User already in place", status_code=403)

        pin_hash = hash_pin(pin)
        full_name = f"{str(first_name)} {str(last_name)}"

        sql = "insert into accounts (first_name, last_name, full_name, balance, username, role, pin_hash) " \
        "values(%s, %s, %s, %s, %s, %s, %s)"

        cursor.execute(sql, (first_name, last_name, full_name, balance, username, role, pin_hash))

        sql = "select id from accounts where username = %s"

        cursor.execute(sql, (username,))

        result = cursor.fetchone()

        return result

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if cursor: conn.close()
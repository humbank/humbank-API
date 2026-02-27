from .connection import (getBank, id_exists, username_exists, business_name_exists)
from app.error import APIError




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

        full_name = results["first_name"] + " " + results["last_name"]

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

        results = cursor.fetchall()[0]

        print(results)

        return results

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if cursor: conn.close()
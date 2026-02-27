from .connection import (getBank, id_exists, username_exists, business_name_exists)
from app.error import APIError


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
        if conn: conn.close()
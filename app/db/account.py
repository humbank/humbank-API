from .connection import (getBank, id_exists, username_exists, business_name_exists)
from app.error import APIError





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


def get_user_account(username):
    try:
        if not (username and username_exists(username)):
            raise APIError(message="Username not found", status_code=404)
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = "select * from accounts where username = %s"

        cursor.execute(sql, (username,))

        results = cursor.fetchall()

        return results[0]

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if cursor: conn.close()
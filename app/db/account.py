from .connection import getBank
from app.error import APIError


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
    cursor.execute("select username from accounts where username = %s and deleted_at is NULL and banned_at is NULL;", (username,))
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
    
    return result is not None




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
        print(results)

        return results

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if cursor: conn.close()
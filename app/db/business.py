from .connection import (getBank, id_exists, username_exists, business_is_deleted)
from app.error import APIError
from app.auth import hash_pin
import json
import os

# ------------------------------------------------
#       GET USER ID BY USERNAME
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


# ---------------------------------
#       CREATE BUSINESS
# ---------------------------------
def create_business(owner_username, start_balance, business_name, pin, description, member_role):
    try:
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        if not can_create_business(owner_username, cursor, limit=1):
            raise APIError(message="Owner reached business limit", status_code=403)
        
        if business_is_deleted(owner_username):
            raise APIError(message="Business was already created", status_code=403)
        
        pin_hash = hash_pin(pin)
        owner_id = get_user_id_by_username(owner_username)

        sql = "insert into business_accounts (business_name, balance, pin_hash, owner_id, owner_username) values" \
        "(%s, %s, %s, %s, %s)"

        cursor.execute(sql, (business_name, start_balance, pin_hash, owner_id, owner_username))

        business_id = cursor.lastrowid


        #add description to description file
        descr_file = "business_descr.json"
        data = {}
        if os.path.exists(descr_file):
            with open(descr_file, "r", encoding="utf-8") as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    data = {}

        # Add new business
        data[business_id] = description

        # Write back
        with open(descr_file, "w") as file:
            json.dump(data, file)

        conn.commit()

        create_business_member(owner_id, owner_username, business_id, member_role)

        return business_id
            
    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --------------------------------
#     BUSINESS CREATION HELPER
# --------------------------------
def can_create_business(username, cursor, limit=1):
    sql = "select count(*) as count from business_accounts where owner_username = %s and deleted_at is NULL;"
    cursor.execute(sql, (username,))
    active_count = cursor.fetchone()
    return active_count["count"] < limit


# ---------------------------------
#       CREATE BUSINESS MEMBER
# ---------------------------------
def create_business_member(user_id, username, business_id, member_role):
    try:
        conn = getBank()
        cursor = conn.cursor(dictionary=True)


        sql = "insert into business_members (business_id, user_id, role, username) values" \
        "(%s, %s, %s, %s, %s)"

        cursor.execute(sql, (business_id, user_id, member_role, username))

        conn.commit()
            
    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ---------------------------------
#       DISABLE BUSINESS
# ---------------------------------
def disable_business(owner_username):
    try:
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        
        if business_is_deleted(owner_username):
            raise APIError(message="Business was already deleted", status_code=422)

        sql = "update business_accounts set deleted_at = now() where owner_username = %s"

        cursor.execute(sql, (owner_username,))

        conn.commit()


            
    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()
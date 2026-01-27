import mysql.connector
from flask import current_app

# Create a fresh MySQL connection using credentials from config
def getBank():
    return mysql.connector.connect(
        host=current_app.config["MYSQL_HOST"],
        user=current_app.config["MYSQL_USER"],
        password=current_app.config["MYSQL_PASS"],
        database=current_app.config["MYSQL_DB"],
        autocommit=False  # IMPORTANT: we control commits manually
    )

def id_exists(id):
    conn = getBank()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM accounts WHERE id = %s;", (id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result is not None

def username_exists(username):
    conn = getBank()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM accounts WHERE username = %s;", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result is not None

def get_user_balance(username):
    try:
        if not (username and username_exists(username)):
            raise Exception("Missing requirements or id not existing")
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = "select balance from accounts where username = %s;"

        cursor.execute(sql, (username,))
        results = cursor.fetchone()

        return results

    except Exception as e:
        return str(e)
    finally:
        cursor.close()
        conn.close()

# Perform a SAFE money transfer (atomic)
def execute_transfer(current_username, payer_username, issuer_username, amount, transaction_id, describtion):
    """
    Atomic payment transfer:
    - Locks both payer and issuer rows using SELECT ... FOR UPDATE
    - Checks payer balance
    - Updates both balances
    - Inserts transaction record
    - Commits or rolls back
    """
    conn = getBank()
    cursor = conn.cursor(dictionary=True)

    try:
        describtion = describtion or "UNKNOWN REASON!"
        # Start transaction
        conn.start_transaction()

        # Lock payer
        cursor.execute(
            "select balance from accounts where username = %s for upate",
            (payer_username,)
        )
        payer = cursor.fetchone()
        if not payer:
            raise Exception("Payer not found")

        if payer["balance"] < amount:
            raise Exception("Insufficient funds")

        # Lock issuer
        cursor.execute(
            "select balance from accounts where id = %s for update",
            (issuer_username,)
        )
        issuer = cursor.fetchone()
        if not issuer:
            raise Exception("Issuer not found")

        # Update balances
        cursor.execute(
            "update accounts set balance = balance - %s where username = %s",
            (amount, payer_username)
        )
        cursor.execute(
            "update accounts set balance = balance + %s where username = %s",
            (amount, issuer_username)
        )

        # Insert transaction
        cursor.execute(
            "insert into transactions (transaction_id, payer_username, issuer_username, amount, describtion) values (%s, %s, %s, %s, %s)",
            (transaction_id, payer_username, issuer_username, amount, describtion)
        )

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        return str(e)

    finally:
        cursor.close()
        conn.close()


# Load today's transactions for a user (raw SQL)
def get_todays_transactions(user_id, start_of_day, now):
    try:
        if not (user_id and start_of_day and now and id_exists(user_id)):
            raise Exception("Missing requirements or id not existing")
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT * from transactions
            WHERE (payer_id = %s OR issuer_id = %s)
            AND transaction_date between %s AND %s
            ORDER BY transaction_date DESC
        """

        cursor.execute(sql, (user_id, user_id, start_of_day, now))
        results = cursor.fetchall()

        return results
    except Exception as e:
        return str(e)
        
    finally:
        cursor.close()
        conn.close()

#get the amount of transactions done today
def transactions_amount(user_id):
    try:
        if not (user_id and id_exists(user_id)):
            raise Exception("Missing requirements or id not existing")
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT COUNT(*) as trans_amount from transactions
            WHERE (payer_id = %s OR issuer_id = %s)
        """

        cursor.execute(sql, (user_id, user_id))
        results = cursor.fetchone()

        return results

    except Exception as e:
        return str(e)
        
    finally:
        cursor.close()
        conn.close()

#get the Users first and last name via the user_id
def get_user_by_id(user_id):
    try:
        if not (user_id and id_exists(user_id)):
            raise Exception("Missing requirements or id not existing")
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = """
                select first_name, last_name from accounts
                where id = %s;"""
        
        cursor.execute(sql, (user_id,))
        results = cursor.fetchone()

        return results
    
    except Exception as e:
        return str(e)
    finally:
        cursor.close()
        conn.close()

#get the user id by the username
def get_user_id_by_username(username):
    try:
        if not (username and username_exists(username)):
            raise Exception("Missing requirements or username not existing")
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = """
                select id from accounts
                where username = %s;"""
        
        cursor.execute(sql, (username,))
        results = cursor.fetchone()

        return results["id"]
    
    except Exception as e:
        return str(e)
    
    finally:
        cursor.close()
        conn.close()

# ---------------------------------
#       GET BUSINESS ID BY USER ID
# ---------------------------------
def get_business_id_by_user_id(user_id):
    try:
        if not (user_id and id_exists(user_id)):
            raise Exception("Missing Credentials")
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)
        
        sql = "select id from business_accounts where owner_id = %s;"

        cursor.execute(sql, (user_id, ))

        business_id = cursor.fetchone()

        return business_id["id"]

    except Exception as e:
        return str(e)
    
    finally:
        cursor.close()
        conn.close()

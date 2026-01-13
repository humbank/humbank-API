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

def get_balance(user_id):
    try:
        if not (user_id and id_exists(user_id)):
            raise Exception("Missing requirements or id not existing")
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = "select balance from accounts where id = %s;"

        cursor.execute(sql, (user_id,))
        results = cursor.fetchone()

        return results

    except Exception as e:
        return str(e)
    finally:
        cursor.close()
        conn.close()

# Perform a SAFE money transfer (atomic)
def execute_transfer(payer_id, issuer_id, amount, transaction_id):
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
        # Start transaction
        conn.start_transaction()

        # Lock payer
        cursor.execute(
            "SELECT balance FROM accounts WHERE id = %s FOR UPDATE",
            (payer_id,)
        )
        payer = cursor.fetchone()
        if not payer:
            raise Exception("Payer not found")

        if payer["balance"] < amount:
            raise Exception("Insufficient funds")

        # Lock issuer
        cursor.execute(
            "SELECT balance FROM accounts WHERE id = %s FOR UPDATE",
            (issuer_id,)
        )
        issuer = cursor.fetchone()
        if not issuer:
            raise Exception("Issuer not found")

        # Update balances
        cursor.execute(
            "UPDATE accounts SET balance = balance - %s WHERE id = %s",
            (amount, payer_id)
        )
        cursor.execute(
            "UPDATE accounts SET balance = balance + %s WHERE id = %s",
            (amount, issuer_id)
        )

        # Insert transaction
        cursor.execute(
            "INSERT INTO transactions (transaction_id, payer_id, issuer_id, amount) VALUES (%s, %s, %s, %s)",
            (transaction_id, payer_id, issuer_id, amount)
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
def transactions_amount(user_id, start_of_day, now):
    try:
        if not (user_id and start_of_day and now and id_exists(user_id)):
            raise Exception("Missing requirements or id not existing")
        
        conn = getBank()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT COUNT(*) from transactions
            WHERE (payer_id = %s OR issuer_id = %s)
        """

        cursor.execute(sql, (user_id, user_id))
        results = cursor.fetchall()

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

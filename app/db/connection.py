import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool



POOL = None

def init_connection_pool(app):
    global POOL
    POOL = MySQLConnectionPool(
        pool_name="humbank_pool",
        pool_size=10,  # adjust later if needed
        host=app.config["MYSQL_HOST"],
        user=app.config["MYSQL_USER"],
        password=app.config["MYSQL_PASS"],
        database=app.config["MYSQL_DB"],
        charset="utf8mb4",
        autocommit=False
    )

# Create a fresh MySQL connection using credentials from config
def getBank():
    return POOL.get_connection()

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

def business_is_deleted(owner_username):
    conn = getBank()
    cursor = conn.cursor()
    cursor.execute("select deleted_at from business_accounts where owner_username = %s;", (owner_username,))
    result = cursor.fetchone()
    print(result)
    cursor.close()
    conn.close()
    
    return result is not None

def get_full_name(username):
    conn = getBank()
    cursor = conn.cursor()
    cursor.execute("select concat(first_name, ' ', last_name) from accounts where username = %s and deleted_at is NULL and banned_at is NULL;", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result

def get_user_role(username):
    conn = getBank()
    cursor = conn.cursor()
    cursor.execute("select role from accounts where username = %s and deleted_at is NULL and banned_at is NULL;", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result


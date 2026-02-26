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
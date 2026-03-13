from .connection import (getBank, id_exists, username_exists, business_name_exists)
from app.error import APIError




# ----------------------------------------
#       CREATE PRODUCT
# ----------------------------------------
def create_product(business_name, product_name, price, description):
    try:
       
        conn = getBank()
        cursor = conn.cursor()

        sql = "insert into products (business_name, product_name, price, description) values (%s, %s, %s, %s);"

        cursor.execute(sql, (business_name, product_name, price, description))

        return True

    except APIError:
        conn.rollback()
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

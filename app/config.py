import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("APP_SECRET")

    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASS = os.getenv("MYSQL_PASS")
    MYSQL_DB   = os.getenv("MYSQL_DB")

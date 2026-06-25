import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    database_url = os.getenv("DATABASE_URL")
    print(f"DATABASE_URL found: {database_url is not None}")
    print(f"DATABASE_URL value starts with: {str(database_url)[:20] if database_url else 'NONE'}")

    if database_url:
        conn = psycopg2.connect(database_url)
    else:
        conn = psycopg2.connect(
            host     = os.getenv("DB_HOST"),
            port     = os.getenv("DB_PORT"),
            dbname   = os.getenv("DB_NAME"),
            user     = os.getenv("DB_USER"),
            password = os.getenv("DB_PASSWORD")
        )
    return conn

def get_cursor():
    conn = get_connection()
    cur  = conn.cursor()
    return conn, cur
import os
import psycopg2
from psycopg2 import pool, OperationalError
import time
import logging
from colorlog import ColoredFormatter

# Logging configuration
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
formatter = ColoredFormatter(
    "%(asctime)s - %(name)s - %(log_color)s%(levelname)s%(reset)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)

def create_db_pool():
    max_attempts = 5
    attempt = 0
    backoff_time = 1  # Initial backoff time in seconds

    while attempt < max_attempts:
        try:
            db_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dbname=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432')
            )
            # Test the connection
            conn = db_pool.getconn()
            db_pool.putconn(conn)  # Return the connection back to the pool
            return db_pool
        except OperationalError:
            attempt += 1
            print(f"Attempt {attempt} failed. Retrying in {backoff_time} seconds...")
            time.sleep(backoff_time)
            backoff_time *= 2  # Exponential backoff

    raise Exception("Unable to connect to the database after multiple attempts, verify your database status.")

# Usage
try:
    db_pool = create_db_pool()
    print("Database pool created successfully.")
except Exception as e:
    print(f"Error creating database pool: {e}")

def get_db_connection():
    try:
        conn = db_pool.getconn()
        if conn.closed != 0:
            raise psycopg2.InterfaceError("Connection is closed.")
        logger.info("Database connection retrieved from pool.")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise

def put_connection(conn):
    db_pool.putconn(conn)

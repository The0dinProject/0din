import os
import sqlite3
import time
import logging
from colorlog import ColoredFormatter

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

DB_PATH = os.getenv("DB_PATH", "index.sqlite")

# SQLite connection setup
def create_sqlite_connection():
    max_attempts = 5
    attempt = 0
    backoff_time = 1

    while attempt < max_attempts:
        try:
            conn = sqlite3.connect(DB_PATH)
            logger.info("Successfully connected to SQLite database.")
            return conn
        except sqlite3.Error as e:
            attempt += 1
            logger.warning(f"Attempt {attempt} failed. Retrying in {backoff_time} seconds...")
            logger.error(f"Error: {e}")
            time.sleep(backoff_time)
            backoff_time *= 2

    raise Exception("Unable to connect to the database after multiple attempts. Verify the database file.")

def execute_query(query, params=None):
    try:
        conn = create_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        logger.info("Query executed successfully.")
        return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Query execution failed: {e}")
        raise
    finally:
        conn.close()
        logger.info("SQLite connection closed.")

def init_db():
    conn = create_sqlite_connection()
    try:
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                md5_hash TEXT NOT NULL,
                path TEXT NOT NULL,
                download_count INTEGER DEFAULT 0,
                file_size INTEGER
            );
        """)
        conn.commit()
        logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        conn.close()
"""
Database Configuration Module
Centralized database configuration for DisasterGuard
Uses SQLite by default for easy setup, with PostgreSQL as an option
"""

import os
import sqlite3
from dotenv import load_dotenv
from contextlib import contextmanager

# Path is now ../../.env since we're in database/ directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Default to SQLite for simplicity
USE_SQLITE = False

# SQLite database file path
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'disasterguard.db')

# PostgreSQL Database Configuration (if USE_SQLITE is False)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'disasterguard'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}


@contextmanager
def get_db_connection():
    """Get database connection - uses SQLite by default"""
    conn = None
    try:
        if USE_SQLITE:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.row_factory = sqlite3.Row  # To get dictionaries from rows
            yield conn
        else:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(**DB_CONFIG)
            conn.cursor_factory = RealDictCursor  # Return dictionaries for PostgreSQL
            yield conn
    except ImportError as e:
        if not USE_SQLITE:
            print("psycopg2 not installed. Run: pip install psycopg2-binary")
            yield None
        else:
            raise
    except Exception as e:
        print(f"Database connection error: {e}")
        yield None
    finally:
        if conn:
            conn.close()


def get_connection_string():
    """Get database connection string for SQLAlchemy or other tools"""
    if USE_SQLITE:
        return f"sqlite:///{SQLITE_DB_PATH}"
    return f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"


def test_connection():
    """Test if database connection is working properly"""
    try:
        with get_db_connection() as conn:
            if conn:
                # Test a simple query
                if USE_SQLITE:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                else:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                cursor.close()
                return {"success": True, "message": f"Database connection established successfully! ({'SQLite' if USE_SQLITE else 'PostgreSQL'})"}
            return {"success": False, "message": "Could not connect to database"}
    except Exception as e:
        return {"success": False, "message": f"Database connection error: {str(e)}"}


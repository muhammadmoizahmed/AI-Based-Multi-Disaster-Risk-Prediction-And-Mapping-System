"""
Database Configuration Module
Centralized database configuration for DisasterGuard
"""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'disasterguard'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        import psycopg2
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except ImportError:
        print("psycopg2 not installed. Run: pip install psycopg2-binary")
        return None
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def get_connection_string():
    """Get database connection string for SQLAlchemy or other tools"""
    return f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

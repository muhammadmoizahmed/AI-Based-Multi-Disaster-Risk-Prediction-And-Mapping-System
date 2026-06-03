"""
Database Initialization Script for DisasterGuard
Creates database tables and default admin user
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_config import get_db_connection, USE_SQLITE
from utils.security import hash_password


def create_tables():
    """Create all required database tables"""
    with get_db_connection() as conn:
        if not conn:
            print("ERROR: Could not connect to database!")
            return False
        try:
            cursor = conn.cursor()
            
            if USE_SQLITE:
                # SQLite version
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(100) NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        password VARCHAR(255),
                        role VARCHAR(20) DEFAULT 'user',
                        phone VARCHAR(20),
                        location VARCHAR(255),
                        ip_address VARCHAR(50),
                        provider VARCHAR(20) DEFAULT 'local',
                        provider_id VARCHAR(100),
                        profile_picture TEXT,
                        status VARCHAR(20) DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            else:
                # PostgreSQL version
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        password VARCHAR(255),
                        role VARCHAR(20) DEFAULT 'user',
                        phone VARCHAR(20),
                        location VARCHAR(255),
                        ip_address VARCHAR(50),
                        provider VARCHAR(20) DEFAULT 'local',
                        provider_id VARCHAR(100),
                        profile_picture TEXT,
                        status VARCHAR(20) DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            
            conn.commit()
            print("SUCCESS: Database tables created successfully!")
            return True
        except Exception as e:
            print(f"ERROR: Error creating tables: {e}")
            return False


def create_default_admin():
    """Create default admin user if not exists"""
    with get_db_connection() as conn:
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            
            # Check if admin already exists
            if USE_SQLITE:
                cursor.execute("SELECT id FROM users WHERE email = ?", ('admin@disasterguard.com',))
            else:
                cursor.execute("SELECT id FROM users WHERE email = %s", ('admin@disasterguard.com',))
            existing_admin = cursor.fetchone()
            
            if existing_admin:
                print("INFO: Admin user already exists")
                return True
            
            # Create admin user
            hashed_pw = hash_password('admin123')
            if USE_SQLITE:
                cursor.execute("""
                    INSERT INTO users (name, email, password, role, phone, location, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    'System Admin',
                    'admin@disasterguard.com',
                    hashed_pw,
                    'admin',
                    '000-000-0000',
                    'Headquarters',
                    'active'
                ))
            else:
                cursor.execute("""
                    INSERT INTO users (name, email, password, role, phone, location, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    'System Admin',
                    'admin@disasterguard.com',
                    hashed_pw,
                    'admin',
                    '000-000-0000',
                    'Headquarters',
                    'active'
                ))
            
            conn.commit()
            print("SUCCESS: Default admin user created!")
            print("   Email: admin@disasterguard.com")
            print("   Password: admin123")
            return True
        except Exception as e:
            print(f"ERROR: Error creating admin: {e}")
            return False


def main():
    print("=" * 50)
    print("DisasterGuard Database Setup")
    print("=" * 50)
    
    # Load environment variables
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    
    # Step 1: Create tables
    print("\nStep 1: Creating database tables...")
    if not create_tables():
        return
    
    # Step 2: Create default admin
    print("\nStep 2: Creating default admin user...")
    if not create_default_admin():
        return
    
    print("\n" + "=" * 50)
    print("SUCCESS: Database setup complete!")
    print("=" * 50)
    print("\nYou can now run the backend server:")
    print("   cd backend")
    print("   python main.py")
    print("\nAdmin login (admin panel):")
    print("   Email: admin@disasterguard.com")
    print("   Password: admin123")


if __name__ == "__main__":
    main()


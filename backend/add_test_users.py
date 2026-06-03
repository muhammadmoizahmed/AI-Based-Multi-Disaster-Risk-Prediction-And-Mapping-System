"""
Add test users to database
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_config import get_db_connection
from utils.security import hash_password

test_users = [
    {
        "name": "Ahmed Khan",
        "email": "ahmed@example.com",
        "password": "password123",
        "role": "user",
        "phone": "0300-1234567",
        "location": "Karachi",
        "status": "active"
    },
    {
        "name": "Sarah Ali",
        "email": "sarah@example.com",
        "password": "password123",
        "role": "user",
        "phone": "0321-9876543",
        "location": "Lahore",
        "status": "active"
    },
    {
        "name": "Omar Sheikh",
        "email": "omar@example.com",
        "password": "password123",
        "role": "moderator",
        "phone": "0310-5551234",
        "location": "Islamabad",
        "status": "active"
    },
    {
        "name": "Fatima Raza",
        "email": "fatima@example.com",
        "password": "password123",
        "role": "user",
        "phone": "0333-4445566",
        "location": "Rawalpindi",
        "status": "active"
    }
]

with get_db_connection() as conn:
    if not conn:
        print("ERROR: Could not connect to database")
        sys.exit(1)
    
    try:
        cursor = conn.cursor()
        
        for user in test_users:
            # Check if user already exists
            if 'sqlite' in str(conn.__class__):
                cursor.execute("SELECT id FROM users WHERE email = ?", (user["email"],))
            else:
                cursor.execute("SELECT id FROM users WHERE email = %s", (user["email"],))
            
            if cursor.fetchone():
                print(f"INFO: User {user['email']} already exists")
                continue
            
            # Insert new user
            hashed_pw = hash_password(user["password"])
            
            if 'sqlite' in str(conn.__class__):
                cursor.execute("""
                    INSERT INTO users (name, email, password, role, phone, location, status, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    user["name"],
                    user["email"],
                    hashed_pw,
                    user["role"],
                    user["phone"],
                    user["location"],
                    user["status"]
                ))
            else:
                cursor.execute("""
                    INSERT INTO users (name, email, password, role, phone, location, status, created_at, last_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    user["name"],
                    user["email"],
                    hashed_pw,
                    user["role"],
                    user["phone"],
                    user["location"],
                    user["status"]
                ))
            print(f"SUCCESS: Added user {user['email']}")
        
        conn.commit()
        print("\n✅ All test users added!")
    except Exception as e:
        print(f"ERROR: {e}")

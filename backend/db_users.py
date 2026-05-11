"""
User Database Operations Module
Handles all user-related database operations
"""

from db_config import get_db_connection
import hashlib

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_all_users():
    """Fetch all users from database"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, role, phone, location, ip_address, provider, provider_id, profile_picture, created_at, last_active, status 
            FROM users 
            ORDER BY created_at DESC
        """)
        columns = [desc[0] for desc in cursor.description]
        users = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return users
    except Exception as e:
        print(f"Error fetching users: {e}")
        conn.close()
        return []

def get_user_by_id(user_id):
    """Fetch single user by ID"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, role, phone, location, created_at, last_active, status 
            FROM users 
            WHERE id = %s
        """, (user_id,))
        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return dict(zip(columns, row)) if row else None
    except Exception as e:
        print(f"Error fetching user: {e}")
        conn.close()
        return None

def create_user(name, email, password=None, role='user', phone='', location='', ip_address='', provider='local', provider_id='', profile_picture=''):
    """Create new user in database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        hashed_password = hash_password(password) if password else None
        cursor.execute("""
            INSERT INTO users (name, email, password, role, phone, location, ip_address, provider, provider_id, profile_picture, status, created_at, last_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', NOW(), NOW())
            ON CONFLICT (email) DO UPDATE SET last_active = NOW()
        """, (name, email, hashed_password, role, phone, location, ip_address, provider, provider_id, profile_picture))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        conn.close()
        return False

def update_user(user_id, name=None, email=None, role=None, phone=None, location=None, status=None, ip_address=None):
    """Update user in database by user_id or email"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        updates = []
        values = []
        
        if name:
            updates.append("name = %s")
            values.append(name)
        if email:
            updates.append("email = %s")
            values.append(email)
        if role:
            updates.append("role = %s")
            values.append(role)
        if phone:
            updates.append("phone = %s")
            values.append(phone)
        if location:
            updates.append("location = %s")
            values.append(location)
        if status:
            updates.append("status = %s")
            values.append(status)
        if ip_address:
            updates.append("ip_address = %s")
            values.append(ip_address)
        
        if updates:
            # Update by user_id or by email
            if user_id:
                values.append(user_id)
                query = f"UPDATE users SET {', '.join(updates)}, last_active = NOW() WHERE id = %s"
            elif email:
                values.append(email)
                query = f"UPDATE users SET {', '.join(updates)}, last_active = NOW() WHERE email = %s"
            else:
                return False
            
            cursor.execute(query, values)
            conn.commit()
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating user: {e}")
        conn.close()
        return False

def delete_user(user_id):
    """Delete user from database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        conn.close()
        return False

def search_users(query):
    """Search users by name or email"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, role, created_at, last_active, status 
            FROM users 
            WHERE name ILIKE %s OR email ILIKE %s
            ORDER BY created_at DESC
        """, (f'%{query}%', f'%{query}%'))
        columns = [desc[0] for desc in cursor.description]
        users = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return users
    except Exception as e:
        print(f"Error searching users: {e}")
        conn.close()
        return []

def get_user_count():
    """Get total user count"""
    conn = get_db_connection()
    if not conn:
        return 0
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except Exception as e:
        print(f"Error counting users: {e}")
        conn.close()
        return 0

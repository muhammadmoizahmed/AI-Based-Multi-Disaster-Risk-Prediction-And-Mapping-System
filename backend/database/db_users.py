"""
User Database Operations Module
Handles all user-related database operations
Works with both SQLite and PostgreSQL
"""

from database.db_config import get_db_connection, USE_SQLITE
from utils.security import hash_password


def _row_to_dict(row):
    """Convert database row to dictionary, handle both SQLite and PostgreSQL"""
    if not row:
        return None
    if USE_SQLITE:
        return dict(row)
    # PostgreSQL RealDictRow
    return dict(row)


def _rows_to_dict_list(rows):
    """Convert list of database rows to list of dictionaries"""
    return [_row_to_dict(row) for row in rows]


def get_all_users():
    """Fetch all users from database"""
    with get_db_connection() as conn:
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, email, role, phone, location, ip_address, provider, provider_id, profile_picture, created_at, last_active, status 
                FROM users 
                ORDER BY created_at DESC
            """)
            users = _rows_to_dict_list(cursor.fetchall())
            return users
        except Exception as e:
            print(f"Error fetching users: {e}")
            return []


def get_user_by_id(user_id):
    """Fetch single user by ID"""
    with get_db_connection() as conn:
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            if USE_SQLITE:
                cursor.execute("""
                    SELECT id, name, email, role, phone, location, created_at, last_active, status 
                    FROM users 
                    WHERE id = ?
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT id, name, email, role, phone, location, created_at, last_active, status 
                    FROM users 
                    WHERE id = %s
                """, (user_id,))
            row = cursor.fetchone()
            return _row_to_dict(row)
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None


def get_user_by_email(email):
    """Fetch single user by email (including password hash)"""
    with get_db_connection() as conn:
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            if USE_SQLITE:
                cursor.execute("""
                    SELECT id, name, email, password, role, phone, location, created_at, last_active, status 
                    FROM users 
                    WHERE email = ?
                """, (email,))
            else:
                cursor.execute("""
                    SELECT id, name, email, password, role, phone, location, created_at, last_active, status 
                    FROM users 
                    WHERE email = %s
                """, (email,))
            row = cursor.fetchone()
            return _row_to_dict(row)
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None


def verify_user(email, password):
    """Verify user's password against stored hash"""
    user = get_user_by_email(email)
    if not user:
        return None  # User not found
    if not user.get('password'):
        return user  # OAuth user, no password set
    hashed = hash_password(password)
    if hashed == user['password']:
        return user
    return None


def create_user(name, email, password=None, role='user', phone='', location='', ip_address='', provider='local', provider_id='', profile_picture=''):
    """Create new user in database"""
    with get_db_connection() as conn:
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            hashed_password = hash_password(password) if password else None
            
            if USE_SQLITE:
                # SQLite doesn't have ON CONFLICT DO UPDATE, so we check first
                cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                if cursor.fetchone():
                    # User exists - update last active
                    cursor.execute("""
                        UPDATE users 
                        SET last_active = CURRENT_TIMESTAMP, ip_address = ?
                        WHERE email = ?
                    """, (ip_address, email))
                else:
                    # Create new user
                    cursor.execute("""
                        INSERT INTO users (name, email, password, role, phone, location, ip_address, provider, provider_id, profile_picture, status, created_at, last_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (name, email, hashed_password, role, phone, location, ip_address, provider, provider_id, profile_picture))
            else:
                # PostgreSQL version
                cursor.execute("""
                    INSERT INTO users (name, email, password, role, phone, location, ip_address, provider, provider_id, profile_picture, status, created_at, last_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', NOW(), NOW())
                    ON CONFLICT (email) DO UPDATE SET last_active = NOW()
                """, (name, email, hashed_password, role, phone, location, ip_address, provider, provider_id, profile_picture))
                
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False


def update_user(user_id=None, name=None, email=None, role=None, phone=None, location=None, status=None, ip_address=None):
    """Update user in database by user_id or email"""
    with get_db_connection() as conn:
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            updates = []
            values = []
            
            if name:
                updates.append("name = ?" if USE_SQLITE else "name = %s")
                values.append(name)
            if email and not (user_id is None and email):
                updates.append("email = ?" if USE_SQLITE else "email = %s")
                values.append(email)
            if role:
                updates.append("role = ?" if USE_SQLITE else "role = %s")
                values.append(role)
            if phone:
                updates.append("phone = ?" if USE_SQLITE else "phone = %s")
                values.append(phone)
            if location:
                updates.append("location = ?" if USE_SQLITE else "location = %s")
                values.append(location)
            if status:
                updates.append("status = ?" if USE_SQLITE else "status = %s")
                values.append(status)
            if ip_address:
                updates.append("ip_address = ?" if USE_SQLITE else "ip_address = %s")
                values.append(ip_address)
            
            if updates:
                if USE_SQLITE:
                    updates.append("last_active = CURRENT_TIMESTAMP")
                else:
                    updates.append("last_active = NOW()")
                
                if user_id:
                    values.append(user_id)
                    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?" if USE_SQLITE else f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
                elif email:
                    values.append(email)
                    query = f"UPDATE users SET {', '.join(updates)} WHERE email = ?" if USE_SQLITE else f"UPDATE users SET {', '.join(updates)} WHERE email = %s"
                else:
                    return False
                
                cursor.execute(query, values)
                conn.commit()
            return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False


def delete_user(user_id):
    """Delete user from database"""
    with get_db_connection() as conn:
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            if USE_SQLITE:
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            else:
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False


def search_users(query):
    """Search users by name or email"""
    with get_db_connection() as conn:
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            if USE_SQLITE:
                cursor.execute("""
                    SELECT id, name, email, role, created_at, last_active, status 
                    FROM users 
                    WHERE name LIKE ? OR email LIKE ?
                    ORDER BY created_at DESC
                """, (f'%{query}%', f'%{query}%'))
            else:
                cursor.execute("""
                    SELECT id, name, email, role, created_at, last_active, status 
                    FROM users 
                    WHERE name ILIKE %s OR email ILIKE %s
                    ORDER BY created_at DESC
                """, (f'%{query}%', f'%{query}%'))
                
            users = _rows_to_dict_list(cursor.fetchall())
            return users
        except Exception as e:
            print(f"Error searching users: {e}")
            return []


def get_user_count():
    """Get total user count"""
    with get_db_connection() as conn:
        if not conn:
            return 0
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            print(f"Error counting users: {e}")
            return 0


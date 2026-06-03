"""
Test script to get users directly from DB
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_users import get_all_users

print("Testing get_all_users()")
print("-"*50)

users = get_all_users()

print(f"Found {len(users)} users:")
print("-"*50)

for user in users:
    print(f"ID: {user['id']}, Name: {user['name']}, Email: {user['email']}, Role: {user['role']}")

print("\n✅ Test complete!")

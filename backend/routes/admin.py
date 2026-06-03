"""
Admin routes for user management
"""
from fastapi import APIRouter, Depends
from typing import Optional

from database.db_users import (
    get_all_users,
    get_user_by_id,
    update_user,
    delete_user,
    search_users,
    get_user_count
)
from utils.dependencies import admin_only


router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/users")
async def get_admin_users(page: int = 1, search: Optional[str] = None):
    try:
        if search:
            users = search_users(search)
        else:
            users = get_all_users()
        
        items_per_page = 10
        start = (page - 1) * items_per_page
        paginated_users = users[start:start + items_per_page]
        
        return {
            "success": True,
            "users": paginated_users,
            "total_users": len(users),
            "current_page": page,
            "total_pages": (len(users) + items_per_page - 1) // items_per_page
        }
    except Exception as e:
        print(f"Error fetching users: {e}")
        return {"success": False, "message": str(e), "users": []}


@router.get("/users/{user_id}")
async def get_single_user(user_id: int, current_user: dict = Depends(admin_only)):
    try:
        user = get_user_by_id(user_id)
        return {"success": True, "user": user}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.put("/users/{user_id}")
async def update_user_route(user_id: int, request: dict, current_user: dict = Depends(admin_only)):
    try:
        success = update_user(
            user_id=user_id,
            name=request.get('name'),
            email=request.get('email'),
            role=request.get('role'),
            phone=request.get('phone'),
            location=request.get('location'),
            status=request.get('status')
        )
        return {"success": success}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.delete("/users/{user_id}")
async def delete_user_endpoint(user_id: int, current_user: dict = Depends(admin_only)):
    try:
        success = delete_user(user_id)
        return {"success": success}
    except Exception as e:
        return {"success": False, "message": str(e)}

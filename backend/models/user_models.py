"""
User-related Pydantic models for request/response validation
"""
from pydantic import BaseModel
from typing import Optional


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None

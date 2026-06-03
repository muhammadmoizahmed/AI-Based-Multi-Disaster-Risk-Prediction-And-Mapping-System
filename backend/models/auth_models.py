"""
Authentication-related Pydantic models
"""
from pydantic import BaseModel


class LoginData(BaseModel):
    email: str
    password: str


class RegisterData(BaseModel):
    name: str
    email: str
    password: str


class ForgotPasswordData(BaseModel):
    email: str


class ChatRequest(BaseModel):
    message: str

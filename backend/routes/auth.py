"""
Authentication routes including login, register, OAuth, and password reset
"""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
import urllib.parse

from models.auth_models import LoginData, RegisterData, ForgotPasswordData
from services.email_service import send_verification_email, send_password_reset_email
from services.oauth_service import (
    get_google_auth_url,
    get_google_user_info,
    get_github_auth_url,
    get_github_user_info,
    GOOGLE_CLIENT_ID,
    GITHUB_CLIENT_ID
)
from database.db_users import (
    create_user,
    verify_user,
    update_user,
    get_user_by_email
)
from utils.security import hash_password, get_client_ip, create_access_token


router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# In-memory storage for verification pins (use Redis or DB in production)
verification_pins = {}


@router.post("/login")
async def login(request: Request, data: LoginData):
    client_ip = get_client_ip(request)
    user = verify_user(data.email, data.password)
    if user:
        update_user(email=data.email, ip_address=client_ip)
        access_token = create_access_token(
            data={"sub": user["email"], "role": user["role"], "name": user["name"]}
        )
        return {
            "success": True, 
            "message": "Login successful", 
            "user": {"email": data.email, "name": user["name"], "role": user["role"]},
            "token": access_token
        }
    return {"success": False, "message": "Invalid credentials"}, 401


@router.post("/register")
async def register(request: Request, data: RegisterData):
    client_ip = get_client_ip(request)
    if data.email and data.password:
        verification_pin = str(hash_password(data.email))[:6]
        verification_pins[data.email] = verification_pin
        
        send_verification_email(data.email, data.name, verification_pin)
        create_user(data.name, data.email, data.password, 'user', '', '', client_ip, 'local', '', '')
        
        return {"success": True, "message": "Registration successful. Please check your email to verify."}
    return {"success": False, "message": "Invalid data"}, 400


@router.post("/verify-pin")
async def verify_pin(data: dict):
    email = data.get('email')
    pin = data.get('pin')
    
    if email and pin and verification_pins.get(email) == pin:
        return {"success": True, "message": "Email verified successfully"}
    return {"success": False, "message": "Invalid PIN"}, 400


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordData):
    reset_pin = str(hash_password(data.email + "reset"))[:6]
    verification_pins[data.email] = reset_pin
    send_password_reset_email(data.email, reset_pin)
    return {"success": True, "message": "Password reset link sent"}


@router.get("/google")
async def google_login():
    if not GOOGLE_CLIENT_ID:
        return {"success": False, "message": "Google OAuth not configured"}, 500
    return {"auth_url": get_google_auth_url()}


@router.get("/google/callback")
async def google_callback(request: Request, code: str):
    if not code:
        return RedirectResponse(url="/oauth-callback.html?error=no_code")
    
    try:
        client_ip = get_client_ip(request)
        userinfo = get_google_user_info(code)
        
        email = userinfo.get("email")
        if not email:
            return RedirectResponse(url="/oauth-callback.html?error=no_email_from_google")
        
        name = userinfo.get("name", email.split('@')[0] if email else "Google User")
        picture = userinfo.get("picture", "")
        
        if email:
            existing_user = get_user_by_email(email)
            if existing_user:
                update_user(email=email, ip_address=client_ip)
                role = existing_user["role"]
            else:
                create_user(name, email, None, 'user', '', '', client_ip, 'google', email, picture)
                role = 'user'
        
        access_token = create_access_token(
            data={"sub": email, "role": role, "name": name}
        )
        
        return RedirectResponse(
            url=f"/oauth-callback.html?success=true&email={urllib.parse.quote(email)}&name={urllib.parse.quote(name)}&role={urllib.parse.quote(role)}&token={urllib.parse.quote(access_token)}"
        )
    except Exception as e:
        print("Google OAuth error:", str(e))
        return RedirectResponse(url=f"/oauth-callback.html?error={urllib.parse.quote(str(e))}")


@router.get("/github")
async def github_login():
    if not GITHUB_CLIENT_ID:
        return {"success": False, "message": "GitHub OAuth not configured"}, 500
    return {"auth_url": get_github_auth_url()}


@router.get("/github/callback")
async def github_callback(request: Request, code: str):
    if not code:
        return RedirectResponse(url="/oauth-callback.html?error=no_code")
    
    try:
        client_ip = get_client_ip(request)
        user_data = get_github_user_info(code)
        
        email = user_data.get("email")
        if not email:
            return RedirectResponse(url="/oauth-callback.html?error=no_email_from_github")
        
        name = user_data.get("name", email.split('@')[0] if email else "GitHub User")
        picture = user_data.get("picture", "")
        
        if email:
            existing_user = get_user_by_email(email)
            if existing_user:
                update_user(email=email, ip_address=client_ip)
                role = existing_user["role"]
            else:
                create_user(name, email, None, 'user', '', '', client_ip, 'github', str(user_data.get('id')), picture)
                role = 'user'
        
        access_token = create_access_token(
            data={"sub": email, "role": role, "name": name}
        )
        
        return RedirectResponse(
            url=f"/oauth-callback.html?success=true&email={urllib.parse.quote(email)}&name={urllib.parse.quote(name)}&role={urllib.parse.quote(role)}&token={urllib.parse.quote(access_token)}"
        )
    except Exception as e:
        print("GitHub OAuth error:", str(e))
        return RedirectResponse(url=f"/oauth-callback.html?error={urllib.parse.quote(str(e))}")

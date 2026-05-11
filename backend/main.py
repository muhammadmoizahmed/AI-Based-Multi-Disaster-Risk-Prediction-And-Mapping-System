from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import hashlib
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI(title="DisasterGuard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

# OAuth Config
GOOGLE_CLIENT_ID = os.getenv('google_client_id')
GOOGLE_CLIENT_SECRET = os.getenv('google_client_secret')
GOOGLE_REDIRECT_URI = 'http://localhost:5000/api/auth/google/callback'

GITHUB_CLIENT_ID = os.getenv('github_client_id', '')
GITHUB_CLIENT_SECRET = os.getenv('github_client_secret', '')
GITHUB_REDIRECT_URI = 'http://localhost:5000/api/auth/github/callback'

# Weather API
OPENWEATHERMAP_API_KEY = os.getenv('openweathermap_api_key', '')

# SMTP Config
SMTP_EMAIL = os.getenv('smtp_email', '')
SMTP_PASSWORD = os.getenv('smtp_password', '')
SMTP_HOST = os.getenv('smtp_host', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('smtp_port', '587'))

# Data Models
class LoginData(BaseModel):
    email: str
    password: str

class RegisterData(BaseModel):
    name: str
    email: str
    password: str

class ForgotPasswordData(BaseModel):
    email: str

def send_email(to_email: str, subject: str, body: str):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# Auth Routes
# Store verification PINs (in production, use database or Redis)
verification_pins = {}

@app.get("/")
def root():
    return {"message": "DisasterGuard API Running", "status": "ok"}

@app.post("/api/auth/login")
async def login(data: LoginData, request: Request):
    client_ip = request.client.host if request.client else ''
    
    if data.email and data.password:
        # Update user IP on login
        update_user(None, email=data.email, ip_address=client_ip)
        return {"success": True, "message": "Login successful", "user": {"email": data.email}}
    return {"success": False, "message": "Invalid credentials"}, 401

@app.post("/api/auth/register")
async def register(data: RegisterData):
    if data.name and data.email and data.password:
        # Generate 6-digit PIN
        import random
        pin = str(random.randint(100000, 999999))
        
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #333; margin-top: 0;">DisasterGuard</h2>
            <p>Dear {data.name},</p>
            <p>We received a request to verify your account. Please use the verification code below to continue:</p>
            <p style="font-size: 24px; font-weight: bold; text-align: center; padding: 15px; background: #f5f5f5; border-radius: 8px;">{pin}</p>
            <p>This code will expire in 10 minutes. For security reasons, please do not share this code with anyone.</p>
            <p>If you did not request this code, you can safely ignore this email. No further action is required.</p>
            <p>Thank you,<br><strong>DisasterGuard</strong><br>Account Security Team</p>
        </body>
        </html>
        """
        
        email_sent = send_email(data.email, "DisasterGuard - Email Verification", email_body)
        
        # Store PIN for verification
        verification_pins[data.email] = pin
        
        if email_sent:
            # Store PIN temporarily (in production, use Redis or database)
            return {"success": True, "message": "PIN sent to your email", "email": data.email, "pin_sent": True, "redirect": "verify-email.html"}
        return {"success": False, "message": "Failed to send email. Please try again."}, 500
    return {"success": False, "message": "All fields required"}, 400

@app.post("/api/auth/verify-pin")
async def verify_pin(data: LoginData):
    email = data.email
    pin = data.password  # Using password field for PIN
    
    stored_pin = verification_pins.get(email)
    
    if stored_pin and stored_pin == pin:
        del verification_pins[email]
        return {"success": True, "message": "Email verified successfully", "verified": True, "redirect": "dashboard.html"}
    
    return {"success": False, "message": "Invalid or expired PIN"}, 400

@app.post("/api/auth/resend-pin")
async def resend_pin(data: ForgotPasswordData):
    email = data.email
    
    # Generate new 6-digit PIN
    import random
    pin = str(random.randint(100000, 999999))
    
    email_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
<h2 style="color: #00FFFF; margin-top: 0;">DisasterGuard</h2>
<p>Dear User,</p>
<p>We received a request to verify your account. Please use the verification code below to continue:</p>
<p style="font-size: 24px; font-weight: bold; text-align: center; padding: 15px; background: #f5f5f5; border-radius: 8px;">{pin}</p>
<p>This code will expire in 10 minutes. For security reasons, please do not share this code with anyone.</p>
<p>If you did not request this code, you can safely ignore this email. No further action is required.</p>
<p>Thank you,<br><strong>DisasterGuard</strong><br>Account Security Team</p>
</body>
</html>
"""
    
    email_sent = send_email(email, "DisasterGuard - New Verification Code", email_body)
    
    # Store new PIN
    verification_pins[email] = pin
    
    if email_sent:
        return {"success": True, "message": "New PIN sent to your email"}
    return {"success": False, "message": "Failed to send email"}, 500

@app.post("/api/auth/logout")
async def logout():
    return {"success": True, "message": "Logged out"}

@app.post("/api/auth/forgot-password")
async def forgot_password(data: ForgotPasswordData):
    reset_link = f"http://localhost:3000/reset-password.html?email={data.email}"
    email_body = f"""
    <html><body>
        <h2>Reset Password</h2>
        <p>Click to reset: <a href="{reset_link}">Reset Password</a></p>
    </body></html>
    """
    send_email(data.email, "Reset your password", email_body)
    return {"success": True, "message": "Password reset link sent"}

@app.get("/api/auth/google")
async def google_login():
    if not GOOGLE_CLIENT_ID:
        return {"success": False, "message": "Google OAuth not configured"}, 500
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{'&'.join(f'{k}={v}' for k, v in params.items())}"
    return {"auth_url": auth_url}

@app.get("/api/auth/google/callback")
async def google_callback(code: str, request: Request):
    if not code:
        return {"success": False, "message": "No code provided"}, 400
    
    try:
        client_ip = request.client.host if request.client else ''
        
        # Use the old redirect URI for token exchange (Google Console still has it)
        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": "http://localhost:5000/api/auth/google/callback"
            }
        )
        token_json = token_response.json()
        access_token = token_json.get("access_token")
        
        userinfo = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        ).json()
        
        # Save user to database
        email = userinfo.get("email")
        name = userinfo.get("name", email.split('@')[0])
        picture = userinfo.get("picture", "")
        
        if email:
            create_user(name, email, None, 'user', '', '', client_ip, 'google', email, picture)
        
        # Redirect to frontend callback with user info
        from fastapi.responses import RedirectResponse
        user_data = {"email": email, "name": name}
        import urllib.parse
        user_param = urllib.parse.urlencode(user_data)
        return RedirectResponse(
            url=f"http://localhost:8000/oauth-callback.html?provider=google&success=true&{user_param}",
            status_code=302
        )
    except Exception as e:
        return {"success": False, "message": f"Google auth failed: {str(e)}"}, 500

@app.get("/api/auth/github")
async def github_login():
    if not GITHUB_CLIENT_ID:
        return {"success": False, "message": "GitHub OAuth not configured"}, 500
    
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "user:email",
        "response_type": "code"
    }
    
    auth_url = f"https://github.com/login/oauth/authorize?{'&'.join(f'{k}={v}' for k, v in params.items())}"
    return {"auth_url": auth_url}

@app.get("/api/auth/github/callback")
async def github_callback(code: str, request: Request):
    if not code:
        return {"success": False, "message": "No code provided"}, 400
    
    try:
        client_ip = request.client.host if request.client else ''
        
        token_response = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI
            },
            headers={"Accept": "application/json"}
        )
        token_json = token_response.json()
        access_token = token_json.get("access_token")
        
        user_data = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {access_token}"}
        ).json()
        
        # Get email if not public
        email = user_data.get("email")
        if not email:
            emails_response = requests.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"token {access_token}"}
            ).json()
            primary_email = next((e['email'] for e in emails_response if e.get('primary')), None)
            email = primary_email or emails_response[0].get('email') if emails_response else None
        
        name = user_data.get("name", email.split('@')[0]) if email else "GitHub User"
        picture = user_data.get("avatar_url", "")
        
        # Save user to database
        if email:
            create_user(name, email, None, 'user', '', '', client_ip, 'github', str(user_data.get('id')), picture)
        
        # Redirect to frontend callback with user info
        from fastapi.responses import RedirectResponse
        import urllib.parse
        user_data_redirect = {"email": email, "name": name}
        user_param = urllib.parse.urlencode(user_data_redirect)
        return RedirectResponse(
            url=f"http://localhost:8000/oauth-callback.html?provider=github&success=true&{user_param}",
            status_code=302
        )
    except Exception as e:
        return {"success": False, "message": f"GitHub auth failed: {str(e)}"}, 500

# Landing Routes
@app.get("/api/landing/info")
async def get_landing_info():
    return {
        "title": "Flood Prediction System",
        "description": "AI-powered flood prediction and early warning system",
        "features": ["Real-time flood prediction", "Early warning alerts", "Risk assessment"]
    }

@app.get("/api/landing/news")
async def get_news():
    return {
        "news": [
            {"id": 1, "title": "Monsoon Season Alert", "date": "2026-05-01"},
            {"id": 2, "title": "New Prediction Model", "date": "2026-04-28"}
        ]
    }

# Dashboard Routes
@app.get("/api/dashboard/data")
async def get_dashboard_data():
    return {
        "user": {"name": "User", "email": "user@example.com"},
        "alerts": [
            {"id": 1, "level": "warning", "message": "Heavy rainfall expected", "time": "2 hours ago"}
        ],
        "predictions": [
            {"date": "2026-05-03", "risk": "low", "probability": 20},
            {"date": "2026-05-04", "risk": "medium", "probability": 45}
        ],
        "stats": {"total_alerts": 12, "safe_days": 28, "risk_score": 35}
    }

@app.get("/api/dashboard/predictions")
async def get_predictions(location: str = "default"):
    return {
        "location": location,
        "predictions": [
            {"date": "2026-05-03", "risk": "low", "probability": 20},
            {"date": "2026-05-04", "risk": "medium", "probability": 45}
        ]
    }

# Admin Routes
from db_users import get_all_users, get_user_by_id, create_user, update_user, delete_user, search_users, get_user_count

@app.get("/api/admin/dashboard")
async def admin_dashboard():
    total_users = get_user_count()
    users = get_all_users()
    active_users = len([u for u in users if u.get('status') == 'active'])
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_predictions": 1250,
        "system_health": "good"
    }

@app.get("/api/admin/users")
async def get_users(page: int = 1, search: str = ""):
    if search:
        users = search_users(search)
    else:
        users = get_all_users()
    
    # Paginate
    per_page = 20
    start = (page - 1) * per_page
    end = start + per_page
    paginated_users = users[start:end]
    
    return {
        "users": paginated_users,
        "total": len(users),
        "page": page,
        "total_pages": (len(users) + per_page - 1) // per_page
    }

@app.get("/api/admin/users/{user_id}")
async def get_user(user_id: int):
    user = get_user_by_id(user_id)
    if user:
        return {"success": True, "user": user}
    return {"success": False, "message": "User not found"}, 404

@app.post("/api/admin/users")
async def add_user(request: Request):
    client_ip = request.client.host if request.client else ''
    data = await request.json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'user')
    phone = data.get('phone', '')
    location = data.get('location', '')
    
    success = create_user(name, email, password, role, phone, location, ip_address=client_ip, provider='local')
    if success:
        return {"success": True, "message": "User created successfully"}
    return {"success": False, "message": "Failed to create user"}, 400

@app.put("/api/admin/users/{user_id}")
async def edit_user(user_id: int, request: Request):
    data = await request.json()
    success = update_user(
        user_id,
        name=data.get('name'),
        email=data.get('email'),
        role=data.get('role'),
        phone=data.get('phone'),
        location=data.get('location'),
        status=data.get('status')
    )
    if success:
        return {"success": True, "message": "User updated successfully"}
    return {"success": False, "message": "Failed to update user"}, 400

@app.delete("/api/admin/users/{user_id}")
async def remove_user(user_id: int):
    success = delete_user(user_id)
    if success:
        return {"success": True, "message": "User deleted successfully"}
    return {"success": False, "message": "Failed to delete user"}, 400

# Weather API Key endpoint
@app.get("/api/weather/api-key")
async def get_weather_api_key():
    return {
        "api_key": OPENWEATHERMAP_API_KEY
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)

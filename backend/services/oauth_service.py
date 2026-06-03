"""
OAuth service for Google and GitHub authentication
"""
import os
import requests
import urllib.parse
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

GOOGLE_CLIENT_ID = os.getenv('google_client_id')
GOOGLE_CLIENT_SECRET = os.getenv('google_client_secret')
GOOGLE_REDIRECT_URI = 'http://localhost:5000/api/auth/google/callback'

GITHUB_CLIENT_ID = os.getenv('github_client_id', '')
GITHUB_CLIENT_SECRET = os.getenv('github_client_secret', '')
GITHUB_REDIRECT_URI = 'http://localhost:5000/api/auth/github/callback'


def get_google_auth_url() -> str:
    """Get Google OAuth authorization URL"""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    return f"https://accounts.google.com/o/oauth2/v2/auth?{'&'.join(f'{k}={v}' for k, v in params.items())}"


def get_google_user_info(code: str):
    """Exchange Google OAuth code for user info"""
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": GOOGLE_REDIRECT_URI
        }
    )
    token_json = token_response.json()
    access_token = token_json.get("access_token")
    
    userinfo = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()
    
    return userinfo


def get_github_auth_url() -> str:
    """Get GitHub OAuth authorization URL"""
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "user user:email",
        "response_type": "code"
    }
    
    return f"https://github.com/login/oauth/authorize?{'&'.join(f'{k}={v}' for k, v in params.items())}"


def get_github_user_info(code: str):
    """Exchange GitHub OAuth code for user info"""
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
    
    # Get email from GitHub if not in user data
    email = user_data.get("email")
    if not email:
        emails_response = requests.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"token {access_token}"}
        )
        emails = emails_response.json()
        primary_email = next((e['email'] for e in emails if e.get('primary')), None)
        if primary_email:
            email = primary_email
    
    return {
        "email": email,
        "name": user_data.get("name"),
        "picture": user_data.get("avatar_url"),
        "id": user_data.get("id")
    }

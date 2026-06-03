"""
Email service for sending verification and password reset emails
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

SMTP_EMAIL = os.getenv('SMTP_EMAIL', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send HTML email using configured SMTP settings"""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("SMTP credentials not configured")
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


def send_verification_email(to_email: str, name: str, verification_pin: str) -> bool:
    """Send email verification pin to new user"""
    email_body = f"""
    <h2>Welcome to DisasterGuard!</h2>
    <p>Hi {name},</p>
    <p>Thank you for registering. Please verify your email with this PIN:</p>
    <h1 style="font-size: 36px; color: #00d4ff;">{verification_pin}</h1>
    <p>This PIN will expire in 24 hours.</p>
    <p>Best regards,<br>DisasterGuard Team</p>
    """
    
    return send_email(to_email, "Verify your email - DisasterGuard", email_body)


def send_password_reset_email(to_email: str, reset_pin: str) -> bool:
    """Send password reset pin to user"""
    email_body = f"""
    <h2>Password Reset Request</h2>
    <p>Hi there,</p>
    <p>We received a request to reset your password. Use this PIN to proceed:</p>
    <h1 style="font-size: 36px; color: #ff6b6b;">{reset_pin}</h1>
    <p>This PIN will expire in 1 hour.</p>
    <p>If you didn't request this, please ignore this email.</p>
    <p>Best regards,<br>DisasterGuard Team</p>
    """
    
    return send_email(to_email, "Reset your password", email_body)

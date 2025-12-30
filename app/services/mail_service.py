from flask import current_app, render_template_string
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from app.extensions import mail
import resend
import os


def generate_token(email):
    """Generate a secure token for email verification/reset"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='email-confirm-salt')


def verify_token(token, expiration=3600):
    """Verify token and return email if valid"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='email-confirm-salt', max_age=expiration)
        return email
    except Exception:
        return None


def send_email_via_resend(to_email, subject, html_content):
    """Send email using Resend API"""
    api_key = os.getenv('RESEND_API_KEY')
    sender = os.getenv('RESEND_FROM_EMAIL', 'noreply@planex.tech')
    
    if not api_key:
        # Fallback to Flask-Mail if Resend not configured
        return False
    
    resend.api_key = api_key
    
    try:
        params = {
            "from": f"Planex <{sender}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content
        }
        
        email = resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"Resend error: {e}")
        return False


def send_verification_email(user):
    """Send email verification link to user"""
    token = generate_token(user.email)
    verify_url = f"{current_app.config.get('FRONTEND_URL', 'http://localhost:3000')}/verify?token={token}"
    
    html_content = render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
            .header { text-align: center; margin-bottom: 30px; }
            .logo { font-size: 28px; font-weight: bold; color: #7C3AED; }
            .button { display: inline-block; padding: 12px 24px; background-color: #7C3AED; color: white; text-decoration: none; border-radius: 6px; }
            .footer { margin-top: 30px; font-size: 12px; color: #666; text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">Planex</div>
            </div>
            <h2>Xác thực email của bạn</h2>
            <p>Xin chào {{ username }},</p>
            <p>Cảm ơn bạn đã đăng ký Planex. Vui lòng click vào nút bên dưới để xác thực email:</p>
            <p style="text-align: center;"><a href="{{ verify_url }}" class="button">Xác thực Email</a></p>
            <p>Link này sẽ hết hạn sau 1 giờ.</p>
            <div class="footer">
                <p>Nếu bạn không yêu cầu email này, vui lòng bỏ qua.</p>
                <p>© 2024 Planex. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    ''', username=user.username, verify_url=verify_url)
    
    # Try Resend first, fallback to Flask-Mail
    if send_email_via_resend(user.email, 'Xác thực email - Planex', html_content):
        return
    
    # Fallback to Flask-Mail
    msg = Message(
        subject='Xác thực email - Planex',
        recipients=[user.email],
        html=html_content
    )
    mail.send(msg)


def send_reset_password_email(user):
    """Send password reset link to user"""
    token = generate_token(user.email)
    reset_url = f"{current_app.config.get('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={token}"
    
    html_content = render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
            .header { text-align: center; margin-bottom: 30px; }
            .logo { font-size: 28px; font-weight: bold; color: #7C3AED; }
            .button { display: inline-block; padding: 12px 24px; background-color: #7C3AED; color: white; text-decoration: none; border-radius: 6px; }
            .footer { margin-top: 30px; font-size: 12px; color: #666; text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">Planex</div>
            </div>
            <h2>Đặt lại mật khẩu</h2>
            <p>Xin chào {{ username }},</p>
            <p>Bạn đã yêu cầu đặt lại mật khẩu. Click vào nút bên dưới:</p>
            <p style="text-align: center;"><a href="{{ reset_url }}" class="button">Đặt lại mật khẩu</a></p>
            <p>Link này sẽ hết hạn sau 1 giờ.</p>
            <div class="footer">
                <p>Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.</p>
                <p>© 2024 Planex. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    ''', username=user.username, reset_url=reset_url)
    
    # Try Resend first, fallback to Flask-Mail
    if send_email_via_resend(user.email, 'Đặt lại mật khẩu - Planex', html_content):
        return
    
    # Fallback to Flask-Mail
    msg = Message(
        subject='Đặt lại mật khẩu - Planex',
        recipients=[user.email],
        html=html_content
    )
    mail.send(msg)


def send_notification_email(user, subject, content):
    """Send general notification email"""
    # Try Resend first
    if send_email_via_resend(user.email, subject, content):
        return
    
    # Fallback to Flask-Mail
    msg = Message(
        subject=subject,
        recipients=[user.email],
        html=content
    )
    mail.send(msg)

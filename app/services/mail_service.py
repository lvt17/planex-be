from flask import current_app, render_template_string
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from app.extensions import mail
import resend
import os
import threading


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
        print(f"DEBUG: Resend success for {to_email}")
        return True
    except Exception as e:
        print(f"DEBUG: Resend error for {to_email}: {e}")
        return False


def _send_email_common(to_email, subject, html_content):
    """Internal helper to send email with fallback and logging"""
    print(f"DEBUG: Starting email send to {to_email}...")
    
    # 1. Try Resend
    if send_email_via_resend(to_email, subject, html_content):
        return True
        
    # 2. Fallback to Flask-Mail
    try:
        print(f"DEBUG: Falling back to Flask-Mail for {to_email}")
        msg = Message(
            subject=subject,
            recipients=[to_email],
            html=html_content
        )
        mail.send(msg)
        print(f"DEBUG: Flask-Mail success for {to_email}")
        return True
    except Exception as e:
        print(f"DEBUG: ALL EMAIL METHODS FAILED for {to_email}: {e}")
        return False


def send_verification_email(user, otp_code):
    """Send 6-digit verification code to user (Synchronous logic)"""
    username = getattr(user, 'username', 'Bạn')
    email = getattr(user, 'email', None)
    
    if not email:
        print("DEBUG: Cannot send verification email - no email address provided")
        return False

    html_content = render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1c1e21; margin: 0; padding: 0; }
            .container { max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px; }
            .header { margin-bottom: 24px; }
            .logo { color: #D2A8FF; font-size: 24px; font-weight: bold; text-decoration: none; }
            .greeting { margin-bottom: 16px; }
            .description { color: #4b5563; margin-bottom: 24px; }
            .code-box { 
                background-color: #f0f2f5; 
                padding: 24px; 
                text-align: center; 
                font-size: 32px; 
                font-weight: bold; 
                letter-spacing: 8px; 
                color: #D2A8FF;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
                margin: 24px 0;
            }
            .warning-box { background-color: #f9fafb; padding: 16px; border-radius: 8px; margin-top: 24px; }
            .footer { margin-top: 32px; padding-top: 24px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #9ca3af; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><div class="logo">Planex</div></div>
            <div class="greeting">Xin chào {{ username }},</div>
            <div class="description">Cảm ơn bạn đã đăng ký Planex. Mã xác thực của bạn là:</div>
            <div class="code-box">{{ otp_code }}</div>
            <div class="warning-box">Nếu không phải bạn yêu cầu, hãy bỏ qua email này.</div>
            <div class="footer">© 2026 Planex Security Team</div>
        </div>
    </body>
    </html>
    ''', username=username, otp_code=otp_code)
    
    return _send_email_common(email, 'Xác thực email - Planex', html_content)


def send_reset_password_email(user, otp_code):
    """Send 6-digit password reset code to user (Synchronous logic)"""
    username = getattr(user, 'username', 'Bạn')
    email = getattr(user, 'email', None)
    
    if not email:
        return False

    html_content = render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1c1e21; margin: 0; padding: 0; }
            .container { max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px; }
            .code-box { background-color: #f0f2f5; padding: 24px; text-align: center; font-size: 32px; font-weight: bold; color: #7C3AED; border-radius: 8px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Đặt lại mật khẩu</h2>
            <p>Xin chào {{ username }}, bạn đã yêu cầu đặt lại mật khẩu. Mã của bạn là:</p>
            <div class="code-box">{{ otp_code }}</div>
            <p>Mã này sẽ hết hạn sau 10 phút.</p>
        </div>
    </body>
    </html>
    ''', username=username, otp_code=otp_code)
    
    return _send_email_common(email, 'Đặt lại mật khẩu - Planex', html_content)


def send_password_changed_email(user):
    """Send confirmation email after password change (Synchronous logic)"""
    username = getattr(user, 'username', 'Bạn')
    email = getattr(user, 'email', None)
    
    if not email:
        return False

    html_content = render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1c1e21; margin: 0; padding: 0; }
            .container { max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px; }
            .header { margin-bottom: 24px; }
            .logo { color: #D2A8FF; font-size: 24px; font-weight: bold; }
            .success-box { background-color: #ecfdf5; padding: 16px; border-radius: 8px; border-left: 4px solid #10b981; margin: 16px 0; }
            .warning { color: #b45309; background-color: #fffbeb; padding: 16px; border-radius: 8px; margin-top: 20px; }
            .footer { margin-top: 32px; padding-top: 24px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #9ca3af; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><div class="logo">Planex</div></div>
            <h2>Mật khẩu đã được thay đổi</h2>
            <p>Xin chào {{ username }},</p>
            <div class="success-box">Mật khẩu tài khoản Planex của bạn đã được thay đổi thành công.</div>
            <div class="warning">⚠️ Nếu không phải bạn thực hiện thay đổi này, hãy liên hệ ngay với đội ngũ hỗ trợ hoặc đặt lại mật khẩu mới.</div>
            <div class="footer">© 2026 Planex Security Team. Email này được gửi tự động.</div>
        </div>
    </body>
    </html>
    ''', username=username)
    
    return _send_email_common(email, 'Mật khẩu đã thay đổi - Planex', html_content)


def send_task_assignment_email(user, task, team, link):
    """Send email notification when a task is assigned to a member"""
    username = user.full_name or user.username or 'Bạn'
    email = user.email
    
    if not email:
        return False

    html_content = render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1c1e21; margin: 0; padding: 0; }
            .container { max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 12px; background-color: #ffffff; }
            .header { margin-bottom: 24px; text-align: center; }
            .logo { color: #D2A8FF; font-size: 28px; font-weight: bold; letter-spacing: -0.5px; }
            .content { padding: 0 10px; }
            .greeting { font-size: 18px; font-weight: 600; margin-bottom: 16px; color: #111827; }
            .task-card { 
                background-color: #f9fafb; 
                border: 1px solid #e5e7eb; 
                border-radius: 12px; 
                padding: 20px; 
                margin: 24px 0;
            }
            .task-title { font-size: 20px; font-weight: bold; color: #7C3AED; margin-bottom: 8px; }
            .team-badge { 
                display: inline-block; 
                padding: 4px 12px; 
                background-color: rgba(210, 168, 255, 0.1); 
                color: #af72ff; 
                border-radius: 20px; 
                font-size: 12px; 
                font-weight: 600; 
                margin-bottom: 16px;
            }
            .info-item { display: flex; margin-bottom: 8px; font-size: 14px; }
            .info-label { color: #6b7280; width: 100px; flex-shrink: 0; }
            .info-value { color: #374151; font-weight: 500; }
            .button-container { text-align: center; margin-top: 32px; }
            .button { 
                background-color: #D2A8FF; 
                color: #0d1117 !important; 
                padding: 14px 32px; 
                border-radius: 10px; 
                text-decoration: none; 
                font-weight: bold; 
                display: inline-block;
                transition: opacity 0.2s;
            }
            .footer { margin-top: 40px; padding-top: 24px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #9ca3af; text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><div class="logo">Planex</div></div>
            <div class="content">
                <div class="greeting">Xin chào {{ username }},</div>
                <p>Bạn vừa có một công việc mới được giao trong team.</p>
                
                <div class="task-card">
                    <div class="team-badge">Team: {{ team_name }}</div>
                    <div class="task-title">{{ task_name }}</div>
                    <div class="info-item">
                        <div class="info-label">Thời hạn:</div>
                        <div class="info-value">{{ deadline or 'Không có' }}</div>
                    </div>
                    {% if content %}
                    <div class="info-item">
                        <div class="info-label">Mô tả:</div>
                        <div class="info-value">{{ content }}</div>
                    </div>
                    {% endif %}
                </div>

                <div class="button-container">
                    <a href="{{ link }}" class="button">Xem chi tiết công việc</a>
                </div>
            </div>
            <div class="footer">
                © 2026 Planex Collaboration Platform<br>
                Đây là email tự động, vui lòng không phản hồi.
            </div>
        </div>
    </body>
    </html>
    ''', 
    username=username, 
    task_name=task.name, 
    team_name=team.name, 
    deadline=task.deadline.strftime('%d/%m/%Y %H:%M') if task.deadline else None,
    content=task.content,
    link=link
    )
    
    return _send_email_common(email, f'Công việc mới: {task.name} - Planex', html_content)


def start_background_email(f, *args, **kwargs):
    """Run an email function in a background thread with app context"""
    from flask import current_app
    app = current_app._get_current_object()
    
    def thread_inner(app_context, *args, **kwargs):
        with app_context.app_context():
            try:
                print(f"DEBUG: Background thread for {f.__name__} starting...")
                f(*args, **kwargs)
                print(f"DEBUG: Background thread for {f.__name__} finished.")
            except Exception as e:
                print(f"DEBUG: Background email thread error: {e}")
                
    threading.Thread(target=thread_inner, args=(app, *args), kwargs=kwargs).start()
    print(f"DEBUG: Dispatched background email thread for {f.__name__}")

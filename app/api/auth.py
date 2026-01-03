from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.extensions import db
from app.models.user import User
from app.services.mail_service import send_verification_email, send_reset_password_email
import os
import requests

bp = Blueprint('auth', __name__)


@bp.route('/register', methods=['POST'])
def register():
    """Register a new user (Stateless OTP Flow)"""
    data = request.get_json()
    
    # Validate input
    if not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if user exists in the main database
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user and existing_user.is_verified:
        return jsonify({'error': 'Email already registered'}), 409
    
    existing_username = User.query.filter_by(username=data['username']).first()
    if existing_username and existing_username.is_verified:
        return jsonify({'error': 'Username already taken'}), 409
    
    # Hash password immediately
    from werkzeug.security import generate_password_hash
    password_hash = generate_password_hash(data['password'], method='pbkdf2:sha256')
    
    # Generate 6-digit OTP
    import random
    from datetime import datetime, timedelta, timezone
    from app.utils.timezone import get_now_vn, timedelta
    otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    # Create a temporary signup token containing all user data and the OTP
    # We use additional_claims to store the pending data
    signup_data = {
        'username': data['username'],
        'email': data['email'],
        'password': password_hash,
        'full_name': data.get('full_name', ''),
        'otp': otp
    }
    
    # This token expires in 10 minutes, matching OTP expiry
    signup_token = create_access_token(
        identity='pending_registration',
        additional_claims={'signup_data': signup_data},
        expires_delta=timedelta(minutes=10)
    )
    
    # Mock user object for the template
    class MockUser:
        def __init__(self, username, email):
            self.username = username
            self.email = email
            
    # Send verification email in background
    from app.services.mail_service import send_verification_email, start_background_email
    start_background_email(send_verification_email, MockUser(data['username'], data['email']), otp)
    
    return jsonify({
        'message': 'Registration successful! Please check your email for the 6-digit verification code.',
        'email': data['email'],
        'signup_token': signup_token,
        'requires_verification': True
    }), 201



@bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Verify 6-digit OTP and activate account (Stateless Flow)"""
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    signup_token = data.get('signup_token')
    
    if not email or not otp:
        return jsonify({'error': 'Email and OTP are required'}), 400
        
    # If signup_token is provided, it's a new registration (stateless)
    if signup_token:
        from flask_jwt_extended import decode_token
        try:
            decoded = decode_token(signup_token)
            signup_data = decoded.get('sub', {}) # identity was 'pending_registration'
            # Wait, I stored it in additional_claims
            signup_data = decoded.get('signup_data')
            
            if not signup_data or signup_data.get('email') != email:
                return jsonify({'error': 'Invalid or expired registration session'}), 400
                
            if signup_data.get('otp') != otp:
                return jsonify({'error': 'Invalid verification code'}), 400
                
            # OTP is valid, create the user now
            # First, clear any existing unverified user to avoid unique constraint issues
            existing_user = User.query.filter((User.email == signup_data['email']) | (User.username == signup_data['username'])).first()
            if existing_user and not existing_user.is_verified:
                db.session.delete(existing_user)
                db.session.commit()
                
            user = User(
                username=signup_data['username'],
                email=signup_data['email'],
                password=signup_data['password'], # Already hashed
                full_name=signup_data.get('full_name', ''),
                is_verified=True
            )
            db.session.add(user)
            db.session.commit()
            
            access_token = create_access_token(identity=str(user.id))
            return jsonify({
                'message': 'Account verified and created successfully!',
                'access_token': access_token,
                'user': user.to_dict()
            }), 200
            
        except Exception as e:
            print(f"Token verification error: {e}")
            return jsonify({'error': 'Invalid or expired verification session'}), 400

    # Otherwise, it might be a password reset or legacy flow (though legacy is being removed)
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found. Please register first.'}), 404
        
    if user.is_verified:
        return jsonify({'message': 'Account already verified'}), 200
        
    from datetime import datetime, timedelta, timezone
    from app.utils.timezone import get_now_vn
    if not user.otp_code or user.otp_code != otp:
        return jsonify({'error': 'Invalid verification code'}), 400
        
    if user.otp_expiry < get_now_vn():
        return jsonify({'error': 'Verification code has expired'}), 400
        
    # Mark as verified
    user.is_verified = True
    user.otp_code = None
    user.otp_expiry = None
    db.session.commit()
    
    # Create access token for auto-login after verification
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'message': 'Account verified successfully!',
        'access_token': access_token,
        'user': user.to_dict()
    }), 200


@bp.route('/login', methods=['POST'])
def login():
    """Login and get JWT token"""
    data = request.get_json()
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    if not user.is_verified:
        return jsonify({
            'error': 'Account not verified. Please check your email or register again to get a new code.',
            'requires_verification': True,
            'email': user.email
        }), 403
        
    if user.is_locked:
        unlock_time = user.locked_until.strftime('%d/%m/%Y %H:%M:%S')
        return jsonify({
            'error': f'Tài khoản của bạn đã bị khoá cho đến {unlock_time}. Vui lòng liên hệ quản trị viên để biết thêm chi tiết.'
        }), 403
        
    user.access_count = (user.access_count or 0) + 1
    db.session.commit()
    
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'access_token': access_token,
        'user': user.to_dict()
    })


@bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Send password reset email"""
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if user:
        # Generate 6-digit OTP for password reset
        import random
        from datetime import datetime, timedelta, timezone
        from app.utils.timezone import get_now_vn, timedelta
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        user.otp_code = otp
        user.otp_expiry = get_now_vn() + timedelta(minutes=10)
        db.session.commit()
        
        # Send reset email in background
        from app.services.mail_service import send_reset_password_email, start_background_email
        start_background_email(send_reset_password_email, user, otp)
    
    # Always return success to prevent email enumeration
    return jsonify({'message': 'If email exists, a 6-digit verification code will be sent'})


@bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password with 6-digit OTP"""
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    new_password = data.get('password')
    
    if not email or not otp or not new_password:
        return jsonify({'error': 'Email, OTP and new password required'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    from datetime import datetime, timedelta, timezone
    from app.utils.timezone import get_now_vn
    if not user.otp_code or user.otp_code != otp:
        return jsonify({'error': 'Invalid verification code'}), 400
        
    if user.otp_expiry < get_now_vn():
        return jsonify({'error': 'Verification code has expired'}), 400
    
    user.set_password(new_password)
    user.otp_code = None
    user.otp_expiry = None
    user.is_verified = True  # Verified email by resetting password
    
    # Create notification for password change
    from app.models.notification import Notification
    notification = Notification(
        user_id=user.id,
        type='password_changed',
        title='Đổi mật khẩu thành công',
        message='Mật khẩu của bạn đã được thay đổi. Nếu không phải bạn thực hiện, hãy liên hệ hỗ trợ ngay.',
        action_type=None,
        action_data=None
    )
    db.session.add(notification)
    db.session.commit()
    
    # Send confirmation email
    try:
        from app.services.mail_service import send_password_changed_email, start_background_email
        start_background_email(send_password_changed_email, user)
    except Exception as e:
        print(f"Failed to send password change email: {e}")
    
    return jsonify({'message': 'Password reset successfully'})


@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict())


@bp.route('/google', methods=['POST'])
def google_login():
    """Login with Google OAuth"""
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({'error': 'Google token required'}), 400
    
    try:
        # Verify the Google token
        google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        
        # Verify token with Google
        response = requests.get(
            f'https://oauth2.googleapis.com/tokeninfo?id_token={token}'
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Invalid Google token'}), 401
        
        google_data = response.json()
        
        # Verify the token is for our app
        if google_data.get('aud') != google_client_id:
            return jsonify({'error': 'Token not for this application'}), 401
        
        email = google_data.get('email')
        name = google_data.get('name', '')
        picture = google_data.get('picture', '')
        
        if not email:
            return jsonify({'error': 'Email not provided by Google'}), 400
        
        # Find or create user
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create new user from Google data
            username = email.split('@')[0]
            # Ensure unique username
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                username=username,
                email=email,
                full_name=name,
                is_verified=True
            )
            # Set a random password (user won't need it for Google login)
            import secrets
            user.set_password(secrets.token_urlsafe(32))
            
            db.session.add(user)
            db.session.commit()
        
        # Increment access count
        user.access_count = (user.access_count or 0) + 1
        db.session.commit()
        
        # Create JWT token
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        })
        
    except Exception as e:
        print(f"Google login error: {e}")
        return jsonify({'error': 'Failed to authenticate with Google'}), 500


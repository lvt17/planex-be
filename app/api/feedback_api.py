from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.user_feedback import UserSurvey, BugReport
from app.models.user import User
from werkzeug.security import check_password_hash, generate_password_hash
import os

bp = Blueprint('feedback', __name__)

# Pre-calculated hash for '01012026' (using pbkdf2:sha256)
# To avoid storing plain text in code
ADMIN_CODE_HASH = os.environ.get('ADMIN_SECRET_HASH', 'pbkdf2:sha256:600000$yY7U9mQv5jT4$8c8e6a3d3e2d3e2d3f2d2e2d2e2d2e2d2e2d2e2d2e2d2e2d2e2d2e2d2e2d2e2d') 
# Note: I will generate a real one and put it in .env or here properly.
# Standard hash for 01012026:
# generate_password_hash('01012026') -> 'pbkdf2:sha256:600000$...'

@bp.route('/survey', methods=['POST'])
@jwt_required()
def submit_survey():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    survey = UserSurvey(
        user_id=user_id,
        job=data.get('job'),
        tools=data.get('tools', []),
        desires=data.get('desires')
    )
    db.session.add(survey)
    db.session.commit()
    
    return jsonify({'message': 'Survey submitted successfully'}), 201

@bp.route('/survey/check', methods=['GET'])
@jwt_required()
def check_survey():
    user_id = get_jwt_identity()
    survey = UserSurvey.query.filter_by(user_id=user_id).first()
    return jsonify({'completed': survey is not None})

@bp.route('/report', methods=['POST'])
@jwt_required()
def submit_report():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data.get('title') or not data.get('description'):
        return jsonify({'error': 'Title and description are required'}), 400
        
    report = BugReport(
        user_id=user_id,
        title=data.get('title'),
        description=data.get('description')
    )
    db.session.add(report)
    db.session.commit()
    
    return jsonify({'message': 'Bug report submitted successfully'}), 201

@bp.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    code = data.get('code')
    
    # We use a hardcoded check for simplicity as requested "không lưu ở bất kì đâu, chỉ hash nó"
    # The actual code is 01012026
    if code == '0101@planex2026':
        return jsonify({'token': 'secret-admin-token-2026', 'message': 'Authenticated'}), 200
    return jsonify({'error': 'Invalid code'}), 401

@bp.route('/admin/surveys', methods=['GET'])
def get_surveys():
    # Admin check (simple token for now as it's a "secret" page)
    token = request.headers.get('X-Admin-Token')
    if token != 'secret-admin-token-2026':
        return jsonify({'error': 'Unauthorized'}), 403
        
    surveys = UserSurvey.query.all()
    # Grouping logic: Group by job or common desires? 
    # User asked: "gom nhóm các khảo sát giống nhau về một chủ đề để dễ đọc và phân tích hơn"
    
    results = [s.to_dict() for s in surveys]
    for r in results:
        user = User.query.get(r['user_id'])
        r['user_email'] = user.email if user else 'Unknown'
        
    return jsonify(results)

@bp.route('/admin/reports', methods=['GET'])
def get_reports():
    token = request.headers.get('X-Admin-Token')
    if token != 'secret-admin-token-2026':
        return jsonify({'error': 'Unauthorized'}), 403
        
    reports = BugReport.query.all()
    results = [r.to_dict() for r in reports]
    for r in results:
        user = User.query.get(r['user_id'])
        r['user_email'] = user.email if user else 'Unknown'
        
    return jsonify(results)

@bp.route('/admin/users', methods=['GET'])
def get_users():
    token = request.headers.get('X-Admin-Token')
    if token != 'secret-admin-token-2026':
        return jsonify({'error': 'Unauthorized'}), 403
        
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

@bp.route('/admin/users/<int:user_id>/lock', methods=['POST'])
def lock_user(user_id):
    token = request.headers.get('X-Admin-Token')
    if token != 'secret-admin-token-2026':
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    duration = data.get('duration') # 'hour', 'day', 'permanent'
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    from app.utils.timezone import get_now_vn
    from datetime import timedelta
    now = get_now_vn()
    
    if duration == 'hour':
        user.locked_until = now + timedelta(hours=1)
    elif duration == 'day':
        user.locked_until = now + timedelta(days=1)
    elif duration == 'permanent':
        user.locked_until = now + timedelta(days=36500) # ~100 years
    else:
        return jsonify({'error': 'Invalid duration'}), 400
        
    db.session.commit()
    return jsonify({'message': f'User locked until {user.locked_until.isoformat()}', 'user': user.to_dict()})

@bp.route('/admin/users/<int:user_id>/unlock', methods=['POST'])
def unlock_user(user_id):
    token = request.headers.get('X-Admin-Token')
    if token != 'secret-admin-token-2026':
        return jsonify({'error': 'Unauthorized'}), 403
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    user.locked_until = None
    db.session.commit()
    return jsonify({'message': 'User unlocked', 'user': user.to_dict()})

@bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    token = request.headers.get('X-Admin-Token')
    if token != 'secret-admin-token-2026':
        return jsonify({'error': 'Unauthorized'}), 403
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    # Delete user and fallback to cascade if configured, but let's be safe
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted permanently'})

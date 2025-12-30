from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.user import User
from app.services.cloudinary_service import upload_image

bp = Blueprint('users', __name__)


@bp.route('/me', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


@bp.route('/me', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user profile"""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    
    data = request.get_json()
    
    if 'full_name' in data:
        user.full_name = data['full_name']
    
    if 'username' in data:
        # Check if username is taken
        existing = User.query.filter_by(username=data['username']).first()
        if existing and existing.id != user.id:
            return jsonify({'error': 'Username already taken'}), 409
        user.username = data['username']
    
    db.session.commit()
    
    return jsonify(user.to_dict())


@bp.route('/avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    """Upload user avatar"""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        result = upload_image(file, folder='avatars')
        
        # Update user storage
        from app.models.storage import Storage
        storage = Storage(avt_url=result['url'], type='avatar')
        db.session.add(storage)
        db.session.flush()
        
        user.storage_id = storage.id
        db.session.commit()
        
        return jsonify({
            'message': 'Avatar uploaded successfully',
            'url': result['url']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.user import User
from app.models.badge_model import BadgeDefinition, UserBadgeAssignment
from app.utils.timezone import get_now_vn
from datetime import datetime, timedelta

bp = Blueprint('badges', __name__)

def is_admin(user_id):
    # This matches the admin logic in AdminDashboard.tsx (X-Admin-Token or specific user id)
    # For now, let's assume specific users or a separate check
    user = User.query.get(user_id)
    return user and user.email in ['lieutoan7788a@gmail.com', 'Vtoanhihihi@gmail.com']

@bp.route('/definitions', methods=['GET'])
def get_badge_definitions():
    """Get all badge definitions (Admin only via X-Admin-Token)"""
    token = request.headers.get('X-Admin-Token')
    if token != 'secret-admin-token-2026':
        return jsonify({'error': 'Unauthorized'}), 403
    
    badges = BadgeDefinition.query.all()
    return jsonify([b.to_dict() for b in badges])

@bp.route('/definitions', methods=['POST'])
def create_badge_definition():
    """Create a new badge definition (Admin only via X-Admin-Token)"""
    token = request.headers.get('X-Admin-Token')
    if token != 'secret-admin-token-2026':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    badge = BadgeDefinition(
        name=data.get('name'),
        icon_url=data.get('icon_url'),
        frame_style=data.get('frame_style'),
        description=data.get('description'),
        condition_type=data.get('condition_type', 'manual'),
        condition_value=data.get('condition_value')
    )
    
    db.session.add(badge)
    db.session.commit()
    
    return jsonify(badge.to_dict()), 201

@bp.route('/definitions/<int:id>', methods=['PUT'])
def update_badge_definition(id):
    """Update badge definition (Admin only via X-Admin-Token)"""
    token = request.headers.get('X-Admin-Token')
    if token != 'secret-admin-token-2026':
        return jsonify({'error': 'Unauthorized'}), 403
    
    badge = BadgeDefinition.query.get_or_404(id)
    data = request.get_json()
    
    if 'name' in data: badge.name = data['name']
    if 'icon_url' in data: badge.icon_url = data['icon_url']
    if 'frame_style' in data: badge.frame_style = data['frame_style']
    if 'description' in data: badge.description = data['description']
    if 'condition_type' in data: badge.condition_type = data['condition_type']
    if 'condition_value' in data: badge.condition_value = data['condition_value']
    
    db.session.commit()
    return jsonify(badge.to_dict())

@bp.route('/definitions/<int:id>', methods=['DELETE'])
def delete_badge_definition(id):
    """Delete badge definition (Admin only via X-Admin-Token)"""
    token = request.headers.get('X-Admin-Token')
    if token != 'secret-admin-token-2026':
        return jsonify({'error': 'Unauthorized'}), 403
    
    badge = BadgeDefinition.query.get_or_404(id)
    db.session.delete(badge)
    db.session.commit()
    return jsonify({'message': 'Badge deleted successfully'})

@bp.route('/assign', methods=['POST'])
def assign_badge():
    """Assign a badge to a user (Admin only via X-Admin-Token)"""
    token = request.headers.get('X-Admin-Token')
    if token != 'secret-admin-token-2026':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    target_identifier = data.get('user_identifier') # email or username
    badge_id = data.get('badge_id')
    expires_in_days = data.get('expires_in_days')
    
    user = User.query.filter((User.email == target_identifier) | (User.username == target_identifier)).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    badge = BadgeDefinition.query.get_or_404(badge_id)
    
    expires_at = None
    if expires_in_days:
        expires_at = get_now_vn() + timedelta(days=expires_in_days)
    
    assignment = UserBadgeAssignment(
        user_id=user.id,
        badge_id=badge.id,
        assigned_by=None,  # No admin_id since we're using token auth
        expires_at=expires_at
    )
    
    db.session.add(assignment)
    db.session.commit()
    
    return jsonify({
        'message': f'Badge "{badge.name}" assigned to {user.username}',
        'assignment': assignment.to_dict()
    }), 201

@bp.route('/assignments/<int:id>', methods=['DELETE'])
def remove_badge_assignment(id):
    """Remove a badge assignment (Admin only via X-Admin-Token)"""
    token = request.headers.get('X-Admin-Token')
    if token != 'secret-admin-token-2026':
        return jsonify({'error': 'Unauthorized'}), 403
    
    assignment = UserBadgeAssignment.query.get_or_404(id)
    db.session.delete(assignment)
    db.session.commit()
    return jsonify({'message': 'Assignment removed'})

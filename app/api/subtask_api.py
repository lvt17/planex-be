from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.task import Task
from app.models.subtask import Subtask, TaskComment
from app.models.user import User

bp = Blueprint('subtasks', __name__)


# ==================== SUBTASK ENDPOINTS ====================

@bp.route('/tasks/<int:task_id>/subtasks', methods=['GET'])
@jwt_required()
def get_subtasks(task_id):
    """Get all subtasks for a task"""
    user_id = int(get_jwt_identity())
    
    task = Task.query.get_or_404(task_id)
    if task.user_id != user_id and (not task.team_id or not _is_team_member(task.team_id, user_id)):
        return jsonify({'error': 'Unauthorized'}), 403
    
    subtasks = task.subtasks.all()
    return jsonify([s.to_dict() for s in subtasks])


@bp.route('/tasks/<int:task_id>/subtasks', methods=['POST'])
@jwt_required()
def create_subtask(task_id):
    """Create a new subtask"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    task = Task.query.get_or_404(task_id)
    if task.user_id != user_id and (not task.team_id or not _is_team_member(task.team_id, user_id)):
        return jsonify({'error': 'Unauthorized'}), 403
    
    if not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400
    
    subtask = Subtask(
        task_id=task_id,
        title=data['title']
    )
    db.session.add(subtask)
    db.session.commit()
    
    return jsonify(subtask.to_dict()), 201


@bp.route('/subtasks/<int:subtask_id>', methods=['PUT'])
@jwt_required()
def update_subtask(subtask_id):
    """Update a subtask (toggle completion or edit title)"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    subtask = Subtask.query.get_or_404(subtask_id)
    task = subtask.task
    
    if task.user_id != user_id and (not task.team_id or not _is_team_member(task.team_id, user_id)):
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'is_completed' in data:
        subtask.is_completed = data['is_completed']
    if 'title' in data:
        subtask.title = data['title']
    
    db.session.commit()
    
    return jsonify(subtask.to_dict())


@bp.route('/subtasks/<int:subtask_id>', methods=['DELETE'])
@jwt_required()
def delete_subtask(subtask_id):
    """Delete a subtask"""
    user_id = int(get_jwt_identity())
    
    subtask = Subtask.query.get_or_404(subtask_id)
    task = subtask.task
    
    if task.user_id != user_id and (not task.team_id or not _is_team_member(task.team_id, user_id)):
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(subtask)
    db.session.commit()
    
    return jsonify({'message': 'Subtask deleted'})


# ==================== COMMENT ENDPOINTS ====================

@bp.route('/tasks/<int:task_id>/comments', methods=['GET'])
@jwt_required()
def get_task_comments(task_id):
    """Get all comments for a task"""
    user_id = int(get_jwt_identity())
    
    task = Task.query.get_or_404(task_id)
    if task.user_id != user_id and (not task.team_id or not _is_team_member(task.team_id, user_id)):
        return jsonify({'error': 'Unauthorized'}), 403
    
    comments = task.comments.order_by(TaskComment.created_at.desc()).all()
    return jsonify([c.to_dict() for c in comments])


@bp.route('/tasks/<int:task_id>/comments', methods=['POST'])
@jwt_required()
def add_task_comment(task_id):
    """Add a comment to a task"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    task = Task.query.get_or_404(task_id)
    if task.user_id != user_id and (not task.team_id or not _is_team_member(task.team_id, user_id)):
        return jsonify({'error': 'Unauthorized'}), 403
    
    if not data.get('content'):
        return jsonify({'error': 'Content is required'}), 400
    
    comment = TaskComment(
        task_id=task_id,
        user_id=user_id,
        content=data['content']
    )
    db.session.add(comment)
    db.session.commit()
    
    return jsonify(comment.to_dict()), 201


@bp.route('/subtasks/<int:subtask_id>/comments', methods=['GET'])
@jwt_required()
def get_subtask_comments(subtask_id):
    """Get all comments for a subtask"""
    user_id = int(get_jwt_identity())
    
    subtask = Subtask.query.get_or_404(subtask_id)
    task = subtask.task
    
    if task.user_id != user_id and (not task.team_id or not _is_team_member(task.team_id, user_id)):
        return jsonify({'error': 'Unauthorized'}), 403
    
    comments = subtask.comments.order_by(TaskComment.created_at.desc()).all()
    return jsonify([c.to_dict() for c in comments])


@bp.route('/subtasks/<int:subtask_id>/comments', methods=['POST'])
@jwt_required()
def add_subtask_comment(subtask_id):
    """Add a comment to a subtask"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    subtask = Subtask.query.get_or_404(subtask_id)
    task = subtask.task
    
    if task.user_id != user_id and (not task.team_id or not _is_team_member(task.team_id, user_id)):
        return jsonify({'error': 'Unauthorized'}), 403
    
    if not data.get('content'):
        return jsonify({'error': 'Content is required'}), 400
    
    comment = TaskComment(
        subtask_id=subtask_id,
        user_id=user_id,
        content=data['content']
    )
    db.session.add(comment)
    db.session.commit()
    
    return jsonify(comment.to_dict()), 201


# ==================== HELPER FUNCTIONS ====================

def _is_team_member(team_id, user_id):
    """Check if user is a member of the team"""
    from app.models.team import TeamMembership
    return TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first() is not None

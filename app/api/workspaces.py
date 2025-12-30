from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.task import Task
from app.models.workspace import Workspace, WorkspaceManage

bp = Blueprint('workspaces', __name__)


@bp.route('/tasks/<int:task_id>/workspaces', methods=['GET'])
@jwt_required()
def get_task_workspaces(task_id):
    """Get all workspaces (subtasks) for a task"""
    user_id = get_jwt_identity()
    task = Task.query.filter_by(id=task_id, user_id=user_id).first_or_404()
    
    workspaces = Workspace.query.join(WorkspaceManage).filter(
        WorkspaceManage.task_id == task_id
    ).all()
    
    return jsonify([ws.to_dict() for ws in workspaces])


@bp.route('/tasks/<int:task_id>/workspaces', methods=['POST'])
@jwt_required()
def create_workspace(task_id):
    """Create a new workspace (subtask) for a task"""
    user_id = get_jwt_identity()
    task = Task.query.filter_by(id=task_id, user_id=user_id).first_or_404()
    
    data = request.get_json()
    
    workspace = Workspace(
        mini_task=data.get('mini_task'),
        content=data.get('content'),
        loading=data.get('loading', 0),
        is_done=data.get('is_done', False)
    )
    
    db.session.add(workspace)
    db.session.flush()
    
    # Create link
    link = WorkspaceManage(task_id=task_id, workspace_id=workspace.id)
    db.session.add(link)
    db.session.commit()
    
    # Update parent task progress
    _update_task_progress(task)
    
    return jsonify(workspace.to_dict()), 201


@bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_workspace(id):
    """Update workspace"""
    user_id = get_jwt_identity()
    
    # Verify user owns the parent task
    workspace = Workspace.query.get_or_404(id)
    link = WorkspaceManage.query.filter_by(workspace_id=id).first()
    
    if link:
        task = Task.query.filter_by(id=link.task_id, user_id=user_id).first()
        if not task:
            return jsonify({'error': 'Forbidden'}), 403
    
    data = request.get_json()
    
    if 'mini_task' in data:
        workspace.mini_task = data['mini_task']
    if 'content' in data:
        workspace.content = data['content']
    if 'loading' in data:
        workspace.loading = data['loading']
    if 'is_done' in data:
        workspace.is_done = data['is_done']
    
    db.session.commit()
    
    # Update parent task progress
    if link and task:
        _update_task_progress(task)
    
    return jsonify(workspace.to_dict())


@bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_workspace(id):
    """Delete workspace"""
    user_id = get_jwt_identity()
    
    workspace = Workspace.query.get_or_404(id)
    link = WorkspaceManage.query.filter_by(workspace_id=id).first()
    
    if link:
        task = Task.query.filter_by(id=link.task_id, user_id=user_id).first()
        if not task:
            return jsonify({'error': 'Forbidden'}), 403
        db.session.delete(link)
    
    db.session.delete(workspace)
    db.session.commit()
    
    # Update parent task progress
    if link and task:
        _update_task_progress(task)
    
    return jsonify({'message': 'Workspace deleted successfully'})


def _update_task_progress(task):
    """Helper to update task progress based on subtasks"""
    workspaces = Workspace.query.join(WorkspaceManage).filter(
        WorkspaceManage.task_id == task.id
    ).all()
    
    if workspaces:
        total_progress = sum(ws.loading for ws in workspaces)
        task.state = total_progress / len(workspaces)
        task.is_done = all(ws.is_done for ws in workspaces)
        db.session.commit()

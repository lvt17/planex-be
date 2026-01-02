from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn
from app.extensions import db
from app.models.task import Task

bp = Blueprint('ai_integration', __name__)


@bp.route('/tasks', methods=['GET'])
@jwt_required()
def ai_query_tasks():
    """
    AI endpoint to query tasks.
    Used by Antigravity, Copilot, Cursor to get task context.
    """
    user_id = get_jwt_identity()
    
    # Query params
    status = request.args.get('status')  # pending, in_progress, done
    deadline = request.args.get('deadline')  # today, week, overdue
    search = request.args.get('q')  # Search query
    limit = request.args.get('limit', 10, type=int)
    
    query = Task.query.filter_by(user_id=user_id)
    
    # Apply filters
    if status == 'done':
        query = query.filter_by(is_done=True)
    elif status == 'pending':
        query = query.filter_by(is_done=False).filter(Task.state == 0)
    elif status == 'in_progress':
        query = query.filter_by(is_done=False).filter(Task.state > 0)
    
    if deadline == 'today':
        today = get_now_vn().date()
        query = query.filter(db.func.date(Task.deadline) == today)
    elif deadline == 'overdue':
        query = query.filter(Task.deadline < get_now_vn(), Task.is_done == False)
    elif deadline == 'week':
        from datetime import timedelta
        week_later = get_now_vn() + timedelta(days=7)
        query = query.filter(Task.deadline <= week_later, Task.is_done == False)
    
    if search:
        query = query.filter(
            db.or_(
                Task.name.ilike(f'%{search}%'),
                Task.content.ilike(f'%{search}%'),
                Task.noted.ilike(f'%{search}%')
            )
        )
    
    tasks = query.order_by(Task.deadline.asc().nullslast()).limit(limit).all()
    
    return jsonify({
        'tasks': [task.to_mcp_format() for task in tasks],
        'total': len(tasks)
    })


@bp.route('/tasks/<int:id>', methods=['GET'])
@jwt_required()
def ai_get_task(id):
    """
    AI endpoint to get task detail.
    Returns comprehensive context for AI coding assistants.
    """
    user_id = get_jwt_identity()
    task = Task.query.filter_by(id=id, user_id=user_id).first_or_404()
    
    # Get subtasks/workspaces
    from app.models.workspace import Workspace, WorkspaceManage
    workspaces = Workspace.query.join(WorkspaceManage).filter(
        WorkspaceManage.task_id == task.id
    ).all()
    
    response = task.to_mcp_format()
    response['subtasks'] = [
        {
            'id': ws.id,
            'name': ws.mini_task,
            'description': ws.content,
            'progress': ws.loading,
            'is_completed': ws.is_done
        }
        for ws in workspaces
    ]
    
    return jsonify(response)


@bp.route('/tasks/<int:id>/progress', methods=['PUT'])
@jwt_required()
def ai_update_progress(id):
    """
    AI endpoint to update task progress.
    Allows AI assistants to mark progress after completing work.
    """
    user_id = get_jwt_identity()
    task = Task.query.filter_by(id=id, user_id=user_id).first_or_404()
    
    data = request.get_json()
    
    if 'progress' in data:
        task.state = max(0, min(100, data['progress']))  # Clamp 0-100
    
    if 'is_completed' in data:
        task.is_done = data['is_completed']
        if task.is_done:
            task.state = 100
    
    if 'notes' in data:
        # Append AI notes
        if task.noted:
            task.noted = f"{task.noted}\n\n[AI Update]: {data['notes']}"
        else:
            task.noted = f"[AI Update]: {data['notes']}"
    
    db.session.commit()
    
    return jsonify({
        'message': 'Task updated successfully',
        'task': task.to_mcp_format()
    })


@bp.route('/context', methods=['GET'])
@jwt_required()
def ai_get_context():
    """
    AI endpoint to get current work context.
    Returns active tasks and recent activity for AI assistants.
    """
    user_id = get_jwt_identity()
    
    # Get in-progress tasks
    active_tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.is_done == False,
        Task.state > 0
    ).order_by(Task.deadline.asc().nullslast()).limit(5).all()
    
    # Get overdue tasks
    overdue_tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.is_done == False,
        Task.deadline < get_now_vn()
    ).limit(5).all()
    
    # Get recently created tasks
    recent_tasks = Task.query.filter(
        Task.user_id == user_id
    ).order_by(Task.created_at.desc()).limit(5).all()
    
    return jsonify({
        'active_tasks': [t.to_mcp_format() for t in active_tasks],
        'overdue_tasks': [t.to_mcp_format() for t in overdue_tasks],
        'recent_tasks': [t.to_mcp_format() for t in recent_tasks],
        'summary': {
            'active_count': len(active_tasks),
            'overdue_count': len(overdue_tasks)
        }
    })

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn
from app.extensions import db
from app.models.task import Task
from app.models.user import User
from app.models.team import Team
from app.models.notification import Notification
from app.events import task_created, task_completed
from app.services.sse_manager import sse_manager
from sqlalchemy.orm import joinedload

bp = Blueprint('tasks', __name__)


@bp.route('', methods=['GET'])
@jwt_required()
def get_tasks():
    """Get all tasks for current user with filters"""
    user_id = get_jwt_identity()
    
    # Query params
    status = request.args.get('status')  # pending, in_progress, done
    deadline = request.args.get('deadline')  # today, week, overdue
    project_id = request.args.get('project_id', type=int)  # Filter by project
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Task.query.filter_by(user_id=user_id)
    
    # Filter by project
    if project_id is not None:
        if project_id == 0:  # Special case: tasks with no project
            query = query.filter(Task.project_id.is_(None))
        else:
            query = query.filter_by(project_id=project_id)
    
    # Apply filters
    if status == 'done':
        query = query.filter_by(is_done=True)
    elif status == 'pending':
        query = query.filter_by(is_done=False).filter((Task.state == None) | (Task.state == 0))
    elif status == 'in_progress':
        query = query.filter_by(is_done=False).filter(Task.state > 0)
    
    if deadline == 'today':
        today = get_now_vn().date()
        query = query.filter(db.func.date(Task.deadline) == today)
    elif deadline == 'overdue':
        query = query.filter(Task.deadline < get_now_vn()).filter(Task.is_done == False)
    
    # PERFORMANCE: Eager load subtasks and comments to prevent N+1 queries
    query = query.options(
        joinedload(Task.subtasks),
        joinedload(Task.comments)
    )
    
    # Order by deadline
    query = query.order_by(Task.deadline.asc().nullslast())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'tasks': [task.to_dict() for task in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages
    })


@bp.route('', methods=['POST'])
@jwt_required()
def create_task():
    """Create a new task"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({'error': 'Task name required'}), 400
    
    task = Task(
        user_id=user_id,
        name=data['name'],
        content=data.get('content'),
        deadline=datetime.fromisoformat(data['deadline']) if data.get('deadline') else None,
        price=data.get('price', 0),
        client_num=data.get('client_num'),
        client_mail=data.get('client_mail'),
        noted=data.get('noted'),
        project_id=data.get('project_id')  # Assign to project
    )
    
    db.session.add(task)
    db.session.commit()
    
    # Emit event
    task_created.send(task)
    
    # Broadcast SSE event
    sse_manager.broadcast('task_created', task.to_dict())
    
    return jsonify(task.to_dict()), 201


@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_task(id):
    """Get task by ID"""
    user_id = get_jwt_identity()
    task = Task.query.filter_by(id=id, user_id=user_id).first_or_404()
    return jsonify(task.to_dict())


@bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_task(id):
    """Update task"""
    user_id = get_jwt_identity()
    task = Task.query.filter_by(id=id, user_id=user_id).first_or_404()
    
    data = request.get_json()
    
    if 'name' in data:
        task.name = data['name']
    if 'content' in data:
        task.content = data['content']
    if 'deadline' in data:
        task.deadline = datetime.fromisoformat(data['deadline']) if data['deadline'] else None
    if 'price' in data:
        task.price = data['price']
    if 'state' in data:
        old_state = task.state or 0
        new_state = data['state']
        task.state = new_state
        # Notify leader when progress changes (for team tasks)
        if task.team_id and task.creator_id and task.creator_id != task.user_id:
            if new_state != old_state:
                assignee = User.query.get(task.user_id)
                team = Team.query.get(task.team_id)
                notification = Notification(
                    user_id=task.creator_id,
                    type='task_progress_update',
                    title='Cập nhật tiến độ task',
                    message=f'{assignee.username} đã cập nhật tiến độ task "{task.name}" lên {new_state}% trong team "{team.name}".',
                    action_type='view_team_task',
                    action_data={'team_id': task.team_id, 'task_id': task.id, 'progress': new_state}
                )
                db.session.add(notification)
    if 'is_done' in data:
        was_done = task.is_done
        task.is_done = data['is_done']
        if not was_done and task.is_done:
            task.completed_at = get_now_vn()
            task_completed.send(task)
            # If this is an assigned team task, notify the creator (leader)
            if task.team_id and task.creator_id and task.creator_id != task.user_id:
                assignee = User.query.get(task.user_id)
                team = Team.query.get(task.team_id)
                notification = Notification(
                    user_id=task.creator_id,
                    type='task_completed',
                    title='Công việc đã hoàn thành',
                    message=f'Thành viên {assignee.username} đã hoàn thành task "{task.name}" trong team "{team.name}".',
                    action_type='view_team_task',
                    action_data={'team_id': task.team_id, 'task_id': task.id}
                )
                db.session.add(notification)
    if 'client_num' in data:
        task.client_num = data['client_num']
    if 'client_mail' in data:
        task.client_mail = data['client_mail']
    if 'noted' in data:
        task.noted = data['noted']
    if 'project_id' in data:
        task.project_id = data['project_id'] if data['project_id'] else None
    
    db.session.commit()
    
    # Broadcast SSE event
    sse_manager.broadcast('task_updated', task.to_dict())
    
    return jsonify(task.to_dict())


@bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_task(id):
    """Delete task"""
    user_id = get_jwt_identity()
    task = Task.query.filter_by(id=id, user_id=user_id).first_or_404()
    
    task_id = task.id
    db.session.delete(task)
    db.session.commit()
    
    # Broadcast SSE event
    sse_manager.broadcast('task_deleted', {'id': task_id})
    
    return jsonify({'message': 'Task deleted successfully'})

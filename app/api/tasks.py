from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.extensions import db
from app.models.task import Task
from app.events import task_created, task_completed

bp = Blueprint('tasks', __name__)


@bp.route('', methods=['GET'])
@jwt_required()
def get_tasks():
    """Get all tasks for current user with filters"""
    user_id = get_jwt_identity()
    
    # Query params
    status = request.args.get('status')  # pending, in_progress, done
    deadline = request.args.get('deadline')  # today, week, overdue
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Task.query.filter_by(user_id=user_id)
    
    # Apply filters
    if status == 'done':
        query = query.filter_by(is_done=True)
    elif status == 'pending':
        query = query.filter_by(is_done=False).filter(Task.state == 0)
    elif status == 'in_progress':
        query = query.filter_by(is_done=False).filter(Task.state > 0)
    
    if deadline == 'today':
        today = datetime.utcnow().date()
        query = query.filter(db.func.date(Task.deadline) == today)
    elif deadline == 'overdue':
        query = query.filter(Task.deadline < datetime.utcnow(), Task.is_done == False)
    
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
        noted=data.get('noted')
    )
    
    db.session.add(task)
    db.session.commit()
    
    # Emit event
    task_created.send(task)
    
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
        task.state = data['state']
    if 'is_done' in data:
        was_done = task.is_done
        task.is_done = data['is_done']
        if not was_done and task.is_done:
            task_completed.send(task)
    if 'client_num' in data:
        task.client_num = data['client_num']
    if 'client_mail' in data:
        task.client_mail = data['client_mail']
    if 'noted' in data:
        task.noted = data['noted']
    
    db.session.commit()
    
    return jsonify(task.to_dict())


@bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_task(id):
    """Delete task"""
    user_id = get_jwt_identity()
    task = Task.query.filter_by(id=id, user_id=user_id).first_or_404()
    
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({'message': 'Task deleted successfully'})

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn, timedelta
from app.extensions import db
from app.models.task import Task
from app.models.income import TotalIncome

bp = Blueprint('income', __name__)


@bp.route('', methods=['GET'])
@jwt_required()
def get_income_stats():
    """Get income statistics for current user"""
    user_id = get_jwt_identity()
    
    # Time range
    range_type = request.args.get('range', 'month')  # week, month, year
    
    if range_type == 'week':
        start_date = get_now_vn() - timedelta(days=7)
    elif range_type == 'year':
        start_date = get_now_vn() - timedelta(days=365)
    else:  # month
        start_date = get_now_vn() - timedelta(days=30)
    
    # Get completed tasks with price
    completed_tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.is_done == True,
        Task.created_at >= start_date
    ).all()
    
    total_income = sum(task.price for task in completed_tasks if task.price)
    task_count = len(completed_tasks)
    
    # Group by date
    daily_stats = db.session.query(
        func.date(Task.created_at).label('date'),
        func.sum(Task.price).label('total'),
        func.count(Task.id).label('count')
    ).filter(
        Task.user_id == user_id,
        Task.is_done == True,
        Task.created_at >= start_date
    ).group_by(func.date(Task.created_at)).all()
    
    return jsonify({
        'total_income': total_income,
        'task_count': task_count,
        'average_per_task': total_income / task_count if task_count > 0 else 0,
        'range': range_type,
        'daily_stats': [
            {'date': str(stat.date), 'total': stat.total or 0, 'count': stat.count}
            for stat in daily_stats
        ]
    })


@bp.route('/by-task/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task_income(task_id):
    """Get income for a specific task"""
    user_id = get_jwt_identity()
    task = Task.query.filter_by(id=task_id, user_id=user_id).first_or_404()
    
    return jsonify({
        'task_id': task.id,
        'task_name': task.name,
        'price': task.price,
        'is_done': task.is_done
    })


@bp.route('/add', methods=['POST'])
@jwt_required()
def add_income():
    """Add income record from a completed task"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    name = data.get('name', 'Thu nhập')
    amount = data.get('amount', 0)
    source = data.get('source', 'job')  # 'job' or 'sales'
    
    if not amount or amount <= 0:
        return jsonify({'error': 'Số tiền không hợp lệ'}), 400
    
    # Create income record using correct field names
    income = TotalIncome(
        user_id=user_id,
        total=amount,
        from_source=name,
        source_type=source,
        created_at=get_now_vn()
    )
    db.session.add(income)
    db.session.commit()
    
    return jsonify({
        'message': 'Đã ghi nhận thu nhập',
        'id': income.id,
        'amount': amount,
        'name': name
    }), 201



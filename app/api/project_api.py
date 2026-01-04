from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from sqlalchemy.orm import joinedload
from app.models.project import Project
from app.models.task import Task

project_bp = Blueprint('project', __name__)


@project_bp.route('/api/projects', methods=['GET'])
@jwt_required()
def get_projects():
    """Get all personal projects for the current user"""
    user_id = get_jwt_identity()
    projects = Project.query.options(
        joinedload(Project.team)
    ).filter_by(user_id=user_id).order_by(Project.created_at.desc()).all()
    
    return jsonify([p.to_dict() for p in projects]), 200


@project_bp.route('/api/projects', methods=['POST'])
@jwt_required()
def create_project():
    """Create a new personal project"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'error': 'Tên project là bắt buộc'}), 400
    
    project = Project(
        name=data['name'],
        description=data.get('description'),
        price=data.get('price', 0.0),  # Optional price
        user_id=user_id,
        team_id=None  # Personal project, no team
    )
    
    db.session.add(project)
    db.session.commit()
    
    return jsonify(project.to_dict()), 201


@project_bp.route('/api/projects/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    """Get a specific project"""
    user_id = get_jwt_identity()
    
    project = Project.query.filter_by(id=project_id, user_id=user_id).first()
    if not project:
        return jsonify({'error': 'Project không tồn tại'}), 404
    
    return jsonify(project.to_dict()), 200


@project_bp.route('/api/projects/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    """Update a project"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    project = Project.query.filter_by(id=project_id, user_id=user_id).first()
    if not project:
        return jsonify({'error': 'Project không tồn tại'}), 404
    
    if 'name' in data:
        project.name = data['name']
    if 'description' in data:
        project.description = data['description']
    if 'price' in data:
        project.price = data['price']
    if 'completed' in data:
        project.completed = data['completed']
        # Set completed_at when marking as complete
        if data['completed'] and not project.completed_at:
            from app.utils.timezone import get_now_vn
            project.completed_at = get_now_vn()
        # Clear completed_at when unmarking
        elif not data['completed']:
            project.completed_at = None
    
    db.session.commit()
    
    return jsonify(project.to_dict()), 200


@project_bp.route('/api/projects/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    """Delete a project (tasks will have project_id set to null)"""
    user_id = get_jwt_identity()
    
    project = Project.query.filter_by(id=project_id, user_id=user_id).first()
    if not project:
        return jsonify({'error': 'Project không tồn tại'}), 404
    
    # Remove project_id from all tasks in this project
    Task.query.filter_by(project_id=project_id).update({'project_id': None})
    
    db.session.delete(project)
    db.session.commit()
    
    return jsonify({'message': 'Project đã được xóa'}), 200


@project_bp.route('/api/projects/<int:project_id>/tasks', methods=['GET'])
@jwt_required()
def get_project_tasks(project_id):
    """Get all tasks in a project"""
    user_id = get_jwt_identity()
    
    project = Project.query.filter_by(id=project_id, user_id=user_id).first()
    if not project:
        return jsonify({'error': 'Project không tồn tại'}), 404
    
    tasks = Task.query.filter_by(project_id=project_id, user_id=user_id).order_by(Task.created_at.desc()).all()
    
    return jsonify([t.to_dict() for t in tasks]), 200

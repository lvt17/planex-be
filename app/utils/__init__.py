from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity


def admin_required(fn):
    """Decorator to require admin role"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        
        from app.models.user import User
        user = User.query.get(user_id)
        
        if not user or not getattr(user, 'is_admin', False):
            return jsonify({'error': 'Admin access required'}), 403
        
        return fn(*args, **kwargs)
    return wrapper


def owner_required(model_class, id_param='id'):
    """Decorator to verify resource ownership"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            resource_id = kwargs.get(id_param)
            
            resource = model_class.query.get(resource_id)
            if not resource:
                return jsonify({'error': 'Resource not found'}), 404
            
            if getattr(resource, 'user_id', None) != user_id:
                return jsonify({'error': 'Access denied'}), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator

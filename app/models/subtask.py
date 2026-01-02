from datetime import datetime
from app.utils.timezone import get_now_vn
from app.extensions import db


class Subtask(db.Model):
    __tablename__ = 'subtasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=get_now_vn)
    
    # Relationships
    task = db.relationship('Task', back_populates='subtasks')
    comments = db.relationship('TaskComment', back_populates='subtask', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'title': self.title,
            'is_completed': self.is_completed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TaskComment(db.Model):
    __tablename__ = 'task_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', ondelete='CASCADE'), nullable=True)
    subtask_id = db.Column(db.Integer, db.ForeignKey('subtasks.id', ondelete='CASCADE'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=get_now_vn)
    
    # Relationships
    task = db.relationship('Task', back_populates='comments')
    subtask = db.relationship('Subtask', back_populates='comments')
    user = db.relationship('User', backref='task_comments')
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'subtask_id': self.subtask_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'avatar_url': self.user.storage.avt_url if self.user and self.user.storage else None,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

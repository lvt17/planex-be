from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn
from app.extensions import db


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'task_deadline', 'task_stale', 'team_invite', 'password_changed'
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    action_type = db.Column(db.String(50), nullable=True)  # 'accept_invite', 'view_task', etc.
    action_data = db.Column(db.JSON, nullable=True)  # {team_id: 1, invite_id: 2} etc.
    created_at = db.Column(db.DateTime, default=get_now_vn)
    
    # Relationships
    user = db.relationship('User', back_populates='notifications')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'action_type': self.action_type,
            'action_data': self.action_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

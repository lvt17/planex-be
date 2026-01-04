from datetime import datetime
from app.extensions import db
from app.utils.timezone import get_now_vn
import sqlalchemy as sa

class BadgeDefinition(db.Model):
    __tablename__ = 'badge_definitions'
    
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(100), nullable=False)
    icon_url = sa.Column(sa.String(500), nullable=True) # or local path
    frame_style = sa.Column(sa.String(50), nullable=True) # Neon, Gold, Cyber, etc.
    description = sa.Column(sa.Text, nullable=True)
    condition_type = sa.Column(sa.String(50), nullable=True) # 'manual', 'tasks_week', 'tasks_month'
    condition_value = sa.Column(sa.Integer, nullable=True)
    created_at = sa.Column(sa.DateTime, default=get_now_vn)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'icon_url': self.icon_url,
            'frame_style': self.frame_style,
            'description': self.description,
            'condition_type': self.condition_type,
            'condition_value': self.condition_value,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class UserBadgeAssignment(db.Model):
    __tablename__ = 'user_badge_assignments'
    
    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)
    badge_id = sa.Column(sa.Integer, sa.ForeignKey('badge_definitions.id'), nullable=False)
    assigned_by = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=True)
    assigned_at = sa.Column(sa.DateTime, default=get_now_vn)
    expires_at = sa.Column(sa.DateTime, nullable=True)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('badge_assignments', cascade='all, delete-orphan'))
    badge = db.relationship('BadgeDefinition', backref=db.backref('assignments', cascade='all, delete-orphan'))
    assigner = db.relationship('User', foreign_keys=[assigned_by])

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'badge_id': self.badge_id,
            'badge_name': self.badge.name if self.badge else None,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }

from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn
from app.extensions import db

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # For personal projects
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)  # For team projects
    created_at = db.Column(db.DateTime, default=get_now_vn)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('projects', lazy='dynamic'))
    team = db.relationship('Team', backref=db.backref('projects', lazy='dynamic', cascade='all, delete-orphan'))
    tasks = db.relationship('Task', backref='project', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'team_id': self.team_id,
            'team_name': self.team.name if self.team else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'task_count': self.tasks.count()
        }

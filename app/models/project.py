from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn
from app.extensions import db

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=get_now_vn)
    
    # Relationships
    team = db.relationship('Team', backref=db.backref('projects', lazy='dynamic', cascade='all, delete-orphan'))
    tasks = db.relationship('Task', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'team_id': self.team_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'task_count': self.tasks.count()
        }

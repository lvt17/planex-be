from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn
from app.extensions import db

class UserSurvey(db.Model):
    __tablename__ = 'user_surveys'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job = db.Column(db.String(200))
    tools = db.Column(db.JSON)  # List of tools
    desires = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_now_vn)
    
    user = db.relationship('User', back_populates='surveys')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'job': self.job,
            'tools': self.tools,
            'desires': self.desires,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class BugReport(db.Model):
    __tablename__ = 'bug_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='open')  # open, in_progress, closed
    created_at = db.Column(db.DateTime, default=get_now_vn)
    
    user = db.relationship('User', back_populates='reports')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

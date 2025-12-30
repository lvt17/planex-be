from datetime import datetime
from app.extensions import db


class Task(db.Model):
    __tablename__ = 'task'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    deadline = db.Column(db.DateTime)
    price = db.Column(db.Float, default=0)
    state = db.Column(db.Float, default=0)  # Progress 0-100
    is_done = db.Column(db.Boolean, default=False)
    client_num = db.Column(db.String(20))
    client_mail = db.Column(db.String(120))
    noted = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    images = db.relationship('ImageStore', backref='task', lazy='dynamic')
    incomes = db.relationship('OneIncome', backref='task', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'price': self.price,
            'state': self.state,
            'is_done': self.is_done,
            'client_num': self.client_num,
            'client_mail': self.client_mail,
            'noted': self.noted,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def to_mcp_format(self):
        """Format for AI/MCP integration"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.content,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'progress': self.state,
            'is_completed': self.is_done,
            'client': {
                'phone': self.client_num,
                'email': self.client_mail
            },
            'notes': self.noted,
            'price': self.price
        }

from datetime import datetime
from app.extensions import db
from app.utils.timezone import get_now_vn


class Task(db.Model):
    __tablename__ = 'task'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    deadline = db.Column(db.DateTime)
    price = db.Column(db.Integer, default=0)
    state = db.Column(db.Float, default=0)  # Progress 0-100
    is_done = db.Column(db.Boolean, default=False)
    client_num = db.Column(db.String(20))
    client_mail = db.Column(db.String(120))
    paid_at = db.Column(db.DateTime)
    # Portfolio fields
    show_in_portfolio = db.Column(db.Boolean, default=False)
    portfolio_thumbnail = db.Column(db.String(500))
    noted = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_now_vn)
    completed_at = db.Column(db.DateTime, nullable=True)
    # Team fields
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    images = db.relationship('ImageStore', backref='task', lazy='dynamic')
    incomes = db.relationship('OneIncome', backref='task', lazy='dynamic')
    subtasks = db.relationship('Subtask', back_populates='task', cascade='all, delete-orphan')
    comments = db.relationship('TaskComment', back_populates='task', cascade='all, delete-orphan')
    
    def calculate_progress(self):
        """Calculate progress based on subtasks if they exist"""
        subtask_list = self.subtasks
        if not subtask_list:
            return self.state  # Use manual progress if no subtasks
        
        completed = sum(1 for s in subtask_list if s.is_completed)
        return int((completed / len(subtask_list)) * 100) if subtask_list else 0
    
    def to_dict(self, include_relations=True):
        base_dict = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'content': self.content,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'price': self.price,
            'state': self.calculate_progress(),  # Auto-calculate from subtasks
            'is_done': self.is_done,
            'client_num': self.client_num,
            'client_mail': self.client_mail,
            'noted': self.noted,
            'show_in_portfolio': self.show_in_portfolio,
            'portfolio_thumbnail': self.portfolio_thumbnail,
            'team_id': self.team_id,
            'project_id': self.project_id,
            'creator_id': self.creator_id,
            'team_name': self.team.name if self.team else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
        
        # Include subtasks and comments if requested (default: True)
        if include_relations:
            # Use the already loaded relationships
            subtasks_list = self.subtasks
            comments_list = self.comments
            
            base_dict['subtasks'] = [s.to_dict() for s in subtasks_list]
            base_dict['comments'] = [c.to_dict() for c in comments_list]
            base_dict['subtask_count'] = len(subtasks_list)
            base_dict['comment_count'] = len(comments_list)
        else:
            base_dict['subtask_count'] = len(self.subtasks)
            base_dict['comment_count'] = len(self.comments)
        
        return base_dict
    
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

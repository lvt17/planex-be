from datetime import datetime
from app.extensions import db


class Workspace(db.Model):
    __tablename__ = 'workspace'
    
    id = db.Column(db.Integer, primary_key=True)
    mini_task = db.Column(db.String(200))
    content = db.Column(db.Text)
    loading = db.Column(db.Float, default=0)  # Progress 0-100
    is_done = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'mini_task': self.mini_task,
            'content': self.content,
            'loading': self.loading,
            'is_done': self.is_done
        }


class WorkspaceManage(db.Model):
    __tablename__ = 'workspace_manage'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    
    task = db.relationship('Task', backref='workspace_links')
    workspace = db.relationship('Workspace', backref='task_links')

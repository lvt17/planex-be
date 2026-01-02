from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn
from app.extensions import db

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)  # HTML content for rich text
    created_at = db.Column(db.DateTime, default=get_now_vn)
    updated_at = db.Column(db.DateTime, onupdate=get_now_vn)
    
    user = db.relationship('User', backref='documents')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Spreadsheet(db.Model):
    __tablename__ = 'spreadsheets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    data = db.Column(db.JSON)  # Store table data as JSON array of arrays
    created_at = db.Column(db.DateTime, default=get_now_vn)
    updated_at = db.Column(db.DateTime, onupdate=get_now_vn)
    
    user = db.relationship('User', backref='spreadsheets')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'data': self.data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


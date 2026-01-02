from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn
from app.extensions import db


class Whiteboard(db.Model):
    __tablename__ = 'whiteboards'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    data = db.Column(db.JSON)  # Store whiteboard elements as JSON
    created_at = db.Column(db.DateTime, default=get_now_vn)
    updated_at = db.Column(db.DateTime, onupdate=get_now_vn)
    
    # Relationships
    user = db.relationship('User', backref='whiteboards')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'data': self.data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class WhiteboardElement(db.Model):
    __tablename__ = 'whiteboard_elements'
    
    id = db.Column(db.Integer, primary_key=True)
    whiteboard_id = db.Column(db.Integer, db.ForeignKey('whiteboards.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # text, shape, image, etc.
    content = db.Column(db.JSON)  # Element-specific data
    position_x = db.Column(db.Float, default=0)
    position_y = db.Column(db.Float, default=0)
    width = db.Column(db.Float, default=100)
    height = db.Column(db.Float, default=50)
    created_at = db.Column(db.DateTime, default=get_now_vn)
    
    # Relationships
    whiteboard = db.relationship('Whiteboard', backref='elements')
    
    def to_dict(self):
        return {
            'id': self.id,
            'whiteboard_id': self.whiteboard_id,
            'type': self.type,
            'content': self.content,
            'position_x': self.position_x,
            'position_y': self.position_y,
            'width': self.width,
            'height': self.height,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

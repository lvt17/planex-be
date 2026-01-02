from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn
from app.extensions import db


class ImageStore(db.Model):
    __tablename__ = 'images_store'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    storage_id = db.Column(db.Integer, db.ForeignKey('storage.id'))
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=get_now_vn)
    
    storage = db.relationship('Storage', backref='images')
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'url': self.image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

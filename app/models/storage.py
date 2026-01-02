from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn
from app.extensions import db


class Storage(db.Model):
    __tablename__ = 'storage'
    
    id = db.Column(db.Integer, primary_key=True)
    avt_url = db.Column(db.String(500))
    storage_key = db.Column(db.LargeBinary)
    type = db.Column(db.String(50))  # avatar, image, file
    created_at = db.Column(db.DateTime, default=get_now_vn)
    
    def to_dict(self):
        return {
            'id': self.id,
            'url': self.avt_url,
            'type': self.type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

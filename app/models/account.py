from datetime import datetime
from app.extensions import db


class Account(db.Model):
    __tablename__ = 'account'
    
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    noted = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'username': self.username,
            'noted': self.noted,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AccountStore(db.Model):
    __tablename__ = 'accounts_store'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    storage_id = db.Column(db.Integer, db.ForeignKey('storage.id'), nullable=False)
    
    account = db.relationship('Account', backref='storage_links')
    storage = db.relationship('Storage', backref='account_links')

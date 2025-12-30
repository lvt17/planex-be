from datetime import datetime
from app.extensions import db


class Payment(db.Model):
    __tablename__ = 'payment'
    
    id = db.Column(db.Integer, primary_key=True)
    bank_name = db.Column(db.String(100), nullable=False)
    card_code = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'bank_name': self.bank_name,
            'card_code': self.card_code[-4:] if self.card_code else None,  # Only show last 4 digits
            'content': self.content
        }


class PaymentStore(db.Model):
    __tablename__ = 'payment_store'
    
    id = db.Column(db.Integer, primary_key=True)
    storage_id = db.Column(db.Integer, db.ForeignKey('storage.id'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=False)
    
    storage = db.relationship('Storage', backref='payment_links')
    payment = db.relationship('Payment', backref='storage_links')

from app import db
from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn

class Sale(db.Model):
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    total_price = db.Column(db.Numeric(15, 2), nullable=False)
    sale_date = db.Column(db.DateTime, default=get_now_vn)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'quantity': self.quantity,
            'total_price': float(self.total_price) if self.total_price else 0,
            'sale_date': self.sale_date.isoformat() if self.sale_date else None
        }

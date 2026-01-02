from app import db
from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    stock = db.Column(db.Integer, default=0)
    image_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_now_vn)
    
    # Relationships
    sales = db.relationship('Sale', backref='product', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'name': self.name,
            'price': float(self.price) if self.price else 0,
            'stock': self.stock,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'total_sold': sum(s.quantity for s in self.sales) if self.sales else 0
        }

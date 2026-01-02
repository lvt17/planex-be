from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn
from app.extensions import db


class OneIncome(db.Model):
    __tablename__ = 'one_income'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    total_income_id = db.Column(db.Integer, db.ForeignKey('total_income.id'))
    
    total_income = db.relationship('TotalIncome', backref='incomes')


class TotalIncome(db.Model):
    __tablename__ = 'total_income'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total = db.Column(db.Float, default=0)
    from_source = db.Column(db.String(200))  # task_name or source description
    source_type = db.Column(db.String(50), default='job')  # 'job' or 'sales'
    noted = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_now_vn)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'total': self.total,
            'from': self.from_source,
            'source_type': self.source_type,
            'noted': self.noted,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


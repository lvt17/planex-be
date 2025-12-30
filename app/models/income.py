from datetime import datetime
from app.extensions import db


class OneIncome(db.Model):
    __tablename__ = 'one_income'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    total_income_id = db.Column(db.Integer, db.ForeignKey('total_income.id'))
    
    total_income = db.relationship('TotalIncome', backref='incomes')


class TotalIncome(db.Model):
    __tablename__ = 'total_income'
    
    id = db.Column(db.Integer, primary_key=True)
    total = db.Column(db.Float, default=0)
    from_source = db.Column(db.String(200))  # task_name
    noted = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'total': self.total,
            'from': self.from_source,
            'noted': self.noted,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

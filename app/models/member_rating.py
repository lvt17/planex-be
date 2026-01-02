from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn
from app.extensions import db


class MemberRating(db.Model):
    """Rating given by team leader to members"""
    __tablename__ = 'member_ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rater_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Leader who rates
    score = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_now_vn)
    updated_at = db.Column(db.DateTime, onupdate=get_now_vn)
    
    # Unique constraint: one rating per member per team per rater
    __table_args__ = (
        db.UniqueConstraint('team_id', 'member_id', 'rater_id', name='unique_member_rating'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'team_id': self.team_id,
            'member_id': self.member_id,
            'rater_id': self.rater_id,
            'score': self.score,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

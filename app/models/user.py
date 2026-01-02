from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120))
    storage_id = db.Column(db.Integer, db.ForeignKey('storage.id'))
    storage_key = db.Column(db.LargeBinary)
    created_at = db.Column(db.DateTime, default=get_now_vn)
    updated_at = db.Column(db.DateTime, onupdate=get_now_vn)
    is_verified = db.Column(db.Boolean, default=False)
    otp_code = db.Column(db.String(6))
    otp_expiry = db.Column(db.DateTime)
    locked_until = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    storage = db.relationship('Storage', backref='user', foreign_keys=[storage_id])
    tasks = db.relationship('Task', backref='owner', lazy='dynamic', cascade='all, delete-orphan', foreign_keys='Task.user_id')
    created_tasks = db.relationship('Task', backref='creator', lazy='dynamic', foreign_keys='Task.creator_id')
    team_memberships = db.relationship('TeamMembership', back_populates='user', lazy='dynamic', cascade='all, delete-orphan', foreign_keys='TeamMembership.user_id')
    owned_teams = db.relationship('Team', back_populates='owner', lazy='dynamic', cascade='all, delete-orphan', foreign_keys='Team.owner_id')
    chat_messages = db.relationship('ChatMessage', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    surveys = db.relationship('UserSurvey', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    reports = db.relationship('BugReport', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    invites = db.relationship('TeamInvite', back_populates='user', lazy='dynamic', cascade='all, delete-orphan', foreign_keys='TeamInvite.user_id')
    ratings_received = db.relationship('MemberRating', backref='member_obj', lazy='dynamic', cascade='all, delete-orphan', foreign_keys='MemberRating.member_id')
    ratings_given = db.relationship('MemberRating', backref='rater_obj', lazy='dynamic', cascade='all, delete-orphan', foreign_keys='MemberRating.rater_id')
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    sent_invites = db.relationship('TeamMembership', back_populates='inviter', lazy='dynamic', foreign_keys='TeamMembership.invited_by')
    
    def set_password(self, password):
        self.password = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    @property
    def is_locked(self):
        if not self.locked_until:
            return False
        # Handle timezone-naive dates
        now = get_now_vn()
        locked_until = self.locked_until
        # Make both timezone-aware or both naive
        if locked_until.tzinfo is None and now.tzinfo is not None:
            from datetime import timezone
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        elif locked_until.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=locked_until.tzinfo)
        return locked_until > now
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'avatar_url': self.storage.avt_url if self.storage else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'locked_until': self.locked_until.isoformat() if self.locked_until else None,
            'is_locked': self.is_locked
        }

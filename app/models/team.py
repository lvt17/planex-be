from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn
from app.extensions import db


class Team(db.Model):
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    avatar_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=get_now_vn)
    
    # Relationships
    owner = db.relationship('User', back_populates='owned_teams', foreign_keys=[owner_id])
    members = db.relationship('TeamMembership', backref='team', lazy='dynamic', cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='team', lazy='dynamic')
    messages = db.relationship('ChatMessage', backref='team', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'owner_id': self.owner_id,
            'owner_name': self.owner.username if self.owner else None,
            'avatar_url': self.avatar_url,
            'member_count': self.members.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TeamMembership(db.Model):
    __tablename__ = 'team_memberships'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), default='member')  # 'owner', 'admin', 'member'
    invited_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    joined_at = db.Column(db.DateTime, default=get_now_vn)
    
    # Relationships
    user = db.relationship('User', back_populates='team_memberships', foreign_keys=[user_id])
    inviter = db.relationship('User', back_populates='sent_invites', foreign_keys=[invited_by])
    
    def to_dict(self):
        # Get badges safely
        try:
            user_badges = self.user.badges if self.user else []
        except Exception as e:
            import logging
            logging.error(f"TeamMembership.to_dict badges error for user {self.user_id}: {e}")
            user_badges = []
            
        return {
            'id': self.id,
            'team_id': self.team_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'full_name': self.user.full_name if self.user else None,
            'email': self.user.email if self.user else None,
            'avatar_url': self.user.storage.avt_url if self.user and self.user.storage else None,
            'title': self.user.title if self.user else None,
            'badges': user_badges,
            'role': self.role,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None
        }


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=get_now_vn)
    
    # Relationships
    user = db.relationship('User', back_populates='chat_messages')
    
    def to_dict(self):
        # Get team-specific badges instead of global badges
        try:
            user_badges = self.user.get_team_badges(self.team_id) if self.user else []
        except Exception as e:
            import logging
            logging.error(f"ChatMessage.to_dict badges error for user {self.user_id}: {e}")
            user_badges = []
            
        return {
            'id': self.id,
            'team_id': self.team_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'full_name': self.user.full_name if self.user else None,
            'avatar_url': self.user.storage.avt_url if self.user and self.user.storage else None,
            'title': self.user.title if self.user else None,
            'badges': user_badges,
            'content': self.content,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TeamInvite(db.Model):
    """Handles both invite links and join requests"""
    __tablename__ = 'team_invites'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    invite_token = db.Column(db.String(64), unique=True, nullable=True)  # For invite links
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # For join requests
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    invite_type = db.Column(db.String(20), default='link')  # 'link' or 'request'
    created_at = db.Column(db.DateTime, default=get_now_vn)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    team = db.relationship('Team', backref=db.backref('invite_list', overlaps="invites")) # Using backref with overlaps for simplicity here
    user = db.relationship('User', back_populates='invites', foreign_keys=[user_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'team_id': self.team_id,
            'team_name': self.team.name if self.team else None,
            'invite_token': self.invite_token,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'status': self.status,
            'invite_type': self.invite_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


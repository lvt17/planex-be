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
    access_count = db.Column(db.Integer, default=0)
    
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
    
    @property
    def badges(self):
        """Dynamic and manual badges for the user"""
        results = []
        try:
            now = get_now_vn()
            # USE NAIVE DATETIME FOR DATABASE COMPARISON to avoid issues with naive columns
            now_naive = now.replace(tzinfo=None)
            
            # 1. Primary Prestige Tier (The base badge)
            try:
                if self.email in ['lieutoan7788a@gmail.com', 'Vtoanhihihi@gmail.com']:
                    results.append('Planex Ghost')
                else:
                    count = self.access_count or 0
                    if count >= 1000:
                        results.append('Planex Legend')
                    elif count >= 100:
                        results.append('Planex Master')
                    elif count >= 10:
                        results.append('Planex Citizen')
                    else:
                        results.append('Planex Newbie')
            except Exception as e:
                import logging
                logging.error(f"Badge calc error (Prestige): {e}")
                results.append('Planex Newbie')
            
            # 2. Leader Badge (if owns any team)
            try:
                if self.owned_teams.first():
                    results.append('Planex Leader')
            except Exception as e:
                import logging
                logging.error(f"Badge calc error (Leader): {e}")
            
            # 3. Dynamic Performance Badges (Star of the Week/Month)
            try:
                from app.models.task import Task
                
                # Star of the Week logic:
                curr_weekday = now_naive.weekday()
                this_monday = (now_naive - timedelta(days=curr_weekday)).replace(hour=0, minute=0, second=0, microsecond=0)
                last_sunday = this_monday - timedelta(days=1)
                prev_sunday_start = last_sunday - timedelta(days=6)
                
                tasks_prev_week = Task.query.filter_by(user_id=self.id, is_done=True).filter(
                    Task.completed_at >= prev_sunday_start,
                    Task.completed_at < this_monday
                ).count()
                
                if tasks_prev_week >= 5:
                    results.append('Star of the Week')
                    
                # Star of the Month logic:
                first_day_this_month = now_naive.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                last_day_prev_month = first_day_this_month - timedelta(days=1)
                first_day_prev_month = last_day_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                tasks_prev_month = Task.query.filter_by(user_id=self.id, is_done=True).filter(
                    Task.completed_at >= first_day_prev_month,
                    Task.completed_at < first_day_this_month
                ).count()
                
                if tasks_prev_month >= 21:
                    results.append('Star of the Month')
            except Exception as e:
                import logging
                logging.error(f"Badge calc error (Performance): {e}")
                
            # 4. Best Member Badge (highest access_count in any team)
            try:
                memberships = self.team_memberships.all()
                for m in memberships:
                    team = m.team
                    if team and team.members:
                        if team.members.count() > 1:
                            member_counts = [tm.user.access_count or 0 for tm in team.members.all() if tm.user]
                            if member_counts:
                                max_cnt = max(member_counts)
                                if (self.access_count or 0) >= max_cnt and max_cnt > 0:
                                    results.append('The Best Member')
                                    break
            except Exception as e:
                import logging
                logging.error(f"Badge calc error (Best Member): {e}")
                
            # 5. Manual Assignments from Admin
            try:
                from app.models.badge_model import UserBadgeAssignment
                active_assignments = UserBadgeAssignment.query.filter_by(user_id=self.id).filter(
                    (UserBadgeAssignment.expires_at == None) | (UserBadgeAssignment.expires_at > now_naive)
                ).all()
                for assignment in active_assignments:
                    if assignment.badge:
                        results.append(assignment.badge.name)
            except Exception as e:
                import logging
                logging.error(f"Badge calc error (Manual Assignments): {e}")
                # Don't crash if badge assignments fail - just skip them
                
        except Exception as e:
            # Outer fallback for any unexpected errors
            import logging
            logging.error(f"Badge calc critical error: {e}")
            if not results:
                if self.email in ['lieutoan7788a@gmail.com', 'Vtoanhihihi@gmail.com']:
                    results.append('Planex Ghost')
                else:
                    results.append('Planex Newbie')
                    
        return results if results else ['Planex Newbie']
    
    def get_team_badges(self, team_id):
        """Get only team-relevant badges for a specific team"""
        badges = []
        try:
            # 1. Leader Badge (if owns this team)
            from app.models.team import Team
            team = Team.query.get(team_id)
            if team and team.owner_id == self.id:
                badges.append('Planex Leader')
            
            # 2. Best Member Badge (highest access_count in THIS team)
            from app.models.team import TeamMembership
            membership = TeamMembership.query.filter_by(team_id=team_id, user_id=self.id).first()
            if membership and team and team.members:
                if team.members.count() > 1:
                    member_counts = [tm.user.access_count or 0 for tm in team.members.all() if tm.user]
                    if member_counts:
                        max_cnt = max(member_counts)
                        if (self.access_count or 0) >= max_cnt and max_cnt > 0:
                            badges.append('The Best Member')
        except Exception as e:
            import logging
            logging.error(f"get_team_badges error for user {self.id}, team {team_id}: {e}")
        
        return badges

    @property
    def title(self):
        """Primary title for backward compatibility"""
        b = self.badges
        return b[0] if b else 'Planex Newbie'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'avatar_url': self.storage.avt_url if self.storage else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'locked_until': self.locked_until.isoformat() if self.locked_until else None,
            'is_locked': self.is_locked,
            'access_count': self.access_count or 0,
            'title': self.title,
            'badges': self.badges
        }

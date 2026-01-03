from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.notification import Notification
from app.models.task import Task
from app.models.team import TeamMembership, TeamInvite, Team
from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn, timedelta

bp = Blueprint('notifications', __name__)


@bp.route('', methods=['GET'])
@jwt_required()
def get_notifications():
    """Get all notifications for the current user"""
    user_id = get_jwt_identity()
    
    # Also check for stale tasks and deadline tasks
    check_task_notifications(user_id)
    
    notifications = Notification.query.filter_by(user_id=user_id)\
        .order_by(Notification.created_at.desc())\
        .limit(50).all()
    
    unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    
    return jsonify({
        'notifications': [n.to_dict() for n in notifications],
        'unread_count': unread_count
    })


@bp.route('/<int:notification_id>/read', methods=['POST'])
@jwt_required()
def mark_as_read(notification_id):
    """Mark a notification as read"""
    user_id = get_jwt_identity()
    
    notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first_or_404()
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'message': 'Marked as read'})


@bp.route('/read-all', methods=['POST'])
@jwt_required()
def mark_all_as_read():
    """Mark all notifications as read"""
    user_id = get_jwt_identity()
    
    Notification.query.filter_by(user_id=user_id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    
    return jsonify({'message': 'All notifications marked as read'})


@bp.route('/team-invite/<int:invite_id>/accept', methods=['POST'])
@jwt_required()
def accept_team_invite(invite_id):
    """Accept a team invite from notification"""
    user_id = get_jwt_identity()
    
    invite = TeamInvite.query.filter_by(id=invite_id, user_id=user_id, invite_type='invite', status='pending').first()
    if not invite:
        return jsonify({'error': 'Invalid or expired invite'}), 404
    
    # Check if already a member
    existing = TeamMembership.query.filter_by(team_id=invite.team_id, user_id=user_id).first()
    if existing:
        return jsonify({'error': 'Already a member'}), 400
    
    # Add as member
    membership = TeamMembership(
        team_id=invite.team_id,
        user_id=user_id,
        role='member'
    )
    db.session.add(membership)
    
    invite.status = 'accepted'
    
    # Mark related notification as read
    Notification.query.filter_by(
        user_id=user_id, 
        action_type='accept_team_invite',
        is_read=False
    ).update({'is_read': True})
    
    db.session.commit()
    
    return jsonify({'message': 'Đã tham gia team!'})


@bp.route('/team-invite/<int:invite_id>/reject', methods=['POST'])
@jwt_required()
def reject_team_invite(invite_id):
    """Reject a team invite from notification"""
    user_id = get_jwt_identity()
    
    invite = TeamInvite.query.filter_by(id=invite_id, user_id=user_id, invite_type='invite', status='pending').first()
    if not invite:
        return jsonify({'error': 'Invalid or expired invite'}), 404
    
    invite.status = 'rejected'
    
    # Mark related notification as read
    Notification.query.filter_by(
        user_id=user_id, 
        action_type='accept_team_invite',
        is_read=False
    ).update({'is_read': True})
    
    db.session.commit()
    
    return jsonify({'message': 'Đã từ chối lời mời'})


def check_task_notifications(user_id):
    """Check for deadline and stale task notifications"""
    now = get_now_vn()
    today = now.date()
    
    # Get user's tasks
    tasks = Task.query.filter_by(user_id=user_id, is_done=False).all()
    
    for task in tasks:
        # Check deadline (within 24 hours)
        if task.deadline:
            deadline_date = task.deadline.date() if isinstance(task.deadline, datetime) else task.deadline
            days_until = (deadline_date - today).days
            
            if 0 <= days_until <= 1:
                # PERFORMANCE: Avoid direct JSON comparison in query for PostgreSQL compatibility
                existing = Notification.query.filter_by(
                    user_id=user_id,
                    type='task_deadline'
                ).filter(Notification.created_at > now - timedelta(hours=12)).all()
                
                # Manual check in Python
                is_duplicate = any(n.action_data.get('task_id') == task.id for n in existing if n.action_data)
                
                if not is_duplicate:
                    notif = Notification(
                        user_id=user_id,
                        type='task_deadline',
                        title='Task sắp đến deadline!',
                        message=f'Task "{task.name}" sẽ đến hạn {"hôm nay" if days_until == 0 else "ngày mai"}.',
                        action_type='view_task',
                        action_data={'task_id': task.id}
                    )
                    db.session.add(notif)
        
        # Check stale task (no progress change in 2+ days)
        if task.created_at:
            # Make datetime timezone-aware if needed
            task_created = task.created_at
            if task_created.tzinfo is None:
                task_created = task_created.replace(tzinfo=timezone.utc)
            now_for_compare = now
            if now_for_compare.tzinfo is None:
                now_for_compare = now_for_compare.replace(tzinfo=timezone.utc)
            
            days_old = (now_for_compare - task_created).days
            if days_old >= 2 and task.state < 50:
                # PERFORMANCE: Avoid direct JSON comparison in query for PostgreSQL compatibility
                existing = Notification.query.filter_by(
                    user_id=user_id,
                    type='task_stale'
                ).filter(Notification.created_at > now - timedelta(days=1)).all()
                
                # Manual check in Python
                is_duplicate = any(n.action_data.get('task_id') == task.id for n in existing if n.action_data)
                
                if not is_duplicate:
                    notif = Notification(
                        user_id=user_id,
                        type='task_stale',
                        title='Task chậm tiến độ',
                        message=f'Task "{task.name}" đã tạo {days_old} ngày nhưng tiến độ mới {int(task.state)}%.',
                        action_type='view_task',
                        action_data={'task_id': task.id}
                    )
                    db.session.add(notif)
    
    try:
        db.session.commit()
    except:
        db.session.rollback()


def create_team_invite_notification(user_id, team_id, team_name, invite_id, inviter_name):
    """Create a notification for team invite"""
    notif = Notification(
        user_id=user_id,
        type='team_invite',
        title='Lời mời tham gia team',
        message=f'{inviter_name} đã mời bạn tham gia team "{team_name}".',
        action_type='accept_team_invite',
        action_data={'team_id': team_id, 'invite_id': invite_id}
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def create_password_changed_notification(user_id):
    """Create a notification for password change"""
    notif = Notification(
        user_id=user_id,
        type='password_changed',
        title='Đổi mật khẩu thành công',
        message='Mật khẩu của bạn đã được thay đổi. Nếu không phải bạn thực hiện, hãy liên hệ hỗ trợ ngay.',
        action_type=None,
        action_data=None
    )
    db.session.add(notif)
    db.session.commit()
    return notif

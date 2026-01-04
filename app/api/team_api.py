from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.team import Team, TeamMembership, ChatMessage, TeamInvite
from app.models.user import User
from app.models.task import Task
from app.models.project import Project
from app.models.notification import Notification
from app.utils.timezone import get_now_vn
from app.services.sse_manager import sse_manager
import secrets
import os
from datetime import datetime, timedelta, timezone
from app.services.mail_service import send_task_assignment_email, start_background_email
from sqlalchemy.orm import joinedload

bp = Blueprint('teams', __name__)


@bp.route('', methods=['POST'])
@jwt_required()
def create_team():
    """Create a new team"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({'error': 'Team name is required'}), 400
    
    team = Team(name=data['name'], owner_id=user_id)
    db.session.add(team)
    db.session.flush()  # Get team.id
    
    # Add owner as first member
    membership = TeamMembership(
        team_id=team.id,
        user_id=user_id,
        role='owner'
    )
    db.session.add(membership)
    db.session.commit()
    
    return jsonify(team.to_dict()), 201


@bp.route('', methods=['GET'])
@jwt_required()
def list_teams():
    """List all teams the user belongs to"""
    user_id = int(get_jwt_identity())
    # PERFORMANCE: Eager load team and owner to avoid N+1 queries
    memberships = TeamMembership.query.options(
        joinedload(TeamMembership.team).joinedload(Team.owner)
    ).filter_by(user_id=user_id).all()
    
    teams = [m.team.to_dict() for m in memberships if m.team]
    return jsonify(teams)


@bp.route('/<int:team_id>', methods=['GET'])
@jwt_required()
def get_team(team_id):
    """Get team details and members"""
    user_id = int(get_jwt_identity())
    
    # Check if user is a member
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership:
        return jsonify({'error': 'Not a member of this team'}), 403
    
    # Load team with owner (members is dynamic, can't use joinedload)
    team = Team.query.options(
        joinedload(Team.owner)
    ).get_or_404(team_id)
    
    # Load members separately with eager loading on user and storage
    members_query = TeamMembership.query.options(
        joinedload(TeamMembership.user).joinedload(User.storage)
    ).filter_by(team_id=team_id).all()
    
    members = [m.to_dict() for m in members_query]
    
    # Get pending requests for owner/admin
    pending_requests = []
    if membership.role in ['owner', 'admin']:
        pending = TeamInvite.query.filter_by(team_id=team_id, status='pending', invite_type='request').all()
        pending_requests = [r.to_dict() for r in pending]
    
    result = team.to_dict()
    result['members'] = members
    result['my_role'] = membership.role
    result['pending_requests'] = pending_requests
    
    return jsonify(result)


@bp.route('/<int:team_id>', methods=['PUT'])
@jwt_required()
def update_team(team_id):
    """Update team info (name) - owner/admin only"""
    user_id = int(get_jwt_identity())
    
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership or membership.role not in ['owner', 'admin']:
        return jsonify({'error': 'Only owners and admins can update team settings'}), 403
    
    team = Team.query.get_or_404(team_id)
    data = request.get_json()
    
    if 'name' in data and data['name'].strip():
        team.name = data['name'].strip()
    
    db.session.commit()
    return jsonify(team.to_dict())


@bp.route('/<int:team_id>/avatar', methods=['POST'])
@jwt_required()
def upload_team_avatar(team_id):
    """Upload team avatar - owner/admin only"""
    user_id = int(get_jwt_identity())
    
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership or membership.role not in ['owner', 'admin']:
        return jsonify({'error': 'Only owners and admins can update team avatar'}), 403
    
    if 'avatar' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    import uuid
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'team_avatars')
    os.makedirs(upload_dir, exist_ok=True)
    
    ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'png'
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    
    team = Team.query.get_or_404(team_id)
    team.avatar_url = f"/static/team_avatars/{filename}"
    db.session.commit()
    
    return jsonify(team.to_dict())


@bp.route('/<int:team_id>/members/<int:member_id>/role', methods=['PUT'])
@jwt_required()
def change_member_role(team_id, member_id):
    """Change member role - owner only"""
    user_id = int(get_jwt_identity())
    
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership or membership.role != 'owner':
        return jsonify({'error': 'Only owner can change member roles'}), 403
    
    if member_id == user_id:
        return jsonify({'error': 'Cannot change your own role'}), 400
    
    target_membership = TeamMembership.query.filter_by(team_id=team_id, user_id=member_id).first()
    if not target_membership:
        return jsonify({'error': 'Member not found in this team'}), 404
    
    data = request.get_json()
    new_role = data.get('role')
    if new_role not in ['admin', 'member']:
        return jsonify({'error': 'Invalid role. Must be admin or member'}), 400
    
    target_membership.role = new_role
    db.session.commit()
    
    return jsonify({'message': f'Role changed to {new_role}', 'member': target_membership.to_dict()})


@bp.route('/<int:team_id>/invite', methods=['POST'])
@jwt_required()
def invite_member(team_id):
    """Invite a user to the team by email (creates pending invite, user must accept)"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Check if requester is owner or admin
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership or membership.role not in ['owner', 'admin']:
        return jsonify({'error': 'Only owners and admins can invite members'}), 403
    
    identifier = data.get('username') or data.get('identifier')
    if not identifier:
        return jsonify({'error': 'Username hoặc email là bắt buộc'}), 400
    
    # Find user by username or email
    invitee = User.query.filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()
    if not invitee:
        return jsonify({'error': 'Không tìm thấy user'}), 404
    
    # Check if already a member
    existing = TeamMembership.query.filter_by(team_id=team_id, user_id=invitee.id).first()
    if existing:
        return jsonify({'error': 'User is already a member'}), 400
    
    # Check if pending invite exists
    existing_invite = TeamInvite.query.filter_by(
        team_id=team_id, 
        user_id=invitee.id, 
        invite_type='invite', 
        status='pending'
    ).first()
    if existing_invite:
        return jsonify({'error': 'Đã gửi lời mời cho user này rồi'}), 400
    
    # Create pending invite
    invite = TeamInvite(
        team_id=team_id,
        user_id=invitee.id,
        invite_type='invite',
        status='pending'
    )
    db.session.add(invite)
    db.session.flush()
    
    # Create notification for invitee
    from app.models.notification import Notification
    inviter = User.query.get(user_id)
    team = Team.query.get(team_id)
    notification = Notification(
        user_id=invitee.id,
        type='team_invite',
        title='Lời mời tham gia team',
        message=f'{inviter.username} đã mời bạn tham gia team "{team.name}".',
        action_type='accept_team_invite',
        action_data={'team_id': team_id, 'invite_id': invite.id}
    )
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({'message': f'Đã gửi lời mời đến {invitee.username}. Họ cần chấp nhận lời mời.'}), 201



# ==================== INVITE LINK SYSTEM ====================

@bp.route('/<int:team_id>/invite-link', methods=['POST'])
@jwt_required()
def generate_invite_link(team_id):
    """Generate an invite link for the team"""
    user_id = int(get_jwt_identity())
    
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership or membership.role not in ['owner', 'admin']:
        return jsonify({'error': 'Only owners and admins can generate invite links'}), 403
    
    # Generate a unique token
    token = secrets.token_urlsafe(32)
    
    invite = TeamInvite(
        team_id=team_id,
        invite_token=token,
        invite_type='link',
        expires_at=get_now_vn() + timedelta(days=7)  # Link expires in 7 days
    )
    db.session.add(invite)
    db.session.commit()
    
    return jsonify({
        'invite_link': f'/join-team/{token}',
        'token': token,
        'expires_at': invite.expires_at.isoformat()
    }), 201


@bp.route('/join/<token>', methods=['GET'])
def get_invite_info(token):
    """Get team info from invite token (no auth required)"""
    # Clean token from potential trailing slashes or whitespace (common on mobile apps)
    token = token.strip().rstrip('/')
    
    invite = TeamInvite.query.filter_by(invite_token=token, invite_type='link').first()
    
    if not invite:
        return jsonify({'error': 'TOKEN_NOT_FOUND', 'message': 'Mã mời không tồn tại hoặc không hợp lệ'}), 404
    
    now = get_now_vn().replace(tzinfo=None)
    
    if invite.expires_at and invite.expires_at < now:
        return jsonify({
            'error': 'TOKEN_EXPIRED', 
            'message': f'Link mời đã hết hạn vào lúc {invite.expires_at.strftime("%H:%M %d/%m/%Y")}'
        }), 410
    
    return jsonify({
        'team_id': invite.team_id,
        'team_name': invite.team.name if invite.team else 'Team không tên',
        'valid': True
    })


@bp.route('/join/<token>', methods=['POST'])
@jwt_required()
def request_to_join(token):
    """Request to join a team via invite link"""
    user_id = int(get_jwt_identity())
    
    token = token.strip().rstrip('/')
    invite = TeamInvite.query.filter_by(invite_token=token, invite_type='link').first()
    
    if not invite:
        return jsonify({'error': 'TOKEN_NOT_FOUND', 'message': 'Mã mời không tồn tại'}), 404
    
    if invite.expires_at and invite.expires_at < get_now_vn().replace(tzinfo=None):
        return jsonify({
            'error': 'TOKEN_EXPIRED', 
            'message': f'Link mời đã hết hạn vào lúc {invite.expires_at.strftime("%H:%M %d/%m/%Y")}'
        }), 410
    
    team_id = invite.team_id
    
    # Check if already a member
    existing = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if existing:
        return jsonify({'error': 'You are already a member of this team'}), 400
    
    # Check if already requested
    existing_request = TeamInvite.query.filter_by(
        team_id=team_id, 
        user_id=user_id, 
        invite_type='request',
        status='pending'
    ).first()
    if existing_request:
        return jsonify({'error': 'You have already requested to join this team'}), 400
    
    # Create join request
    join_request = TeamInvite(
        team_id=team_id,
        user_id=user_id,
        invite_type='request',
        status='pending'
    )
    db.session.add(join_request)
    db.session.commit()
    
    return jsonify({'message': 'Join request sent. Waiting for leader approval.'}), 201


@bp.route('/<int:team_id>/requests/<int:request_id>/approve', methods=['POST'])
@jwt_required()
def approve_request(team_id, request_id):
    """Approve a join request"""
    user_id = int(get_jwt_identity())
    
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership or membership.role not in ['owner', 'admin']:
        return jsonify({'error': 'Only owners and admins can approve requests'}), 403
    
    join_request = TeamInvite.query.get_or_404(request_id)
    if join_request.team_id != team_id or join_request.invite_type != 'request':
        return jsonify({'error': 'Invalid request'}), 400
    
    if join_request.status != 'pending':
        return jsonify({'error': 'Request already processed'}), 400
    
    # Check if user is already a member (idempotency check)
    existing_membership = TeamMembership.query.filter_by(
        team_id=team_id, 
        user_id=join_request.user_id
    ).first()
    
    if existing_membership:
        # If already a member, just mark the request as approved and return success
        join_request.status = 'approved'
        db.session.commit()
        return jsonify({'message': 'User is already a member. Request marked as approved.'})

    # Add member
    new_member = TeamMembership(
        team_id=team_id,
        user_id=join_request.user_id,
        role='member',
        invited_by=user_id
    )
    db.session.add(new_member)
    
    # Update request status
    join_request.status = 'approved'
    db.session.commit()
    
    return jsonify({'message': 'Request approved. User is now a team member.'})


@bp.route('/<int:team_id>/requests/<int:request_id>/reject', methods=['POST'])
@jwt_required()
def reject_request(team_id, request_id):
    """Reject a join request"""
    user_id = int(get_jwt_identity())
    
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership or membership.role not in ['owner', 'admin']:
        return jsonify({'error': 'Only owners and admins can reject requests'}), 403
    
    join_request = TeamInvite.query.get_or_404(request_id)
    if join_request.team_id != team_id or join_request.invite_type != 'request':
        return jsonify({'error': 'Invalid request'}), 400
    
    if join_request.status != 'pending':
        return jsonify({'error': 'Request already processed'}), 400
    
    join_request.status = 'rejected'
    db.session.commit()
    
    return jsonify({'message': 'Request rejected.'})


@bp.route('/<int:team_id>/projects', methods=['GET', 'POST'])
@jwt_required()
def handle_projects(team_id):
    """Handle project operations in a team"""
    user_id = int(get_jwt_identity())
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    
    if not membership:
        return jsonify({'error': 'Not a member of this team'}), 403

    if request.method == 'POST':
        if membership.role not in ['owner', 'admin']:
            return jsonify({'error': 'Only owners and admins can create projects'}), 403
        data = request.get_json()
        if not data.get('name'):
            return jsonify({'error': 'Project name is required'}), 400
        # Team project: has team_id, NO user_id
        project = Project(
            name=data['name'],
            description=data.get('description'),
            price=data.get('price', 0.0),  # Optional price
            team_id=team_id,
            user_id=None  # Team projects don't belong to individual users
        )
        db.session.add(project)
        db.session.commit()
        return jsonify(project.to_dict()), 201
    
    # GET
    projects = Project.query.filter_by(team_id=team_id).all()
    return jsonify([p.to_dict() for p in projects])


@bp.route('/<int:team_id>/projects/<int:project_id>/tasks', methods=['POST'])
@jwt_required()
def create_project_task(team_id, project_id):
    """Create a task within a specific project and optionally assign it"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership or membership.role not in ['owner', 'admin']:
        return jsonify({'error': 'Only owners and admins can assign project tasks'}), 403
        
    project = Project.query.get_or_404(project_id)
    if project.team_id != team_id:
        return jsonify({'error': 'Project does not belong to this team'}), 400
        
    assignee_id = data.get('assigned_to')
    if assignee_id:
        assignee_membership = TeamMembership.query.filter_by(team_id=team_id, user_id=assignee_id).first()
        if not assignee_membership:
            return jsonify({'error': 'Assignee is not a member of this team'}), 400

    task = Task(
        name=data.get('name'),
        content=data.get('content'),
        deadline=datetime.fromisoformat(data['deadline']) if data.get('deadline') else None,
        price=data.get('price', 0),
        user_id=assignee_id or user_id,  # If assigned, the assignee is the "owner" of the task record
        team_id=team_id,
        project_id=project_id,
        creator_id=user_id
    )
    db.session.add(task)
    db.session.flush()
    
    if assignee_id and assignee_id != user_id:
        # Notify assignee
        creator = User.query.get(user_id)
        team = Team.query.get(team_id)
        notification = Notification(
            user_id=assignee_id,
            type='task_assigned',
            title='Công việc mới được giao',
            message=f'{creator.username} đã giao cho bạn task "{task.name}" trong team "{team.name}".',
            action_type='view_task',
            action_data={'task_id': task.id}
        )
        db.session.add(notification)
        
        # Send Email notification
        assignee = User.query.get(assignee_id)
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        link = f"{frontend_url}/dashboard" # Could be more specific if task detail page exists
        start_background_email(send_task_assignment_email, assignee, task, team, link)
        
    db.session.commit()
    return jsonify(task.to_dict()), 201


# ==================== EXISTING ENDPOINTS ====================

@bp.route('/<int:team_id>/tasks', methods=['GET'])
@jwt_required()
def get_team_tasks(team_id):
    """Get all tasks for a team"""
    user_id = int(get_jwt_identity())
    
    # Check membership
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership:
        return jsonify({'error': 'Not a member of this team'}), 403
    
    tasks = Task.query.filter_by(team_id=team_id).all()
    return jsonify([t.to_dict() for t in tasks])


@bp.route('/<int:team_id>/tasks', methods=['POST'])
@jwt_required()
def create_team_task(team_id):
    """Create a task for the team"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Check membership
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership:
        return jsonify({'error': 'Not a member of this team'}), 403
    
    task = Task(
        name=data.get('name'),
        content=data.get('content'),
        user_id=user_id,
        team_id=team_id,
        assigned_to=data.get('assigned_to')
    )
    db.session.add(task)
    db.session.commit()
    
    return jsonify(task.to_dict()), 201


@bp.route('/<int:team_id>/chat', methods=['GET'])
@jwt_required()
def get_chat_messages(team_id):
    """Get chat messages for a team (with pagination)"""
    user_id = int(get_jwt_identity())
    
    # Check membership
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership:
        return jsonify({'error': 'Not a member of this team'}), 403
    
    # Get last 50 messages by default, or use 'after' param for polling
    after_id = request.args.get('after', type=int)
    
    query = ChatMessage.query.options(
        joinedload(ChatMessage.user).joinedload(User.storage)
    ).filter_by(team_id=team_id)
    if after_id:
        query = query.filter(ChatMessage.id > after_id)
    
    messages = query.order_by(ChatMessage.created_at.desc()).limit(50).all()
    messages.reverse()  # Return in chronological order
    
    return jsonify([m.to_dict() for m in messages])


@bp.route('/<int:team_id>/chat', methods=['POST'])
@jwt_required()
def send_chat_message(team_id):
    """Send a chat message"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Check membership
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership:
        return jsonify({'error': 'Not a member of this team'}), 403
    
    content = data.get('content')
    if not content or not content.strip():
        return jsonify({'error': 'Message content is required'}), 400
    
    message = ChatMessage(
        team_id=team_id,
        user_id=user_id,
        content=content.strip()
    )
    db.session.add(message)
    db.session.commit()
    
    # Broadcast SSE event for realtime chat
    sse_manager.broadcast('chat_message', message.to_dict())
    
    return jsonify(message.to_dict()), 201


@bp.route('/<int:team_id>/chat/image', methods=['POST'])
@jwt_required()
def send_chat_image(team_id):
    """Send an image in chat"""
    user_id = int(get_jwt_identity())
    
    # Check membership
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership:
        return jsonify({'error': 'Not a member of this team'}), 403
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save image
    import uuid
    from werkzeug.utils import secure_filename
    
    # Create uploads directory if not exists
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'chat_images')
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'png'
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    
    # Generate URL
    image_url = f"/static/chat_images/{filename}"
    
    message = ChatMessage(
        team_id=team_id,
        user_id=user_id,
        content=None,
        image_url=image_url
    )
    db.session.add(message)
    db.session.commit()
    
    # Broadcast SSE event for realtime chat
    sse_manager.broadcast('chat_message', message.to_dict())
    
    return jsonify(message.to_dict()), 201

@bp.route('/<int:team_id>/leave', methods=['POST'])
@jwt_required()
def leave_team(team_id):
    """Leave a team. If owner, transfer leadership to another member"""
    user_id = int(get_jwt_identity())
    
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership:
        return jsonify({'error': 'Not a member of this team'}), 404
    
    team = Team.query.get(team_id)
    
    if membership.role == 'owner':
        # Find another member to transfer ownership
        other_member = TeamMembership.query.filter(
            TeamMembership.team_id == team_id,
            TeamMembership.user_id != user_id
        ).first()
        
        if other_member:
            # Transfer ownership
            other_member.role = 'owner'
            team.owner_id = other_member.user_id
            db.session.delete(membership)
            db.session.commit()
            return jsonify({'message': 'Đã rời team. Quyền leader đã chuyển cho thành viên khác.'})
        else:
            # No other members, delete the team
            db.session.delete(team)
            db.session.commit()
            return jsonify({'message': 'Đã giải tán team vì không còn thành viên nào.'})
    
    db.session.delete(membership)
    db.session.commit()
    
    return jsonify({'message': 'Đã rời team thành công'})


@bp.route('/<int:team_id>/dissolve', methods=['POST'])
@jwt_required()
def dissolve_team(team_id):
    """Dissolve the entire team (owner only)"""
    user_id = int(get_jwt_identity())
    
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership or membership.role != 'owner':
        return jsonify({'error': 'Only owners can dissolve teams'}), 403
    
    team = Team.query.get_or_404(team_id)
    
    # Delete all related data
    TeamMembership.query.filter_by(team_id=team_id).delete()
    TeamInvite.query.filter_by(team_id=team_id).delete()
    ChatMessage.query.filter_by(team_id=team_id).delete()
    
    from app.models.member_rating import MemberRating
    MemberRating.query.filter_by(team_id=team_id).delete()
    
    db.session.delete(team)
    db.session.commit()
    
    return jsonify({'message': 'Đã giải tán team thành công'})


@bp.route('/<int:team_id>/members/<int:member_id>', methods=['DELETE'])
@jwt_required()
def remove_member(team_id, member_id):
    """Remove a member from team (owner only)"""
    user_id = int(get_jwt_identity())
    
    # Check if requester is owner
    my_membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not my_membership or my_membership.role != 'owner':
        return jsonify({'error': 'Only owners can remove members'}), 403
    
    if member_id == user_id:
        return jsonify({'error': 'Cannot remove yourself. Use dissolve or leave instead.'}), 400
    
    target = TeamMembership.query.filter_by(team_id=team_id, user_id=member_id).first()
    if not target:
        return jsonify({'error': 'Member not found'}), 404
    
    db.session.delete(target)
    db.session.commit()
    
    return jsonify({'message': 'Đã xóa thành viên khỏi team'})


# ==================== MEMBER RATING SYSTEM ====================

@bp.route('/<int:team_id>/ratings', methods=['GET'])
@jwt_required()
def get_member_ratings(team_id):
    """Get all member ratings for leaderboard"""
    user_id = int(get_jwt_identity())
    
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership:
        return jsonify({'error': 'Not a member'}), 403
    
    from app.models.member_rating import MemberRating
    from sqlalchemy import func
    
    # Get average rating for each member
    ratings = db.session.query(
        MemberRating.member_id,
        func.avg(MemberRating.score).label('avg_score'),
        func.count(MemberRating.id).label('rating_count')
    ).filter_by(team_id=team_id).group_by(MemberRating.member_id).all()
    
    # Get member info
    members = TeamMembership.query.filter_by(team_id=team_id).all()
    member_dict = {m.user_id: m.to_dict() for m in members}
    
    leaderboard = []
    for member in members:
        rating_data = next((r for r in ratings if r.member_id == member.user_id), None)
        avg_score = float(rating_data.avg_score) if rating_data else 0
        count = rating_data.rating_count if rating_data else 0
        
        # Color based on rating
        if avg_score >= 4.5:
            color = 'gold'
        elif avg_score >= 3.5:
            color = 'green'
        elif avg_score >= 2.5:
            color = 'yellow'
        elif avg_score > 0:
            color = 'red'
        else:
            color = 'gray'  # Not rated
        
        leaderboard.append({
            **member.to_dict(),
            'avg_score': round(avg_score, 1),
            'rating_count': count,
            'rank_color': color
        })
    
    # Sort by avg_score descending
    leaderboard.sort(key=lambda x: x['avg_score'], reverse=True)
    
    return jsonify(leaderboard)


@bp.route('/<int:team_id>/ratings/<int:member_id>', methods=['POST'])
@jwt_required()
def rate_member(team_id, member_id):
    """Rate a team member (owner/admin only)"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Check if requester is owner or admin
    my_membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not my_membership or my_membership.role not in ['owner', 'admin']:
        return jsonify({'error': 'Only owners and admins can rate members'}), 403
    
    if member_id == user_id:
        return jsonify({'error': 'Cannot rate yourself'}), 400
    
    score = data.get('score')
    if not score or score < 1 or score > 5:
        return jsonify({'error': 'Score must be between 1 and 5'}), 400
    
    from app.models.member_rating import MemberRating
    
    # Check if already rated
    existing = MemberRating.query.filter_by(
        team_id=team_id, member_id=member_id, rater_id=user_id
    ).first()
    
    if existing:
        existing.score = score
        existing.comment = data.get('comment')
    else:
        rating = MemberRating(
            team_id=team_id,
            member_id=member_id,
            rater_id=user_id,
            score=score,
            comment=data.get('comment')
        )
        db.session.add(rating)
    
    db.session.commit()

    # Notify member of the rating
    rater = User.query.get(user_id)
    team = Team.query.get(team_id)
    notif = Notification(
        user_id=member_id,
        type='member_rated',
        title='Bạn đã nhận được đánh giá mới',
        message=f'{rater.username} đã đánh giá bạn trong team "{team.name}".',
        action_type='view_leaderboard',
        action_data={'team_id': team_id}
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({'message': 'Đã đánh giá thành viên'}), 201


@bp.route('/<int:team_id>/members/<int:member_id>/tasks', methods=['GET'])
@jwt_required()
def get_member_tasks(team_id, member_id):
    """Get all tasks of a specific member in the team - for leaders only"""
    user_id = int(get_jwt_identity())
    
    # Check if requester is owner or admin
    membership = TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not membership or membership.role not in ['owner', 'admin']:
        return jsonify({'error': 'Only owners and admins can view member tasks'}), 403
    
    # Check if target is a member of the team
    target_membership = TeamMembership.query.filter_by(team_id=team_id, user_id=member_id).first()
    if not target_membership:
        return jsonify({'error': 'User is not a member of this team'}), 404
    
    # Get all tasks assigned to this member in this team
    tasks = Task.query.filter_by(team_id=team_id, user_id=member_id).order_by(Task.created_at.desc()).all()
    
    result = []
    for task in tasks:
        task_dict = task.to_dict()
        # Include images
        task_dict['images'] = [{'id': img.id, 'url': img.img_url} for img in task.images.all()]
        # Include subtasks if they exist (mini tasks)
        # Note: If you have a subtask model, add it here
        result.append(task_dict)
    
    return jsonify(result)

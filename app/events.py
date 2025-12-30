"""
Event-driven architecture using blinker signals.
Events allow loose coupling between components.
"""
from blinker import signal

# Task events
task_created = signal('task-created')
task_updated = signal('task-updated')
task_completed = signal('task-completed')
task_deleted = signal('task-deleted')
task_deadline_approaching = signal('task-deadline-approaching')

# Workspace events
workspace_created = signal('workspace-created')
workspace_completed = signal('workspace-completed')

# User events
user_registered = signal('user-registered')
user_verified = signal('user-verified')


# Event handlers
@task_completed.connect
def on_task_completed(sender, **kwargs):
    """Handle task completion - calculate income, send notification"""
    task = sender
    
    # Create income record if task has price
    if task.price and task.price > 0:
        from app.extensions import db
        from app.models.income import TotalIncome, OneIncome
        
        total_income = TotalIncome(
            total=task.price,
            from_source=task.name,
            noted=f"Task #{task.id} completed"
        )
        db.session.add(total_income)
        db.session.flush()
        
        one_income = OneIncome(task_id=task.id, total_income_id=total_income.id)
        db.session.add(one_income)
        db.session.commit()
    
    # Send notification to client if email exists
    if task.client_mail:
        try:
            from app.services.mail_service import send_notification_email
            from app.models.user import User
            
            user = User.query.get(task.user_id)
            # Note: In production, you'd send to client, not user
            # This is just a placeholder
            print(f"Task {task.name} completed - notify {task.client_mail}")
        except Exception as e:
            print(f"Failed to send completion notification: {e}")


@task_created.connect
def on_task_created(sender, **kwargs):
    """Handle task creation - log, etc."""
    task = sender
    print(f"New task created: {task.name} (ID: {task.id})")


@user_registered.connect
def on_user_registered(sender, **kwargs):
    """Handle new user registration"""
    user = sender
    print(f"New user registered: {user.email}")

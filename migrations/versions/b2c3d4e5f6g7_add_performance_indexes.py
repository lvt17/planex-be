"""add performance indexes

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-04 05:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Speed up task queries
    op.create_index('idx_task_user_deadline', 'task', ['user_id', 'deadline'])
    op.create_index('idx_task_project', 'task', ['project_id'])
    
    # Speed up subtask queries
    op.create_index('idx_subtasks_task', 'subtasks', ['task_id'])
    
    # Speed up team queries
    op.create_index('idx_team_memberships_team', 'team_memberships', ['team_id'])
    
    # Speed up chat queries (with DESC sorting for latest messages)
    op.create_index('idx_chat_messages_team_created', 'chat_messages', ['team_id', sa.text('created_at DESC')])


def downgrade():
    op.drop_index('idx_chat_messages_team_created', table_name='chat_messages')
    op.drop_index('idx_team_memberships_team', table_name='team_memberships')
    op.drop_index('idx_subtasks_task', table_name='subtasks')
    op.drop_index('idx_task_project', table_name='task')
    op.drop_index('idx_task_user_deadline', table_name='task')

"""Add notification deduplication and read tracking

Revision ID: notification_updates_001
Revises: 
Create Date: 2025-12-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'notification_updates_001'
down_revision = 'fcm_token_001'  # Latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to notification_logs table
    op.add_column('notification_logs', sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('notification_logs', sa.Column('fcm_message_id', sa.String(length=500), nullable=True))
    op.add_column('notification_logs', sa.Column('notification_hash', sa.String(length=100), nullable=True))
    
    # Add index for faster queries
    op.create_index('idx_notification_hash', 'notification_logs', ['notification_hash'])
    op.create_index('idx_created_at', 'notification_logs', ['created_at'])
    op.create_index('idx_is_read', 'notification_logs', ['is_read'])


def downgrade() -> None:
    # Remove indexes
    op.drop_index('idx_is_read', table_name='notification_logs')
    op.drop_index('idx_created_at', table_name='notification_logs')
    op.drop_index('idx_notification_hash', table_name='notification_logs')
    
    # Remove columns
    op.drop_column('notification_logs', 'notification_hash')
    op.drop_column('notification_logs', 'fcm_message_id')
    op.drop_column('notification_logs', 'is_read')

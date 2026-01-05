"""add fcm token fields

Revision ID: fcm_token_001
Revises: 218be56aa5e5
Create Date: 2025-12-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fcm_token_001'
down_revision: Union[str, None] = '218be56aa5e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add FCM token fields to users table."""
    op.add_column('users', sa.Column('fcm_token', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('fcm_token_updated_at', sa.TIMESTAMP(), nullable=True))


def downgrade() -> None:
    """Remove FCM token fields from users table."""
    op.drop_column('users', 'fcm_token_updated_at')
    op.drop_column('users', 'fcm_token')

"""add notification project type filters

Добавляет колонки notify_individual, notify_template,
notify_duplicate_info, notify_revision_info в notification_settings.

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g7h8i9j0k1l2'
down_revision: Union[str, None] = 'f6g7h8i9j0k1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('notification_settings',
                  sa.Column('notify_individual', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('notification_settings',
                  sa.Column('notify_template', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('notification_settings',
                  sa.Column('notify_duplicate_info', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('notification_settings',
                  sa.Column('notify_revision_info', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('notification_settings', 'notify_revision_info')
    op.drop_column('notification_settings', 'notify_duplicate_info')
    op.drop_column('notification_settings', 'notify_template')
    op.drop_column('notification_settings', 'notify_individual')

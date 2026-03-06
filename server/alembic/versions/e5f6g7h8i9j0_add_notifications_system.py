"""add notifications system

Добавляет поля Telegram-привязки в таблицу employees
и создаёт таблицу notification_settings.

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-03-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6g7h8i9j0'
down_revision: Union[str, None] = 'd4e5f6g7h8i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Добавляем поля Telegram в employees
    op.add_column('employees', sa.Column('telegram_user_id', sa.BigInteger(), nullable=True))
    op.add_column('employees', sa.Column('telegram_link_token', sa.String(32), nullable=True))
    op.add_column('employees', sa.Column('telegram_link_token_expires', sa.DateTime(), nullable=True))
    op.create_index('ix_employees_telegram_link_token', 'employees', ['telegram_link_token'], unique=False)

    # 2. Создаём таблицу notification_settings
    op.create_table(
        'notification_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('telegram_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notify_crm_stage', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notify_assigned', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notify_deadline', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notify_payment', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notify_supervision', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id'),
    )
    op.create_index(op.f('ix_notification_settings_id'), 'notification_settings', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notification_settings_id'), table_name='notification_settings')
    op.drop_table('notification_settings')
    op.drop_index('ix_employees_telegram_link_token', table_name='employees')
    op.drop_column('employees', 'telegram_link_token_expires')
    op.drop_column('employees', 'telegram_link_token')
    op.drop_column('employees', 'telegram_user_id')

"""add employee payment fields

Добавляет платёжные реквизиты в таблицу employees:
payment_type, payment_phone, payment_account,
payment_bank_name, payment_bik, payment_corr_account.

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-03-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h8i9j0k1l2m3'
down_revision: Union[str, None] = 'g7h8i9j0k1l2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('employees', sa.Column('payment_type', sa.String(), nullable=True))
    op.add_column('employees', sa.Column('payment_phone', sa.String(), nullable=True))
    op.add_column('employees', sa.Column('payment_account', sa.String(), nullable=True))
    op.add_column('employees', sa.Column('payment_bank_name', sa.String(), nullable=True))
    op.add_column('employees', sa.Column('payment_bik', sa.String(), nullable=True))
    op.add_column('employees', sa.Column('payment_corr_account', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('employees', 'payment_corr_account')
    op.drop_column('employees', 'payment_bik')
    op.drop_column('employees', 'payment_bank_name')
    op.drop_column('employees', 'payment_account')
    op.drop_column('employees', 'payment_phone')
    op.drop_column('employees', 'payment_type')

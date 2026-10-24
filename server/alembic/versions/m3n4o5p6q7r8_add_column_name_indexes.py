"""add index on column_name for crm_cards and supervision_cards

Ускоряет фильтрацию канбан-колонок и дашборда.

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-04-10

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'm3n4o5p6q7r8'
down_revision: Union[str, None] = 'l2m3n4o5p6q7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_crm_cards_column_name', 'crm_cards', ['column_name'])
    op.create_index('ix_supervision_cards_column_name', 'supervision_cards', ['column_name'])


def downgrade() -> None:
    op.drop_index('ix_crm_cards_column_name', table_name='crm_cards')
    op.drop_index('ix_supervision_cards_column_name', table_name='supervision_cards')

"""add workflow substage group

Добавляет поле current_substage_group в stage_workflow_state
для отслеживания текущей substage_group (кругов правок).

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6g7h8i9j0k1'
down_revision: Union[str, None] = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('stage_workflow_state',
                  sa.Column('current_substage_group', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('stage_workflow_state', 'current_substage_group')

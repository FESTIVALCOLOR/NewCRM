"""add revision_history to stage_workflow_state

П5: Хранить историю всех ревизий (не перезатирать revision_file_path).
Новое поле revision_history — JSON массив [{num, file_path, reason, date}].

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-03-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'l2m3n4o5p6q7'
down_revision: Union[str, None] = 'k1l2m3n4o5p6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('stage_workflow_state',
                  sa.Column('revision_history', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('stage_workflow_state', 'revision_history')

"""add project_subtype to rates table

Позволяет хранить тарифы отдельно для каждого подтипа проекта
(Полный, Эскизный, Планировочный).

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-05-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'n4o5p6q7r8s9'
down_revision: Union[str, None] = 'm3n4o5p6q7r8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('rates', sa.Column('project_subtype', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('rates', 'project_subtype')

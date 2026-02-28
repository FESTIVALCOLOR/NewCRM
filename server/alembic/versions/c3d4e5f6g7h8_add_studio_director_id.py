"""add studio_director_id to supervision_cards

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f7g8
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f7g8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('supervision_cards', sa.Column('studio_director_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_supervision_cards_studio_director',
        'supervision_cards', 'employees',
        ['studio_director_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_supervision_cards_studio_director', 'supervision_cards', type_='foreignkey')
    op.drop_column('supervision_cards', 'studio_director_id')

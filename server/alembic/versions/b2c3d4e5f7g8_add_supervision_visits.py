"""add supervision_visits table

Revision ID: b2c3d4e5f7g8
Revises: a1b2c3d4e5f6
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f7g8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'supervision_visits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supervision_card_id', sa.Integer(), nullable=False),
        sa.Column('stage_code', sa.String(30), nullable=False),
        sa.Column('stage_name', sa.String(255), nullable=False),
        sa.Column('visit_date', sa.String(), nullable=False),
        sa.Column('executor_name', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['supervision_card_id'], ['supervision_cards.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_supervision_visits_card_id', 'supervision_visits', ['supervision_card_id'])


def downgrade() -> None:
    op.drop_index('ix_supervision_visits_card_id', table_name='supervision_visits')
    op.drop_table('supervision_visits')

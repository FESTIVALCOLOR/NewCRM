"""add unexpected_expenses to supervision_budget_extra

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-10-26 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "s9t0u1v2w3x4"
down_revision = "r8s9t0u1v2w3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "supervision_budget_extra",
        sa.Column("unexpected_expenses", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("supervision_budget_extra", "unexpected_expenses")

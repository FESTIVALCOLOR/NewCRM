"""add visit_id to payments

Revision ID: q7r8s9t0u1v2
Revises: p6q7r8s9t0u1
Create Date: 2026-05-20 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "q7r8s9t0u1v2"
down_revision = "p6q7r8s9t0u1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "payments",
        sa.Column(
            "visit_id",
            sa.Integer(),
            sa.ForeignKey("supervision_visits.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_payments_visit_id", "payments", ["visit_id"])


def downgrade():
    op.drop_index("ix_payments_visit_id", table_name="payments")
    op.drop_column("payments", "visit_id")

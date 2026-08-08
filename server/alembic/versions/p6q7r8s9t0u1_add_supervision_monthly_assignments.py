"""add supervision_monthly_assignments table

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2026-05-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "p6q7r8s9t0u1"
down_revision = "o5p6q7r8s9t0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supervision_monthly_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supervision_card_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("employee_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("monthly_amount", sa.Float(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("start_date", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supervision_card_id"], ["supervision_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supervision_monthly_assignments_id", "supervision_monthly_assignments", ["id"])
    op.create_index("ix_supervision_monthly_assignments_supervision_card_id", "supervision_monthly_assignments", ["supervision_card_id"])


def downgrade() -> None:
    op.drop_index("ix_supervision_monthly_assignments_supervision_card_id", table_name="supervision_monthly_assignments")
    op.drop_index("ix_supervision_monthly_assignments_id", table_name="supervision_monthly_assignments")
    op.drop_table("supervision_monthly_assignments")

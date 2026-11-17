"""add supervision client payments

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-10-25 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "r8s9t0u1v2w3"
down_revision = "q7r8s9t0u1v2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "supervision_client_payments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("supervision_card_id", sa.Integer(), sa.ForeignKey("supervision_cards.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("payment_month", sa.String(7), nullable=False),
        sa.Column("payment_date", sa.String(10), nullable=True),
        sa.Column("receipt_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "supervision_payment_notif_settings",
        sa.Column("supervision_card_id", sa.Integer(), sa.ForeignKey("supervision_cards.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("notification_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notification_day", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade():
    op.drop_table("supervision_payment_notif_settings")
    op.drop_table("supervision_client_payments")

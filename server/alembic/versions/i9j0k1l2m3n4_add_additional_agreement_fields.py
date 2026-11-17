"""add additional agreement fields

Добавляет поля для доп. соглашений в таблицу contracts:
additional_agreement_link, additional_agreement_yandex_path,
additional_agreement_file_name и их signed-варианты.

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-03-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i9j0k1l2m3n4'
down_revision: Union[str, None] = 'h8i9j0k1l2m3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('contracts', sa.Column('additional_agreement_link', sa.String(), nullable=True))
    op.add_column('contracts', sa.Column('additional_agreement_yandex_path', sa.String(), nullable=True))
    op.add_column('contracts', sa.Column('additional_agreement_file_name', sa.String(), nullable=True))
    op.add_column('contracts', sa.Column('additional_agreement_signed_link', sa.String(), nullable=True))
    op.add_column('contracts', sa.Column('additional_agreement_signed_yandex_path', sa.String(), nullable=True))
    op.add_column('contracts', sa.Column('additional_agreement_signed_file_name', sa.String(), nullable=True))
    op.add_column('contracts', sa.Column('measurement_folder_public_link', sa.String(), nullable=True))
    op.add_column('contracts', sa.Column('photo_folder_public_link', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('contracts', 'photo_folder_public_link')
    op.drop_column('contracts', 'measurement_folder_public_link')
    op.drop_column('contracts', 'additional_agreement_signed_file_name')
    op.drop_column('contracts', 'additional_agreement_signed_yandex_path')
    op.drop_column('contracts', 'additional_agreement_signed_link')
    op.drop_column('contracts', 'additional_agreement_file_name')
    op.drop_column('contracts', 'additional_agreement_yandex_path')
    op.drop_column('contracts', 'additional_agreement_link')

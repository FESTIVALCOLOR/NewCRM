"""add agent_type to norm_days_templates

Revision ID: a1b2c3d4e5f6
Revises: 9b43f7eaae02
Create Date: 2026-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9b43f7eaae02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем колонку agent_type с дефолтным значением
    op.add_column('norm_days_templates',
                  sa.Column('agent_type', sa.String(), server_default='Все агенты', nullable=True))

    # Обновляем существующие строки
    op.execute("UPDATE norm_days_templates SET agent_type = 'Все агенты' WHERE agent_type IS NULL")

    # Удаляем старый unique constraint
    op.drop_constraint('uq_norm_template', 'norm_days_templates', type_='unique')

    # Создаём новый unique constraint включая agent_type
    op.create_unique_constraint(
        'uq_norm_template',
        'norm_days_templates',
        ['project_type', 'project_subtype', 'stage_code', 'agent_type']
    )


def downgrade() -> None:
    # Удаляем новый constraint
    op.drop_constraint('uq_norm_template', 'norm_days_templates', type_='unique')

    # Восстанавливаем старый
    op.create_unique_constraint(
        'uq_norm_template',
        'norm_days_templates',
        ['project_type', 'project_subtype', 'stage_code']
    )

    # Удаляем колонку
    op.drop_column('norm_days_templates', 'agent_type')

"""add employee_name to payments and salaries

Денормализация: сохраняем имя сотрудника прямо в платеже,
чтобы не терять при удалении сотрудника из системы.

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-03-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Добавляем колонку employee_name
    op.add_column('payments', sa.Column('employee_name', sa.String(), nullable=True))
    op.add_column('salaries', sa.Column('employee_name', sa.String(), nullable=True))

    # 2. Заполняем из таблицы employees через UPDATE ... FROM
    op.execute("""
        UPDATE payments
        SET employee_name = e.full_name
        FROM employees e
        WHERE payments.employee_id = e.id
          AND payments.employee_name IS NULL
    """)
    op.execute("""
        UPDATE salaries
        SET employee_name = e.full_name
        FROM employees e
        WHERE salaries.employee_id = e.id
          AND salaries.employee_name IS NULL
    """)


def downgrade() -> None:
    op.drop_column('salaries', 'employee_name')
    op.drop_column('payments', 'employee_name')

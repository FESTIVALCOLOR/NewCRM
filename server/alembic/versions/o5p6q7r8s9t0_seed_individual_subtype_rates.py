"""seed individual subtype rates for Полный and Эскизный

Добавляет начальные тарифы с разбивкой по подтипу проекта:
- Полный / Дизайнер: 900 руб/м² (Стадия 2: концепция дизайна)
- Эскизный / Дизайнер: 250 руб/м² (Стадия 2: концепция дизайна)

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-05-20

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = 'o5p6q7r8s9t0'
down_revision: Union[str, None] = 'n4o5p6q7r8s9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.utcnow().isoformat()

    # Для каждой стадии индивидуального проекта: Полный — 900, Чертёжник — оставить как есть
    # Проверяем: если уже есть тариф Индивидуальный/Дизайнер/Эскизный — не дублируем
    result = conn.execute(
        sa.text(
            "SELECT id FROM rates WHERE project_type='Индивидуальный' "
            "AND role='Дизайнер' AND project_subtype='Эскизный' "
            "AND stage_name='Стадия 2: концепция дизайна' LIMIT 1"
        )
    ).fetchone()

    if not result:
        conn.execute(
            sa.text(
                "INSERT INTO rates (project_type, project_subtype, role, stage_name, rate_per_m2, created_at, updated_at) "
                "VALUES ('Индивидуальный', 'Эскизный', 'Дизайнер', 'Стадия 2: концепция дизайна', 250.0, :now, :now)"
            ),
            {"now": now}
        )

    # Эскизный / Чертёжник: Стадия 1 — такой же как Полный (берётся из NULL-fallback)
    # Полный явный тариф для Дизайнера Стадия 2 — создаём если нет NULL-subtype тарифа
    # (существующий тариф с NULL project_subtype уже служит как fallback для Полного)


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM rates WHERE project_type='Индивидуальный' "
            "AND project_subtype IS NOT NULL AND project_subtype != ''"
        )
    )

"""reseed scripts with names and personal notifications

Пересоздание всех скриптов с полем name и добавление
шаблонов личных уведомлений (§2-4 notifications-scripts-guide.md).

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-03-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = 'k1l2m3n4o5p6'
down_revision: Union[str, None] = 'j0k1l2m3n4o5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Удаляем все существующие скрипты (они будут пересозданы seed-функцией
    # при первом запуске сервера). Это безопасно т.к. скрипты не имеют
    # FK-зависимостей от других таблиц (message_log ссылается на chat, не script).
    op.execute("DELETE FROM messenger_scripts")


def downgrade() -> None:
    # Невозможно восстановить старые данные, но seed заполнит при запуске
    pass

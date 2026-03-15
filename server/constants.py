"""Константы позиций, ролей и статусов.

Единый источник истины для всех строковых литералов,
используемых в фильтрации, проверках прав и уведомлениях.
"""

# ── Позиции сотрудников ──────────────────────────────────────────────
POSITION_STUDIO_DIRECTOR = 'Руководитель студии'
POSITION_SENIOR_MANAGER = 'Старший менеджер проектов'
POSITION_SDP = 'СДП'
POSITION_GAP = 'ГАП'
POSITION_DAN = 'ДАН'
POSITION_MANAGER = 'Менеджер'
POSITION_MEASURER = 'Замерщик'

# Альтернативные наименования (legacy/полные)
POSITION_DAN_FULL = 'Дизайнер авторского надзора'
DAN_ROLES = [POSITION_DAN, POSITION_DAN_FULL]

# Группы позиций
ADMIN_POSITIONS = [POSITION_STUDIO_DIRECTOR, POSITION_SENIOR_MANAGER, POSITION_SDP, POSITION_GAP]
EXEC_POSITIONS = [POSITION_MANAGER, POSITION_DAN, POSITION_MEASURER]
SUPERUSER_POSITIONS = {POSITION_STUDIO_DIRECTOR}
REVIEWER_ROLES = [POSITION_SDP, POSITION_MANAGER, POSITION_GAP]

# ── Статусы договоров ────────────────────────────────────────────────
STATUS_COMPLETED = 'СДАН'
STATUS_TERMINATED = 'РАСТОРГНУТ'
STATUS_SUPERVISION = 'АВТОРСКИЙ НАДЗОР'

ARCHIVE_STATUSES = [STATUS_COMPLETED, STATUS_TERMINATED, STATUS_SUPERVISION]
INACTIVE_STATUSES = {STATUS_COMPLETED, STATUS_SUPERVISION, STATUS_TERMINATED}

# ── Системные роли ───────────────────────────────────────────────────
ROLE_ADMIN = 'admin'
ROLE_DIRECTOR = 'director'
SUPERUSER_ROLES = {ROLE_ADMIN, ROLE_DIRECTOR, POSITION_STUDIO_DIRECTOR}

# ── Роли для свободного перемещения карточек ──────────────────────────
FREE_MOVE_ROLES = [ROLE_ADMIN, ROLE_DIRECTOR, POSITION_STUDIO_DIRECTOR, POSITION_SENIOR_MANAGER]

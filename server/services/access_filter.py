"""
Фильтрация данных аналитики по правам доступа.

Уровни доступа:
- full:      Руководитель студии — видит всех
- team:      Старший менеджер — видит сотрудников своих проектов
- executors: СДП/ГАП/Менеджер — видит своих исполнителей + себя
- self:      Исполнители/Замерщики/ДАН — видит только себя
"""
import logging
from typing import Optional, Set

from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import (
    Employee, CRMCard, Contract, StageExecutor,
    SupervisionCard,
)
from constants import (
    POSITION_STUDIO_DIRECTOR, POSITION_SENIOR_MANAGER,
    POSITION_SDP, POSITION_GAP, POSITION_MANAGER,
    POSITION_DAN, POSITION_DAN_FULL, POSITION_MEASURER,
    ROLE_ADMIN, ROLE_DIRECTOR,
)

logger = logging.getLogger(__name__)


def get_access_level(employee: Employee) -> str:
    """Определяет уровень доступа пользователя к аналитике."""
    position = employee.position or ''
    role = employee.role or ''

    if position == POSITION_STUDIO_DIRECTOR or role in (ROLE_ADMIN, ROLE_DIRECTOR):
        return 'full'
    elif position == POSITION_SENIOR_MANAGER:
        return 'team'
    elif position in (POSITION_SDP, POSITION_GAP, POSITION_MANAGER):
        return 'executors'
    else:
        return 'self'


def get_visible_employee_ids(db: Session, current_user: Employee,
                             project_type: str) -> Optional[Set[int]]:
    """
    Возвращает набор ID сотрудников, видимых текущему пользователю.
    None = без ограничений (полный доступ).

    Args:
        project_type: 'individual' / 'template' / 'supervision'
    """
    access_level = get_access_level(current_user)

    if access_level == 'full':
        return None  # Без фильтра

    if access_level == 'self':
        return {current_user.id}

    visible = {current_user.id}

    if project_type == 'supervision':
        _add_supervision_team(db, current_user, access_level, visible)
    else:
        project_type_db = 'Индивидуальный' if project_type == 'individual' else 'Шаблонный'
        _add_crm_team(db, current_user, access_level, project_type_db, visible)

    return visible


def _add_crm_team(db: Session, current_user: Employee,
                  access_level: str, project_type_db: str,
                  visible: Set[int]):
    """Добавляет видимых сотрудников из CRM-проектов."""
    position = current_user.position or ''

    if access_level == 'team':
        # Старший менеджер видит всех на своих проектах
        cards = db.query(CRMCard).join(
            Contract, CRMCard.contract_id == Contract.id
        ).filter(
            Contract.project_type == project_type_db,
            CRMCard.senior_manager_id == current_user.id,
        ).all()

        for card in cards:
            if card.sdp_id:
                visible.add(card.sdp_id)
            if card.gap_id:
                visible.add(card.gap_id)
            if card.manager_id:
                visible.add(card.manager_id)
            if card.surveyor_id:
                visible.add(card.surveyor_id)
            for executor in card.stage_executors:
                if executor.executor_id:
                    visible.add(executor.executor_id)

    elif access_level == 'executors':
        # СДП/ГАП/Менеджер видят только исполнителей своих проектов
        if position == POSITION_SDP:
            cards = db.query(CRMCard).join(
                Contract, CRMCard.contract_id == Contract.id
            ).filter(
                Contract.project_type == project_type_db,
                CRMCard.sdp_id == current_user.id,
            ).all()
        elif position == POSITION_GAP:
            cards = db.query(CRMCard).join(
                Contract, CRMCard.contract_id == Contract.id
            ).filter(
                Contract.project_type == project_type_db,
                CRMCard.gap_id == current_user.id,
            ).all()
        elif position == POSITION_MANAGER:
            cards = db.query(CRMCard).join(
                Contract, CRMCard.contract_id == Contract.id
            ).filter(
                Contract.project_type == project_type_db,
                CRMCard.manager_id == current_user.id,
            ).all()
        else:
            cards = []

        for card in cards:
            for executor in card.stage_executors:
                if executor.executor_id:
                    visible.add(executor.executor_id)


def _add_supervision_team(db: Session, current_user: Employee,
                          access_level: str, visible: Set[int]):
    """Добавляет видимых сотрудников из карточек надзора."""
    if access_level == 'team':
        cards = db.query(SupervisionCard).filter(
            SupervisionCard.senior_manager_id == current_user.id,
        ).all()
        for card in cards:
            if card.dan_id:
                visible.add(card.dan_id)

    # executors и self — уже добавлен current_user.id


# ── Маппинг ролей к типам проектов ──────────────────────────────────

ROLES_BY_PROJECT_TYPE = {
    'individual': [
        ('senior_manager', POSITION_SENIOR_MANAGER),
        ('sdp', POSITION_SDP),
        ('gap', POSITION_GAP),
        ('draftsman', 'Чертёжник'),
        ('designer', 'Дизайнер'),
        ('measurer', POSITION_MEASURER),
    ],
    'template': [
        ('senior_manager', POSITION_SENIOR_MANAGER),
        ('manager', POSITION_MANAGER),
        ('gap', POSITION_GAP),
        ('draftsman', 'Чертёжник'),
        ('designer', 'Дизайнер'),
    ],
    'supervision': [
        ('senior_manager', POSITION_SENIOR_MANAGER),
        ('dan', POSITION_DAN),
    ],
}

# Обратный маппинг: код роли → position
ROLE_CODE_TO_POSITION = {
    'senior_manager': POSITION_SENIOR_MANAGER,
    'manager': POSITION_MANAGER,
    'sdp': POSITION_SDP,
    'gap': POSITION_GAP,
    'draftsman': 'Чертёжник',
    'designer': 'Дизайнер',
    'measurer': POSITION_MEASURER,
    'dan': POSITION_DAN,
}


def get_available_roles(project_type: str) -> list:
    """Возвращает список кодов ролей, доступных для данного типа проекта."""
    return [code for code, _ in ROLES_BY_PROJECT_TYPE.get(project_type, [])]


def get_employees_by_role(db: Session, role_code: str, project_type: str,
                          visible_ids: Optional[Set[int]] = None) -> list:
    """
    Возвращает список сотрудников по роли, участвующих в проектах данного типа.
    """
    position = ROLE_CODE_TO_POSITION.get(role_code)
    if not position:
        return []

    # Для ДАН ищем обе позиции
    if role_code == 'dan':
        position_filter = Employee.position.in_([POSITION_DAN, POSITION_DAN_FULL])
    else:
        position_filter = Employee.position == position

    query = db.query(Employee).filter(
        position_filter,
        Employee.status == 'активный',
    )

    if visible_ids is not None:
        query = query.filter(Employee.id.in_(visible_ids))

    return query.all()

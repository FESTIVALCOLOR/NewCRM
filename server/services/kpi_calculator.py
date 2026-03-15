"""
Калькулятор KPI сотрудников.

Считает KPI отдельно по каждому типу проекта (individual / template / supervision).
Формулы:
  CRM:     KPI = W1*Kсрок + W2*Kкачество + W3*Kскорость + W4*Knps
  Надзор:  KPI = W1*Kзакупки + W2*Kдефекты + W3*Kвизиты + W4*Knps
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Any

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract, cast, DateTime

from database import (
    Employee, CRMCard, Contract, StageExecutor, StageWorkflowState,
    ProjectTimelineEntry, SupervisionCard, SupervisionTimelineEntry,
    SupervisionVisit, Payment, ClientSurvey,
)
from constants import (
    POSITION_STUDIO_DIRECTOR, POSITION_SENIOR_MANAGER,
    POSITION_SDP, POSITION_GAP, POSITION_DAN, POSITION_DAN_FULL,
    POSITION_MANAGER, POSITION_MEASURER, POSITION_DESIGNER, POSITION_DRAFTSMAN,
    STATUS_COMPLETED, STATUS_TERMINATED,
)
from services.date_helpers import networkdays

logger = logging.getLogger(__name__)

# ── Маппинг типов проектов ──────────────────────────────────────────
PROJECT_TYPE_MAP = {
    'individual': 'Индивидуальный',
    'template': 'Шаблонный',
    'supervision': 'supervision',  # особый тип — не через contracts.project_type
}

# ── Веса компонентов KPI по ролям (CRM-проекты) ─────────────────────
CRM_KPI_WEIGHTS = {
    POSITION_SENIOR_MANAGER: {'deadline': 0.30, 'quality': 0.20, 'speed': 0.15, 'nps': 0.35},
    POSITION_MANAGER:        {'deadline': 0.30, 'quality': 0.20, 'speed': 0.20, 'nps': 0.30},
    POSITION_SDP:            {'deadline': 0.25, 'quality': 0.35, 'speed': 0.25, 'nps': 0.15},
    POSITION_GAP:            {'deadline': 0.25, 'quality': 0.35, 'speed': 0.25, 'nps': 0.15},
    POSITION_MEASURER:       {'deadline': 0.35, 'quality': 0.15, 'speed': 0.35, 'nps': 0.15},
    POSITION_DESIGNER:       {'deadline': 0.25, 'quality': 0.35, 'speed': 0.25, 'nps': 0.15},
    POSITION_DRAFTSMAN:      {'deadline': 0.30, 'quality': 0.35, 'speed': 0.25, 'nps': 0.10},
}
# Fallback для неизвестных позиций
CRM_KPI_WEIGHTS_DEFAULT = {'deadline': 0.30, 'quality': 0.35, 'speed': 0.25, 'nps': 0.10}

# ── Веса компонентов KPI (авторский надзор) ──────────────────────────
SUPERVISION_KPI_WEIGHTS = {
    POSITION_SENIOR_MANAGER: {'procurement': 0.30, 'defects': 0.20, 'visits': 0.15, 'nps': 0.35},
    POSITION_DAN:            {'procurement': 0.30, 'defects': 0.30, 'visits': 0.20, 'nps': 0.20},
    POSITION_DAN_FULL:       {'procurement': 0.30, 'defects': 0.30, 'visits': 0.20, 'nps': 0.20},
}
SUPERVISION_KPI_WEIGHTS_DEFAULT = {'procurement': 0.30, 'defects': 0.30, 'visits': 0.20, 'nps': 0.20}

# ── Рекомендуемая нагрузка ───────────────────────────────────────────
RECOMMENDED_MAX_LOAD = {
    POSITION_SENIOR_MANAGER: 15,
    POSITION_MANAGER: 8,
    POSITION_SDP: 10,
    POSITION_GAP: 8,
    POSITION_MEASURER: 3,
    POSITION_DAN: 6,
    POSITION_DAN_FULL: 6,
    POSITION_DESIGNER: 4,
}
RECOMMENDED_MAX_LOAD_DEFAULT = 5  # Чертёжники и прочие


def _parse_date(val) -> Optional[date]:
    """Парсит строку даты или datetime → date."""
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S'):
            try:
                return datetime.strptime(val.strip()[:10], '%Y-%m-%d').date()
            except (ValueError, IndexError):
                continue
    return None


def _get_period_range(year: int, quarter: Optional[int] = None,
                      month: Optional[int] = None):
    """Возвращает (start_date, end_date) для заданного периода."""
    if month:
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
    elif quarter:
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3
        start = date(year, start_month, 1)
        if end_month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, end_month + 1, 1) - timedelta(days=1)
    else:
        start = date(year, 1, 1)
        end = date(year, 12, 31)
    return start, end


# ═══════════════════════════════════════════════════════════════════════
# РАСЧЁТ KPI ДЛЯ CRM-ПРОЕКТОВ (индивидуальные / шаблонные)
# ═══════════════════════════════════════════════════════════════════════

def _get_completed_stages(db: Session, employee_id: int, project_type_db: str,
                          period_start: date, period_end: date) -> List:
    """Возвращает завершённые StageExecutor записи сотрудника по типу проекта."""
    return db.query(StageExecutor).join(
        CRMCard, StageExecutor.crm_card_id == CRMCard.id
    ).join(
        Contract, CRMCard.contract_id == Contract.id
    ).filter(
        Contract.project_type == project_type_db,
        StageExecutor.executor_id == employee_id,
        StageExecutor.completed == True,
        StageExecutor.completed_date.isnot(None),
        StageExecutor.completed_date >= datetime.combine(period_start, datetime.min.time()),
        StageExecutor.completed_date <= datetime.combine(period_end, datetime.max.time()),
    ).all()


def calc_k_deadline(db: Session, employee_id: int, project_type_db: str,
                    period_start: date, period_end: date) -> float:
    """Kсрок — процент стадий, завершённых до дедлайна."""
    stages = _get_completed_stages(db, employee_id, project_type_db, period_start, period_end)
    stages_with_deadline = [s for s in stages if s.deadline and _parse_date(s.deadline)]
    if not stages_with_deadline:
        return 100.0

    on_time = 0
    for s in stages_with_deadline:
        dl = _parse_date(s.deadline)
        cd = _parse_date(s.completed_date)
        if cd and dl and cd <= dl:
            on_time += 1

    return (on_time / len(stages_with_deadline)) * 100


def calc_k_quality(db: Session, employee_id: int, project_type_db: str,
                   period_start: date, period_end: date) -> float:
    """Kкачество — процент стадий, принятых без правок."""
    stages = _get_completed_stages(db, employee_id, project_type_db, period_start, period_end)
    if not stages:
        return 100.0

    no_revisions = 0
    for s in stages:
        wf = db.query(StageWorkflowState).filter(
            StageWorkflowState.crm_card_id == s.crm_card_id,
            StageWorkflowState.stage_name == s.stage_name,
        ).first()
        if not wf or (wf.revision_count or 0) == 0:
            no_revisions += 1

    return (no_revisions / len(stages)) * 100


def calc_k_speed(db: Session, employee_id: int, project_type_db: str,
                 period_start: date, period_end: date) -> float:
    """Kскорость — соотношение нормо-дней к фактическим дням."""
    stages = _get_completed_stages(db, employee_id, project_type_db, period_start, period_end)
    if not stages:
        return 100.0

    speed_scores = []
    for s in stages:
        ad = _parse_date(s.assigned_date)
        cd = _parse_date(s.completed_date)
        if not ad or not cd:
            continue

        actual_days = networkdays(ad, cd)
        if actual_days <= 0:
            actual_days = 1

        # Пытаемся найти нормо-дни из таймлайна
        crm_card = s.crm_card
        norm_days = None
        if crm_card and crm_card.contract_id:
            timeline = db.query(ProjectTimelineEntry).filter(
                ProjectTimelineEntry.contract_id == crm_card.contract_id,
            ).first()
            if timeline and timeline.norm_days:
                norm_days = timeline.custom_norm_days or timeline.norm_days

        if not norm_days or norm_days <= 0:
            norm_days = actual_days  # Если нет нормы — считаем как 100%

        ratio = min(norm_days / actual_days, 1.2)
        speed_scores.append(ratio * 100)

    return sum(speed_scores) / len(speed_scores) if speed_scores else 100.0


def calc_k_nps_crm(db: Session, employee_id: int, project_type_db: str,
                   period_start: date, period_end: date) -> Optional[float]:
    """Knps — средний NPS по проектам сотрудника данного типа."""
    pt_code = 'individual' if project_type_db == 'Индивидуальный' else 'template'

    # Опросы по карточкам, где сотрудник назначен
    card_filters = or_(
        CRMCard.senior_manager_id == employee_id,
        CRMCard.sdp_id == employee_id,
        CRMCard.gap_id == employee_id,
        CRMCard.manager_id == employee_id,
        CRMCard.surveyor_id == employee_id,
    )

    surveys_direct = db.query(ClientSurvey).join(
        Contract, ClientSurvey.contract_id == Contract.id
    ).join(
        CRMCard, CRMCard.contract_id == Contract.id
    ).filter(
        ClientSurvey.project_type == pt_code,
        ClientSurvey.status == 'completed',
        ClientSurvey.nps_score.isnot(None),
        card_filters,
    ).all()

    # Опросы через stage_executors
    surveys_executor = db.query(ClientSurvey).join(
        Contract, ClientSurvey.contract_id == Contract.id
    ).join(
        CRMCard, CRMCard.contract_id == Contract.id
    ).join(
        StageExecutor, StageExecutor.crm_card_id == CRMCard.id
    ).filter(
        ClientSurvey.project_type == pt_code,
        ClientSurvey.status == 'completed',
        ClientSurvey.nps_score.isnot(None),
        StageExecutor.executor_id == employee_id,
    ).all()

    all_ids = set()
    nps_values = []
    for s in surveys_direct + surveys_executor:
        if s.id not in all_ids:
            all_ids.add(s.id)
            nps_values.append(s.nps_score * 10)  # 0-10 → 0-100

    return sum(nps_values) / len(nps_values) if nps_values else None


def calc_crm_kpi(db: Session, employee_id: int, position: str,
                 project_type_db: str, period_start: date, period_end: date) -> Dict:
    """Рассчитывает полный KPI для CRM-проекта."""
    k_deadline = calc_k_deadline(db, employee_id, project_type_db, period_start, period_end)
    k_quality = calc_k_quality(db, employee_id, project_type_db, period_start, period_end)
    k_speed = calc_k_speed(db, employee_id, project_type_db, period_start, period_end)
    k_nps = calc_k_nps_crm(db, employee_id, project_type_db, period_start, period_end)

    weights = CRM_KPI_WEIGHTS.get(position, CRM_KPI_WEIGHTS_DEFAULT)

    if k_nps is None:
        remaining = 1.0 - weights['nps']
        if remaining > 0:
            kpi_total = (
                (weights['deadline'] / remaining) * k_deadline +
                (weights['quality'] / remaining) * k_quality +
                (weights['speed'] / remaining) * k_speed
            )
        else:
            kpi_total = (k_deadline + k_quality + k_speed) / 3
    else:
        kpi_total = (
            weights['deadline'] * k_deadline +
            weights['quality'] * k_quality +
            weights['speed'] * k_speed +
            weights['nps'] * k_nps
        )

    # Дополнительные метрики
    stages = _get_completed_stages(db, employee_id, project_type_db, period_start, period_end)
    stages_with_dl = [s for s in stages if s.deadline and _parse_date(s.deadline)]

    on_time = sum(1 for s in stages_with_dl
                  if _parse_date(s.completed_date) and _parse_date(s.deadline)
                  and _parse_date(s.completed_date) <= _parse_date(s.deadline))
    overdue = len(stages_with_dl) - on_time

    overdue_days_list = []
    for s in stages_with_dl:
        cd = _parse_date(s.completed_date)
        dl = _parse_date(s.deadline)
        if cd and dl and cd > dl:
            overdue_days_list.append((cd - dl).days)

    avg_overdue = sum(overdue_days_list) / len(overdue_days_list) if overdue_days_list else 0.0

    # Кол-во правок
    revision_total = 0
    for s in stages:
        wf = db.query(StageWorkflowState).filter(
            StageWorkflowState.crm_card_id == s.crm_card_id,
            StageWorkflowState.stage_name == s.stage_name,
        ).first()
        if wf:
            revision_total += (wf.revision_count or 0)

    return {
        'kpi_total': round(min(max(kpi_total, 0), 100), 1),
        'k_deadline': round(k_deadline, 1),
        'k_quality': round(k_quality, 1),
        'k_speed': round(k_speed, 1),
        'k_nps': round(k_nps, 1) if k_nps is not None else None,
        'stages_completed': len(stages),
        'stages_on_time': on_time,
        'stages_overdue': overdue,
        'avg_overdue_days': round(avg_overdue, 1),
        'revision_count': revision_total,
    }


# ═══════════════════════════════════════════════════════════════════════
# РАСЧЁТ KPI ДЛЯ АВТОРСКОГО НАДЗОРА
# ═══════════════════════════════════════════════════════════════════════

def calc_k_procurement(db: Session, employee_id: int,
                       period_start: date, period_end: date) -> float:
    """Kзакупки — % стадий, завершённых до plan_date."""
    cards = db.query(SupervisionCard).filter(
        or_(
            SupervisionCard.dan_id == employee_id,
            SupervisionCard.senior_manager_id == employee_id,
        )
    ).all()

    card_ids = [c.id for c in cards]
    if not card_ids:
        return 100.0

    entries = db.query(SupervisionTimelineEntry).filter(
        SupervisionTimelineEntry.supervision_card_id.in_(card_ids),
        SupervisionTimelineEntry.actual_date.isnot(None),
        SupervisionTimelineEntry.plan_date.isnot(None),
        SupervisionTimelineEntry.actual_date >= period_start,
        SupervisionTimelineEntry.actual_date <= period_end,
    ).all()

    if not entries:
        return 100.0

    on_time = 0
    for e in entries:
        ad = _parse_date(e.actual_date)
        pd = _parse_date(e.plan_date)
        if ad and pd and ad <= pd:
            on_time += 1

    return (on_time / len(entries)) * 100


def calc_k_defects(db: Session, employee_id: int,
                   period_start: date, period_end: date) -> float:
    """Kдефекты — % устранённых дефектов."""
    cards = db.query(SupervisionCard).filter(
        or_(
            SupervisionCard.dan_id == employee_id,
            SupervisionCard.senior_manager_id == employee_id,
        )
    ).all()

    card_ids = [c.id for c in cards]
    if not card_ids:
        return 100.0

    result = db.query(
        func.coalesce(func.sum(SupervisionTimelineEntry.defects_found), 0).label('found'),
        func.coalesce(func.sum(SupervisionTimelineEntry.defects_resolved), 0).label('resolved'),
    ).filter(
        SupervisionTimelineEntry.supervision_card_id.in_(card_ids),
        SupervisionTimelineEntry.actual_date >= period_start,
        SupervisionTimelineEntry.actual_date <= period_end,
    ).first()

    found = result.found or 0
    resolved = result.resolved or 0

    if found == 0:
        return 100.0

    return min((resolved / found) * 100, 100.0)


def calc_k_nps_supervision(db: Session, employee_id: int,
                           period_start: date, period_end: date) -> Optional[float]:
    """Knps для надзора — средний NPS по надзорным проектам."""
    surveys = db.query(ClientSurvey).join(
        Contract, ClientSurvey.contract_id == Contract.id
    ).join(
        SupervisionCard, SupervisionCard.contract_id == Contract.id
    ).filter(
        ClientSurvey.project_type == 'supervision',
        ClientSurvey.status == 'completed',
        ClientSurvey.nps_score.isnot(None),
        or_(
            SupervisionCard.dan_id == employee_id,
            SupervisionCard.senior_manager_id == employee_id,
        ),
    ).all()

    if not surveys:
        return None

    nps_values = [s.nps_score * 10 for s in surveys]
    return sum(nps_values) / len(nps_values)


def calc_supervision_kpi(db: Session, employee_id: int, position: str,
                         period_start: date, period_end: date) -> Dict:
    """Рассчитывает KPI для авторского надзора."""
    try:
        return _calc_supervision_kpi_inner(db, employee_id, position, period_start, period_end)
    except Exception:
        logger.exception(
            "Ошибка расчёта KPI надзора: employee_id=%s, period=%s..%s",
            employee_id, period_start, period_end,
        )
        return {
            'kpi_total': 0, 'k_deadline': 0, 'k_quality': 0, 'k_speed': 0, 'k_nps': None,
            'stages_completed': 0, 'stages_on_time': 0, 'stages_overdue': 0,
            'avg_overdue_days': 0, 'revision_count': 0,
            'defects_found': 0, 'defects_resolved': 0, 'site_visits': 0,
            'budget_savings': 0, 'active_supervisions': 0,
        }


def _calc_supervision_kpi_inner(db: Session, employee_id: int, position: str,
                                 period_start: date, period_end: date) -> Dict:
    """Внутренняя реализация расчёта KPI надзора."""
    k_procurement = calc_k_procurement(db, employee_id, period_start, period_end)
    k_defects = calc_k_defects(db, employee_id, period_start, period_end)
    k_nps = calc_k_nps_supervision(db, employee_id, period_start, period_end)

    # k_visits — пока упрощённый (100% если есть визиты)
    cards = db.query(SupervisionCard).filter(
        or_(
            SupervisionCard.dan_id == employee_id,
            SupervisionCard.senior_manager_id == employee_id,
        )
    ).all()
    card_ids = [c.id for c in cards]

    visits_count = 0
    defects_found_total = 0
    defects_resolved_total = 0
    budget_savings_total = 0.0

    if card_ids:
        visits_count = db.query(func.count(SupervisionVisit.id)).filter(
            SupervisionVisit.supervision_card_id.in_(card_ids),
        ).scalar() or 0

        agg = db.query(
            func.coalesce(func.sum(SupervisionTimelineEntry.defects_found), 0),
            func.coalesce(func.sum(SupervisionTimelineEntry.defects_resolved), 0),
            func.coalesce(func.sum(SupervisionTimelineEntry.budget_savings), 0),
        ).filter(
            SupervisionTimelineEntry.supervision_card_id.in_(card_ids),
        ).first()
        defects_found_total = agg[0] or 0
        defects_resolved_total = agg[1] or 0
        budget_savings_total = agg[2] or 0.0

    # Ожидаем 2 визита на каждый активный надзор за период
    k_visits = min((visits_count / max(len(card_ids) * 2, 1)) * 100, 100.0)

    weights = SUPERVISION_KPI_WEIGHTS.get(position, SUPERVISION_KPI_WEIGHTS_DEFAULT)

    if k_nps is None:
        remaining = 1.0 - weights['nps']
        if remaining > 0:
            kpi_total = (
                (weights['procurement'] / remaining) * k_procurement +
                (weights['defects'] / remaining) * k_defects +
                (weights['visits'] / remaining) * k_visits
            )
        else:
            kpi_total = (k_procurement + k_defects + k_visits) / 3
    else:
        kpi_total = (
            weights['procurement'] * k_procurement +
            weights['defects'] * k_defects +
            weights['visits'] * k_visits +
            weights['nps'] * k_nps
        )

    # Подсчёт просроченных закупок
    procurement_entries = db.query(SupervisionTimelineEntry).filter(
        SupervisionTimelineEntry.supervision_card_id.in_(card_ids),
        SupervisionTimelineEntry.actual_date.isnot(None),
        SupervisionTimelineEntry.plan_date.isnot(None),
    ).all() if card_ids else []

    procurement_overdue = sum(
        1 for e in procurement_entries
        if _parse_date(e.actual_date) and _parse_date(e.plan_date)
        and _parse_date(e.actual_date) > _parse_date(e.plan_date)
    )

    active_cards = sum(1 for c in cards
                       if c.column_name not in (STATUS_COMPLETED, STATUS_TERMINATED))

    return {
        'kpi_total': round(min(max(kpi_total, 0), 100), 1),
        'k_deadline': round(k_procurement, 1),  # alias для единообразия
        'k_quality': round(k_defects, 1),
        'k_speed': round(k_visits, 1),
        'k_nps': round(k_nps, 1) if k_nps is not None else None,
        'stages_completed': len(procurement_entries),
        'stages_on_time': len(procurement_entries) - procurement_overdue,
        'stages_overdue': procurement_overdue,
        'avg_overdue_days': 0,
        'revision_count': 0,
        'defects_found': defects_found_total,
        'defects_resolved': defects_resolved_total,
        'site_visits': visits_count,
        'budget_savings': round(budget_savings_total, 2),
        'active_supervisions': active_cards,
    }


# ═══════════════════════════════════════════════════════════════════════
# ПУБЛИЧНЫЙ ИНТЕРФЕЙС
# ═══════════════════════════════════════════════════════════════════════

def calculate_employee_kpi(db: Session, employee_id: int, position: str,
                           project_type: str, year: int,
                           quarter: Optional[int] = None,
                           month: Optional[int] = None) -> Dict:
    """
    Главная функция расчёта KPI сотрудника.

    Args:
        project_type: 'individual' / 'template' / 'supervision'
    """
    try:
        period_start, period_end = _get_period_range(year, quarter, month)

        if project_type == 'supervision':
            return calc_supervision_kpi(db, employee_id, position, period_start, period_end)
        else:
            project_type_db = PROJECT_TYPE_MAP.get(project_type, 'Индивидуальный')
            return calc_crm_kpi(db, employee_id, position, project_type_db,
                                period_start, period_end)
    except Exception:
        logger.exception(
            "Ошибка расчёта KPI: employee_id=%s, project_type=%s, year=%s, quarter=%s, month=%s",
            employee_id, project_type, year, quarter, month,
        )
        # Возвращаем нулевой результат, чтобы не ломать весь дашборд
        return {
            'kpi_total': 0, 'k_deadline': 0, 'k_quality': 0, 'k_speed': 0, 'k_nps': None,
            'stages_completed': 0, 'stages_on_time': 0, 'stages_overdue': 0,
            'avg_overdue_days': 0, 'revision_count': 0,
        }


def get_concurrent_projects(db: Session, employee_id: int,
                            project_type: str, position: str) -> int:
    """Возвращает текущее кол-во одновременных проектов/стадий."""
    if project_type == 'supervision':
        return db.query(func.count(SupervisionCard.id)).filter(
            or_(
                SupervisionCard.dan_id == employee_id,
                SupervisionCard.senior_manager_id == employee_id,
            ),
            SupervisionCard.column_name.notin_([STATUS_COMPLETED, STATUS_TERMINATED]),
        ).scalar() or 0

    project_type_db = PROJECT_TYPE_MAP.get(project_type, 'Индивидуальный')

    if position == POSITION_SENIOR_MANAGER:
        return db.query(func.count(CRMCard.id)).join(
            Contract, CRMCard.contract_id == Contract.id
        ).filter(
            Contract.project_type == project_type_db,
            CRMCard.senior_manager_id == employee_id,
            CRMCard.column_name.notin_([STATUS_COMPLETED, STATUS_TERMINATED, 'РАСТОРГНУТ']),
        ).scalar() or 0

    # Для исполнителей — активные (незавершённые) StageExecutor
    return db.query(func.count(StageExecutor.id)).join(
        CRMCard, StageExecutor.crm_card_id == CRMCard.id
    ).join(
        Contract, CRMCard.contract_id == Contract.id
    ).filter(
        Contract.project_type == project_type_db,
        StageExecutor.executor_id == employee_id,
        StageExecutor.completed == False,
    ).scalar() or 0


def get_recommended_max_load(position: str) -> int:
    """Рекомендуемый максимум одновременных проектов."""
    return RECOMMENDED_MAX_LOAD.get(position, RECOMMENDED_MAX_LOAD_DEFAULT)


def get_total_salary(db: Session, employee_id: int, project_type: str,
                     period_start: date, period_end: date) -> float:
    """Сумма выплат за период по типу проекта."""
    query = db.query(func.coalesce(func.sum(Payment.final_amount), 0)).filter(
        Payment.employee_id == employee_id,
    )

    if project_type == 'supervision':
        query = query.filter(Payment.supervision_card_id.isnot(None))
    else:
        project_type_db = PROJECT_TYPE_MAP.get(project_type, 'Индивидуальный')
        query = query.join(
            Contract, Payment.contract_id == Contract.id
        ).filter(
            Contract.project_type == project_type_db,
            Payment.supervision_card_id.is_(None),
        )

    return query.scalar() or 0.0


def get_total_area(db: Session, employee_id: int, project_type_db: str,
                   period_start: date, period_end: date) -> float:
    """Суммарная площадь проектов, на которые назначен сотрудник.

    Считает площадь уникальных контрактов (по contract_id), где
    сотрудник — исполнитель хотя бы одной стадии.
    """
    contract_ids = db.query(Contract.id).join(
        CRMCard, CRMCard.contract_id == Contract.id
    ).join(
        StageExecutor, StageExecutor.crm_card_id == CRMCard.id
    ).filter(
        Contract.project_type == project_type_db,
        StageExecutor.executor_id == employee_id,
    ).distinct().subquery()

    result = db.query(
        func.coalesce(func.sum(Contract.area), 0)
    ).filter(Contract.id.in_(contract_ids)).scalar()
    return result or 0.0

"""
Фоновый планировщик проверки дедлайнов.
Запускается при старте сервера, проверяет каждые 4 часа.
Отправляет уведомления:
- За 2 рабочих дня до дедлайна
- При просрочке дедлайна

Согласно руководству (workflow-guide §10):
- Дедлайн = рабочие дни без выходных и праздников
- Просрочка: уведомить исполнителя + ст.менеджера + reviewer (СДП/ГАП/Менеджер)
"""

import asyncio
from datetime import date, datetime, timedelta
import logging
from typing import Optional, Set

logger = logging.getLogger(__name__)

# Интервал проверки (секунды): 4 часа
CHECK_INTERVAL = 4 * 60 * 60

# Государственные праздники РФ (фиксированные даты, месяц-день)
# Перенос выходных регулируется ежегодно, но базовые даты стабильны
_RUSSIAN_HOLIDAYS_MD: set[tuple] = {
    (1, 1),
    (1, 2),
    (1, 3),
    (1, 4),
    (1, 5),
    (1, 6),
    (1, 7),
    (1, 8),  # Новогодние каникулы
    (2, 23),  # День защитника Отечества
    (3, 8),  # Международный женский день
    (5, 1),  # Праздник Весны и Труда
    (5, 9),  # День Победы
    (6, 12),  # День России
    (11, 4),  # День народного единства
}


def _is_russian_holiday(d: date) -> bool:
    """Проверить, является ли дата государственным праздником РФ."""
    return (d.month, d.day) in _RUSSIAN_HOLIDAYS_MD


def _count_business_days_between(start: date, end: date) -> int:
    """Посчитать рабочие дни между двумя датами (без выходных и праздников РФ)."""
    if start >= end:
        return 0
    days = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5 and not _is_russian_holiday(current):
            days += 1
    return days


def _get_reviewer_id(card, stage_name: str, pt_key: str) -> Optional[int]:
    """Определить ID проверяющего (reviewer) по стадии и типу проекта.

    Согласно руководству (workflow-guide §2):
    - Инд. Стадия 1,2 → СДП
    - Инд. Стадия 3 → ГАП
    - Шабл. Стадия 1,3 → Менеджер
    - Шабл. Стадия 2 → ГАП
    """
    sl = stage_name.lower() if stage_name else ""
    if "рабочие чертежи" in sl or "рабочая документация" in sl:
        return getattr(card, "gap_id", None)
    elif pt_key == "template" and ("планировочн" in sl or "3д" in sl or "визуализац" in sl):
        return getattr(card, "manager_id", None)
    else:
        return getattr(card, "sdp_id", None)


def _already_sent_today(db, employee_id: int, entity_id: int, msg_key: str) -> bool:
    """Проверить по БД, было ли уведомление уже отправлено сегодня.

    msg_key — уникальный суффикс в заголовке (напр. stage_name + type).
    Используется вместо in-memory set, который сбрасывается при перезапуске сервера.
    """
    from database import Notification

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    exists = (
        db.query(Notification)
        .filter(
            Notification.employee_id == employee_id,
            Notification.notification_type == "deadline",
            Notification.related_entity_id == entity_id,
            Notification.message.contains(msg_key),
            Notification.created_at >= today_start,
        )
        .first()
    )
    return exists is not None


async def check_deadlines_once():
    """Однократная проверка всех дедлайнов CRM и надзора."""
    today = date.today()

    from services.notification_dispatcher import dispatch_notification

    from database import Contract, CRMCard, SessionLocal, StageExecutor, SupervisionCard, SupervisionTimelineEntry

    db = SessionLocal()
    try:
        # === CRM дедлайны ===
        executors = (
            db.query(StageExecutor)
            .filter(
                StageExecutor.deadline.isnot(None),
                StageExecutor.completed == False,
            )
            .all()
        )

        for ex in executors:
            try:
                dl = ex.deadline
                if isinstance(dl, str):
                    dl = datetime.strptime(dl, "%Y-%m-%d").date()
                elif isinstance(dl, datetime):
                    dl = dl.date()

                biz_days = _count_business_days_between(today, dl)

                card = db.query(CRMCard).filter(CRMCard.id == ex.crm_card_id).first()
                if not card:
                    continue
                contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
                if not contract:
                    continue
                # Пропускаем архивные договоры (СДАН, РАСТОРГНУТ, АВТОРСКИЙ НАДЗОР)
                if contract.status in ("СДАН", "РАСТОРГНУТ", "АВТОРСКИЙ НАДЗОР"):
                    continue
                # Пропускаем если карточка уже перешла на другую стадию (безопасность)
                if card.column_name != ex.stage_name:
                    continue

                address = contract.address if contract else ""
                pt = (contract.project_type or "").lower() if contract else ""
                pt_key = "template" if "шабл" in pt else "individual"
                dl_str = dl.strftime("%d.%m.%Y")
                stage_short = ex.stage_name or ""

                # Предупреждение за 2 рабочих дня
                if biz_days == 2:
                    warn_key = f"через 2 рабочих дня ({dl_str})"
                    if not _already_sent_today(db, ex.executor_id, card.id, warn_key):
                        await dispatch_notification(
                            db=db,
                            employee_id=ex.executor_id,
                            event_type="deadline",
                            title=f"Дедлайн: {address}",
                            message=f'Дедлайн по стадии "{stage_short}" проекта {address} через 2 рабочих дня ({dl_str}).',
                            related_entity_type="crm_card",
                            related_entity_id=card.id,
                            project_type=pt_key,
                            card_id=card.id,
                        )

                # Просрочка
                # Руководство §2.4: Исполнитель + Ст.менеджер + Reviewer (СДП/ГАП/Менеджер)
                elif today > dl:
                    overdue_msg = f'Дедлайн по стадии "{stage_short}" проекта {address} просрочен! Было: {dl_str}.'
                    sent_ids = set()

                    # Исполнителю
                    if not _already_sent_today(db, ex.executor_id, card.id, dl_str):
                        await dispatch_notification(
                            db=db,
                            employee_id=ex.executor_id,
                            event_type="deadline",
                            title=f"Просрочка: {address}",
                            message=overdue_msg,
                            related_entity_type="crm_card",
                            related_entity_id=card.id,
                            project_type=pt_key,
                            card_id=card.id,
                        )
                    sent_ids.add(ex.executor_id)

                    # Старшему менеджеру
                    if card.senior_manager_id and card.senior_manager_id not in sent_ids:
                        if not _already_sent_today(db, card.senior_manager_id, card.id, dl_str):
                            await dispatch_notification(
                                db=db,
                                employee_id=card.senior_manager_id,
                                event_type="deadline",
                                title=f"Просрочка: {address}",
                                message=overdue_msg,
                                related_entity_type="crm_card",
                                related_entity_id=card.id,
                                project_type=pt_key,
                                card_id=card.id,
                            )
                        sent_ids.add(card.senior_manager_id)

                    # Reviewer (СДП/ГАП/Менеджер — зависит от стадии и типа проекта)
                    reviewer_id = _get_reviewer_id(card, ex.stage_name, pt_key)
                    if reviewer_id and reviewer_id not in sent_ids:
                        if not _already_sent_today(db, reviewer_id, card.id, dl_str):
                            await dispatch_notification(
                                db=db,
                                employee_id=reviewer_id,
                                event_type="deadline",
                                title=f"Просрочка: {address}",
                                message=overdue_msg,
                                related_entity_type="crm_card",
                                related_entity_id=card.id,
                                project_type=pt_key,
                                card_id=card.id,
                            )
            except Exception as e:
                logger.warning(f"deadline_checker CRM executor {ex.id}: {e}")

        # === Надзор дедлайны ===
        sv_cards = (
            db.query(SupervisionCard)
            .filter(
                SupervisionCard.deadline.isnot(None),
                SupervisionCard.column_name != "Выполненный проект",
                SupervisionCard.is_paused == False,
            )
            .all()
        )

        for sv in sv_cards:
            try:
                dl = sv.deadline
                if isinstance(dl, str):
                    dl = datetime.strptime(dl, "%Y-%m-%d").date()
                elif isinstance(dl, datetime):
                    dl = dl.date()

                biz_days = _count_business_days_between(today, dl)
                contract = db.query(Contract).filter(Contract.id == sv.contract_id).first()
                address = contract.address if contract else ""
                dl_str = dl.strftime("%d.%m.%Y")
                recipients = [r for r in [sv.dan_id, sv.senior_manager_id] if r]

                if biz_days == 2:
                    for emp_id in recipients:
                        warn_key = f"через 2 рабочих дня ({dl_str})"
                        if not _already_sent_today(db, emp_id, sv.id, warn_key):
                            await dispatch_notification(
                                db=db,
                                employee_id=emp_id,
                                event_type="deadline",
                                title=f"Дедлайн надзора: {address}",
                                message=f"Общий дедлайн по надзору {address} через 2 рабочих дня ({dl_str}).",
                                related_entity_type="supervision_card",
                                related_entity_id=sv.id,
                                project_type="supervision",
                            )
                elif today > dl:
                    for emp_id in recipients:
                        if not _already_sent_today(db, emp_id, sv.id, dl_str):
                            await dispatch_notification(
                                db=db,
                                employee_id=emp_id,
                                event_type="deadline",
                                title=f"Просрочка надзора: {address}",
                                message=f"Общий дедлайн по надзору {address} просрочен! Было: {dl_str}.",
                                related_entity_type="supervision_card",
                                related_entity_id=sv.id,
                                project_type="supervision",
                            )
            except Exception as e:
                logger.warning(f"deadline_checker supervision {sv.id}: {e}")

        # === Надзор дедлайны по стадиям (plan_date из SupervisionTimelineEntry) ===
        # Руководство §4: "Дедлайн по стадии "{stage_name}" надзора {address}"
        sv_stages = (
            db.query(SupervisionTimelineEntry)
            .filter(
                SupervisionTimelineEntry.plan_date.isnot(None),
                SupervisionTimelineEntry.plan_date != "",
                SupervisionTimelineEntry.status != "Выполнено",
            )
            .all()
        )

        for ste in sv_stages:
            try:
                sv = db.query(SupervisionCard).filter(SupervisionCard.id == ste.supervision_card_id).first()
                if not sv or sv.column_name == "Выполненный проект" or sv.is_paused:
                    continue

                dl = ste.plan_date
                if isinstance(dl, str):
                    dl = datetime.strptime(dl, "%Y-%m-%d").date()
                elif isinstance(dl, datetime):
                    dl = dl.date()

                biz_days = _count_business_days_between(today, dl)
                contract = db.query(Contract).filter(Contract.id == sv.contract_id).first()
                address = contract.address if contract else ""
                dl_str = dl.strftime("%d.%m.%Y")
                recipients = [r for r in [sv.dan_id, sv.senior_manager_id] if r]

                if biz_days == 2:
                    for emp_id in recipients:
                        warn_key = f"через 2 рабочих дня ({dl_str})"
                        if not _already_sent_today(db, emp_id, sv.id, warn_key):
                            await dispatch_notification(
                                db=db,
                                employee_id=emp_id,
                                event_type="deadline",
                                title=f"Дедлайн стадии надзора: {address}",
                                message=f'Дедлайн по стадии "{ste.stage_name}" надзора {address} через 2 рабочих дня ({dl_str}).',
                                related_entity_type="supervision_card",
                                related_entity_id=sv.id,
                                project_type="supervision",
                            )
                elif today > dl:
                    for emp_id in recipients:
                        if not _already_sent_today(db, emp_id, sv.id, dl_str):
                            await dispatch_notification(
                                db=db,
                                employee_id=emp_id,
                                event_type="deadline",
                                title=f"Просрочка стадии надзора: {address}",
                                message=f'Дедлайн по стадии "{ste.stage_name}" надзора {address} просрочен! Было: {dl_str}.',
                                related_entity_type="supervision_card",
                                related_entity_id=sv.id,
                                project_type="supervision",
                            )
            except Exception as e:
                logger.warning(f"deadline_checker supervision stage {ste.id}: {e}")

    except Exception as e:
        logger.error(f"deadline_checker: {e}")
    finally:
        db.close()


async def create_monthly_supervision_payments(db_session_factory):
    """Создаёт ежемесячные оплаты для активных назначений надзора (запускать 1-го числа каждого месяца)."""
    from database import Payment, SupervisionCard, SupervisionMonthlyAssignment

    logger.info("Запуск ежемесячного создания оплат надзора...")
    with db_session_factory() as db:
        try:
            current_month = datetime.utcnow().strftime("%Y-%m")
            COMPLETED_COLUMN = "Выполненный проект"

            assignments = (
                db.query(SupervisionMonthlyAssignment)
                .join(SupervisionCard, SupervisionMonthlyAssignment.supervision_card_id == SupervisionCard.id)
                .filter(
                    SupervisionMonthlyAssignment.is_active == True,
                    SupervisionCard.column_name != COMPLETED_COLUMN,
                )
                .all()
            )

            created = 0
            for a in assignments:
                # Проверить нет ли уже оплаты за этот месяц
                exists = (
                    db.query(Payment)
                    .filter(
                        Payment.supervision_card_id == a.supervision_card_id,
                        Payment.employee_name == a.employee_name,
                        Payment.stage_name == "Ежемесячная ставка",
                        Payment.report_month == current_month,
                    )
                    .first()
                )
                if exists:
                    continue

                card = db.query(SupervisionCard).filter(SupervisionCard.id == a.supervision_card_id).first()
                if not card:
                    continue

                payment = Payment(
                    contract_id=card.contract_id,
                    supervision_card_id=a.supervision_card_id,
                    employee_id=a.employee_id,
                    employee_name=a.employee_name,
                    role=a.role,
                    stage_name="Ежемесячная ставка",
                    calculated_amount=a.monthly_amount,
                    final_amount=a.monthly_amount,
                    payment_type="Оклад",
                    report_month=current_month,
                    payment_status="pending",
                    is_paid=False,
                )
                db.add(payment)
                created += 1

            db.commit()
            logger.info(f"Ежемесячные оплаты надзора: создано {created} записей за {current_month}")
        except Exception as e:
            logger.exception(f"Ошибка при создании ежемесячных оплат надзора: {e}")
            db.rollback()


async def deadline_checker_loop():
    """Бесконечный цикл проверки дедлайнов, запускается ежедневно в 10:00 МСК (07:00 UTC)."""
    logger.info("Deadline checker запущен (ежедневно в 10:00 МСК = 07:00 UTC)")
    while True:
        try:
            now = datetime.utcnow()
            next_run = now.replace(hour=7, minute=0, second=0, microsecond=0)
            if now >= next_run:
                next_run = next_run + timedelta(days=1)
            sleep_secs = (next_run - now).total_seconds()
            logger.info(f"Deadline checker: следующий запуск через {sleep_secs / 3600:.1f}ч (в 10:00 МСК)")
            await asyncio.sleep(sleep_secs)
            await check_deadlines_once()
        except Exception as e:
            logger.error(f"deadline_checker_loop: {e}")
            await asyncio.sleep(3600)

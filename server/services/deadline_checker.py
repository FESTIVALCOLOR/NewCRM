"""
Фоновый планировщик проверки дедлайнов.
Запускается при старте сервера, проверяет каждые 4 часа.
Отправляет уведомления:
- За 2 рабочих дня до дедлайна
- При просрочке дедлайна
"""
import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Интервал проверки (секунды): 4 часа
CHECK_INTERVAL = 4 * 60 * 60

# Набор уже отправленных уведомлений (чтобы не дублировать в рамках дня)
# Формат: {(card_id, stage_name, date_str, type)}
_sent_today: set = set()
_sent_date: Optional[date] = None


def _count_business_days_between(start: date, end: date) -> int:
    """Посчитать рабочие дни между двумя датами (без выходных)."""
    if start >= end:
        return 0
    days = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Пн-Пт
            days += 1
    return days


async def check_deadlines_once():
    """Однократная проверка всех дедлайнов CRM и надзора."""
    global _sent_today, _sent_date

    # Сброс кэша при смене даты
    today = date.today()
    if _sent_date != today:
        _sent_today = set()
        _sent_date = today

    from database import SessionLocal, StageExecutor, CRMCard, Contract, SupervisionCard
    from services.notification_dispatcher import dispatch_notification

    db = SessionLocal()
    try:
        # === CRM дедлайны ===
        executors = db.query(StageExecutor).filter(
            StageExecutor.deadline.isnot(None),
            StageExecutor.completed == False,
        ).all()

        for ex in executors:
            try:
                dl = ex.deadline
                if isinstance(dl, str):
                    dl = datetime.strptime(dl, '%Y-%m-%d').date()
                elif isinstance(dl, datetime):
                    dl = dl.date()

                biz_days = _count_business_days_between(today, dl)

                card = db.query(CRMCard).filter(CRMCard.id == ex.crm_card_id).first()
                if not card:
                    continue
                contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
                address = contract.address if contract else ''
                pt = (contract.project_type or '').lower() if contract else ''
                pt_key = 'template' if 'шабл' in pt else 'individual'
                dl_str = dl.strftime('%d.%m.%Y')

                # Предупреждение за 2 рабочих дня
                if biz_days == 2:
                    key = (card.id, ex.stage_name, str(today), 'warning')
                    if key not in _sent_today:
                        _sent_today.add(key)
                        await dispatch_notification(
                            db=db, employee_id=ex.executor_id,
                            event_type='deadline',
                            title=f'Дедлайн: {address}',
                            message=f'Дедлайн по проекту {address} через 2 рабочих дня ({dl_str}).',
                            related_entity_type='crm_card',
                            related_entity_id=card.id,
                            project_type=pt_key,
                            card_id=card.id,
                        )

                # Просрочка
                elif today > dl:
                    key = (card.id, ex.stage_name, str(today), 'overdue')
                    if key not in _sent_today:
                        _sent_today.add(key)
                        # Исполнителю
                        await dispatch_notification(
                            db=db, employee_id=ex.executor_id,
                            event_type='deadline',
                            title=f'Просрочка: {address}',
                            message=f'Дедлайн по проекту {address} просрочен! Было: {dl_str}.',
                            related_entity_type='crm_card',
                            related_entity_id=card.id,
                            project_type=pt_key,
                            card_id=card.id,
                        )
                        # Старшему менеджеру
                        if card.senior_manager_id and card.senior_manager_id != ex.executor_id:
                            await dispatch_notification(
                                db=db, employee_id=card.senior_manager_id,
                                event_type='deadline',
                                title=f'Просрочка: {address}',
                                message=f'Дедлайн по проекту {address} просрочен! Было: {dl_str}.',
                                related_entity_type='crm_card',
                                related_entity_id=card.id,
                                project_type=pt_key,
                                card_id=card.id,
                            )
            except Exception as e:
                logger.warning(f"deadline_checker CRM executor {ex.id}: {e}")

        # === Надзор дедлайны ===
        sv_cards = db.query(SupervisionCard).filter(
            SupervisionCard.deadline.isnot(None),
            SupervisionCard.column_name != 'Выполненный проект',
            SupervisionCard.is_paused == False,
        ).all()

        for sv in sv_cards:
            try:
                dl = sv.deadline
                if isinstance(dl, str):
                    dl = datetime.strptime(dl, '%Y-%m-%d').date()
                elif isinstance(dl, datetime):
                    dl = dl.date()

                biz_days = _count_business_days_between(today, dl)
                contract = db.query(Contract).filter(Contract.id == sv.contract_id).first()
                address = contract.address if contract else ''
                dl_str = dl.strftime('%d.%m.%Y')
                recipients = [r for r in [sv.dan_id, sv.senior_manager_id] if r]

                if biz_days == 2:
                    for emp_id in recipients:
                        key = (sv.id, 'supervision', str(today), 'warning')
                        if key not in _sent_today:
                            _sent_today.add(key)
                            await dispatch_notification(
                                db=db, employee_id=emp_id,
                                event_type='deadline',
                                title=f'Дедлайн надзора: {address}',
                                message=f'Общий дедлайн по надзору {address} через 2 рабочих дня ({dl_str}).',
                                related_entity_type='supervision_card',
                                related_entity_id=sv.id,
                                project_type='supervision',
                            )
                elif today > dl:
                    for emp_id in recipients:
                        key = (sv.id, 'supervision', str(today), 'overdue')
                        if key not in _sent_today:
                            _sent_today.add(key)
                            await dispatch_notification(
                                db=db, employee_id=emp_id,
                                event_type='deadline',
                                title=f'Просрочка надзора: {address}',
                                message=f'Общий дедлайн по надзору {address} просрочен! Было: {dl_str}.',
                                related_entity_type='supervision_card',
                                related_entity_id=sv.id,
                                project_type='supervision',
                            )
            except Exception as e:
                logger.warning(f"deadline_checker supervision {sv.id}: {e}")

    except Exception as e:
        logger.error(f"deadline_checker: {e}")
    finally:
        db.close()


async def deadline_checker_loop():
    """Бесконечный цикл проверки дедлайнов."""
    logger.info("Deadline checker запущен (интервал: 4 часа)")
    while True:
        try:
            await check_deadlines_once()
        except Exception as e:
            logger.error(f"deadline_checker_loop: {e}")
        await asyncio.sleep(CHECK_INTERVAL)

"""
Роутер для уведомлений и настроек уведомлений.
Endpoints:
  GET    /notifications                         → список уведомлений текущего пользователя
  PUT    /notifications/{id}/read               → отметить прочитанным
  GET    /notifications/settings/{employee_id}  → настройки канала
  PUT    /notifications/settings/{employee_id}  → обновить настройки
  POST   /employees/{employee_id}/send-invite   → отправить приглашение сотруднику
  POST   /notifications/test                    → тест уведомления (Директор)
"""
import logging
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, Employee, Notification, NotificationSettings
from auth import get_current_user
from permissions import require_permission, SUPERUSER_ROLES
from schemas import NotificationResponse, NotificationSettingsResponse, NotificationSettingsUpdate
from constants import (
    POSITION_DAN, POSITION_SENIOR_MANAGER, POSITION_STUDIO_DIRECTOR,
    POSITION_SDP, POSITION_MEASURER,
    ROLE_ADMIN, ROLE_DIRECTOR,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── СТАТИЧЕСКИЕ ПУТИ ПЕРЕД ДИНАМИЧЕСКИМИ ──

@router.get("/notifications/settings/{employee_id}", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    employee_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить настройки уведомлений сотрудника"""
    # Директор видит всех, остальные — только себя
    if current_user.id != employee_id and current_user.role not in SUPERUSER_ROLES:
        raise HTTPException(status_code=403, detail="Нет доступа к настройкам другого сотрудника")

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    settings = db.query(NotificationSettings).filter_by(employee_id=employee_id).first()
    if not settings:
        # Рекомендуемые дефолты по ролям (см. docs/notifications-scripts-guide.md §10)
        role = employee.role or ''
        pos = employee.position or ''

        # supervision: ДАН, Ст.менеджер, Руководитель
        supervision_roles = {
            POSITION_DAN, POSITION_SENIOR_MANAGER,
            POSITION_STUDIO_DIRECTOR, ROLE_ADMIN, ROLE_DIRECTOR,
        }
        # payment: Руководитель, Ст.менеджер
        payment_roles = {
            POSITION_STUDIO_DIRECTOR, POSITION_SENIOR_MANAGER,
            ROLE_ADMIN, ROLE_DIRECTOR,
        }
        # crm_stage: Выкл для ДАН и Замерщик
        crm_stage_off = {POSITION_DAN, POSITION_MEASURER}
        # deadline: Выкл для Замерщик
        deadline_off = {POSITION_MEASURER}
        # individual: Выкл для ДАН
        individual_off = {POSITION_DAN}
        # template: Выкл для ДАН и СДП
        template_off = {POSITION_DAN, POSITION_SDP}

        is_senior_manager = pos == POSITION_SENIOR_MANAGER

        return NotificationSettingsResponse(
            employee_id=employee_id,
            telegram_enabled=True,
            email_enabled=False,
            notify_crm_stage=role not in crm_stage_off,
            notify_assigned=True,
            notify_deadline=role not in deadline_off,
            notify_payment=role in payment_roles,
            notify_supervision=role in supervision_roles,
            notify_individual=role not in individual_off,
            notify_template=role not in template_off,
            notify_duplicate_info=is_senior_manager,
            notify_revision_info=is_senior_manager,
            telegram_connected=bool(employee.telegram_user_id),
        )

    return NotificationSettingsResponse(
        employee_id=employee_id,
        telegram_enabled=settings.telegram_enabled,
        email_enabled=settings.email_enabled,
        notify_crm_stage=settings.notify_crm_stage,
        notify_assigned=settings.notify_assigned,
        notify_deadline=settings.notify_deadline,
        notify_payment=settings.notify_payment,
        notify_supervision=settings.notify_supervision,
        notify_individual=getattr(settings, 'notify_individual', True),
        notify_template=getattr(settings, 'notify_template', True),
        notify_duplicate_info=getattr(settings, 'notify_duplicate_info', False),
        notify_revision_info=getattr(settings, 'notify_revision_info', False),
        telegram_connected=bool(employee.telegram_user_id),
        push_enabled=getattr(settings, 'push_enabled', False),
        notification_channel=getattr(settings, 'notification_channel', 'telegram') or 'telegram',
    )


@router.put("/notifications/settings/{employee_id}", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    employee_id: int,
    data: NotificationSettingsUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Обновить настройки уведомлений сотрудника"""
    if current_user.id != employee_id and current_user.role not in SUPERUSER_ROLES:
        raise HTTPException(status_code=403, detail="Нет доступа к настройкам другого сотрудника")

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    settings = db.query(NotificationSettings).filter_by(employee_id=employee_id).first()
    if not settings:
        settings = NotificationSettings(
            employee_id=employee_id,
            created_at=datetime.utcnow(),
        )
        db.add(settings)

    settings.telegram_enabled = data.telegram_enabled
    settings.email_enabled = data.email_enabled
    settings.notify_crm_stage = data.notify_crm_stage
    settings.notify_assigned = data.notify_assigned
    settings.notify_deadline = data.notify_deadline
    settings.notify_payment = data.notify_payment
    settings.notify_supervision = data.notify_supervision
    settings.notify_individual = data.notify_individual
    settings.notify_template = data.notify_template
    settings.notify_duplicate_info = data.notify_duplicate_info
    settings.notify_revision_info = data.notify_revision_info
    # Web Push поля
    if data.push_enabled is not None:
        settings.push_enabled = data.push_enabled
    if data.notification_channel is not None:
        settings.notification_channel = data.notification_channel
    settings.updated_at = datetime.utcnow()

    db.commit()

    return NotificationSettingsResponse(
        employee_id=employee_id,
        telegram_enabled=settings.telegram_enabled,
        email_enabled=settings.email_enabled,
        notify_crm_stage=settings.notify_crm_stage,
        notify_assigned=settings.notify_assigned,
        notify_deadline=settings.notify_deadline,
        notify_payment=settings.notify_payment,
        notify_supervision=settings.notify_supervision,
        notify_individual=getattr(settings, 'notify_individual', True),
        notify_template=getattr(settings, 'notify_template', True),
        notify_duplicate_info=getattr(settings, 'notify_duplicate_info', False),
        notify_revision_info=getattr(settings, 'notify_revision_info', False),
        telegram_connected=bool(employee.telegram_user_id),
        push_enabled=getattr(settings, 'push_enabled', False),
        notification_channel=getattr(settings, 'notification_channel', 'telegram') or 'telegram',
    )


@router.post("/notifications/test")
async def send_test_notification(
    employee_id: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отправить тестовое уведомление.
    Директор может отправить любому сотруднику (employee_id).
    Обычный пользователь может отправить только себе.
    """
    if employee_id and employee_id != current_user.id:
        # Отправка другому сотруднику — только для директора
        if current_user.role not in SUPERUSER_ROLES:
            raise HTTPException(status_code=403, detail="Только директор может отправлять тесты другим сотрудникам")

    target_id = employee_id or current_user.id
    from services.notification_dispatcher import dispatch_notification
    await dispatch_notification(
        db=db,
        employee_id=target_id,
        event_type="assigned",
        title="Тестовое уведомление",
        message="Система уведомлений CRM Festival Color работает корректно.",
    )
    return {"ok": True, "message": "Тестовое уведомление отправлено"}


@router.get("/notifications/push/vapid-public-key")
async def get_vapid_public_key():
    """Получить VAPID public key для Web Push подписки"""
    from config import get_settings
    s = get_settings()
    return {"vapid_public_key": s.vapid_public_key or ""}


@router.post("/notifications/push/subscribe")
async def subscribe_push(
    subscription: dict,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Сохранить Web Push подписку пользователя"""
    import json
    settings = db.query(NotificationSettings).filter_by(employee_id=current_user.id).first()
    if not settings:
        settings = NotificationSettings(employee_id=current_user.id)
        db.add(settings)
    settings.push_subscription = json.dumps(subscription)
    settings.push_enabled = True
    # Если канал был только telegram — переключаем на both
    if settings.notification_channel == 'telegram':
        settings.notification_channel = 'both'
    db.commit()
    return {"status": "subscribed"}


@router.post("/notifications/push/unsubscribe")
async def unsubscribe_push(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отписаться от Web Push уведомлений"""
    settings = db.query(NotificationSettings).filter_by(employee_id=current_user.id).first()
    if settings:
        settings.push_enabled = False
        settings.push_subscription = None
        if settings.notification_channel == 'push':
            settings.notification_channel = 'telegram'
        elif settings.notification_channel == 'both':
            settings.notification_channel = 'telegram'
        db.commit()
    return {"status": "unsubscribed"}


@router.put("/notifications/channel/{employee_id}")
async def update_notification_channel(
    employee_id: int,
    channel: str,  # 'telegram', 'push', 'both'
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Обновить канал уведомлений: telegram, push или both"""
    if channel not in ('telegram', 'push', 'both'):
        raise HTTPException(status_code=400, detail="Допустимые каналы: telegram, push, both")
    if employee_id != current_user.id and current_user.role not in SUPERUSER_ROLES:
        raise HTTPException(status_code=403, detail="Нет прав")
    settings = db.query(NotificationSettings).filter_by(employee_id=employee_id).first()
    if not settings:
        settings = NotificationSettings(employee_id=employee_id)
        db.add(settings)
    settings.notification_channel = channel
    db.commit()
    return {"status": "ok", "channel": channel}


# ── ДИНАМИЧЕСКИЕ ПУТИ ──

@router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить уведомления текущего пользователя"""
    query = db.query(Notification).filter(Notification.employee_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    return query.order_by(Notification.created_at.desc()).all()


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отметить все уведомления текущего пользователя как прочитанные"""
    now = datetime.utcnow()
    updated = db.query(Notification).filter(
        Notification.employee_id == current_user.id,
        Notification.is_read == False,
    ).update({
        Notification.is_read: True,
        Notification.read_at: now,
    }, synchronize_session='fetch')
    db.commit()
    return {"message": f"Прочитано {updated} уведомлений", "count": updated}


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отметить уведомление как прочитанное"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.employee_id == current_user.id,
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    return {"message": "Уведомление прочитано"}


@router.post("/employees/{employee_id}/send-invite")
async def send_employee_invite(
    employee_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отправить приглашение сотруднику: welcome email + Telegram deep link"""
    if current_user.role not in SUPERUSER_ROLES:
        raise HTTPException(status_code=403, detail="Только директор может отправлять приглашения")

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    if not employee.email:
        raise HTTPException(status_code=400, detail="Email сотрудника не заполнен")

    # Генерация одноразового токена Telegram (действует 30 дней)
    token = secrets.token_hex(16)
    employee.telegram_link_token = token
    employee.telegram_link_token_expires = datetime.utcnow() + timedelta(days=30)

    # Временный пароль: используем существующий или генерируем новый
    from auth import get_password_hash
    if employee.invite_temp_password:
        temp_password = employee.invite_temp_password
    else:
        temp_password = secrets.token_urlsafe(8)
        employee.invite_temp_password = temp_password
        employee.password_hash = get_password_hash(temp_password)

    db.commit()

    from email_service import get_email_service
    email_svc = get_email_service()

    if not email_svc.available:
        raise HTTPException(status_code=503, detail="Email-сервис не настроен")

    # Получить реальный bot_username из Telegram API
    bot_username = "festival_color_crm_bot"  # fallback
    try:
        from telegram_service import get_telegram_service
        tg = get_telegram_service()
        if tg.bot_available:
            bot_info = await tg._bot.get_me()
            if bot_info.username:
                bot_username = bot_info.username
    except Exception as e:
        logger.warning(f"Не удалось получить bot_username: {e}")

    # Получить ссылку на скачивание из настроек
    from routers.messenger_router import load_messenger_settings
    messenger_settings = load_messenger_settings(db)
    download_link = messenger_settings.get(
        "app_download_url",
        "https://disk.yandex.ru/d/5LT3jFbE5ISHpA"
    )

    try:
        ok = await email_svc.send_welcome_email(
            to_email=employee.email,
            employee_name=employee.full_name,
            login=employee.login or "",
            password=temp_password,
            telegram_token=token,
            bot_username=bot_username,
            download_link=download_link,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка SMTP: {e}")

    if not ok:
        raise HTTPException(status_code=500, detail="Ошибка отправки письма")

    return {"ok": True, "message": f"Приглашение отправлено на {employee.email}"}

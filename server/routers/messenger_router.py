"""
Роутер мессенджера (messenger) — чаты, скрипты, настройки, MTProto.
Подключается в main.py через:
    app.include_router(messenger_router, prefix="/api/messenger")
    app.include_router(sync_messenger_router, prefix="/api/sync")
"""
import logging
import os
import asyncio
import tempfile
import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import sqlalchemy as sa
from sqlalchemy.orm import Session
from typing import List, Optional

from database import (
    get_db, Employee, Client, Contract, ProjectFile,
    CRMCard, SupervisionCard,
    MessengerChat, MessengerChatMember, MessengerScript, MessengerSetting, MessengerMessageLog,
)
from auth import get_current_user
from constants import SUPERUSER_ROLES
from permissions import require_permission
from pydantic import BaseModel
from messenger_schemas import (
    MessengerChatCreate, MessengerChatBind, SupervisionChatCreate,
    MessengerChatResponse, MessengerChatDetailResponse,
    ChatMemberInput, ChatMemberResponse,
    MessengerScriptCreate, MessengerScriptUpdate, MessengerScriptResponse,
    MessengerSettingUpdate, MessengerSettingResponse, MessengerSettingsBulkUpdate,
    SendMessageRequest, SendFilesRequest, SendScriptMessageRequest, MessageLogResponse,
    SendInvitesRequest, PreviewScriptRequest, PreviewScriptResponse, SendEditedScriptRequest,
    PreviewActRequest, PreviewActResponse, SendActRequest,
)
from telegram_service import get_telegram_service, PYROGRAM_AVAILABLE
from email_service import get_email_service
from services.notification_service import (
    send_invites_to_members, build_script_context, decline_name_dative,
    trigger_messenger_notification, trigger_supervision_notification,
    _find_matching_script,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["messenger"])
sync_messenger_router = APIRouter(tags=["sync"])

# PostgreSQL advisory lock namespace для предотвращения дублей между воркерами
_CHAT_CREATE_LOCK_NS = 900100  # namespace для pg_advisory_xact_lock(ns, card_id)


# =============================================
# HELPER-ФУНКЦИИ
# =============================================

_settings_cache = {'data': None, 'ts': 0}


def load_messenger_settings(db: Session, force: bool = False) -> dict:
    """Загрузить настройки мессенджера из БД с кэшированием (TTL 60 сек)"""
    if not force and _settings_cache['data'] is not None and time.time() - _settings_cache['ts'] < 60:
        return _settings_cache['data']
    result = {}
    for row in db.query(MessengerSetting).all():
        result[row.setting_key] = row.setting_value or ""
    _settings_cache['data'] = result
    _settings_cache['ts'] = time.time()
    return result


def seed_default_messenger_scripts(db: Session):
    """Заполнить дефолтные скрипты если таблица пуста"""
    # Блокировка от параллельного seed из нескольких worker'ов
    try:
        db.execute(sa.text("SELECT pg_advisory_lock(777888999)"))
    except Exception:
        pass  # SQLite не поддерживает advisory locks
    try:
        existing = db.query(MessengerScript).count()
        if existing > 0:
            return
        _do_seed_scripts(db)
    finally:
        try:
            db.execute(sa.text("SELECT pg_advisory_unlock(777888999)"))
        except Exception:
            pass


def _do_seed_scripts(db: Session):
    """Внутренняя функция — создание дефолтных скриптов"""

    defaults = [
        # =============================================
        # CRM ИНДИВИДУАЛЬНЫЕ — project_start (§6.1)
        # =============================================
        MessengerScript(
            name="Начало проекта (инд.)",
            script_type="project_start",
            project_type="Индивидуальный",
            stage_name=None,
            message_template=(
                "Здравствуйте, {client_first_name}!\n\n"
                "Рады приветствовать Вас в проектном чате студии Festival Color!\n\n"
                "Это Ваш персональный чат по проекту по адресу: {address}.\n"
                "Номер договора: {contract_number}.\n"
                "Площадь объекта: {area} м².\n\n"
                "Ваша команда:\n"
                " — Старший менеджер: {senior_manager} (@{senior_manager_username})\n"
                " — Менеджер: {manager_name} (@{manager_username})\n"
                " — Старший дизайнер-проектировщик: {sdp} (@{sdp_username})\n"
                " — Руководитель студии: {director} (@{director_username})\n\n"
                "Через этот чат Вы будете получать уведомления о ходе работы\n"
                "над Вашим проектом, а также сможете задать любые вопросы.\n\n"
                "В этом чате мы будем:\n"
                " — Отправлять Вам результаты работы на каждом этапе\n"
                " — Уведомлять о сроках рассмотрения\n"
                " — Принимать Ваши замечания и пожелания\n\n"
                "Прикрепляем памятку клиента — в ней описаны основные этапы\n"
                "работы и что от Вас потребуется на каждом из них.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=1,
        ),
        # =============================================
        # CRM ИНДИВИДУАЛЬНЫЕ — stage_complete (§6.2)
        # =============================================
        MessengerScript(
            name="Планировки (первичная)",
            script_type="stage_complete",
            project_type="Индивидуальный",
            stage_name="Стадия 1, подэтап 1.1",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) завершена разработка\n"
                "3 вариантов планировочных решений.\n\n"
                "Результаты работы направлены Вам на рассмотрение.\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение и предоставление замечаний: {deadline}\n"
                "(3 рабочих дня с момента отправки).\n\n"
                "Пожалуйста, ознакомьтесь с материалами и сообщите:\n"
                " — Всё устраивает — и мы продолжим работу\n"
                " — Есть замечания — опишите их в этом чате, и мы внесём\n"
                "   необходимые корректировки\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=2,
        ),
        MessengerScript(
            name="Фин. планировка (1 круг)",
            script_type="stage_complete",
            project_type="Индивидуальный",
            stage_name="Стадия 1, подэтап 1.2",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) подготовлено финальное\n"
                "планировочное решение с учётом Ваших пожеланий.\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "Пожалуйста, ознакомьтесь с обновлёнными материалами.\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=3,
        ),
        MessengerScript(
            name="Планировка (2 круг правок)",
            script_type="stage_complete",
            project_type="Индивидуальный",
            stage_name="Стадия 1, подэтап 1.3",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) выполнена доработка\n"
                "планировочного решения (2 круг правок).\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=4,
        ),
        MessengerScript(
            name="Планировка (платный круг)",
            script_type="stage_complete",
            project_type="Индивидуальный",
            stage_name="Стадия 1, платный круг",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) выполнена доработка\n"
                "планировочного решения (дополнительный круг правок).\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=5,
        ),
        MessengerScript(
            name="Мудборды",
            script_type="stage_complete",
            project_type="Индивидуальный",
            stage_name="Стадия 2, подэтап 2.1",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) разработаны мудборды —\n"
                "визуальные концепции будущего интерьера.\n\n"
                "Мудборды определяют стилистическое направление, цветовую палитру\n"
                "и ключевые элементы дизайна Вашего пространства.\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "Пожалуйста, сообщите, какое направление Вам ближе, или\n"
                "опишите пожелания по корректировке.\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=6,
        ),
        MessengerScript(
            name="Визуализация 1 помещения",
            script_type="stage_complete",
            project_type="Индивидуальный",
            stage_name="Стадия 2, подэтап 2.2",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) подготовлена визуализация\n"
                "первого помещения.\n\n"
                "Это позволит оценить, как будет выглядеть пространство\n"
                "по утверждённой концепции, и при необходимости скорректировать\n"
                "детали до начала работы над остальными помещениями.\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=7,
        ),
        MessengerScript(
            name="Виз. 1 пом. (1 круг правок)",
            script_type="stage_complete",
            project_type="Индивидуальный",
            stage_name="Стадия 2, подэтап 2.3",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) выполнена доработка\n"
                "визуализации первого помещения с учётом Ваших замечаний\n"
                "(1 круг правок).\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=8,
        ),
        MessengerScript(
            name="Виз. 1 пом. (2 круг правок)",
            script_type="stage_complete",
            project_type="Индивидуальный",
            stage_name="Стадия 2, подэтап 2.4",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) выполнена доработка\n"
                "визуализации первого помещения (2 круг правок).\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=9,
        ),
        MessengerScript(
            name="Визуализации всех помещений",
            script_type="stage_complete",
            project_type="Индивидуальный",
            stage_name="Стадия 2, подэтап 2.5",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) подготовлены визуализации\n"
                "всех помещений.\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "Пожалуйста, ознакомьтесь с визуализациями и сообщите\n"
                "Ваши замечания или одобрение.\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=10,
        ),
        MessengerScript(
            name="Виз. все (1 круг правок)",
            script_type="stage_complete",
            project_type="Индивидуальный",
            stage_name="Стадия 2, подэтап 2.6",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) выполнена доработка\n"
                "визуализаций всех помещений с учётом Ваших замечаний\n"
                "(1 круг правок).\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=11,
        ),
        MessengerScript(
            name="Виз. все (2 круг правок)",
            script_type="stage_complete",
            project_type="Индивидуальный",
            stage_name="Стадия 2, подэтап 2.7",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) выполнена доработка\n"
                "визуализаций всех помещений (2 круг правок).\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=12,
        ),
        MessengerScript(
            name="Визуализация (платный круг)",
            script_type="stage_complete",
            project_type="Индивидуальный",
            stage_name="Стадия 2, платный круг",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) выполнена доработка\n"
                "визуализаций (дополнительный круг правок).\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=13,
        ),
        MessengerScript(
            name="Рабочая документация",
            script_type="stage_complete",
            project_type="Индивидуальный",
            stage_name="Стадия 3",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) подготовлен комплект рабочей\n"
                "документации (рабочие чертежи).\n\n"
                "Этот комплект содержит все необходимые чертежи и спецификации\n"
                "для начала строительно-отделочных работ.\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=14,
        ),
        MessengerScript(
            name="Раб. документация (платный круг)",
            script_type="stage_complete",
            project_type="Индивидуальный",
            stage_name="Стадия 3, платный круг",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) выполнена доработка\n"
                "рабочей документации (дополнительный круг правок).\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=15,
        ),
        # =============================================
        # CRM ИНДИВИДУАЛЬНЫЕ — project_end (§6.4)
        # =============================================
        MessengerScript(
            name="Завершение проекта (инд.)",
            script_type="project_end",
            project_type="Индивидуальный",
            stage_name=None,
            message_template=(
                "{client_first_name}, здравствуйте!\n\n"
                "Рады сообщить, что работа над Вашим проектом ({address})\n"
                "полностью завершена!\n\n"
                "Все этапы пройдены:\n"
                " — Планировочные решения — согласованы\n"
                " — Концепция дизайна — утверждена\n"
                " — Рабочая документация — передана\n\n"
                "Всё готово!\n\n"
                "Благодарим Вас за доверие и сотрудничество!\n\n"
                "Мы будем очень признательны, если Вы оставите отзыв о нашей\n"
                "работе — это поможет нам стать лучше:\n"
                "{review_link}\n\n"
                "В приложении — памятка с полезной информацией на этапе\n"
                "реализации проекта.\n\n"
                "Если в будущем потребуется авторский надзор за ремонтом\n"
                "или другие услуги — обращайтесь, мы всегда на связи!\n\n"
                "С благодарностью,\n"
                "{sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=16,
        ),
        # =============================================
        # CRM ШАБЛОННЫЕ — project_start (§6.1)
        # =============================================
        MessengerScript(
            name="Начало проекта (шабл.)",
            script_type="project_start",
            project_type="Шаблонный",
            stage_name=None,
            message_template=(
                "Здравствуйте, {client_first_name}!\n\n"
                "Рады приветствовать Вас в проектном чате студии Festival Color!\n\n"
                "Это Ваш персональный чат по проекту по адресу: {address}.\n"
                "Номер договора: {contract_number}.\n\n"
                "Ваша команда:\n"
                " — Старший менеджер: {senior_manager} (@{senior_manager_username})\n"
                " — Менеджер: {manager_name} (@{manager_username})\n\n"
                "Здесь Вы будете получать уведомления о ходе работы,\n"
                "результаты на каждом этапе и сможете задавать вопросы.\n\n"
                "Прикрепляем памятку клиента с описанием этапов и сроков.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=17,
        ),
        # =============================================
        # CRM ШАБЛОННЫЕ — stage_complete (§6.3)
        # =============================================
        MessengerScript(
            name="Планировки (шабл.)",
            script_type="stage_complete",
            project_type="Шаблонный",
            stage_name="Стадия 1",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) подготовлены варианты\n"
                "планировочных решений.\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "Ознакомьтесь и выберите наиболее подходящий вариант,\n"
                "или сообщите пожелания в этом чате.\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=18,
        ),
        MessengerScript(
            name="Фин. планировка (шабл.)",
            script_type="stage_complete",
            project_type="Шаблонный",
            stage_name="Стадия 1, подэтап 1.2",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) подготовлен финальный вариант\n"
                "планировочных решений с учётом Ваших пожеланий.\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=19,
        ),
        MessengerScript(
            name="Рабочие чертежи (шабл.)",
            script_type="stage_complete",
            project_type="Шаблонный",
            stage_name="Стадия 2",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) подготовлен комплект\n"
                "рабочих чертежей.\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=20,
        ),
        MessengerScript(
            name="3Д визуализация (шабл.)",
            script_type="stage_complete",
            project_type="Шаблонный",
            stage_name="Стадия 3",
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему проекту ({address}) подготовлены 3Д визуализации\n"
                "интерьера.\n"
                "{stage_files}\n\n"
                "Срок на рассмотрение: {deadline} (3 рабочих дня).\n\n"
                "При необходимости видеосозвона напишите удобную дату.\n"
                "Если необходимо больше времени на рассмотрение, просим\n"
                "Вас сообщить об этом.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=21,
        ),
        # =============================================
        # CRM ШАБЛОННЫЕ — project_end (§6.4)
        # =============================================
        MessengerScript(
            name="Завершение проекта (шабл.)",
            script_type="project_end",
            project_type="Шаблонный",
            stage_name=None,
            message_template=(
                "{client_first_name}, здравствуйте!\n\n"
                "Работа над Вашим проектом ({address}) завершена!\n\n"
                "Всё готово!\n\n"
                "Благодарим за доверие!\n\n"
                "Будем признательны за Ваш отзыв:\n"
                "{review_link}\n\n"
                "В приложении — полезная памятка.\n"
                "Если потребуются дополнительные услуги — обращайтесь!\n\n"
                "С благодарностью,\n"
                "{sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=22,
        ),
        # =============================================
        # АВТОРСКИЙ НАДЗОР — supervision_start (§7.1)
        # =============================================
        MessengerScript(
            name="Начало надзора",
            script_type="supervision_start",
            project_type="Авторский надзор",
            stage_name=None,
            message_template=(
                "{client_first_name}, здравствуйте!\n\n"
                "Рады сообщить, что по Вашему объекту ({address})\n"
                "начинается этап авторского надзора!\n\n"
                "Это означает, что наша команда будет сопровождать Вас\n"
                "на всех этапах закупок и помогать выбрать именно те материалы,\n"
                "которые предусмотрены дизайн-проектом. Также мы будем помогать\n"
                "в ремонте и общении со строительной бригадой.\n\n"
                "Ваша команда:\n"
                " — Старший менеджер: {senior_manager} (@{senior_manager_username})\n"
                " — Дизайнер авторского надзора: {dan} (@{dan_username})\n"
                " — Руководитель студии: {director} (@{director_username})\n\n"
                "В этом чате мы будем:\n"
                " — Отправлять отчёты по каждой стадии закупок\n"
                " — Согласовывать выбранные позиции\n"
                " — Помогать с вопросами по материалам и поставщикам\n"
                " — Координировать работу со строительной бригадой\n\n"
                "Прикрепляем памятку — в ней описаны все 12 стадий закупок\n"
                "и что от Вас потребуется на каждой из них.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=23,
        ),
        # =============================================
        # АВТОРСКИЙ НАДЗОР — supervision_stage_complete (§7.2)
        # =============================================
        MessengerScript(
            name="Завершение стадии надзора",
            script_type="supervision_stage_complete",
            project_type="Авторский надзор",
            stage_name=None,
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему объекту ({address}) завершена стадия:\n"
                "\"{stage_name}\".\n\n"
                "В приложении — отчёт по данной стадии с перечнем\n"
                "выбранных позиций, поставщиков и стоимости.\n\n"
                "Если у Вас есть вопросы по выбранным позициям — пишите\n"
                "в этот чат, мы оперативно ответим.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=True,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=24,
        ),
        # =============================================
        # АВТОРСКИЙ НАДЗОР — supervision_visit (§7.3)
        # =============================================
        MessengerScript(
            name="Выезд надзора",
            script_type="supervision_visit",
            project_type="Авторский надзор",
            stage_name=None,
            message_template=(
                "{client_first_name}, добрый день!\n\n"
                "По Вашему объекту ({address}) состоялся выезд авторского\n"
                "надзора ({visit_date}).\n\n"
                "В приложении — отчёт по результатам выезда.\n\n"
                "Если у Вас есть вопросы — пишите в этот чат.\n\n"
                "С уважением, {sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=False,
            attach_stage_files=True,
            is_enabled=True,
            sort_order=25,
        ),
        # =============================================
        # АВТОРСКИЙ НАДЗОР — supervision_end (§7.4)
        # =============================================
        MessengerScript(
            name="Завершение надзора",
            script_type="supervision_end",
            project_type="Авторский надзор",
            stage_name=None,
            message_template=(
                "{client_first_name}, здравствуйте!\n\n"
                "Авторский надзор по Вашему объекту ({address})\n"
                "полностью завершён!\n\n"
                "Все 12 стадий закупок пройдены, необходимые материалы\n"
                "и оборудование подобраны и согласованы.\n\n"
                "Ремонт завершён — поздравляем! Желаем Вам получать\n"
                "настоящее удовольствие от жизни в Вашем новом доме!\n\n"
                "Благодарим Вас за доверие на протяжении всего проекта!\n\n"
                "Мы будем очень признательны за Ваш отзыв о нашей работе:\n"
                "{review_link}\n\n"
                "В приложении — памятка с рекомендациями по приёмке\n"
                "материалов и контролю ремонтных работ.\n\n"
                "Если возникнут вопросы — обращайтесь, мы всегда на связи!\n\n"
                "С благодарностью,\n"
                "{sender_name}\n"
                "Festival Color"
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=26,
        ),
        # =============================================
        # ЛИЧНЫЕ УВЕДОМЛЕНИЯ — Индивидуальные проекты (§2)
        # =============================================
        MessengerScript(
            name="Назначение на проект",
            script_type="personal_assigned",
            project_type="Индивидуальный",
            stage_name=None,
            message_template=(
                "Вы назначены {role_name} по проекту {address} ({client_name})."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=27,
        ),
        MessengerScript(
            name="Смена стадии (исполнитель)",
            script_type="personal_crm_stage",
            project_type="Индивидуальный",
            stage_name=None,
            message_template=(
                "Проект {address} перешёл в \"{stage_name}\". Приступайте к работе."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=28,
        ),
        MessengerScript(
            name="Смена стадии (проверяющий)",
            script_type="personal_crm_stage",
            project_type="Индивидуальный",
            stage_name=None,
            message_template=(
                "Проект {address} перешёл в \"{stage_name}\". Вы — проверяющий."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=29,
        ),
        MessengerScript(
            name="Сдача работы (проверяющему)",
            script_type="personal_crm_stage",
            project_type="Индивидуальный",
            stage_name=None,
            message_template=(
                "{executor_role} сдал работу по проекту {address}, стадия \"{stage_name}\". Проверьте."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=30,
        ),
        MessengerScript(
            name="Возврат на исправление",
            script_type="personal_crm_stage",
            project_type="Индивидуальный",
            stage_name=None,
            message_template=(
                "Работа по проекту {address} возвращена на исправление (правка #{revision_count})."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=31,
        ),
        MessengerScript(
            name="Отправлено клиенту",
            script_type="personal_crm_stage",
            project_type="Индивидуальный",
            stage_name=None,
            message_template=(
                "Проект {address} отправлен клиенту на согласование ({stage_name})."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=32,
        ),
        MessengerScript(
            name="Клиент согласовал",
            script_type="personal_crm_stage",
            project_type="Индивидуальный",
            stage_name=None,
            message_template=(
                "Клиент согласовал {stage_name} по проекту {address}."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=33,
        ),
        MessengerScript(
            name="Акт подписан",
            script_type="personal_crm_stage",
            project_type="Индивидуальный",
            stage_name=None,
            message_template=(
                "Акт по {stage_name} проекта {address} подписан."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=34,
        ),
        MessengerScript(
            name="Проект завершён (личное)",
            script_type="personal_crm_stage",
            project_type="Индивидуальный",
            stage_name=None,
            message_template=(
                "Проект {address} завершён."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=35,
        ),
        MessengerScript(
            name="Дедлайн через 2 дня",
            script_type="personal_deadline",
            project_type="Индивидуальный",
            stage_name=None,
            message_template=(
                "Дедлайн по проекту {address} через 2 рабочих дня ({deadline_date})."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=36,
        ),
        MessengerScript(
            name="Дедлайн просрочен",
            script_type="personal_deadline",
            project_type="Индивидуальный",
            stage_name=None,
            message_template=(
                "Дедлайн по проекту {address} просрочен! Было: {deadline_date}."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=37,
        ),
        MessengerScript(
            name="Создание оплаты",
            script_type="personal_payment",
            project_type="Индивидуальный",
            stage_name=None,
            message_template=(
                "Создана оплата {amount} руб. по договору {contract_number} ({address})."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=38,
        ),
        # =============================================
        # ЛИЧНЫЕ УВЕДОМЛЕНИЯ — Шаблонные проекты (§3)
        # =============================================
        MessengerScript(
            name="Назначение на проект (шабл.)",
            script_type="personal_assigned",
            project_type="Шаблонный",
            stage_name=None,
            message_template=(
                "Вы назначены {role_name} по проекту {address} ({client_name})."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=39,
        ),
        MessengerScript(
            name="Смена стадии (шабл., исполнитель)",
            script_type="personal_crm_stage",
            project_type="Шаблонный",
            stage_name=None,
            message_template=(
                "Проект {address} перешёл в \"{stage_name}\". Приступайте к работе."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=40,
        ),
        MessengerScript(
            name="Сдача работы (шабл., проверяющему)",
            script_type="personal_crm_stage",
            project_type="Шаблонный",
            stage_name=None,
            message_template=(
                "{executor_role} сдал работу по проекту {address}. Проверьте."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=41,
        ),
        MessengerScript(
            name="Проект завершён (шабл., личное)",
            script_type="personal_crm_stage",
            project_type="Шаблонный",
            stage_name=None,
            message_template=(
                "Проект {address} завершён."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=42,
        ),
        MessengerScript(
            name="Дедлайн через 2 дня (шабл.)",
            script_type="personal_deadline",
            project_type="Шаблонный",
            stage_name=None,
            message_template=(
                "Дедлайн по проекту {address} через 2 рабочих дня ({deadline_date})."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=43,
        ),
        MessengerScript(
            name="Дедлайн просрочен (шабл.)",
            script_type="personal_deadline",
            project_type="Шаблонный",
            stage_name=None,
            message_template=(
                "Дедлайн по проекту {address} просрочен! Было: {deadline_date}."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=44,
        ),
        # =============================================
        # ЛИЧНЫЕ УВЕДОМЛЕНИЯ — Авторский надзор (§4)
        # =============================================
        MessengerScript(
            name="Создание карточки надзора",
            script_type="personal_supervision",
            project_type="Авторский надзор",
            stage_name=None,
            message_template=(
                "Новая карточка авторского надзора: {address} ({client_name}). Назначьте сотрудников."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=45,
        ),
        MessengerScript(
            name="Назначение ДАН",
            script_type="personal_supervision",
            project_type="Авторский надзор",
            stage_name=None,
            message_template=(
                "Вы назначены дизайнером авторского надзора по объекту {address} ({client_name})."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=46,
        ),
        MessengerScript(
            name="Дедлайн стадии надзора",
            script_type="personal_deadline",
            project_type="Авторский надзор",
            stage_name=None,
            message_template=(
                "Дедлайн по стадии \"{stage_name}\" надзора {address} через 2 рабочих дня ({deadline_date})."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=47,
        ),
        MessengerScript(
            name="Завершение стадии (личное)",
            script_type="personal_supervision",
            project_type="Авторский надзор",
            stage_name=None,
            message_template=(
                "Стадия \"{stage_name}\" завершена по надзору {address}."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=48,
        ),
        MessengerScript(
            name="Приостановка надзора",
            script_type="personal_supervision",
            project_type="Авторский надзор",
            stage_name=None,
            message_template=(
                "Карточка надзора {address} приостановлена. Причина: {pause_reason}."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=49,
        ),
        MessengerScript(
            name="Возобновление надзора",
            script_type="personal_supervision",
            project_type="Авторский надзор",
            stage_name=None,
            message_template=(
                "Карточка надзора {address} возобновлена."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=50,
        ),
        MessengerScript(
            name="Выезд надзора (личное)",
            script_type="personal_supervision",
            project_type="Авторский надзор",
            stage_name=None,
            message_template=(
                "Запланирован выезд по надзору {address} на {visit_date}."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=51,
        ),
        MessengerScript(
            name="Надзор завершён (личное)",
            script_type="personal_supervision",
            project_type="Авторский надзор",
            stage_name=None,
            message_template=(
                "Авторский надзор по {address} завершён."
            ),
            use_auto_deadline=False,
            attach_stage_files=False,
            is_enabled=True,
            sort_order=52,
        ),
    ]

    for script in defaults:
        db.add(script)
    db.commit()
    logger.info(f"Создано {len(defaults)} дефолтных скриптов мессенджера")


def _build_chat_title(contract: Contract, card: CRMCard) -> str:
    """Сформировать название чата по контракту и CRM-карточке"""
    city = (contract.city or '').replace('_', '-')
    address = (contract.address or '').replace('_', '-')
    if city and address:
        city_map = {'спб': 'санкт-петербург', 'мск': 'москва', 'нск': 'новосибирск', 'екб': 'екатеринбург'}
        full_city = city_map.get(city.lower(), city.lower())
        addr_check = address.lower().replace('_', '-')
        for c in [full_city, city.lower()]:
            if addr_check.startswith(c):
                address = address[len(c):].lstrip('.,;:_ -')
                break
    # Определяем префикс по типу проекта: ИН — индивидуальный, ШП — шаблонный
    project_type = (contract.project_type or '').strip().lower()
    if 'шаблон' in project_type:
        prefix = "ШП"
    else:
        prefix = "ИН"
    return f"{prefix}-{city}-{address}"


def _add_chat_members(
    db: Session, chat: MessengerChat, members_input: list,
    contract: Contract, card: CRMCard = None
) -> list:
    """Добавить участников в чат"""
    members_resp = []

    for m in members_input:
        phone = None
        email = None

        telegram_user_id = None
        if m.member_type == 'employee':
            emp = db.query(Employee).filter(Employee.id == m.member_id).first()
            if emp:
                phone = emp.phone
                email = emp.email
                telegram_user_id = emp.telegram_user_id
        elif m.member_type == 'client':
            cl = db.query(Client).filter(Client.id == m.member_id).first()
            if cl:
                phone = cl.phone
                email = cl.email

        member = MessengerChatMember(
            messenger_chat_id=chat.id,
            member_type=m.member_type,
            member_id=m.member_id,
            role_in_project=m.role_in_project,
            is_mandatory=m.is_mandatory,
            phone=phone,
            email=email,
            telegram_user_id=telegram_user_id,
            invite_status='pending',
        )
        db.add(member)
        db.flush()
        members_resp.append(ChatMemberResponse.model_validate(member))

    return members_resp


# =============================================
# PREVIEW SCRIPT (предпросмотр перед отправкой)
# =============================================

@router.post("/preview-script", response_model=PreviewScriptResponse)
async def preview_script(
    data: PreviewScriptRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Предпросмотр скрипта с рендерингом переменных и списком файлов подэтапа"""
    from database import ProjectTimelineEntry, StageWorkflowState

    card = db.query(CRMCard).filter(CRMCard.id == data.card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="CRM-карточка не найдена")
    contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    stage_name = data.stage_name or card.column_name or ''
    project_type = contract.project_type or ''

    # Определяем stage_group и текущий подэтап через workflow state
    from routers.crm_router import _resolve_stage_group, _add_business_days
    stage_group = _resolve_stage_group(stage_name)

    # Получить текущий подэтап из workflow state → substage_group из timeline
    script_stage_name = stage_name  # fallback
    wf = db.query(StageWorkflowState).filter(
        StageWorkflowState.crm_card_id == data.card_id,
        StageWorkflowState.stage_name == stage_name
    ).first()

    substage_group = ''
    if wf and wf.current_substep_code and stage_group:
        # Найти timeline entry по substep_code → получить substage_group
        tl_entry = db.query(ProjectTimelineEntry).filter(
            ProjectTimelineEntry.contract_id == contract.id,
            ProjectTimelineEntry.stage_code == wf.current_substep_code,
        ).first()
        if tl_entry and tl_entry.substage_group:
            substage_group = tl_entry.substage_group
            # Скрипты имеют stage_name в формате "Стадия N, подэтап X.Y"
            # Маппинг: STAGE1 + "Подэтап 1.1" → "Стадия 1, подэтап 1.1"
            stage_num = stage_group.replace('STAGE', '')
            substep_num = substage_group.replace('Подэтап ', '')
            script_stage_name = f"Стадия {stage_num}, подэтап {substep_num}"

    # 1. Найти подходящий скрипт
    script = _find_matching_script(db, data.script_type, script_stage_name, project_type)

    # 2. Собрать контекст и рендерить
    ctx = build_script_context(db, card, contract)
    ctx['stage_name'] = substage_group or stage_name

    # Подпись отправителя = текущий пользователь (не роль из карточки)
    sender_name = current_user.full_name or ''
    ctx['sender_name'] = sender_name
    # Шаблоны используют {senior_manager} или {manager_name} для подписи —
    # в превью заменяем на текущего пользователя (plain text, без tg-ссылки)
    ctx['senior_manager'] = sender_name
    ctx['manager_name'] = sender_name

    # 3. Вычислить дедлайн по норма-дням
    deadline_str = ''
    norm_days_val = 0

    if stage_group:
        # Ищем следующую незаполненную клиентскую строку в текущем подэтапе
        client_q = db.query(ProjectTimelineEntry).filter(
            ProjectTimelineEntry.contract_id == contract.id,
            ProjectTimelineEntry.stage_group == stage_group,
            ProjectTimelineEntry.executor_role == 'Клиент',
            ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == '')
        )
        if substage_group:
            client_q = client_q.filter(
                ProjectTimelineEntry.substage_group == substage_group
            )
        client_entry = client_q.order_by(ProjectTimelineEntry.sort_order).first()

        if client_entry:
            norm_days_val = client_entry.custom_norm_days or client_entry.norm_days or 3
            prev_entry = db.query(ProjectTimelineEntry).filter(
                ProjectTimelineEntry.contract_id == contract.id,
                ProjectTimelineEntry.sort_order < client_entry.sort_order,
                ProjectTimelineEntry.actual_date.isnot(None),
                ProjectTimelineEntry.actual_date != ''
            ).order_by(ProjectTimelineEntry.sort_order.desc()).first()

            base_date = prev_entry.actual_date if prev_entry else None
            if not base_date:
                from datetime import date as date_type
                base_date = date_type.today().strftime('%Y-%m-%d')

            try:
                deadline_date = _add_business_days(base_date, norm_days_val)
                deadline_str = deadline_date.strftime('%d.%m.%Y')
            except Exception:
                pass

    ctx['deadline'] = deadline_str
    ctx['deadline_date'] = deadline_str

    rendered_text = ''
    script_id = None
    script_name = None
    if script:
        tg = get_telegram_service()
        rendered_text = tg.render_template(script.message_template, ctx)
        script_id = script.id
        script_name = script.name

    # 4. Файлы подэтапа
    # STAGE1 → stage1, STAGE2 → stage2, STAGE3 → stage3
    file_stage_code = stage_group.lower() if stage_group else ''
    files = db.query(ProjectFile).filter(
        ProjectFile.contract_id == contract.id,
        ProjectFile.stage == file_stage_code,
    ).order_by(ProjectFile.file_order, ProjectFile.variation).all()

    files_list = [{
        'id': f.id,
        'file_name': f.file_name,
        'yandex_path': f.yandex_path,
        'variation': f.variation,
        'file_type': f.file_type or 'file',
        'public_link': f.public_link or '',
    } for f in files]

    # 5. Найти чат для карточки
    chat = db.query(MessengerChat).filter(
        MessengerChat.crm_card_id == data.card_id,
        MessengerChat.is_active == True
    ).first()

    return PreviewScriptResponse(
        rendered_text=rendered_text,
        script_id=script_id,
        script_name=script_name,
        stage_name=stage_name,
        deadline_date=deadline_str,
        norm_days=norm_days_val,
        files=files_list,
        sender_name=sender_name,
        chat_id=chat.telegram_chat_id if chat else None,
        messenger_chat_id=chat.id if chat else None,
    )


# =============================================
# PREVIEW ACT (предпросмотр скрипта акта)
# =============================================

@router.post("/preview-act", response_model=PreviewActResponse)
async def preview_act(
    data: PreviewActRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Предпросмотр скрипта отправки акта клиенту"""
    card = db.query(CRMCard).filter(CRMCard.id == data.card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="CRM-карточка не найдена")
    contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    stage_name = card.column_name or ''
    sender_name = current_user.full_name or ''
    client_first_name = ''
    if contract.client_id:
        client = db.query(Client).filter(Client.id == contract.client_id).first()
        if client:
            parts = (client.full_name or '').split()
            client_first_name = parts[1] if len(parts) > 1 else parts[0] if parts else ''

    address = contract.address or ''

    # Определяем описание стадии для текста (с заглавной буквы)
    stage_desc = stage_name
    if 'планировочн' in stage_name.lower():
        stage_desc = 'Планировочные решения'
    elif 'концепция' in stage_name.lower() or 'дизайн' in stage_name.lower():
        stage_desc = 'Концепция дизайна'
    elif 'рабочие чертежи' in stage_name.lower() or 'рабочая документация' in stage_name.lower():
        stage_desc = 'Рабочая документация'

    # Генерируем текст скрипта акта
    rendered_text = (
        f"{client_first_name}, добрый день!\n\n"
        f"Работа по стадии: {stage_desc} Вашего проекта ({address}) "
        f"завершена и согласована.\n\n"
        f"Направляем Вам акт выполненных работ на подписание.\n\n"
        f"Просим ознакомиться, подписать и направить скан подписанного акта "
        f"в этот чат.\nПосле подписания акта мы сможем перейти к разработке "
        f"следующего этапа.\n\n"
        f"С уважением, {sender_name}\n"
        f"Festival Color"
    )

    # Определяем какие акты без подписи есть в договоре для данной стадии
    act_files = []
    stage_lower = stage_name.lower()

    act_mappings = []
    if 'планировочн' in stage_lower:
        act_mappings.append(('act_planning', 'Акт ПР'))
    elif 'концепция' in stage_lower or 'дизайн' in stage_lower:
        act_mappings.append(('act_concept', 'Акт КД'))
    elif 'рабочие чертежи' in stage_lower or 'рабочая документация' in stage_lower or 'чертежн' in stage_lower:
        act_mappings.append(('act_final', 'Акт финальный'))
        act_mappings.append(('info_letter', 'Информационное письмо'))

    for prefix, label in act_mappings:
        link = getattr(contract, f'{prefix}_link', '') or ''
        yandex_path = getattr(contract, f'{prefix}_yandex_path', '') or ''
        file_name = getattr(contract, f'{prefix}_file_name', '') or ''
        if link or yandex_path:
            act_files.append({
                'prefix': prefix,
                'label': label,
                'file_name': file_name or f'{label}.pdf',
                'link': link,
                'yandex_path': yandex_path,
            })

    # Чат
    chat = db.query(MessengerChat).filter(
        MessengerChat.crm_card_id == data.card_id,
        MessengerChat.is_active == True
    ).first()

    return PreviewActResponse(
        rendered_text=rendered_text,
        stage_name=stage_name,
        act_files=act_files,
        sender_name=sender_name,
        chat_id=chat.telegram_chat_id if chat else None,
        messenger_chat_id=chat.id if chat else None,
    )


@router.post("/send-act")
async def send_act(
    data: SendActRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отправить акт в групповой чат: текст + ссылки на файлы актов из договора"""
    card = db.query(CRMCard).filter(CRMCard.id == data.card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="CRM-карточка не найдена")

    chat = db.query(MessengerChat).filter(
        MessengerChat.crm_card_id == data.card_id,
        MessengerChat.is_active == True
    ).first()
    if not chat or not chat.telegram_chat_id:
        raise HTTPException(status_code=404, detail="Чат не найден или не привязан к Telegram")

    tg = get_telegram_service()

    # 1. Отправить текст
    await tg.send_message(chat.telegram_chat_id, data.text, parse_mode="HTML")

    # 2. Отправить ссылки на акты из договора
    #    link в БД — ссылка на ПАПКУ, не на файл.
    #    Поэтому собираем путь к конкретному файлу и публикуем его.
    sent_files = 0
    if data.act_prefixes:
        contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
        if contract:
            from yandex_disk_service import get_yandex_disk_service
            file_lines = []
            for prefix in data.act_prefixes:
                yandex_path = getattr(contract, f'{prefix}_yandex_path', '') or ''
                file_name = getattr(contract, f'{prefix}_file_name', '') or ''

                if not yandex_path or not file_name:
                    continue

                # yandex_path — путь к папке, file_name — имя файла
                file_full_path = f"{yandex_path}/{file_name}"
                try:
                    yd_svc = get_yandex_disk_service()
                    public_url = yd_svc.get_public_link(file_full_path)
                except Exception:
                    public_url = ''

                if public_url:
                    file_lines.append(f'<a href="{public_url}">{file_name}</a>')
                else:
                    file_lines.append(file_name)
                sent_files += 1

            if file_lines:
                files_msg = "\n".join(file_lines)
                await tg.send_message(chat.telegram_chat_id, files_msg, parse_mode="HTML")

    # 3. Логируем
    log = MessengerMessageLog(
        messenger_chat_id=chat.id,
        message_type='act',
        message_text=data.text[:500],
        sent_by=current_user.id,
        delivery_status='sent',
    )
    db.add(log)
    db.commit()

    return {"status": "sent", "sent_files": sent_files}


@router.post("/send-edited-script")
async def send_edited_script(
    data: SendEditedScriptRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отправить отредактированный скрипт в групповой чат + прикрепить выбранные файлы"""
    from database import ProjectTimelineEntry

    card = db.query(CRMCard).filter(CRMCard.id == data.card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="CRM-карточка не найдена")

    # Найти активный чат
    chat = db.query(MessengerChat).filter(
        MessengerChat.crm_card_id == data.card_id,
        MessengerChat.is_active == True
    ).first()
    if not chat or not chat.telegram_chat_id:
        raise HTTPException(status_code=404, detail="Чат не найден или не привязан к Telegram")

    tg = get_telegram_service()

    # 1. Отправить текст
    msg_id = await tg.send_message(chat.telegram_chat_id, data.text, parse_mode="HTML")

    # 2. Отправить выбранные файлы как ссылки на Яндекс.Диск
    #    (мгновенно, без скачивания/загрузки, без лимита 50МБ)
    sent_file_count = 0
    if data.file_ids:
        file_lines = []
        for file_id in data.file_ids:
            pf = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
            if not pf:
                continue
            link = pf.public_link or ''
            if not link and pf.yandex_path:
                # Генерируем ссылку из пути ЯД
                from urllib.parse import quote
                yd_path = pf.yandex_path
                if yd_path.startswith('disk:'):
                    yd_path = yd_path[5:]
                encoded = quote(yd_path, safe='/')
                link = f"https://disk.yandex.ru/client/disk{encoded}"
            if link:
                file_lines.append(f'<a href="{link}">{pf.file_name}</a>')
            else:
                file_lines.append(pf.file_name)
            sent_file_count += 1

        if file_lines:
            files_msg = "\n".join(file_lines)
            await tg.send_message(chat.telegram_chat_id, files_msg, parse_mode="HTML")

    # 3. Обновить custom_norm_days если дедлайн изменён вручную
    if data.custom_deadline and data.deadline_date:
        from routers.crm_router import _resolve_stage_group, _add_business_days
        contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
        stage_group = _resolve_stage_group(card.column_name)
        if stage_group and contract:
            client_entry = db.query(ProjectTimelineEntry).filter(
                ProjectTimelineEntry.contract_id == contract.id,
                ProjectTimelineEntry.stage_group == stage_group,
                ProjectTimelineEntry.executor_role == 'Клиент',
                ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == '')
            ).order_by(ProjectTimelineEntry.sort_order).first()

            if client_entry:
                # Считаем custom_norm_days из выбранного дедлайна
                try:
                    from datetime import date as date_type
                    dl = datetime.strptime(data.deadline_date, '%d.%m.%Y').date()
                    # Базовая дата — предыдущая заполненная строка или сегодня
                    prev_entry = db.query(ProjectTimelineEntry).filter(
                        ProjectTimelineEntry.contract_id == contract.id,
                        ProjectTimelineEntry.sort_order < client_entry.sort_order,
                        ProjectTimelineEntry.actual_date.isnot(None),
                        ProjectTimelineEntry.actual_date != ''
                    ).order_by(ProjectTimelineEntry.sort_order.desc()).first()

                    base = prev_entry.actual_date if prev_entry else date_type.today().strftime('%Y-%m-%d')
                    if isinstance(base, str):
                        base = datetime.strptime(base, '%Y-%m-%d').date()

                    # Считаем рабочие дни между base и dl
                    from routers.crm_router import _is_working_day
                    working = 0
                    cur = base
                    from datetime import timedelta
                    while cur < dl:
                        cur += timedelta(days=1)
                        if _is_working_day(cur):
                            working += 1

                    if working != (client_entry.norm_days or 3):
                        client_entry.custom_norm_days = working
                        client_entry.updated_at = datetime.utcnow()
                        logger.info(
                            f"custom_norm_days обновлён: {client_entry.norm_days} → {working} "
                            f"(contract={contract.id}, stage_group={stage_group})"
                        )
                except Exception as e:
                    logger.warning(f"Ошибка расчёта custom_norm_days: {e}")

    # 4. Логируем сообщение
    log = MessengerMessageLog(
        messenger_chat_id=chat.id,
        message_type='script_manual',
        message_text=data.text,
        sent_by=current_user.id,
        telegram_message_id=msg_id,
        delivery_status='sent' if msg_id else 'failed',
    )
    db.add(log)
    db.commit()

    return {
        "status": "sent" if msg_id else "failed",
        "telegram_message_id": msg_id,
        "sent_files": sent_file_count,
    }


# =============================================
# TRIGGER SCRIPT (ручная отправка скрипта)
# =============================================

class TriggerScriptRequest(BaseModel):
    card_id: int
    script_type: str  # project_start, project_end, stage_complete, supervision_start, supervision_end
    entity_type: str = 'crm'  # 'crm' или 'supervision'


@router.post("/trigger-script")
async def trigger_script_endpoint(
    request: TriggerScriptRequest,
    current_user: Employee = Depends(require_permission("messenger.create_chat")),
    db: Session = Depends(get_db)
):
    """Ручная отправка скрипта мессенджера"""
    if request.entity_type == 'supervision':
        await trigger_supervision_notification(request.card_id, request.script_type,
                                                sender_id=current_user.id)
    else:
        await trigger_messenger_notification(request.card_id, request.script_type,
                                              sender_id=current_user.id)

    return {"status": "success"}


# =============================================
# MESSENGER CHATS ENDPOINTS
# Порядок: статические пути ПЕРЕД динамическими
# =============================================

@router.post("/chats", response_model=MessengerChatDetailResponse)
async def create_messenger_chat(
    data: MessengerChatCreate,
    current_user: Employee = Depends(require_permission("messenger.create_chat")),
    db: Session = Depends(get_db)
):
    """Создать чат автоматически (MTProto) для CRM-карточки"""
    card_id = data.crm_card_id

    # PostgreSQL advisory lock — работает между воркерами uvicorn
    # pg_try_advisory_xact_lock возвращает false если лок уже занят другим воркером
    try:
        got_lock = db.execute(
            sa.text("SELECT pg_try_advisory_xact_lock(:ns, :card_id)"),
            {"ns": _CHAT_CREATE_LOCK_NS, "card_id": card_id}
        ).scalar()
    except Exception:
        got_lock = True  # fallback для SQLite (тестов)

    if not got_lock:
        raise HTTPException(status_code=409, detail="Чат уже создаётся, подождите")

    return await _do_create_messenger_chat(data, current_user, db)


async def _do_create_messenger_chat(
    data: MessengerChatCreate,
    current_user: Employee,
    db: Session,
):
    """Внутренняя логика создания чата (под lock)."""
    # Перечитываем настройки (для консистентности между воркерами)
    messenger_settings = load_messenger_settings(db)
    tg_svc = get_telegram_service()
    tg_svc.configure(messenger_settings)

    # Проверка: уже есть активный чат
    existing = db.query(MessengerChat).filter(
        MessengerChat.crm_card_id == data.crm_card_id,
        MessengerChat.is_active == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Чат для этой карточки уже существует")

    # Получаем карточку и контракт
    card = db.query(CRMCard).filter(CRMCard.id == data.crm_card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="CRM-карточка не найдена")
    contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    # Проверка обязательных ролей перед созданием чата
    project_type = (contract.project_type or '').strip()
    missing_roles = []
    if not card.senior_manager_id:
        missing_roles.append('Старший менеджер')
    if project_type == 'Индивидуальный':
        if not card.sdp_id:
            missing_roles.append('Старший дизайнер-проектировщик (СДП)')
    elif project_type == 'Шаблонный':
        if not card.manager_id:
            missing_roles.append('Менеджер')
    if missing_roles:
        roles_str = ', '.join(missing_roles)
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя создать чат: не назначены обязательные роли: {roles_str}"
        )

    tg = get_telegram_service()
    if not tg.mtproto_available:
        raise HTTPException(status_code=503, detail="MTProto не настроен. Используйте привязку чата.")

    # Формируем название чата (кастомное или автогенерация)
    chat_title = data.chat_title.strip() if data.chat_title else _build_chat_title(contract, card)

    # Определяем фото
    avatar_type = (contract.agent_type or '').lower()
    if 'фестиваль' in avatar_type or 'festival' in avatar_type:
        avatar_type = 'festival'
    elif 'петрович' in avatar_type or 'petrovich' in avatar_type:
        avatar_type = 'petrovich'
    else:
        avatar_type = 'festival'

    photo_path = os.path.join(os.path.dirname(__file__), '..', 'resources', f'{avatar_type}_logo.png')
    if not os.path.exists(photo_path):
        photo_path = None

    # Получаем username бота
    bot_username = None
    if tg.bot_available:
        try:
            bot_info = await tg._bot.get_me()
            bot_username = bot_info.username
        except Exception:
            pass

    # Создаём группу
    result = await tg.create_group(
        title=chat_title,
        photo_path=photo_path,
        bot_username=bot_username,
    )

    # Сохраняем в БД
    chat = MessengerChat(
        contract_id=contract.id,
        crm_card_id=data.crm_card_id,
        messenger_type=data.messenger_type,
        telegram_chat_id=result["chat_id"],
        chat_title=result["title"],
        invite_link=result["invite_link"],
        avatar_type=avatar_type,
        creation_method="auto",
        created_by=current_user.id,
        is_active=True,
    )
    db.add(chat)
    db.flush()

    # Добавляем участников
    members_resp = _add_chat_members(db, chat, data.members, contract, card)

    db.commit()

    # Рассылаем invite-ссылки асинхронно (с собственной сессией БД)
    asyncio.create_task(send_invites_to_members(chat.id))

    # Авто-триггер начального скрипта project_start
    try:
        if data.crm_card_id:
            asyncio.create_task(
                trigger_messenger_notification(data.crm_card_id, 'project_start',
                                               sender_id=current_user.id)
            )
    except Exception as e:
        logger.warning(f"Не удалось отправить project_start: {e}")

    return MessengerChatDetailResponse(
        chat=MessengerChatResponse.model_validate(chat),
        members=members_resp
    )


@router.post("/chats/bind", response_model=MessengerChatDetailResponse)
async def bind_messenger_chat(
    data: MessengerChatBind,
    current_user: Employee = Depends(require_permission("messenger.create_chat")),
    db: Session = Depends(get_db)
):
    """Привязать существующий чат по invite-ссылке"""
    # Проверка: уже есть активный чат
    existing = db.query(MessengerChat).filter(
        MessengerChat.crm_card_id == data.crm_card_id,
        MessengerChat.is_active == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Чат для этой карточки уже существует")

    card = db.query(CRMCard).filter(CRMCard.id == data.crm_card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="CRM-карточка не найдена")
    contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    chat_title = _build_chat_title(contract, card)

    # Определяем avatar_type
    avatar_type = (contract.agent_type or '').lower()
    if 'фестиваль' in avatar_type or 'festival' in avatar_type:
        avatar_type = 'festival'
    else:
        avatar_type = 'petrovich'

    # Вступаем в чат через MTProto + добавляем бота + повышаем до админа
    tg = get_telegram_service()
    messenger_settings = load_messenger_settings(db)
    tg.configure(messenger_settings)

    telegram_chat_id = None
    final_invite_link = data.invite_link

    join_result = await tg.join_chat_by_link(data.invite_link)
    if join_result:
        telegram_chat_id = join_result["chat_id"]
        final_invite_link = join_result.get("invite_link") or data.invite_link
        if join_result.get("title"):
            chat_title = join_result["title"]  # Используем реальное название чата
        logger.info(f"Привязка чата: вступили в {telegram_chat_id}, бот добавлен")
    else:
        logger.warning(f"Не удалось вступить в чат по ссылке {data.invite_link}, сохраняем без chat_id")

    chat = MessengerChat(
        contract_id=contract.id,
        crm_card_id=data.crm_card_id,
        messenger_type=data.messenger_type,
        telegram_chat_id=telegram_chat_id,
        chat_title=chat_title,
        invite_link=final_invite_link,
        avatar_type=avatar_type,
        creation_method="manual",
        created_by=current_user.id,
        is_active=True,
    )
    db.add(chat)
    db.flush()

    # Участники
    members_resp = _add_chat_members(db, chat, data.members, contract, card)

    db.commit()

    # Рассылаем invite-ссылки
    asyncio.create_task(send_invites_to_members(chat.id))

    return MessengerChatDetailResponse(
        chat=MessengerChatResponse.model_validate(chat),
        members=members_resp
    )


@router.post("/chats/supervision", response_model=MessengerChatDetailResponse)
async def create_supervision_chat(
    data: SupervisionChatCreate,
    current_user: Employee = Depends(require_permission("messenger.create_chat")),
    db: Session = Depends(get_db)
):
    """Создать чат автоматически (MTProto) для карточки надзора"""
    # Перечитываем настройки
    messenger_settings = load_messenger_settings(db)
    tg_svc = get_telegram_service()
    tg_svc.configure(messenger_settings)

    # Проверка: уже есть активный чат
    existing = db.query(MessengerChat).filter(
        MessengerChat.supervision_card_id == data.supervision_card_id,
        MessengerChat.is_active == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Чат для этой карточки надзора уже существует")

    # Получаем карточку надзора и контракт
    sv_card = db.query(SupervisionCard).filter(SupervisionCard.id == data.supervision_card_id).first()
    if not sv_card:
        raise HTTPException(status_code=404, detail="Карточка надзора не найдена")
    contract = db.query(Contract).filter(Contract.id == sv_card.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    # Проверка обязательных ролей для надзора
    missing_roles = []
    if not sv_card.senior_manager_id:
        missing_roles.append('Старший менеджер')
    dan_id = getattr(sv_card, 'dan_id', None)
    if not dan_id:
        missing_roles.append('Руководитель надзора (ДАН)')
    if missing_roles:
        roles_str = ', '.join(missing_roles)
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя создать чат: не назначены обязательные роли: {roles_str}"
        )

    tg = get_telegram_service()
    if not tg.mtproto_available:
        raise HTTPException(status_code=503, detail="MTProto не настроен")

    # Формируем название чата: АН-Город-Адрес
    city = (contract.city or '').replace('_', '-')
    address = (contract.address or '').replace('_', '-')
    if city and address:
        city_map = {'спб': 'санкт-петербург', 'мск': 'москва', 'нск': 'новосибирск', 'екб': 'екатеринбург'}
        full_city = city_map.get(city.lower(), city.lower())
        addr_check = address.lower().replace('_', '-')
        for c in [full_city, city.lower()]:
            if addr_check.startswith(c):
                address = address[len(c):].lstrip('.,;:_ -')
                break
    # Кастомное имя или автогенерация
    chat_title = data.chat_title.strip() if data.chat_title else f"АН-{city}-{address}"

    # Определяем фото
    avatar_type = (contract.agent_type or '').lower()
    if 'фестиваль' in avatar_type or 'festival' in avatar_type:
        avatar_type = 'festival'
    elif 'петрович' in avatar_type or 'petrovich' in avatar_type:
        avatar_type = 'petrovich'
    else:
        avatar_type = 'festival'

    photo_path = os.path.join(os.path.dirname(__file__), '..', 'resources', f'{avatar_type}_logo.png')
    if not os.path.exists(photo_path):
        photo_path = None

    # Получаем username бота
    bot_username = None
    if tg.bot_available:
        try:
            bot_info = await tg._bot.get_me()
            bot_username = bot_info.username
        except Exception:
            pass

    # Создаём группу
    result = await tg.create_group(
        title=chat_title,
        photo_path=photo_path,
        bot_username=bot_username,
    )

    # Сохраняем в БД
    chat = MessengerChat(
        contract_id=contract.id,
        supervision_card_id=data.supervision_card_id,
        messenger_type=data.messenger_type,
        telegram_chat_id=result["chat_id"],
        chat_title=result["title"],
        invite_link=result["invite_link"],
        avatar_type=avatar_type,
        creation_method="auto",
        created_by=current_user.id,
        is_active=True,
    )
    db.add(chat)
    db.flush()

    # Добавляем участников (переиспользуем _add_chat_members)
    members_resp = _add_chat_members(db, chat, data.members, contract)

    db.commit()

    # Рассылаем invite-ссылки
    asyncio.create_task(send_invites_to_members(chat.id, db))

    return MessengerChatDetailResponse(
        chat=MessengerChatResponse.model_validate(chat),
        members=members_resp
    )


@router.get("/chats/by-card/{card_id}", response_model=MessengerChatDetailResponse)
async def get_messenger_chat_by_card(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить чат по CRM-карточке"""
    chat = db.query(MessengerChat).filter(
        MessengerChat.crm_card_id == card_id,
        MessengerChat.is_active == True
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    members = db.query(MessengerChatMember).filter(
        MessengerChatMember.messenger_chat_id == chat.id
    ).all()

    return MessengerChatDetailResponse(
        chat=MessengerChatResponse.model_validate(chat),
        members=[ChatMemberResponse.model_validate(m) for m in members]
    )


@router.get("/chats/by-supervision/{supervision_card_id}", response_model=MessengerChatDetailResponse)
async def get_messenger_chat_by_supervision(
    supervision_card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить чат по карточке надзора"""
    chat = db.query(MessengerChat).filter(
        MessengerChat.supervision_card_id == supervision_card_id,
        MessengerChat.is_active == True
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    members = db.query(MessengerChatMember).filter(
        MessengerChatMember.messenger_chat_id == chat.id
    ).all()

    return MessengerChatDetailResponse(
        chat=MessengerChatResponse.model_validate(chat),
        members=[ChatMemberResponse.model_validate(m) for m in members]
    )


@router.delete("/chats/{chat_id}")
async def delete_messenger_chat(
    chat_id: int,
    current_user: Employee = Depends(require_permission("messenger.delete_chat")),
    db: Session = Depends(get_db)
):
    """Удалить/отвязать чат"""
    chat = db.query(MessengerChat).filter(MessengerChat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    tg = get_telegram_service()

    # Собираем telegram_user_id участников из БД для кика
    member_tg_ids = []
    db_members = db.query(MessengerChatMember).filter(
        MessengerChatMember.messenger_chat_id == chat_id
    ).all()
    for m in db_members:
        if m.telegram_user_id:
            member_tg_ids.append(m.telegram_user_id)

    # Если чат был создан автоматически — пробуем удалить группу
    if chat.creation_method == 'auto' and chat.telegram_chat_id:
        await tg.delete_group(chat.telegram_chat_id, member_tg_ids=member_tg_ids)
    elif chat.telegram_chat_id and tg.bot_available:
        # Для привязанного чата — бот просто покидает
        await tg.leave_chat(chat.telegram_chat_id)

    # Помечаем как неактивный + деактивируем orphan-чаты этой карточки
    chat.is_active = False
    if chat.crm_card_id:
        orphans = db.query(MessengerChat).filter(
            MessengerChat.crm_card_id == chat.crm_card_id,
            MessengerChat.id != chat.id,
            MessengerChat.is_active == True
        ).all()
        for orphan in orphans:
            orphan.is_active = False
            logger.info(f"Деактивирован orphan-чат id={orphan.id} для карточки {chat.crm_card_id}")
    db.commit()

    return {"status": "deleted", "chat_id": chat_id}


@router.post("/chats/{chat_id}/message")
async def send_chat_message(
    chat_id: int,
    data: SendMessageRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отправить сообщение в чат"""
    chat = db.query(MessengerChat).filter(
        MessengerChat.id == chat_id, MessengerChat.is_active == True
    ).first()
    if not chat or not chat.telegram_chat_id:
        raise HTTPException(status_code=404, detail="Чат не найден или не привязан")

    tg = get_telegram_service()
    msg_id = await tg.send_message(chat.telegram_chat_id, data.text)

    # Логируем
    log = MessengerMessageLog(
        messenger_chat_id=chat.id,
        message_type='manual',
        message_text=data.text,
        sent_by=current_user.id,
        telegram_message_id=msg_id,
        delivery_status='sent' if msg_id else 'failed',
    )
    db.add(log)
    db.commit()

    return {"status": "sent" if msg_id else "failed", "telegram_message_id": msg_id}


class AddMemberRequest(BaseModel):
    employee_id: int
    role_in_project: str = ""


@router.post("/chats/{chat_id}/add-member")
async def add_member_to_chat(
    chat_id: int,
    data: AddMemberRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Добавить сотрудника в существующий чат и отправить invite"""
    chat = db.query(MessengerChat).filter(
        MessengerChat.id == chat_id, MessengerChat.is_active == True
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    emp = db.query(Employee).filter(Employee.id == data.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    emp_name = emp.full_name or 'Коллега'
    has_email = bool(emp.email)
    has_telegram = bool(emp.telegram_user_id)

    # Нет ни email ни telegram — нельзя пригласить
    if not has_email and not has_telegram:
        raise HTTPException(
            status_code=400,
            detail=f"У сотрудника {emp_name} не указаны ни email, ни Telegram ID. "
                   f"Заполните контактные данные в карточке сотрудника."
        )

    # Проверяем, не добавлен ли уже
    existing_member = db.query(MessengerChatMember).filter(
        MessengerChatMember.messenger_chat_id == chat_id,
        MessengerChatMember.member_id == data.employee_id,
        MessengerChatMember.member_type == 'employee',
    ).first()
    if existing_member:
        raise HTTPException(
            status_code=409,
            detail=f"{emp_name} уже добавлен в чат"
        )

    member = MessengerChatMember(
        messenger_chat_id=chat.id,
        member_type='employee',
        member_id=data.employee_id,
        role_in_project=data.role_in_project,
        is_mandatory=False,
        phone=emp.phone,
        email=emp.email,
        telegram_user_id=emp.telegram_user_id,
        invite_status='pending',
    )
    db.add(member)
    db.commit()

    # Отправить invite только этому сотруднику
    invite_link = chat.invite_link

    email_sent = False
    if invite_link and has_email:
        try:
            email_svc = get_email_service()
            messenger_settings = load_messenger_settings(db)
            email_svc.configure(messenger_settings)
            await email_svc.send_chat_invite(
                to_email=emp.email,
                recipient_name=emp_name,
                chat_title=chat.chat_title or '',
                invite_link=invite_link,
            )
            email_sent = True
            logger.info(f"Invite отправлен: {emp_name} ({emp.email}) → чат {chat.id}")
        except Exception as e:
            logger.warning(f"Не удалось отправить invite {emp.email}: {e}")

    return {
        "status": "ok",
        "employee_name": emp_name,
        "email_sent": email_sent,
        "has_telegram": has_telegram,
    }


@router.post("/chats/{chat_id}/send-invites")
async def send_chat_invites(
    chat_id: int,
    data: SendInvitesRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Разослать invite-ссылки участникам"""
    chat = db.query(MessengerChat).filter(MessengerChat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    await send_invites_to_members(chat.id, db)
    return {"status": "invites_sent"}


@router.post("/chats/{chat_id}/files")
async def send_files_to_chat(
    chat_id: int,
    data: SendFilesRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отправить файлы в чат (с Яндекс.Диска)"""
    from yandex_disk_service import get_yandex_disk_service

    chat = db.query(MessengerChat).filter(
        MessengerChat.id == chat_id, MessengerChat.is_active == True
    ).first()
    if not chat or not chat.telegram_chat_id:
        raise HTTPException(status_code=404, detail="Чат не найден или не привязан")

    tg = get_telegram_service()
    yd = get_yandex_disk_service()
    sent_ids = []

    # Собираем Yandex пути: из file_ids + из прямых yandex_paths
    yandex_files = []
    for file_id in (data.file_ids or []):
        pf = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
        if pf and pf.yandex_path:
            yandex_files.append({
                "yandex_path": pf.yandex_path,
                "file_name": pf.file_name or os.path.basename(pf.yandex_path),
                "file_type": pf.file_type or "file",
            })

    for yp in (data.yandex_paths or []):
        yandex_files.append({
            "yandex_path": yp,
            "file_name": os.path.basename(yp),
            "file_type": "image" if any(yp.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']) else "file",
        })

    if not yandex_files:
        raise HTTPException(status_code=400, detail="Нет файлов для отправки")

    # Определяем тип отправки: галерея (изображения) или документы
    image_exts = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

    if data.as_gallery:
        # Отправка изображений галереей
        images_for_gallery = []
        docs_to_send = []

        for yf in yandex_files:
            ext = os.path.splitext(yf["file_name"])[1].lower()
            if ext in image_exts:
                images_for_gallery.append(yf)
            else:
                docs_to_send.append(yf)

        # Скачиваем и отправляем изображения галереей
        if images_for_gallery:
            photo_bytes_list = []
            for img in images_for_gallery[:10]:  # Telegram ограничение: 10 фото в галерее
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(img["file_name"])[1]) as tmp:
                        yd.download_file(img["yandex_path"], tmp.name)
                        with open(tmp.name, 'rb') as f:
                            photo_bytes_list.append({
                                "bytes": f.read(),
                                "filename": img["file_name"],
                            })
                    os.unlink(tmp.name)
                except Exception as e:
                    logger.warning(f"Ошибка скачивания {img['yandex_path']}: {e}")

            if photo_bytes_list:
                msg_ids = await tg.send_media_group_from_bytes(
                    chat.telegram_chat_id, photo_bytes_list, caption=data.caption
                )
                if msg_ids:
                    sent_ids.extend(msg_ids)

        # Документы отправляем отдельно
        for doc in docs_to_send:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(doc["file_name"])[1]) as tmp:
                    yd.download_file(doc["yandex_path"], tmp.name)
                    with open(tmp.name, 'rb') as f:
                        file_bytes = f.read()
                    msg_id = await tg.send_document_from_bytes(
                        chat.telegram_chat_id, file_bytes,
                        filename=doc["file_name"], caption=doc["file_name"]
                    )
                    if msg_id:
                        sent_ids.append(msg_id)
                os.unlink(tmp.name)
            except Exception as e:
                logger.warning(f"Ошибка отправки документа {doc['file_name']}: {e}")
    else:
        # Все файлы как документы (со ссылками)
        links = []
        for yf in yandex_files:
            try:
                public_link = yd.get_public_link(yf["yandex_path"])
                links.append(f'<a href="{public_link}">{yf["file_name"]}</a>')
            except Exception:
                links.append(yf["file_name"])

        if links:
            text = data.caption + "\n\n" if data.caption else ""
            text += "\n".join(links)
            msg_id = await tg.send_message(chat.telegram_chat_id, text, parse_mode="HTML")
            if msg_id:
                sent_ids.append(msg_id)

    # Логируем
    file_names = [yf["file_name"] for yf in yandex_files]
    log = MessengerMessageLog(
        messenger_chat_id=chat.id,
        message_type='files',
        message_text=data.caption or "",
        file_links=",".join(file_names),
        sent_by=current_user.id,
        telegram_message_id=sent_ids[0] if sent_ids else None,
        delivery_status='sent' if sent_ids else 'failed',
    )
    db.add(log)
    db.commit()

    return {
        "status": "sent" if sent_ids else "failed",
        "files_count": len(yandex_files),
        "telegram_message_ids": sent_ids,
    }


# =============================================
# MESSENGER SCRIPTS ENDPOINTS
# =============================================

@router.get("/scripts", response_model=list[MessengerScriptResponse])
async def get_messenger_scripts(
    project_type: str = None,
    script_type: str = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить скрипты (с фильтрацией)"""
    query = db.query(MessengerScript)
    if project_type:
        query = query.filter(
            (MessengerScript.project_type == project_type) | (MessengerScript.project_type.is_(None))
        )
    if script_type:
        query = query.filter(MessengerScript.script_type == script_type)

    scripts = query.order_by(MessengerScript.sort_order).all()
    return [MessengerScriptResponse.model_validate(s) for s in scripts]


@router.post("/scripts", response_model=MessengerScriptResponse)
async def create_messenger_script(
    data: MessengerScriptCreate,
    current_user: Employee = Depends(require_permission("messenger.manage_scripts")),
    db: Session = Depends(get_db)
):
    """Создать скрипт"""
    script = MessengerScript(**data.model_dump())
    db.add(script)
    db.commit()
    db.refresh(script)
    return MessengerScriptResponse.model_validate(script)


@router.put("/scripts/{script_id}", response_model=MessengerScriptResponse)
async def update_messenger_script(
    script_id: int,
    data: MessengerScriptUpdate,
    current_user: Employee = Depends(require_permission("messenger.manage_scripts")),
    db: Session = Depends(get_db)
):
    """Обновить скрипт"""
    script = db.query(MessengerScript).filter(MessengerScript.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Скрипт не найден")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(script, key, value)
    script.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(script)
    return MessengerScriptResponse.model_validate(script)


@router.delete("/scripts/{script_id}")
async def delete_messenger_script(
    script_id: int,
    current_user: Employee = Depends(require_permission("messenger.manage_scripts")),
    db: Session = Depends(get_db)
):
    """Удалить скрипт"""
    script = db.query(MessengerScript).filter(MessengerScript.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Скрипт не найден")
    db.delete(script)
    db.commit()
    return {"status": "deleted"}


@router.patch("/scripts/{script_id}/toggle")
async def toggle_messenger_script(
    script_id: int,
    current_user: Employee = Depends(require_permission("messenger.manage_scripts")),
    db: Session = Depends(get_db)
):
    """Включить/выключить скрипт"""
    script = db.query(MessengerScript).filter(MessengerScript.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Скрипт не найден")
    script.is_enabled = not script.is_enabled
    script.updated_at = datetime.utcnow()
    db.commit()
    return {"id": script.id, "is_enabled": script.is_enabled}


# =============================================
# MESSENGER SETTINGS ENDPOINTS
# =============================================

@router.get("/settings", response_model=list[MessengerSettingResponse])
async def get_messenger_settings(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить все настройки мессенджера"""
    settings_list = db.query(MessengerSetting).all()
    return [MessengerSettingResponse.model_validate(s) for s in settings_list]


@router.put("/settings")
async def update_messenger_settings(
    data: MessengerSettingsBulkUpdate,
    current_user: Employee = Depends(require_permission("messenger.create_chat")),
    db: Session = Depends(get_db)
):
    """Обновить настройки мессенджера (массовое обновление)"""
    for item in data.settings:
        setting = db.query(MessengerSetting).filter(
            MessengerSetting.setting_key == item.setting_key
        ).first()
        if setting:
            setting.setting_value = item.setting_value
            setting.updated_at = datetime.utcnow()
            setting.updated_by = current_user.id
        else:
            setting = MessengerSetting(
                setting_key=item.setting_key,
                setting_value=item.setting_value,
                updated_by=current_user.id,
            )
            db.add(setting)

    db.commit()

    # Инвалидируем кэш и переинициализируем сервисы с новыми настройками
    messenger_settings = load_messenger_settings(db, force=True)

    tg = get_telegram_service()
    tg.configure(messenger_settings)

    email_svc = get_email_service()
    email_svc.configure(messenger_settings)

    return {"status": "updated", "bot_available": tg.bot_available, "email_available": email_svc.available}


@router.get("/status")
async def get_messenger_status(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Статус сервисов мессенджера (перечитывает настройки из БД для консистентности между воркерами)"""
    # Перечитываем настройки из БД чтобы учесть изменения от другого воркера
    messenger_settings = {}
    for row in db.query(MessengerSetting).all():
        messenger_settings[row.setting_key] = row.setting_value or ""

    tg = get_telegram_service()
    tg.configure(messenger_settings)

    email_svc = get_email_service()
    email_svc.configure(messenger_settings)

    return {
        "telegram_bot_available": tg.bot_available,
        "telegram_mtproto_available": tg.mtproto_available,
        "email_available": email_svc.available,
    }


# =============================================
# MESSENGER MTPROTO AUTHORIZATION
# =============================================

@router.post("/mtproto/send-code")
async def mtproto_send_code(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Шаг 1: Отправить код подтверждения на телефон для MTProto авторизации"""
    if current_user.role not in SUPERUSER_ROLES:
        raise HTTPException(status_code=403, detail="Только администратор или директор")

    # Перечитываем настройки из БД
    messenger_settings = {}
    for row in db.query(MessengerSetting).all():
        messenger_settings[row.setting_key] = row.setting_value or ""

    tg = get_telegram_service()
    tg.configure(messenger_settings)

    if not PYROGRAM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Pyrogram не установлен на сервере")

    if not messenger_settings.get("telegram_api_id") or not messenger_settings.get("telegram_api_hash"):
        raise HTTPException(status_code=400, detail="API ID и API Hash не заполнены")
    if not messenger_settings.get("telegram_phone"):
        raise HTTPException(status_code=400, detail="Телефон не указан")

    try:
        phone_code_hash = await tg.send_auth_code()
        # Сохраняем hash в БД чтобы любой воркер мог его прочитать
        existing = db.query(MessengerSetting).filter_by(setting_key="telegram_phone_code_hash").first()
        if existing:
            existing.setting_value = phone_code_hash
        else:
            db.add(MessengerSetting(setting_key="telegram_phone_code_hash", setting_value=phone_code_hash))
        db.commit()
        return {"status": "code_sent", "phone": messenger_settings["telegram_phone"]}
    except Exception as e:
        logger.exception(f"Ошибка при отправке кода MTProto: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/mtproto/resend-sms")
async def mtproto_resend_sms(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отправить код сразу по SMS (send_code + resend_code за один вызов)"""
    if current_user.role not in SUPERUSER_ROLES:
        raise HTTPException(status_code=403, detail="Только администратор или директор")

    messenger_settings = {}
    for row in db.query(MessengerSetting).all():
        messenger_settings[row.setting_key] = row.setting_value or ""

    tg = get_telegram_service()
    tg.configure(messenger_settings)

    try:
        new_hash = await tg.send_auth_code_sms()
        # Сохраняем hash в БД
        existing = db.query(MessengerSetting).filter_by(setting_key="telegram_phone_code_hash").first()
        if existing:
            existing.setting_value = new_hash
        else:
            db.add(MessengerSetting(setting_key="telegram_phone_code_hash", setting_value=new_hash))
        db.commit()
        return {"status": "sms_sent", "phone": messenger_settings.get("telegram_phone", "")}
    except Exception as e:
        logger.exception(f"Ошибка при отправке кода по SMS MTProto: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/mtproto/verify-code")
async def mtproto_verify_code(
    data: dict,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Шаг 2: Подтвердить код и активировать MTProto сессию"""
    if current_user.role not in SUPERUSER_ROLES:
        raise HTTPException(status_code=403, detail="Только администратор или директор")

    code = str(data.get("code", "")).strip()
    if not code:
        raise HTTPException(status_code=400, detail="Код не указан")

    # Перечитываем настройки и hash из БД
    messenger_settings = {}
    for row in db.query(MessengerSetting).all():
        messenger_settings[row.setting_key] = row.setting_value or ""

    phone_code_hash = messenger_settings.get("telegram_phone_code_hash", "")
    if not phone_code_hash:
        raise HTTPException(status_code=400, detail="Сначала запросите код через send-code")

    tg = get_telegram_service()
    tg.configure(messenger_settings)

    try:
        user_info = await tg.verify_auth_code(phone_code_hash, code)
        # Удаляем hash — больше не нужен
        hash_row = db.query(MessengerSetting).filter_by(setting_key="telegram_phone_code_hash").first()
        if hash_row:
            db.delete(hash_row)
            db.commit()
        return {"status": "success", "user": user_info}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Ошибка при верификации MTProto: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/mtproto/session-status")
async def mtproto_session_status(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Проверить статус Pyrogram-сессии"""
    if current_user.role not in SUPERUSER_ROLES:
        raise HTTPException(status_code=403, detail="Только администратор или директор")

    messenger_settings = {}
    for row in db.query(MessengerSetting).all():
        messenger_settings[row.setting_key] = row.setting_value or ""

    tg = get_telegram_service()
    tg.configure(messenger_settings)

    try:
        result = await tg.check_session_valid()
        return result
    except Exception as e:
        logger.error(f"Ошибка проверки MTProto сессии: {e}")
        return {"valid": False, "error": str(e)}


# =============================================
# SYNC MESSENGER DATA (sync_messenger_router)
# =============================================

@sync_messenger_router.get("/messenger-chats")
async def sync_messenger_chats(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Синхронизация чатов"""
    chats = db.query(MessengerChat).all()
    return [{
        'id': c.id,
        'contract_id': c.contract_id,
        'crm_card_id': c.crm_card_id,
        'messenger_type': c.messenger_type,
        'telegram_chat_id': c.telegram_chat_id,
        'chat_title': c.chat_title,
        'invite_link': c.invite_link,
        'avatar_type': c.avatar_type,
        'creation_method': c.creation_method,
        'created_by': c.created_by,
        'created_at': c.created_at.isoformat() if c.created_at else None,
        'is_active': c.is_active,
    } for c in chats]


@sync_messenger_router.get("/messenger-scripts")
async def sync_messenger_scripts(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Синхронизация скриптов"""
    scripts = db.query(MessengerScript).all()
    return [{
        'id': s.id,
        'script_type': s.script_type,
        'project_type': s.project_type,
        'stage_name': s.stage_name,
        'message_template': s.message_template,
        'use_auto_deadline': s.use_auto_deadline,
        'is_enabled': s.is_enabled,
        'sort_order': s.sort_order,
        'created_at': s.created_at.isoformat() if s.created_at else None,
        'updated_at': s.updated_at.isoformat() if s.updated_at else None,
    } for s in scripts]

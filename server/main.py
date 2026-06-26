"""
FastAPI приложение - главный файл
REST API для многопользовательской CRM
"""

import asyncio
from datetime import datetime
import logging
import os
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from rate_limit import limiter
from slowapi.errors import RateLimitExceeded
from sqlalchemy import or_
from sqlalchemy.orm import Session

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class _PyrogramFilter(logging.Filter):
    """Фильтр: блокирует INFO/DEBUG из pyrogram.* (reconnect-spam при заблокированном DC).
    Добавляется на root LOGGER и pyrogram LOGGER (не на handlers) — проверяется ДО dispatch,
    поэтому не зависит от того, какие handlers uvicorn создаёт/заменяет через dictConfig.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name.startswith("pyrogram") and record.levelno < logging.WARNING:
            return False
        return True


# Добавляем фильтр к pyrogram sub-loggers на уровне модуля.
# При propagation Python logging вызывает Logger.filter() только для исходного logger'а —
# поэтому фильтр нужен именно на pyrogram.* loggers, не на root.
_pf_init = _PyrogramFilter()
for _pname_init in [
    "pyrogram",
    "pyrogram.connection",
    "pyrogram.connection.connection",
    "pyrogram.connection.transport.tcp.tcp",
    "pyrogram.session.session",
]:
    logging.getLogger(_pname_init).addFilter(_pf_init)

from auth import get_current_user
from constants import POSITION_STUDIO_DIRECTOR
from email_service import get_email_service
from permissions import seed_permissions
from schemas import NotificationResponse, SyncRequest, SyncResponse
from telegram_service import get_telegram_service

from config import get_settings
from database import (
    Client,
    Contract,
    Employee,
    Notification,
    SessionLocal,
    get_db,
    init_db,
)

settings = get_settings()


# Создание приложения
app = FastAPI(title=settings.app_name, version=settings.app_version, description="REST API для многопользовательской CRM Interior Studio")

# CORS middleware — ЗАПРЕЩЁН wildcard "*" при allow_credentials=True
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "").strip()
if not _allowed_origins or _allowed_origins == "*":
    # По умолчанию разрешаем только localhost (для разработки)
    _cors_origins = ["http://localhost:3000", "http://localhost:8080"]
    logger.warning("CORS: ALLOWED_ORIGINS не задан, используются origins для разработки")
else:
    _cors_origins = [o.strip() for o in _allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)


# Rate Limiting — из rate_limit.py
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Обработчик превышения лимита запросов"""
    from starlette.responses import JSONResponse

    return JSONResponse(status_code=429, content={"detail": "Слишком много запросов. Повторите позже."})


# Security headers настроены в nginx.conf (server_tokens off, X-Frame-Options, CSP, HSTS и т.д.)
# Дублирование middleware удалено в Phase 5 (W-04)


# =========================
# API VERSIONING (backward-compatible)
# =========================
# Все эндпоинты теперь под /api/v1/.
# Middleware перезаписывает /api/... → /api/v1/... для обратной совместимости
# со старыми клиентами, которые ещё используют /api/ без версии.


@app.middleware("http")
async def api_version_compat(request, call_next):
    """Rewrite /api/xxx → /api/v1/xxx для backward-compat."""
    path = request.scope["path"]
    if path.startswith("/api/") and not path.startswith("/api/v1/"):
        new_path = "/api/v1/" + path[5:]  # len("/api/") = 5
        # Убираем trailing slash — все endpoint-ы определены без неё,
        # иначе FastAPI шлёт лишний 307 redirect
        if new_path.endswith("/") and len(new_path) > 1:
            new_path = new_path.rstrip("/")
        request.scope["path"] = new_path
    # Передаём scheme от X-Forwarded-Proto (nginx → app через HTTP)
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if forwarded_proto:
        request.scope["scheme"] = forwarded_proto
    return await call_next(request)


def seed_cities(db):
    """Заполнить таблицу городов дефолтными значениями"""
    from database import City

    defaults = ["СПБ", "МСК", "ВН"]
    for name in defaults:
        existing = db.query(City).filter(City.name == name).first()
        if not existing:
            db.add(City(name=name))
    db.commit()


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info(f"Запуск {settings.app_name} v{settings.app_version}")

    # Добавляем фильтр к конкретным pyrogram loggers.
    # ВАЖНО: logging.Filter.filter() проверяется только в Logger.handle() исходного logger-а,
    # а при propagation через callHandlers() промежуточные Logger.filters НЕ проверяются.
    # Поэтому фильтр нужно добавлять к logger'у, где запись создаётся (pyrogram subleLoggers),
    # а НЕ к root logger или обёрточному pyrogram logger.
    _pf = _PyrogramFilter()
    for _pname in [
        "pyrogram",
        "pyrogram.connection",
        "pyrogram.connection.connection",
        "pyrogram.connection.transport",
        "pyrogram.connection.transport.tcp",
        "pyrogram.connection.transport.tcp.tcp",
        "pyrogram.session",
        "pyrogram.session.session",
        "pyrogram.session.auth",
    ]:
        _plog = logging.getLogger(_pname)
        if not any(isinstance(f, _PyrogramFilter) for f in _plog.filters):
            _plog.addFilter(_pf)

    init_db()
    logger.info("База данных инициализирована")

    # Миграция таблицы user_permissions: переименование колонок
    from sqlalchemy import inspect, text

    from database import UserPermission, engine

    try:
        insp = inspect(engine)
        if insp.has_table("user_permissions"):
            columns = [c["name"] for c in insp.get_columns("user_permissions")]
            if "permission_type" in columns and "permission_name" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE user_permissions RENAME COLUMN permission_type TO permission_name"))
                    logger.info("Migrated user_permissions: permission_type -> permission_name")
            if "target" in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE user_permissions DROP COLUMN target"))
                    logger.info("Migrated user_permissions: dropped column target")
    except Exception as e:
        logger.warning(f"user_permissions migration note: {e}")

    # Миграция activity_log: employee_id должен быть nullable (для login_failed без сотрудника)
    try:
        from sqlalchemy import text as _text

        with engine.begin() as conn:
            conn.execute(_text("ALTER TABLE activity_log ALTER COLUMN employee_id DROP NOT NULL"))
            logger.info("Migrated activity_log: employee_id is now nullable")
    except Exception as e:
        if "already" not in str(e).lower() and "no such" not in str(e).lower():
            logger.debug(f"activity_log migration note: {e}")

    # Миграция project_files: добавить stage_code
    try:
        from sqlalchemy import text as _text2

        with engine.begin() as conn:
            conn.execute(_text2("ALTER TABLE project_files ADD COLUMN IF NOT EXISTS stage_code VARCHAR"))
            logger.info("Migrated project_files: added stage_code column")
    except Exception as e:
        if "duplicate" not in str(e).lower() and "already" not in str(e).lower():
            logger.debug(f"project_files migration note: {e}")

    # Миграция: добавить actual_date и visit_type в supervision_visits
    try:
        from sqlalchemy import text as _text3

        with engine.begin() as conn:
            conn.execute(_text3("ALTER TABLE supervision_visits ADD COLUMN IF NOT EXISTS actual_date VARCHAR(30)"))
            conn.execute(_text3("ALTER TABLE supervision_visits ADD COLUMN IF NOT EXISTS visit_type VARCHAR(50) DEFAULT 'На объект'"))
            logger.info("Migrated supervision_visits: added actual_date, visit_type columns")
    except Exception as e:
        if "duplicate" not in str(e).lower() and "already" not in str(e).lower():
            logger.debug(f"supervision_visits migration note: {e}")

    # Миграция: last_guest_activity в internal_chat_members
    try:
        from sqlalchemy import text as _text4

        with engine.begin() as conn:
            conn.execute(_text4("ALTER TABLE internal_chat_members ADD COLUMN IF NOT EXISTS last_guest_activity TIMESTAMP"))
            logger.info("Migrated internal_chat_members: added last_guest_activity column")
    except Exception as e:
        if "duplicate" not in str(e).lower() and "already" not in str(e).lower():
            logger.debug(f"internal_chat_members migration note: {e}")

    # Миграция: min_visits_per_month в supervision_cards + is_additional + executor_role в supervision_visits
    try:
        from sqlalchemy import text as _text_visits

        with engine.begin() as conn:
            conn.execute(_text_visits("ALTER TABLE supervision_cards ADD COLUMN IF NOT EXISTS min_visits_per_month INTEGER"))
            conn.execute(_text_visits("ALTER TABLE supervision_visits ADD COLUMN IF NOT EXISTS is_additional BOOLEAN DEFAULT FALSE"))
            conn.execute(_text_visits("ALTER TABLE supervision_visits ADD COLUMN IF NOT EXISTS executor_role VARCHAR(100)"))
            logger.info("Migrated: min_visits_per_month, is_additional, executor_role added")
    except Exception as e:
        if "duplicate" not in str(e).lower() and "already" not in str(e).lower():
            logger.debug(f"visits migration note: {e}")

    # Миграция: tag_color в crm_cards
    try:
        from sqlalchemy import text as _text_tag_color

        with engine.begin() as conn:
            conn.execute(_text_tag_color("ALTER TABLE crm_cards ADD COLUMN IF NOT EXISTS tag_color VARCHAR"))
            logger.info("Migrated crm_cards: added tag_color column")
    except Exception as e:
        if "duplicate" not in str(e).lower() and "already" not in str(e).lower():
            logger.debug(f"tag_color migration note: {e}")

    # Миграция: tag_color в supervision_cards
    try:
        from sqlalchemy import text as _text_sv_tag_color

        with engine.begin() as conn:
            conn.execute(_text_sv_tag_color("ALTER TABLE supervision_cards ADD COLUMN IF NOT EXISTS tag_color VARCHAR"))
            logger.info("Migrated supervision_cards: added tag_color column")
    except Exception as e:
        if "duplicate" not in str(e).lower() and "already" not in str(e).lower():
            logger.debug(f"supervision_cards tag_color migration note: {e}")

    # Миграция: is_admin_chat, admin_chat_type в internal_chats + таблица user_chat_pins
    try:
        from sqlalchemy import text as _text_admin_chat

        with engine.begin() as conn:
            conn.execute(_text_admin_chat("ALTER TABLE internal_chats ADD COLUMN IF NOT EXISTS is_admin_chat BOOLEAN DEFAULT FALSE"))
            conn.execute(_text_admin_chat("ALTER TABLE internal_chats ADD COLUMN IF NOT EXISTS admin_chat_type VARCHAR(10)"))
            conn.execute(_text_admin_chat("CREATE UNIQUE INDEX IF NOT EXISTS uq_admin_chat_type ON internal_chats (admin_chat_type) WHERE is_admin_chat = TRUE"))
        logger.info("Migrated internal_chats: added is_admin_chat, admin_chat_type, unique index")
    except Exception as e:
        if "duplicate" not in str(e).lower() and "already" not in str(e).lower():
            logger.debug(f"internal_chats admin chat migration: {e}")

    try:
        from database import UserChatPin

        UserChatPin.__table__.create(bind=engine, checkfirst=True)
        logger.info("user_chat_pins table ensured")
    except Exception as e:
        logger.debug(f"user_chat_pins table: {e}")

    # Seed дефолтных прав и admin-пользователя
    from auth import get_password_hash

    from database import Employee, SessionLocal

    db = SessionLocal()
    try:
        # Создаём admin только если в БД нет ни одного активного Руководителя студии
        # (нужен для CI и первого запуска; на продакшне с реальным директором — пропускается)
        existing_director = (
            db.query(Employee)
            .filter(
                Employee.position == POSITION_STUDIO_DIRECTOR,
                Employee.status == "активный",
            )
            .first()
        )
        if not existing_director:
            admin = db.query(Employee).filter(Employee.login == "admin").first()
            if not admin:
                admin = Employee(
                    full_name="Администратор",
                    phone="+70000000000",
                    login="admin",
                    password_hash=get_password_hash("admin123"),
                    role=POSITION_STUDIO_DIRECTOR,
                    position=POSITION_STUDIO_DIRECTOR,
                    department="Административный",
                    status="активный",
                )
                db.add(admin)
                db.commit()
                logger.info("Admin user seeded")

        seed_permissions(db)
        logger.info("Permissions seeded")

        # Seed городов по умолчанию (СПБ, МСК, ВН)
        try:
            seed_cities(db)
            logger.info("Cities seeded")
        except Exception as e:
            db.rollback()
            logger.warning(f"Cities seed: {e}")

        # Seed агентов по умолчанию (ПЕТРОВИЧ, ФЕСТИВАЛЬ)
        from database import Agent

        try:
            if db.query(Agent).count() == 0:
                db.add_all(
                    [
                        Agent(name="ПЕТРОВИЧ", color="#FFA500"),
                        Agent(name="ФЕСТИВАЛЬ", color="#FF69B4"),
                    ]
                )
                db.commit()
                logger.info("Default agents seeded (ПЕТРОВИЧ, ФЕСТИВАЛЬ)")
        except Exception as e:
            db.rollback()
            logger.warning(f"Agents seed: {e}")

        # Инициализация Telegram и Email сервисов из настроек БД
        try:
            messenger_settings = load_messenger_settings(db)

            tg_service = get_telegram_service()
            tg_service.configure(messenger_settings)
            logger.info(f"Telegram: bot={'да' if tg_service.bot_available else 'нет'}, mtproto={'да' if tg_service.mtproto_available else 'нет'}")

            email_svc = get_email_service()
            email_svc.configure(messenger_settings)
            logger.info(f"Email: {'настроен' if email_svc.available else 'не настроен'}")
        except Exception as e:
            logger.warning(f"Messenger services init: {e}")

        # Seed дефолтных скриптов мессенджера
        try:
            seed_default_messenger_scripts(db)
        except Exception as e:
            logger.warning(f"Messenger scripts seed: {e}")

        # Создать/синхронизировать административные чаты
        try:
            from services.chat_service import ensure_admin_chats

            ensure_admin_chats(db)
            logger.info("Admin chats ensured")
        except Exception as e:
            db.rollback()
            logger.warning(f"Admin chats seed: {e}")
    finally:
        db.close()

    # N3: Запуск фонового планировщика дедлайнов
    try:
        from services.deadline_checker import deadline_checker_loop

        asyncio.create_task(deadline_checker_loop())
        logger.info("Deadline checker: задача запущена")
    except Exception as e:
        logger.warning(f"Deadline checker: {e}")

    # N4: Запуск фонового расчёта KPI (ежедневные снимки)
    try:
        from services.kpi_snapshot import kpi_snapshot_loop

        asyncio.create_task(kpi_snapshot_loop())
        logger.info("KPI snapshot: задача запущена")
    except Exception as e:
        logger.warning(f"KPI snapshot: {e}")

    # N5: Обслуживание чатов — удаление старых файлов ЯД (раз в сутки в 03:00)
    try:
        from services.maintenance_service import chat_maintenance_loop

        asyncio.create_task(chat_maintenance_loop())
        logger.info("Chat maintenance: задача запущена (ежедневно 03:00 UTC)")
    except Exception as e:
        logger.warning(f"Chat maintenance: {e}")

    # N7: Ежемесячные оплаты надзора (1-го числа в 09:00 UTC)
    async def _monthly_supervision_payments_loop():
        """Запускает create_monthly_supervision_payments 1-го числа каждого месяца в 09:00 UTC."""
        from services.deadline_checker import create_monthly_supervision_payments

        logger.info("Monthly supervision payments loop: запущен")
        while True:
            try:
                now = datetime.utcnow()
                # Следующее 1-е число в 09:00 UTC
                if now.month == 12:
                    next_run = now.replace(year=now.year + 1, month=1, day=1, hour=9, minute=0, second=0, microsecond=0)
                else:
                    next_run = now.replace(month=now.month + 1, day=1, hour=9, minute=0, second=0, microsecond=0)
                # Если сейчас 1-е число и время ещё не наступило — запустить сегодня
                if now.day == 1 and now.hour < 9:
                    next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
                sleep_secs = (next_run - now).total_seconds()
                logger.info(f"Monthly supervision payments: следующий запуск через {sleep_secs / 3600:.1f}ч")
                await asyncio.sleep(sleep_secs)
                await create_monthly_supervision_payments(SessionLocal)
            except Exception as e:
                logger.error(f"_monthly_supervision_payments_loop: {e}")
                await asyncio.sleep(3600)  # При ошибке — повтор через час

    try:
        asyncio.create_task(_monthly_supervision_payments_loop())
        logger.info("Monthly supervision payments: задача запущена (1-го числа в 09:00 UTC)")
    except Exception as e:
        logger.warning(f"Monthly supervision payments: {e}")

    # N6: Разовая синхронизация аватаров из Telegram для уже привязанных сотрудников
    try:
        from telegram_bot_handlers import sync_employee_telegram_avatars

        asyncio.create_task(sync_employee_telegram_avatars())
        logger.info("Telegram avatar sync: задача запущена")
    except Exception as e:
        logger.warning(f"Telegram avatar sync: {e}")

    # N8: Ежедневный автоматический бекап PostgreSQL в 03:00 UTC
    try:
        from routers.admin_router import scheduled_backup_loop

        asyncio.create_task(scheduled_backup_loop())
        logger.info("Scheduled backup: задача запущена (ежедневно 03:00 UTC)")
    except Exception as e:
        logger.warning(f"Scheduled backup: {e}")

    # N9: Кэш превью — создать директорию и запустить ежедневную очистку в 04:30 UTC
    try:
        from services.preview_service import CACHE_DIR, cleanup_stale_all

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Preview cache dir: {CACHE_DIR}")

        async def _preview_cleanup_loop():
            logger.info("Preview cleanup loop: запущен (ежедневно 04:30 UTC)")
            while True:
                try:
                    now = datetime.utcnow()
                    next_run = now.replace(hour=4, minute=30, second=0, microsecond=0)
                    if now >= next_run:
                        # вычислить следующие сутки в 04:30
                        import calendar

                        _, days_in_month = calendar.monthrange(now.year, now.month)
                        if now.day < days_in_month:
                            next_run = next_run.replace(day=now.day + 1)
                        elif now.month == 12:
                            next_run = next_run.replace(year=now.year + 1, month=1, day=1)
                        else:
                            next_run = next_run.replace(month=now.month + 1, day=1)
                    sleep_secs = (next_run - now).total_seconds()
                    logger.info(f"Preview cleanup: следующий запуск через {sleep_secs / 3600:.1f}ч")
                    await asyncio.sleep(sleep_secs)
                    db = SessionLocal()
                    try:
                        n = cleanup_stale_all(db)
                        logger.info(f"Preview cleanup: удалено {n} протухших записей")
                    finally:
                        db.close()
                except Exception as exc:
                    logger.error(f"Preview cleanup loop error: {exc}")
                    await asyncio.sleep(3600)

        asyncio.create_task(_preview_cleanup_loop())
        logger.info("Preview cleanup: задача запущена (ежедневно 04:30 UTC)")
    except Exception as e:
        logger.warning(f"Preview cleanup: {e}")

    # Запуск Telegram Bot polling для обработки /start (привязка аккаунтов)
    # Используем file-lock чтобы только ОДИН воркер Uvicorn запускал polling
    # (иначе TelegramConflictError при --workers > 1)
    try:
        from telegram_bot_handlers import AIOGRAM_AVAILABLE as BOT_AVAILABLE
        from telegram_bot_handlers import router as bot_router

        if BOT_AVAILABLE and bot_router is not None:
            import fcntl

            lock_path = "/tmp/telegram_polling.lock"
            try:
                _polling_lock_fd = open(lock_path, "w")
                fcntl.flock(_polling_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Блокировка получена — этот воркер запускает polling
                # Сохраняем fd в app.state чтобы не собрал GC
                app.state._polling_lock_fd = _polling_lock_fd
                from aiogram import Dispatcher as BotDispatcher

                tg = get_telegram_service()
                if tg.bot_available:
                    dp = BotDispatcher()
                    dp.include_router(bot_router)
                    asyncio.create_task(dp.start_polling(tg._bot, handle_signals=False))
                    logger.info("Telegram Bot polling запущен (этот воркер — primary)")
            except (IOError, OSError):
                # Другой воркер уже держит блокировку — пропускаем
                logger.info("Telegram Bot polling: пропущен (другой воркер уже обрабатывает)")
    except Exception as e:
        logger.warning(f"Telegram Bot polling: {e}")


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {"app": settings.app_name, "version": settings.app_version, "status": "running"}


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy"}


@app.get("/api/v1/version")
async def get_app_version():
    """Получить текущую версию серверного приложения для сверки клиентами"""
    return {"version": settings.app_version, "app": settings.app_name}


@app.put("/api/v1/version")
async def set_app_version(data: dict, current_user=Depends(get_current_user)):
    """Обновить версию сервера (только для администратора)"""
    if current_user.position not in ("Руководитель студии", "СДП"):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    new_version = data.get("version", "").strip()
    if not new_version:
        raise HTTPException(status_code=400, detail="Версия не указана")
    settings.app_version = new_version
    return {"version": settings.app_version, "status": "updated"}


# =========================
# ГЛОБАЛЬНЫЙ ПОИСК
# =========================


@app.get("/api/v1/search")
async def global_search(q: str, limit: int = 50, entity_types: Optional[str] = None, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Полнотекстовый поиск по клиентам, договорам, CRM карточкам и карточкам надзора.
    entity_types — через запятую: clients,contracts,crm_cards,supervision_cards
    """
    if not q or len(q.strip()) < 2:
        return {"results": [], "total": 0, "query": q}

    query_text = q.strip()
    search_pattern = f"%{query_text}%"
    results = []
    types_filter = entity_types.split(",") if entity_types else ["clients", "contracts", "crm_cards", "supervision_cards"]

    # Фильтрация типов по access.* правам пользователя
    from permissions import check_permission

    access_map = {
        "clients": "access.clients",
        "contracts": "access.contracts",
        "crm_cards": "access.crm",
        "supervision_cards": "access.supervision",
    }
    types_filter = [t for t in types_filter if check_permission(current_user, access_map.get(t, ""), db)]

    from constants import ARCHIVE_STATUSES

    # Поиск по клиентам
    if "clients" in types_filter:
        from database import Client as ClientModel

        clients = (
            db.query(ClientModel)
            .filter(
                or_(ClientModel.full_name.ilike(search_pattern), ClientModel.phone.ilike(search_pattern), ClientModel.email.ilike(search_pattern), ClientModel.organization_name.ilike(search_pattern))
            )
            .limit(limit)
            .all()
        )
        for c in clients:
            results.append(
                {
                    "type": "client",
                    "id": c.id,
                    "title": c.full_name or "",
                    "subtitle": c.phone or c.email or "",
                }
            )

    # Поиск по договорам
    if "contracts" in types_filter:
        from database import Contract as ContractModel

        contracts = (
            db.query(ContractModel)
            .filter(
                or_(
                    ContractModel.contract_number.ilike(search_pattern),
                    ContractModel.address.ilike(search_pattern),
                )
            )
            .limit(limit)
            .all()
        )
        for ct in contracts:
            results.append(
                {
                    "type": "contract",
                    "id": ct.id,
                    "title": ct.contract_number or "",
                    "subtitle": ct.address or "",
                }
            )

    # Определяем права суперпользователя один раз для CRM и Надзора
    is_admin_user = getattr(current_user, "role", "") in ("admin", "director") or getattr(current_user, "position", "") in ("Руководитель студии", "Старший менеджер проектов")

    # Поиск по CRM карточкам (через join с договором)
    if "crm_cards" in types_filter:
        from database import Contract as ContractModel2
        from database import CRMCard as CRMCardModel

        cards = (
            db.query(CRMCardModel)
            .join(ContractModel2, CRMCardModel.contract_id == ContractModel2.id)
            .filter(
                or_(
                    ContractModel2.address.ilike(search_pattern),
                    ContractModel2.contract_number.ilike(search_pattern),
                )
            )
        )
        # Ограничение по назначению — не-суперпользователи видят только свои карточки
        if not is_admin_user:
            from database import StageExecutor as SEModel

            assigned_card_ids = db.query(SEModel.crm_card_id).filter(SEModel.executor_id == current_user.id, SEModel.crm_card_id.isnot(None)).subquery()
            cards_filter = or_(
                CRMCardModel.senior_manager_id == current_user.id,
                CRMCardModel.sdp_id == current_user.id,
                CRMCardModel.gap_id == current_user.id,
                CRMCardModel.manager_id == current_user.id,
                CRMCardModel.surveyor_id == current_user.id,
                CRMCardModel.id.in_(assigned_card_ids),
            )
            cards = cards.filter(cards_filter)
        cards = cards.limit(limit).all()
        can_view_archive = check_permission(current_user, "crm_cards.view_archive", db)
        for card in cards:
            contract = db.query(ContractModel2).filter(ContractModel2.id == card.contract_id).first()
            is_archive = (contract.status in ARCHIVE_STATUSES) if contract and contract.status else False
            # Скрываем архивные карточки пользователям без права view_archive
            if is_archive and not can_view_archive:
                continue
            project_type = contract.project_type if contract else None
            results.append(
                {
                    "type": "crm_card",
                    "id": card.id,
                    "title": f"Проект #{card.id}",
                    "subtitle": f"{contract.address if contract else ''} ({card.column_name})",
                    "is_archive": is_archive,
                    "project_type": project_type,
                }
            )

    # Поиск по карточкам авторского надзора (через join с договором)
    if "supervision_cards" in types_filter:
        from database import Contract as ContractModel3
        from database import SupervisionCard as SupervisionCardModel

        sup_cards = (
            db.query(SupervisionCardModel)
            .join(ContractModel3, SupervisionCardModel.contract_id == ContractModel3.id)
            .filter(
                or_(
                    ContractModel3.address.ilike(search_pattern),
                    ContractModel3.contract_number.ilike(search_pattern),
                )
            )
        )
        # Ограничение надзора по назначению
        if not is_admin_user:
            sup_filter = or_(
                SupervisionCardModel.dan_id == current_user.id,
                SupervisionCardModel.senior_manager_id == current_user.id,
                SupervisionCardModel.studio_director_id == current_user.id,
            )
            sup_cards = sup_cards.filter(sup_filter)
        sup_cards = sup_cards.limit(limit).all()
        for sc in sup_cards:
            contract = db.query(ContractModel3).filter(ContractModel3.id == sc.contract_id).first()
            results.append(
                {
                    "type": "supervision_card",
                    "id": sc.id,
                    "title": f"Надзор #{sc.id}",
                    "subtitle": f"{contract.address if contract else ''} ({sc.column_name})",
                }
            )

    return {"results": results[:limit], "total": len(results), "query": q}


# =========================
# РОУТЕРЫ (вынесены из main.py)
# =========================
from routers.auth_router import router as auth_router
from routers.clients_router import router as clients_router
from routers.contracts_router import router as contracts_router
from routers.employees_router import router as employees_router

app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(employees_router, prefix="/api/v1")
app.include_router(clients_router, prefix="/api/v1/clients")
app.include_router(contracts_router, prefix="/api/v1/contracts")

from routers.dashboard_router import router as dashboard_router
from routers.rates_router import router as rates_router
from routers.salaries_router import router as salaries_router
from routers.statistics_router import router as statistics_router
from routers.sync_router import router as sync_router

app.include_router(rates_router, prefix="/api/v1/rates")
app.include_router(salaries_router, prefix="/api/v1/salaries")
app.include_router(statistics_router, prefix="/api/v1/statistics")
app.include_router(dashboard_router, prefix="/api/v1/dashboard")
app.include_router(sync_router, prefix="/api/v1/sync")

from routers.agents_router import router as agents_router
from routers.cities_router import router as cities_router
from routers.files_router import router as files_router
from routers.heartbeat_router import router as heartbeat_router
from routers.locks_router import router as locks_router
from routers.payments_router import router as payments_router

app.include_router(payments_router, prefix="/api/v1/payments")
app.include_router(files_router, prefix="/api/v1/files")
app.include_router(agents_router, prefix="/api/v1/agents")
app.include_router(cities_router, prefix="/api/v1/cities")
app.include_router(heartbeat_router, prefix="/api/v1")
app.include_router(locks_router, prefix="/api/v1/locks")

from routers.action_history_router import router as action_history_router
from routers.norm_days_router import router as norm_days_router
from routers.project_templates_router import router as project_templates_router
from routers.reports_router import router as reports_router
from routers.supervision_router import router as supervision_router
from routers.supervision_timeline_router import router as supervision_timeline_router
from routers.timeline_router import router as timeline_router

app.include_router(timeline_router, prefix="/api/v1/timeline")
app.include_router(norm_days_router, prefix="/api/v1/norm-days")
app.include_router(supervision_timeline_router, prefix="/api/v1/supervision-timeline")
app.include_router(project_templates_router, prefix="/api/v1/project-templates")
app.include_router(supervision_router, prefix="/api/v1/supervision")

from routers.supervision_budget_router import router as supervision_budget_router
from routers.supervision_visits_router import router as supervision_visits_router

app.include_router(supervision_visits_router, prefix="/api/v1/supervision-visits")
app.include_router(supervision_budget_router, prefix="/api/v1/supervision-budget")
app.include_router(action_history_router, prefix="/api/v1/action-history")
app.include_router(reports_router, prefix="/api/v1/reports")

from routers.crm_router import router as crm_router
from routers.messenger_router import (
    load_messenger_settings,
    seed_default_messenger_scripts,
    sync_messenger_router,
)
from routers.messenger_router import (
    router as messenger_router,
)

app.include_router(crm_router, prefix="/api/v1/crm")
app.include_router(messenger_router, prefix="/api/v1/messenger")
app.include_router(sync_messenger_router, prefix="/api/v1/sync")

from routers.notifications_router import router as notifications_router

app.include_router(notifications_router, prefix="/api/v1")

from routers.websocket_router import router as websocket_router

app.include_router(websocket_router, prefix="/api/v1")

from routers.employee_analytics_router import router as employee_analytics_router
from routers.survey_router import router as survey_router

app.include_router(employee_analytics_router, prefix="/api/v1/employee-analytics")
app.include_router(survey_router, prefix="/api/v1/surveys")

from routers.chat_router import router as chat_router
from routers.client_chat_router import router as client_chat_router
from routers.deleted_contracts_router import router as deleted_contracts_router

app.include_router(chat_router, prefix="/api/v1/chats")
# Клиентский доступ без JWT + WebSocket эндпоинты — отдельный роутер
app.include_router(client_chat_router, prefix="/api/v1")
app.include_router(deleted_contracts_router, prefix="/api/v1/admin/deleted-contracts")

from routers.admin_router import router as admin_router
from routers.preview_router import router as preview_router

app.include_router(admin_router, prefix="/api/v1/admin")
app.include_router(preview_router, prefix="/api/v1/preview")


# =========================
# СИНХРОНИЗАЦИЯ
# =========================


@app.post("/api/v1/sync", response_model=SyncResponse)
async def sync_data(sync_request: SyncRequest, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Синхронизация данных
    Возвращает все изменения после указанного timestamp
    """
    response = SyncResponse(timestamp=datetime.utcnow())

    # Клиенты
    if "clients" in sync_request.entity_types:
        clients = db.query(Client).filter(Client.updated_at > sync_request.last_sync_timestamp).all()
        response.clients = clients

    # Договоры
    if "contracts" in sync_request.entity_types:
        contracts = db.query(Contract).filter(Contract.updated_at > sync_request.last_sync_timestamp).all()
        response.contracts = contracts

    # Сотрудники
    if "employees" in sync_request.entity_types:
        employees = db.query(Employee).filter(Employee.updated_at > sync_request.last_sync_timestamp).all()
        response.employees = employees

    # Уведомления
    notifications = db.query(Notification).filter(Notification.employee_id == current_user.id, Notification.created_at > sync_request.last_sync_timestamp).all()
    response.notifications = notifications

    return response


# =========================
# УВЕДОМЛЕНИЯ
# =========================


@app.get("/api/v1/notifications", response_model=list[NotificationResponse])
async def get_notifications(unread_only: bool = False, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить уведомления текущего пользователя"""
    query = db.query(Notification).filter(Notification.employee_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read == False)

    notifications = query.order_by(Notification.created_at.desc()).all()
    return notifications


@app.put("/api/v1/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Отметить уведомление как прочитанное"""
    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.employee_id == current_user.id).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()

    return {"message": "Уведомление прочитано"}

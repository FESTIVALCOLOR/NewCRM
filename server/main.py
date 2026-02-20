"""
FastAPI приложение - главный файл
REST API для многопользовательской CRM
"""
import logging
import os
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from typing import List, Optional

from slowapi.errors import RateLimitExceeded
from rate_limit import limiter


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from config import get_settings
from database import (
    get_db, init_db, SessionLocal,
    Employee, Client, Contract, Notification,
)
from schemas import NotificationResponse, SyncRequest, SyncResponse
from telegram_service import get_telegram_service
from email_service import get_email_service
from auth import get_current_user
from permissions import seed_permissions

settings = get_settings()




# Создание приложения
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="REST API для многопользовательской CRM Interior Studio"
)

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
    return JSONResponse(
        status_code=429,
        content={"detail": "Слишком много запросов. Повторите позже."}
    )


# Security headers настроены в nginx.conf (server_tokens off, X-Frame-Options, CSP, HSTS и т.д.)
# Дублирование middleware удалено в Phase 5 (W-04)


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info(f"Запуск {settings.app_name} v{settings.app_version}")
    init_db()
    logger.info("База данных инициализирована")

    # Миграция таблицы user_permissions: переименование колонок
    from database import engine, UserPermission
    from sqlalchemy import inspect, text
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

    # Seed дефолтных прав
    from database import SessionLocal
    db = SessionLocal()
    try:
        seed_permissions(db)
        logger.info("Permissions seeded")

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
    finally:
        db.close()




@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy"}


@app.get("/api/version")
async def get_app_version():
    """Получить текущую версию серверного приложения для сверки клиентами"""
    return {
        "version": settings.app_version,
        "app": settings.app_name
    }


# =========================
# ГЛОБАЛЬНЫЙ ПОИСК
# =========================

@app.get("/api/search")
async def global_search(
    q: str,
    limit: int = 50,
    entity_types: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Полнотекстовый поиск по клиентам, договорам и CRM карточкам.
    entity_types — через запятую: clients,contracts,crm_cards
    """
    if not q or len(q.strip()) < 2:
        return {"results": [], "total": 0, "query": q}

    query_text = q.strip()
    search_pattern = f"%{query_text}%"
    results = []
    types_filter = entity_types.split(",") if entity_types else ["clients", "contracts", "crm_cards"]

    # Поиск по клиентам
    if "clients" in types_filter:
        from database import Client as ClientModel
        clients = db.query(ClientModel).filter(
            or_(
                ClientModel.full_name.ilike(search_pattern),
                ClientModel.phone.ilike(search_pattern),
                ClientModel.email.ilike(search_pattern),
                ClientModel.organization_name.ilike(search_pattern)
            )
        ).limit(limit).all()
        for c in clients:
            results.append({
                "type": "client",
                "id": c.id,
                "title": c.full_name or "",
                "subtitle": c.phone or c.email or "",
            })

    # Поиск по договорам
    if "contracts" in types_filter:
        from database import Contract as ContractModel
        contracts = db.query(ContractModel).filter(
            or_(
                ContractModel.contract_number.ilike(search_pattern),
                ContractModel.address.ilike(search_pattern),
            )
        ).limit(limit).all()
        for ct in contracts:
            results.append({
                "type": "contract",
                "id": ct.id,
                "title": ct.contract_number or "",
                "subtitle": ct.address or "",
            })

    # Поиск по CRM карточкам (через join с договором)
    if "crm_cards" in types_filter:
        from database import CRMCard as CRMCardModel, Contract as ContractModel2
        cards = db.query(CRMCardModel).join(
            ContractModel2, CRMCardModel.contract_id == ContractModel2.id
        ).filter(
            or_(
                ContractModel2.address.ilike(search_pattern),
                ContractModel2.contract_number.ilike(search_pattern),
            )
        ).limit(limit).all()
        for card in cards:
            contract = db.query(ContractModel2).filter(ContractModel2.id == card.contract_id).first()
            results.append({
                "type": "crm_card",
                "id": card.id,
                "title": f"Проект #{card.id}",
                "subtitle": f"{contract.address if contract else ''} ({card.column_name})",
            })

    return {
        "results": results[:limit],
        "total": len(results),
        "query": q
    }



# =========================
# РОУТЕРЫ (вынесены из main.py)
# =========================
from routers.auth_router import router as auth_router
from routers.employees_router import router as employees_router
from routers.clients_router import router as clients_router
from routers.contracts_router import router as contracts_router

app.include_router(auth_router, prefix="/api/auth")
app.include_router(employees_router, prefix="/api")
app.include_router(clients_router, prefix="/api/clients")
app.include_router(contracts_router, prefix="/api/contracts")

from routers.rates_router import router as rates_router
from routers.salaries_router import router as salaries_router
from routers.statistics_router import router as statistics_router
from routers.dashboard_router import router as dashboard_router
from routers.sync_router import router as sync_router

app.include_router(rates_router, prefix="/api/rates")
app.include_router(salaries_router, prefix="/api/salaries")
app.include_router(statistics_router, prefix="/api/statistics")
app.include_router(dashboard_router, prefix="/api/dashboard")
app.include_router(sync_router, prefix="/api/sync")

from routers.payments_router import router as payments_router
from routers.files_router import router as files_router
from routers.agents_router import router as agents_router
from routers.heartbeat_router import router as heartbeat_router
from routers.locks_router import router as locks_router

app.include_router(payments_router, prefix="/api/payments")
app.include_router(files_router, prefix="/api/files")
app.include_router(agents_router, prefix="/api/agents")
app.include_router(heartbeat_router, prefix="/api")
app.include_router(locks_router, prefix="/api/locks")

from routers.timeline_router import router as timeline_router
from routers.norm_days_router import router as norm_days_router
from routers.supervision_timeline_router import router as supervision_timeline_router
from routers.project_templates_router import router as project_templates_router
from routers.supervision_router import router as supervision_router
from routers.action_history_router import router as action_history_router
from routers.reports_router import router as reports_router

app.include_router(timeline_router, prefix="/api/timeline")
app.include_router(norm_days_router, prefix="/api/norm-days")
app.include_router(supervision_timeline_router, prefix="/api/supervision-timeline")
app.include_router(project_templates_router, prefix="/api/project-templates")
app.include_router(supervision_router, prefix="/api/supervision")
app.include_router(action_history_router, prefix="/api/action-history")
app.include_router(reports_router, prefix="/api/reports")

from routers.crm_router import router as crm_router
from routers.messenger_router import (
    router as messenger_router, sync_messenger_router,
    load_messenger_settings, seed_default_messenger_scripts,
)

app.include_router(crm_router, prefix="/api/crm")
app.include_router(messenger_router, prefix="/api/messenger")
app.include_router(sync_messenger_router, prefix="/api/sync")


# =========================
# СИНХРОНИЗАЦИЯ
# =========================

@app.post("/api/sync", response_model=SyncResponse)
async def sync_data(
    sync_request: SyncRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Синхронизация данных
    Возвращает все изменения после указанного timestamp
    """
    response = SyncResponse(timestamp=datetime.utcnow())

    # Клиенты
    if 'clients' in sync_request.entity_types:
        clients = db.query(Client).filter(
            Client.updated_at > sync_request.last_sync_timestamp
        ).all()
        response.clients = clients

    # Договоры
    if 'contracts' in sync_request.entity_types:
        contracts = db.query(Contract).filter(
            Contract.updated_at > sync_request.last_sync_timestamp
        ).all()
        response.contracts = contracts

    # Сотрудники
    if 'employees' in sync_request.entity_types:
        employees = db.query(Employee).filter(
            Employee.updated_at > sync_request.last_sync_timestamp
        ).all()
        response.employees = employees

    # Уведомления
    notifications = db.query(Notification).filter(
        Notification.employee_id == current_user.id,
        Notification.created_at > sync_request.last_sync_timestamp
    ).all()
    response.notifications = notifications

    return response


# =========================
# УВЕДОМЛЕНИЯ
# =========================

@app.get("/api/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить уведомления текущего пользователя"""
    query = db.query(Notification).filter(Notification.employee_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read == False)

    notifications = query.order_by(Notification.created_at.desc()).all()
    return notifications


@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отметить уведомление как прочитанное"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.employee_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()

    return {"message": "Уведомление прочитано"}



"""
FastAPI приложение для сайта (лендинг) — отдельный сервис.
Содержит только site_router, site_admin_router и auth (для входа в CMS).
Не запускает фоновые задачи CRM (deadline_checker, kpi_snapshot и т.д.);
единственная фоновая задача — обновление карты объектов сайта.
"""

import asyncio
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from config import get_settings
from database import SessionLocal, init_db

settings = get_settings()

app = FastAPI(
    title="Interior Studio Site API",
    version=settings.app_version,
    description="API для публичного сайта и CMS festivalcolor.ru",
)

# CORS
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "").strip()
if not _allowed_origins or _allowed_origins == "*":
    _cors_origins = ["http://localhost:3000", "http://localhost:5173"]
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


@app.middleware("http")
async def api_version_compat(request, call_next):
    """Rewrite /api/xxx → /api/v1/xxx для backward-compat."""
    path = request.scope["path"]
    if path.startswith("/api/") and not path.startswith("/api/v1/"):
        new_path = "/api/v1/" + path[5:]
        if new_path.endswith("/") and len(new_path) > 1:
            new_path = new_path.rstrip("/")
        request.scope["path"] = new_path
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if forwarded_proto:
        request.scope["scheme"] = forwarded_proto
    return await call_next(request)


@app.on_event("startup")
async def startup_event():
    logger.info(f"Site API запуск v{settings.app_version}")
    init_db()
    logger.info("База данных инициализирована (site)")

    from routers.site_ready_router import ensure_directions_section
    from services.site_map_service import ensure_map_section

    db = SessionLocal()
    try:
        ensure_map_section(db)
        ensure_directions_section(db)
    except Exception as exc:
        db.rollback()
        logger.warning(f"Секции сайта: не удалось добавить новую секцию: {exc}")
    finally:
        db.close()
    asyncio.create_task(_map_sync_loop())


async def _map_sync_loop():
    """Раз в шесть часов ищет координаты для новых и изменённых адресов договоров."""
    from services.site_map_service import sync_map_points

    await asyncio.sleep(30)
    while True:
        try:
            await asyncio.to_thread(sync_map_points)
        except Exception as exc:
            logger.warning(f"Карта объектов: ошибка фоновой синхронизации: {exc}")
        await asyncio.sleep(6 * 3600)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "site_api"}


# Auth — для входа в CMS (тот же /api/v1/auth/login что и CRM)
from routers.auth_router import router as auth_router

app.include_router(auth_router, prefix="/api/v1/auth")

# Site — публичные эндпоинты и CMS-администрирование
from routers.site_admin_router import router as site_admin_router
from routers.site_router import router as site_router

app.include_router(site_router, prefix="/api/v1")
app.include_router(site_admin_router, prefix="/api/v1")

from routers.site_ready_router import admin_router as site_ready_admin_router
from routers.site_ready_router import public_router as site_ready_public_router

app.include_router(site_ready_public_router, prefix="/api/v1")
app.include_router(site_ready_admin_router, prefix="/api/v1")

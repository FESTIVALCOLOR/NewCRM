"""
Публичный API лендинга festivalcolor.ru
GET /api/v1/site/public — весь контент одним запросом (без авторизации)
GET /api/v1/site/media/{filename} — публичный доступ к загруженным изображениям
"""

import os

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import FileResponse
from schemas import SitePublicResponse
from sqlalchemy.orm import Session

from database import (
    PortfolioImage,
    PricingPlan,
    Review,
    SiteAnalytics,
    SiteSection,
    SiteService,
    SiteSetting,
    StatItem,
    TeamMember,
    get_db,
)

UPLOADS_DIR = os.environ.get("SITE_UPLOADS_DIR", "/app/uploads/site")

router = APIRouter(prefix="/site", tags=["site-public"])


@router.get("/public", response_model=SitePublicResponse)
def get_public_site(db: Session = Depends(get_db)):
    settings_rows = db.query(SiteSetting).all()
    settings = {r.key: r.value for r in settings_rows}

    sections = db.query(SiteSection).order_by(SiteSection.sort_order).all()
    team = db.query(TeamMember).filter(TeamMember.is_visible == True).order_by(TeamMember.sort_order).all()
    stats = db.query(StatItem).order_by(StatItem.sort_order).all()
    services = db.query(SiteService).filter(SiteService.is_visible == True).order_by(SiteService.sort_order).all()
    pricing = db.query(PricingPlan).filter(PricingPlan.is_visible == True).order_by(PricingPlan.sort_order).all()
    reviews = db.query(Review).filter(Review.is_active == True).order_by(Review.sort_order).all()
    portfolio = db.query(PortfolioImage).filter(PortfolioImage.is_visible == True).order_by(PortfolioImage.sort_order).all()
    analytics = db.query(SiteAnalytics).filter(SiteAnalytics.id == 1).first()

    return SitePublicResponse(
        settings=settings,
        sections=sections,
        team=team,
        stats=stats,
        services=services,
        pricing=pricing,
        reviews=reviews,
        portfolio=portfolio,
        analytics=analytics,
    )


@router.get("/map-points")
def get_map_points(db: Session = Depends(get_db)):
    """Точки для карты объектов: сдвинутые координаты, состояние и город — без адресов."""
    from services.site_map_service import public_points

    return public_points(db)


@router.get("/visitor-region")
def get_visitor_region(request: Request, response: Response, db: Session = Depends(get_db)):
    """Регион цены готового дизайна для посетителя: по IP через локальную базу, без внешних сервисов.

    IP-адрес никуда не передаётся и не сохраняется; в ответе только регион цены и название города.
    """
    from services.site_visitor_region import visitor_region

    # Настоящий адрес посетителя передаёт nginx (он получает его по proxy_protocol)
    ip = (request.headers.get("x-real-ip") or (request.client.host if request.client else "")).strip()
    row = db.query(SiteSetting).filter(SiteSetting.key == "ready_region_cities").first()
    response.headers["Cache-Control"] = "no-store"
    return visitor_region(ip, row.value if row else "")


@router.get("/media/{filename}", include_in_schema=False)
def serve_media_public(filename: str):
    """Публичный доступ к загруженным изображениям сайта"""
    path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.isfile(path):
        from fastapi import HTTPException

        raise HTTPException(404)
    return FileResponse(path)

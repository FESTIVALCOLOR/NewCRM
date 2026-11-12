"""
Публичный API лендинга festivalcolor.ru
GET /api/site/public — весь контент одним запросом (без авторизации)
"""

from fastapi import APIRouter, Depends
from schemas import SitePublicResponse
from sqlalchemy.orm import Session

from database import (
    PortfolioImage,
    PricingPlan,
    Review,
    SiteSection,
    SiteService,
    SiteSetting,
    StatItem,
    TeamMember,
    get_db,
)

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

    return SitePublicResponse(
        settings=settings,
        sections=sections,
        team=team,
        stats=stats,
        services=services,
        pricing=pricing,
        reviews=reviews,
        portfolio=portfolio,
    )

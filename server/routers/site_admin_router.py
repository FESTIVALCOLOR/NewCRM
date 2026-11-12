"""
Admin API для управления контентом сайта festivalcolor.ru
Все endpoints требуют авторизации (JWT).
Prefix: /api/site/admin
"""

from typing import List

from auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from schemas import (
    PortfolioImageCreate,
    PortfolioImageResponse,
    PortfolioImageUpdate,
    PricingPlanCreate,
    PricingPlanResponse,
    PricingPlanUpdate,
    ReviewCreate,
    ReviewResponse,
    ReviewUpdate,
    SiteSectionResponse,
    SiteSectionUpdate,
    SiteServiceCreate,
    SiteServiceResponse,
    SiteServiceUpdate,
    SiteSettingResponse,
    SiteSettingUpdate,
    StatItemCreate,
    StatItemResponse,
    StatItemUpdate,
    TeamMemberCreate,
    TeamMemberResponse,
    TeamMemberUpdate,
)
from sqlalchemy.orm import Session

from database import (
    Employee,
    PortfolioImage,
    PricingItem,
    PricingPlan,
    Review,
    SiteSection,
    SiteService,
    SiteSetting,
    StatItem,
    TeamMember,
    get_db,
)

router = APIRouter(prefix="/site/admin", tags=["site-admin"])


# ──────────────────────────────────────────────
# НАСТРОЙКИ (key/value)
# ──────────────────────────────────────────────


@router.get("/settings", response_model=list[SiteSettingResponse])
def list_settings(db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    return db.query(SiteSetting).order_by(SiteSetting.id).all()


@router.put("/settings/{key}", response_model=SiteSettingResponse)
def update_setting(key: str, data: SiteSettingUpdate, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    if not obj:
        raise HTTPException(404, f"Настройка '{key}' не найдена")
    obj.value = data.value
    db.commit()
    db.refresh(obj)
    return obj


# ──────────────────────────────────────────────
# СЕКЦИИ (видимость / порядок)
# ──────────────────────────────────────────────


@router.get("/sections", response_model=list[SiteSectionResponse])
def list_sections(db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    return db.query(SiteSection).order_by(SiteSection.sort_order).all()


@router.put("/sections/{key}", response_model=SiteSectionResponse)
def update_section(key: str, data: SiteSectionUpdate, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = db.query(SiteSection).filter(SiteSection.key == key).first()
    if not obj:
        raise HTTPException(404, f"Секция '{key}' не найдена")
    if data.is_visible is not None:
        obj.is_visible = data.is_visible
    if data.sort_order is not None:
        obj.sort_order = data.sort_order
    db.commit()
    db.refresh(obj)
    return obj


# ──────────────────────────────────────────────
# КОМАНДА
# ──────────────────────────────────────────────


@router.get("/team", response_model=list[TeamMemberResponse])
def list_team(db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    return db.query(TeamMember).order_by(TeamMember.sort_order).all()


@router.post("/team", response_model=TeamMemberResponse)
def create_team(data: TeamMemberCreate, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = TeamMember(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/team/{id}", response_model=TeamMemberResponse)
def update_team(id: int, data: TeamMemberUpdate, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = db.query(TeamMember).filter(TeamMember.id == id).first()
    if not obj:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/team/{id}")
def delete_team(id: int, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = db.query(TeamMember).filter(TeamMember.id == id).first()
    if not obj:
        raise HTTPException(404)
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ──────────────────────────────────────────────
# СТАТИСТИКА
# ──────────────────────────────────────────────


@router.get("/stats", response_model=list[StatItemResponse])
def list_stats(db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    return db.query(StatItem).order_by(StatItem.sort_order).all()


@router.post("/stats", response_model=StatItemResponse)
def create_stat(data: StatItemCreate, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = StatItem(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/stats/{id}", response_model=StatItemResponse)
def update_stat(id: int, data: StatItemUpdate, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = db.query(StatItem).filter(StatItem.id == id).first()
    if not obj:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/stats/{id}")
def delete_stat(id: int, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = db.query(StatItem).filter(StatItem.id == id).first()
    if not obj:
        raise HTTPException(404)
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ──────────────────────────────────────────────
# УСЛУГИ
# ──────────────────────────────────────────────


@router.get("/services", response_model=list[SiteServiceResponse])
def list_services(db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    return db.query(SiteService).order_by(SiteService.sort_order).all()


@router.post("/services", response_model=SiteServiceResponse)
def create_service(data: SiteServiceCreate, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = SiteService(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/services/{id}", response_model=SiteServiceResponse)
def update_service(id: int, data: SiteServiceUpdate, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = db.query(SiteService).filter(SiteService.id == id).first()
    if not obj:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/services/{id}")
def delete_service(id: int, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = db.query(SiteService).filter(SiteService.id == id).first()
    if not obj:
        raise HTTPException(404)
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ──────────────────────────────────────────────
# ТАРИФЫ
# ──────────────────────────────────────────────


@router.get("/pricing", response_model=list[PricingPlanResponse])
def list_pricing(db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    return db.query(PricingPlan).order_by(PricingPlan.sort_order).all()


@router.post("/pricing", response_model=PricingPlanResponse)
def create_pricing(data: PricingPlanCreate, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    plan_data = data.model_dump(exclude={"items"})
    plan = PricingPlan(**plan_data)
    db.add(plan)
    db.flush()
    for i, item in enumerate(data.items):
        db.add(PricingItem(plan_id=plan.id, text=item.text, sort_order=item.sort_order or i))
    db.commit()
    db.refresh(plan)
    return plan


@router.put("/pricing/{id}", response_model=PricingPlanResponse)
def update_pricing(id: int, data: PricingPlanUpdate, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    plan = db.query(PricingPlan).filter(PricingPlan.id == id).first()
    if not plan:
        raise HTTPException(404)
    for k, v in data.model_dump(exclude={"items"}).items():
        setattr(plan, k, v)
    if data.items is not None:
        db.query(PricingItem).filter(PricingItem.plan_id == id).delete()
        for i, item in enumerate(data.items):
            db.add(PricingItem(plan_id=plan.id, text=item.text, sort_order=item.sort_order or i))
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/pricing/{id}")
def delete_pricing(id: int, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    plan = db.query(PricingPlan).filter(PricingPlan.id == id).first()
    if not plan:
        raise HTTPException(404)
    db.delete(plan)
    db.commit()
    return {"ok": True}


# ──────────────────────────────────────────────
# ОТЗЫВЫ
# ──────────────────────────────────────────────


@router.get("/reviews", response_model=list[ReviewResponse])
def list_reviews(db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    return db.query(Review).order_by(Review.sort_order).all()


@router.post("/reviews", response_model=ReviewResponse)
def create_review(data: ReviewCreate, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = Review(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/reviews/{id}", response_model=ReviewResponse)
def update_review(id: int, data: ReviewUpdate, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = db.query(Review).filter(Review.id == id).first()
    if not obj:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/reviews/{id}")
def delete_review(id: int, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = db.query(Review).filter(Review.id == id).first()
    if not obj:
        raise HTTPException(404)
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ──────────────────────────────────────────────
# ПОРТФОЛИО
# ──────────────────────────────────────────────


@router.get("/portfolio", response_model=list[PortfolioImageResponse])
def list_portfolio(db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    return db.query(PortfolioImage).order_by(PortfolioImage.sort_order).all()


@router.post("/portfolio", response_model=PortfolioImageResponse)
def create_portfolio(data: PortfolioImageCreate, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = PortfolioImage(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/portfolio/{id}", response_model=PortfolioImageResponse)
def update_portfolio(id: int, data: PortfolioImageUpdate, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = db.query(PortfolioImage).filter(PortfolioImage.id == id).first()
    if not obj:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/portfolio/{id}")
def delete_portfolio(id: int, db: Session = Depends(get_db), _: Employee = Depends(get_current_user)):
    obj = db.query(PortfolioImage).filter(PortfolioImage.id == id).first()
    if not obj:
        raise HTTPException(404)
    db.delete(obj)
    db.commit()
    return {"ok": True}

"""
Заявки с сайта в CRM (страница «Заявки»): просмотр, обработка с результатом, удаление.
Доступ — право access.leads, удаление — leads.delete (настраиваются в ролях админки CRM).
"""

from fastapi import APIRouter, Depends
from permissions import require_permission
from schemas import SiteLeadResponse, SiteLeadStatusUpdate
from services import site_leads
from sqlalchemy.orm import Session

from database import Employee, SiteLead, get_db

router = APIRouter(tags=["leads"])


@router.get("", response_model=list[SiteLeadResponse])
def list_leads(status: str = "", db: Session = Depends(get_db), _: Employee = Depends(require_permission("access.leads"))):
    return site_leads.list_leads(db, status)


@router.get("/count")
def count_new_leads(db: Session = Depends(get_db), _: Employee = Depends(require_permission("access.leads"))):
    return {"new": db.query(SiteLead).filter(SiteLead.status == "new").count()}


@router.put("/{lead_id}", response_model=SiteLeadResponse)
def update_lead_status(lead_id: int, data: SiteLeadStatusUpdate, db: Session = Depends(get_db), user: Employee = Depends(require_permission("access.leads"))):
    return site_leads.update_lead_status(db, lead_id, data.status, data.result, user)


@router.delete("/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db), _: Employee = Depends(require_permission("leads.delete"))):
    site_leads.delete_lead(db, lead_id)
    return {"ok": True}

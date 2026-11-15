"""
Оплаты клиента по договору: СБП-ссылка, проведение оплаты (СБП / наличные / перевод / карта), документ об оплате,
доп. соглашения, расчёт при расторжении, возвраты. prefix="/api/v1/client-payments"

Права:
  client_payments.manage   — сформировать ссылку, провести оплату, выписать документ, доп. платёж, уменьшение, расторжение
  client_payments.refund   — провести возврат клиенту
  client_payments.cancel   — снять проведённую оплату/возврат (документ аннулируется), удалить неоплаченную строку
  client_payments.settings — настройки СБП и реквизитов
Публично (без входа): документ по токену — страница /p/{token} в PWA и PDF.
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from permissions import check_permission, require_permission
from pydantic import BaseModel, Field
from services import client_payments as cp
from sqlalchemy.orm import Session

from database import ClientPaymentDoc, Employee, get_db

router = APIRouter(tags=["client-payments"])


class PaidBody(BaseModel):
    amount: Optional[float] = None
    date: Optional[str] = None  # YYYY-MM-DD
    time: Optional[str] = None  # HH:MM (МСК)
    method: str = Field(..., pattern="^(sbp|cash|transfer|card)$")


class ExtraBody(BaseModel):
    reason: str = Field("services", pattern="^(area|services)$")
    amount: float
    basis: str = Field(..., max_length=500)
    new_area: Optional[float] = None


class DecreaseBody(BaseModel):
    amount: float
    basis: str = Field(..., max_length=500)
    new_area: Optional[float] = None


class TerminateBody(BaseModel):
    retained: float
    reason: str = Field(..., max_length=1000)


class SettingsBody(BaseModel):
    sbp_link: Optional[str] = Field(None, max_length=1000)
    message_template: Optional[str] = Field(None, max_length=3000)
    seller_name: Optional[str] = Field(None, max_length=200)
    seller_inn: Optional[str] = Field(None, max_length=20)
    seller_ogrnip: Optional[str] = Field(None, max_length=20)
    tax_system: Optional[str] = Field(None, max_length=200)
    service_name: Optional[str] = Field(None, max_length=300)
    place_remote: Optional[str] = Field(None, max_length=300)
    place_office: Optional[str] = Field(None, max_length=300)
    cashier: Optional[str] = Field(None, max_length=200)


def _result(db, contract_id, **extra):
    contract = cp.get_contract_or_404(db, contract_id)
    return {**cp.contract_payments(db, contract), **extra}


# ── Статические пути (до динамических) ────────────────────────────────────────


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), user: Employee = Depends(require_permission("access.contracts"))):
    settings = cp.get_settings(db)
    if not check_permission(user, "client_payments.settings", db):
        # Без права настроек — только то, что нужно для «Сформировать оплату»
        settings = {"sbp_link": settings["sbp_link"]}
    return {**settings, "requisites_missing": cp.requisites_missing(cp.get_settings(db)), "cashier_default": cp.director_cashier(db, {})}


@router.put("/settings")
def save_settings(body: SettingsBody, db: Session = Depends(get_db), _: Employee = Depends(require_permission("client_payments.settings"))):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    settings = cp.save_settings(db, data)
    return {**settings, "requisites_missing": cp.requisites_missing(settings)}


@router.get("/qr.svg")
def qr_preview(data: str, _: Employee = Depends(require_permission("access.contracts"))):
    """QR-код для предпросмотра СБП-ссылки в админке."""
    from services.payment_doc_pdf import qr_svg

    if not data or len(data) > 1000:
        raise HTTPException(400, "Пустая или слишком длинная ссылка")
    return Response(qr_svg(data), media_type="image/svg+xml")


def _public_doc(db, token):
    doc = db.query(ClientPaymentDoc).filter(ClientPaymentDoc.token == token).first()
    if not doc:
        raise HTTPException(404, "Документ не найден")
    return doc


@router.get("/public/docs/{token}")
def public_doc(token: str, db: Session = Depends(get_db)):
    """Публично: данные документа для страницы /p/{token} (клиент открывает по ссылке)."""
    doc = _public_doc(db, token)
    return {**(doc.data or {}), "number": doc.number, "annulled": doc.annulled_at is not None, "filename": cp.doc_filename(doc)}


@router.get("/public/docs/{token}/pdf")
def public_doc_pdf(token: str, download: bool = False, db: Session = Depends(get_db)):
    """Публично: PDF документа об оплате."""
    from urllib.parse import quote

    doc = _public_doc(db, token)
    disposition = "attachment" if download else "inline"
    return Response(
        cp.doc_pdf_bytes(db, doc),
        media_type="application/pdf",
        headers={"Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(cp.doc_filename(doc))}", "Cache-Control": "no-store"},
    )


@router.get("/contract/{contract_id}")
def list_contract_payments(contract_id: int, db: Session = Depends(get_db), _: Employee = Depends(require_permission("access.contracts"))):
    return _result(db, contract_id)


@router.post("/contract/{contract_id}/extra")
def add_extra(contract_id: int, body: ExtraBody, db: Session = Depends(get_db), user: Employee = Depends(require_permission("client_payments.manage"))):
    contract = cp.get_contract_or_404(db, contract_id)
    info = cp.add_extra(db, contract, body.model_dump(), user)
    return _result(db, contract_id, area_change=info["area_change"])


@router.post("/contract/{contract_id}/decrease")
def decrease(contract_id: int, body: DecreaseBody, db: Session = Depends(get_db), user: Employee = Depends(require_permission("client_payments.manage"))):
    contract = cp.get_contract_or_404(db, contract_id)
    info = cp.decrease(db, contract, body.model_dump(), user)
    return _result(db, contract_id, refund=info["refund"], area_change=info["area_change"])


@router.post("/contract/{contract_id}/terminate")
def terminate(contract_id: int, body: TerminateBody, db: Session = Depends(get_db), user: Employee = Depends(require_permission("client_payments.manage"))):
    contract = cp.get_contract_or_404(db, contract_id)
    info = cp.terminate(db, contract, body.model_dump(), user)
    return _result(db, contract_id, **info)


# ── Динамические пути по платежу ──────────────────────────────────────────────


@router.post("/{payment_id}/link")
def payment_link(payment_id: int, db: Session = Depends(get_db), user: Employee = Depends(require_permission("client_payments.manage"))):
    row = cp.get_payment_or_404(db, payment_id)
    return cp.payment_link(db, row, user)


@router.post("/{payment_id}/pay")
def pay(payment_id: int, body: PaidBody, background: BackgroundTasks, db: Session = Depends(get_db), user: Employee = Depends(require_permission("client_payments.manage"))):
    row = cp.get_payment_or_404(db, payment_id)
    if row.direction == "out" and not check_permission(user, "client_payments.refund", db):
        raise HTTPException(403, "Проводить возврат клиенту может только руководитель")
    doc = cp.pay(db, row, body.model_dump(), user)
    background.add_task(cp.upload_doc_to_disk, doc.id)
    return _result(db, row.contract_id, doc=cp.serialize_doc(doc, cp.get_settings(db)))


@router.post("/{payment_id}/issue-doc")
def issue_doc(payment_id: int, body: PaidBody, background: BackgroundTasks, db: Session = Depends(get_db), user: Employee = Depends(require_permission("client_payments.manage"))):
    row = cp.get_payment_or_404(db, payment_id)
    if row.direction == "out" and not check_permission(user, "client_payments.refund", db):
        raise HTTPException(403, "Документ о возврате выписывает руководитель")
    doc = cp.issue_doc_for_legacy(db, row, body.model_dump(), user)
    background.add_task(cp.upload_doc_to_disk, doc.id)
    return _result(db, row.contract_id, doc=cp.serialize_doc(doc, cp.get_settings(db)))


@router.post("/{payment_id}/cancel")
def cancel_paid(payment_id: int, db: Session = Depends(get_db), user: Employee = Depends(require_permission("client_payments.cancel"))):
    row = cp.get_payment_or_404(db, payment_id)
    cp.cancel_paid(db, row, user)
    return _result(db, row.contract_id)


@router.delete("/{payment_id}")
def delete_open(payment_id: int, db: Session = Depends(get_db), user: Employee = Depends(require_permission("client_payments.cancel"))):
    row = cp.get_payment_or_404(db, payment_id)
    contract_id = row.contract_id
    cp.delete_open(db, row, user)
    return _result(db, contract_id)

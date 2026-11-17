"""Роутер для работы с корзиной договоров (снимки удалённых)."""

from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from permissions import require_permission
from sqlalchemy.orm import Session

from database import (
    ApprovalStageDeadline,
    Contract,
    CRMCard,
    DeletedContract,
    Employee,
    FileStorage,
    Payment,
    ProjectFile,
    ProjectTimelineEntry,
    Salary,
    StageExecutor,
    StageWorkflowState,
    SupervisionCard,
    SupervisionProjectHistory,
    SupervisionTimelineEntry,
    SupervisionVisit,
    get_db,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["deleted-contracts"])


@router.get("/")
async def list_deleted_contracts(
    current_user: Employee = Depends(require_permission("contracts.delete")),
    db: Session = Depends(get_db),
):
    """Список удалённых договоров (корзина)."""
    items = db.query(DeletedContract).order_by(DeletedContract.deleted_at.desc()).all()
    return [
        {
            "id": r.id,
            "original_contract_id": r.original_contract_id,
            "contract_number": r.contract_number,
            "client_name": r.client_name,
            "address": r.address,
            "project_type": r.project_type,
            "project_subtype": r.project_subtype,
            "deleted_at": r.deleted_at.isoformat() if r.deleted_at else None,
            "deleted_by_id": r.deleted_by_id,
        }
        for r in items
    ]


@router.post("/{deleted_id}/restore")
async def restore_deleted_contract(
    deleted_id: int,
    current_user: Employee = Depends(require_permission("contracts.delete")),
    db: Session = Depends(get_db),
):
    """Восстановить договор из корзины."""
    rec = db.query(DeletedContract).filter(DeletedContract.id == deleted_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Запись в корзине не найдена")

    snap = rec.snapshot
    try:

        def _dt(v):
            if v is None:
                return None
            try:
                return datetime.fromisoformat(v)
            except Exception:
                return None

        # 1. Восстанавливаем договор
        cdata = {k: v for k, v in snap["contract"].items() if k != "id"}
        for f in ("contract_date", "status_changed_date", "created_at", "updated_at"):
            if f in cdata:
                cdata[f] = _dt(cdata[f])
        new_contract = Contract(**cdata)
        db.add(new_contract)
        db.flush()
        new_cid = new_contract.id

        # 2. CRM карточки
        card_id_map = {}
        for card_snap in snap.get("crm_cards", []):
            cd = {k: v for k, v in card_snap["card"].items() if k != "id"}
            old_card_id = card_snap["card"]["id"]
            cd["contract_id"] = new_cid
            for f in ("paused_at", "deadline", "created_at", "updated_at"):
                if f in cd:
                    cd[f] = _dt(cd[f])
            new_card = CRMCard(**cd)
            db.add(new_card)
            db.flush()
            new_card_id = new_card.id
            card_id_map[old_card_id] = new_card_id

            for se in card_snap.get("stage_executors", []):
                sed = {k: v for k, v in se.items() if k != "id"}
                sed["crm_card_id"] = new_card_id
                for f in ("deadline", "completed_date", "assigned_date", "submitted_date", "created_at"):
                    if f in sed:
                        sed[f] = _dt(sed[f])
                db.add(StageExecutor(**sed))

            for wf in card_snap.get("workflow_states", []):
                wfd = {k: v for k, v in wf.items() if k != "id"}
                wfd["crm_card_id"] = new_card_id
                for f in ("updated_at", "submitted_at", "created_at"):
                    if f in wfd:
                        wfd[f] = _dt(wfd[f])
                db.add(StageWorkflowState(**wfd))

            for ad in card_snap.get("approval_deadlines", []):
                add = {k: v for k, v in ad.items() if k != "id"}
                add["crm_card_id"] = new_card_id
                for f in ("completed_date", "created_at"):
                    if f in add:
                        add[f] = _dt(add[f])
                db.add(ApprovalStageDeadline(**add))

            for p in card_snap.get("payments", []):
                pd = {k: v for k, v in p.items() if k != "id"}
                pd["contract_id"] = new_cid
                pd["crm_card_id"] = new_card_id
                db.add(Payment(**pd))

        # 3. Надзор-карточки
        sup_id_map = {}
        for sup_snap in snap.get("supervision_cards", []):
            sd = {k: v for k, v in sup_snap["card"].items() if k != "id"}
            old_sup_id = sup_snap["card"]["id"]
            sd["contract_id"] = new_cid
            for f in ("paused_at", "start_date", "created_at", "updated_at"):
                if f in sd:
                    sd[f] = _dt(sd[f])
            new_sup = SupervisionCard(**sd)
            db.add(new_sup)
            db.flush()
            new_sup_id = new_sup.id
            sup_id_map[old_sup_id] = new_sup_id

            for te in sup_snap.get("timeline_entries", []):
                ted = {k: v for k, v in te.items() if k != "id"}
                ted["supervision_card_id"] = new_sup_id
                db.add(SupervisionTimelineEntry(**ted))

            for v in sup_snap.get("visits", []):
                vd = {k: v for k, v in v.items() if k != "id"}
                vd["supervision_card_id"] = new_sup_id
                for f in ("visit_date", "created_at"):
                    if f in vd:
                        vd[f] = _dt(vd[f])
                db.add(SupervisionVisit(**vd))

            for h in sup_snap.get("history", []):
                hd = {k: v for k, v in h.items() if k != "id"}
                hd["supervision_card_id"] = new_sup_id
                for f in ("completed_date", "created_at"):
                    if f in hd:
                        hd[f] = _dt(hd[f])
                db.add(SupervisionProjectHistory(**hd))

            for p in sup_snap.get("payments", []):
                pd = {k: v for k, v in p.items() if k != "id"}
                pd["contract_id"] = new_cid
                pd["supervision_card_id"] = new_sup_id
                db.add(Payment(**pd))

        # 4. Оставшиеся платежи (по contract_id, без дублей)
        existing_crm_ids = {p["crm_card_id"] for cs in snap.get("crm_cards", []) for p in cs.get("payments", [])}
        existing_sup_ids = {p["supervision_card_id"] for ss in snap.get("supervision_cards", []) for p in ss.get("payments", [])}
        for p in snap.get("payments", []):
            if p.get("crm_card_id") in existing_crm_ids or p.get("supervision_card_id") in existing_sup_ids:
                continue
            pd = {k: v for k, v in p.items() if k != "id"}
            pd["contract_id"] = new_cid
            if pd.get("crm_card_id") and pd["crm_card_id"] in card_id_map:
                pd["crm_card_id"] = card_id_map[pd["crm_card_id"]]
            db.add(Payment(**pd))

        # 5. Зарплаты
        for s in snap.get("salaries", []):
            sd = {k: v for k, v in s.items() if k != "id"}
            sd["contract_id"] = new_cid
            for f in ("paid_date", "created_at"):
                if f in sd:
                    sd[f] = _dt(sd[f])
            db.add(Salary(**sd))

        # 6. Файлы проекта (записи в БД)
        for f in snap.get("project_files", []):
            fd = {k: v for k, v in f.items() if k != "id"}
            fd["contract_id"] = new_cid
            db.add(ProjectFile(**fd))

        # 7. Timeline
        for t in snap.get("timeline_entries", []):
            td = {k: v for k, v in t.items() if k != "id"}
            td["contract_id"] = new_cid
            for f in ("updated_at", "created_at"):
                if f in td:
                    td[f] = _dt(td[f])
            db.add(ProjectTimelineEntry(**td))

        # 8. FileStorage
        for f in snap.get("file_storage", []):
            fd = {k: v for k, v in f.items() if k != "id"}
            fd["contract_id"] = new_cid
            db.add(FileStorage(**fd))

        # 9. Восстанавливаем папку с ЯД из корзины
        if rec.yandex_folder_path:
            try:
                from yandex_disk_service import get_yandex_disk_service

                yd = get_yandex_disk_service()
                if yd and yd.token:
                    trash_path = rec.yandex_folder_path.replace("disk:", "")
                    yd.restore_from_trash(trash_path)
                    logger.info(f"Папка ЯД восстановлена из корзины: {trash_path}")
            except Exception as e:
                logger.warning(f"Не удалось восстановить папку ЯД из корзины: {e}")

        # 10. Удаляем запись из корзины
        db.delete(rec)
        db.commit()

        return {
            "status": "restored",
            "new_contract_id": new_cid,
            "message": f"Договор №{rec.contract_number} восстановлен",
        }

    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка восстановления договора {deleted_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка восстановления: {str(e)}")


@router.delete("/{deleted_id}")
async def permanently_delete(
    deleted_id: int,
    current_user: Employee = Depends(require_permission("contracts.delete")),
    db: Session = Depends(get_db),
):
    """Безвозвратно удалить запись из корзины (и с ЯД навсегда)."""
    rec = db.query(DeletedContract).filter(DeletedContract.id == deleted_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if rec.yandex_folder_path:
        try:
            from yandex_disk_service import get_yandex_disk_service

            yd = get_yandex_disk_service()
            if yd and yd.token:
                trash_path = rec.yandex_folder_path.replace("disk:", "")
                yd.delete_file(trash_path, permanently=True)
        except Exception as e:
            logger.warning(f"Не удалось безвозвратно удалить ЯД {rec.yandex_folder_path}: {e}")

    db.delete(rec)
    db.commit()
    return {"status": "deleted", "message": "Удалено безвозвратно"}

"""
Роутер шаблонов проектов (project-templates).
Подключается в main.py через app.include_router(project_templates_router, prefix="/api/project-templates").
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, Employee, Contract, ProjectFile
from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["project-templates"])


@router.post("/")
async def add_project_template(
    contract_id: int,
    template_url: str,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Добавить ссылку на шаблон проекта"""
    try:
        # Проверяем существование договора
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Договор не найден")

        # Сохраняем шаблон как файл проекта
        file_record = ProjectFile(
            contract_id=contract_id,
            stage='template',
            file_type='template_url',
            public_link=template_url,
            yandex_path='',
            file_name=template_url
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)

        return {'id': file_record.id, 'contract_id': contract_id, 'template_url': template_url}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при добавлении шаблона проекта: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/{contract_id}")
async def get_project_templates(
    contract_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить все шаблоны для договора"""
    templates = db.query(ProjectFile).filter(
        ProjectFile.contract_id == contract_id,
        ProjectFile.stage == 'template'
    ).all()

    return [{
        'id': t.id,
        'contract_id': t.contract_id,
        'template_url': t.public_link,
        'created_at': t.upload_date.isoformat() if t.upload_date else None
    } for t in templates]


@router.delete("/{template_id}")
async def delete_project_template(
    template_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить шаблон проекта"""
    template = db.query(ProjectFile).filter(
        ProjectFile.id == template_id,
        ProjectFile.stage == 'template'
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    db.delete(template)
    db.commit()

    return {"status": "success", "message": "Шаблон удален"}

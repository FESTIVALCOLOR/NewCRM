"""
Роутер опросов клиентов (интеграция с Яндекс Формами).

Подключение: app.include_router(survey_router, prefix="/api/surveys")

Эндпоинты:
  POST /create                  — создать опрос для договора (авторизация)
  GET  /contract/{contract_id}  — получить опрос по договору (авторизация)
  POST /{survey_id}/resend      — переотправить ссылку (авторизация)
  GET  /stats                   — статистика по опросам (авторизация)
  POST /yandex-webhook          — принять ответы из Яндекс Форм (без авторизации)
  POST /manual-import           — ручной импорт результатов (авторизация, fallback)
"""
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import (
    get_db, Employee, Contract, CRMCard, SupervisionCard,
    ClientSurvey,
)
from auth import get_current_user
from constants import ROLE_ADMIN, ROLE_DIRECTOR, POSITION_STUDIO_DIRECTOR

logger = logging.getLogger(__name__)

router = APIRouter(tags=["surveys"])

# ── Константы ────────────────────────────────────────────────────────

SURVEY_EXPIRY_DAYS = 30  # Срок действия ссылки на опрос

# ID формы в Яндекс Формах (настраивается через переменные окружения или БД)
# Три формы — по одной на каждый тип проекта
YANDEX_FORM_IDS = {
    'individual': '69b6c7214936397cd99e21f7',
    'template': '69b6dce484227c670638562d',
    'supervision': '69b6ddd784227c6ccf385618',
}


# ── Pydantic-схемы ──────────────────────────────────────────────────

class SurveyCreateRequest(BaseModel):
    contract_id: int
    project_type: str = Field(..., pattern='^(individual|template|supervision)$')


class SurveyResponse(BaseModel):
    id: int
    contract_id: int
    project_type: str
    status: str
    survey_link: Optional[str] = None
    nps_score: Optional[int] = None
    csat_score: Optional[int] = None
    design_score: Optional[int] = None
    deadline_score: Optional[int] = None
    communication_score: Optional[int] = None
    expectations_score: Optional[int] = None
    supervision_score: Optional[int] = None
    comment: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ManualImportRequest(BaseModel):
    """Ручной импорт результатов опроса (fallback если webhook не работает)."""
    survey_token: str
    nps_score: int = Field(..., ge=0, le=10)
    csat_score: int = Field(..., ge=1, le=5)
    design_score: int = Field(..., ge=1, le=5)
    deadline_score: int = Field(..., ge=1, le=5)
    communication_score: int = Field(..., ge=1, le=5)
    expectations_score: int = Field(..., ge=1, le=5)
    supervision_score: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class SurveyStatsResponse(BaseModel):
    total: int
    pending: int
    sent: int
    completed: int
    expired: int
    avg_nps: Optional[float] = None
    avg_csat: Optional[float] = None
    response_rate: float  # % завершённых от отправленных


# ── Вспомогательные функции ──────────────────────────────────────────

def _generate_survey_link(survey: ClientSurvey) -> str:
    """Генерирует ссылку на Яндекс Форму со скрытыми параметрами."""
    form_id = YANDEX_FORM_IDS.get(survey.project_type, '')
    if not form_id:
        return f"[форма не настроена для {survey.project_type}]"

    return (
        f"https://forms.yandex.ru/cloud/{form_id}/"
        f"?contract_id={survey.contract_id}"
        f"&project_type={survey.project_type}"
        f"&survey_token={survey.access_token}"
    )


def _is_admin(employee: Employee) -> bool:
    """Проверяет, является ли сотрудник руководителем/администратором."""
    role = employee.role or ''
    position = employee.position or ''
    return (
        role in (ROLE_ADMIN, ROLE_DIRECTOR)
        or position == POSITION_STUDIO_DIRECTOR
    )


def _survey_to_response(survey: ClientSurvey) -> dict:
    """Конвертирует модель в dict для ответа API."""
    return {
        "id": survey.id,
        "contract_id": survey.contract_id,
        "project_type": survey.project_type,
        "status": survey.status,
        "survey_link": _generate_survey_link(survey) if survey.status != 'completed' else None,
        "nps_score": survey.nps_score,
        "csat_score": survey.csat_score,
        "design_score": survey.design_score,
        "deadline_score": survey.deadline_score,
        "communication_score": survey.communication_score,
        "expectations_score": survey.expectations_score,
        "supervision_score": survey.supervision_score,
        "comment": survey.comment,
        "created_at": survey.created_at.isoformat() if survey.created_at else None,
        "completed_at": survey.completed_at.isoformat() if survey.completed_at else None,
    }


def _apply_scores(survey: ClientSurvey, answers: dict):
    """Заполняет оценки опроса из словаря ответов.

    Поддерживает несколько вариантов именования ключей:
    - Короткие: nps, csat, design, deadline, communication, expectations, supervision, comment
    - С префиксом q: q1_nps, q2_csat, ...
    - Яндекс slugs: answer_number_XXXXX, answer_short_text_XXXXX
    """
    survey.nps_score = _safe_int(_find_answer(answers, 'nps', 'q1_nps'))
    survey.csat_score = _safe_int(_find_answer(answers, 'csat', 'q2_csat'))
    survey.design_score = _safe_int(_find_answer(answers, 'design', 'q3_design'))
    survey.deadline_score = _safe_int(_find_answer(answers, 'deadline', 'q4_deadline'))
    survey.communication_score = _safe_int(_find_answer(answers, 'communication', 'q5_communication'))
    survey.expectations_score = _safe_int(_find_answer(answers, 'expectations', 'q6_expectations'))
    supervision = _find_answer(answers, 'supervision', 'q7_supervision')
    survey.supervision_score = _safe_int(supervision) if supervision else None
    survey.comment = _find_answer(answers, 'comment', 'q8_comment') or ''


def _find_answer(answers: dict, *keys):
    """Ищет значение по нескольким возможным ключам."""
    for key in keys:
        val = answers.get(key)
        if val is not None and val != '':
            return val
    return None


def _safe_int(value) -> Optional[int]:
    """Безопасное преобразование в int.

    Яндекс Формы передают ответы шкалы в формате:
      '"0 - Точно не буду рекомендовать, 10 - Обязательно порекомендую": 10'
    Извлекаем число после последнего двоеточия.
    """
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        pass
    # Пробуем извлечь число после последнего ":"
    if isinstance(value, str) and ':' in value:
        try:
            return int(value.rsplit(':', 1)[1].strip())
        except (ValueError, IndexError):
            pass
    # Пробуем найти последнее число в строке
    if isinstance(value, str):
        import re
        nums = re.findall(r'\d+', value)
        if nums:
            return int(nums[-1])
    return None


# ── Эндпоинты (с авторизацией) ──────────────────────────────────────

@router.post("/create")
async def create_survey(
    req: SurveyCreateRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Создать опрос для договора.
    Генерирует уникальный токен и ссылку на Яндекс Форму.
    """
    # Проверяем существование договора
    contract = db.query(Contract).filter(Contract.id == req.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    # Проверяем, нет ли уже активного опроса
    existing = db.query(ClientSurvey).filter(
        ClientSurvey.contract_id == req.contract_id,
        ClientSurvey.project_type == req.project_type,
        ClientSurvey.status.in_(['pending', 'sent']),
    ).first()

    if existing:
        return _survey_to_response(existing)

    # Генерируем уникальный токен
    token = secrets.token_urlsafe(32)

    survey = ClientSurvey(
        contract_id=req.contract_id,
        project_type=req.project_type,
        access_token=token,
        status='pending',
        expires_at=datetime.utcnow() + timedelta(days=SURVEY_EXPIRY_DAYS),
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)

    logger.info(
        f"Опрос создан: survey_id={survey.id}, contract_id={req.contract_id}, "
        f"type={req.project_type}, by={current_user.full_name}"
    )

    return _survey_to_response(survey)


@router.get("/contract/{contract_id}")
async def get_surveys_by_contract(
    contract_id: int,
    project_type: Optional[str] = Query(None, pattern='^(individual|template|supervision)$'),
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить опросы по договору."""
    query = db.query(ClientSurvey).filter(
        ClientSurvey.contract_id == contract_id,
    )
    if project_type:
        query = query.filter(ClientSurvey.project_type == project_type)

    surveys = query.order_by(ClientSurvey.created_at.desc()).all()
    return [_survey_to_response(s) for s in surveys]


@router.post("/{survey_id}/resend")
async def resend_survey(
    survey_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Переотправить ссылку на опрос (обновить статус и срок)."""
    survey = db.query(ClientSurvey).filter(ClientSurvey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Опрос не найден")

    if survey.status == 'completed':
        raise HTTPException(status_code=400, detail="Опрос уже завершён")

    survey.status = 'sent'
    survey.sent_at = datetime.utcnow()
    survey.expires_at = datetime.utcnow() + timedelta(days=SURVEY_EXPIRY_DAYS)
    db.commit()

    logger.info(f"Опрос переотправлен: survey_id={survey_id}, by={current_user.full_name}")

    return _survey_to_response(survey)


@router.get("/stats")
async def get_survey_stats(
    project_type: Optional[str] = Query(None, pattern='^(individual|template|supervision)$'),
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Статистика по опросам. Доступна только руководителям."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Нет доступа к статистике опросов")

    query = db.query(ClientSurvey)
    if project_type:
        query = query.filter(ClientSurvey.project_type == project_type)

    surveys = query.all()

    total = len(surveys)
    by_status = {}
    for s in surveys:
        by_status[s.status] = by_status.get(s.status, 0) + 1

    completed = [s for s in surveys if s.status == 'completed']
    sent_or_completed = by_status.get('sent', 0) + by_status.get('completed', 0)

    avg_nps = None
    avg_csat = None
    if completed:
        nps_values = [s.nps_score for s in completed if s.nps_score is not None]
        csat_values = [s.csat_score for s in completed if s.csat_score is not None]
        avg_nps = round(sum(nps_values) / len(nps_values), 1) if nps_values else None
        avg_csat = round(sum(csat_values) / len(csat_values), 1) if csat_values else None

    return {
        "total": total,
        "pending": by_status.get('pending', 0),
        "sent": by_status.get('sent', 0),
        "completed": by_status.get('completed', 0),
        "expired": by_status.get('expired', 0),
        "avg_nps": avg_nps,
        "avg_csat": avg_csat,
        "response_rate": round(
            len(completed) / sent_or_completed * 100, 1
        ) if sent_or_completed > 0 else 0,
    }


# ── Webhook Яндекс Форм (без авторизации) ───────────────────────────

@router.post("/yandex-webhook")
async def handle_yandex_form_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Принимает ответы из Яндекс Форм при заполнении.

    Яндекс Формы (бизнес) отправляет данные в формате JSON-RPC 2.0:
    {"jsonrpc": "2.0", "method": "...", "params": {...}, "id": "..."}

    Параметры настраиваются в интеграции формы. Ожидаемые params:
      survey_token, contract_id, project_type,
      nps, csat, design, deadline, communication, expectations,
      supervision (опционально), comment
    """
    try:
        data = await request.json()
    except Exception:
        logger.warning("Webhook: невалидный JSON")
        raise HTTPException(status_code=400, detail="Невалидный JSON")

    logger.info(f"Webhook: входящие данные: {str(data)[:500]}")

    # Извлекаем params из JSON-RPC или из плоского JSON
    if 'jsonrpc' in data and 'params' in data:
        # JSON-RPC 2.0 формат (Яндекс Формы бизнес)
        answers = data.get('params', {})
        logger.info(f"Webhook: JSON-RPC формат, params keys: {list(answers.keys())}")
    elif 'answer' in data and isinstance(data.get('answer'), dict):
        # Cloud Functions формат: {answer: {data: {slug: {value: ...}}}}
        answers = {}
        answer_data = data['answer'].get('data', {})
        for slug, entry in answer_data.items():
            val = entry.get('value', '')
            # Для choices — склеиваем тексты
            if isinstance(val, list):
                val = ', '.join(item.get('text', str(item)) for item in val)
            answers[slug] = val
        logger.info(f"Webhook: Cloud Functions формат, keys: {list(answers.keys())}")
    elif 'answers' in data and isinstance(data['answers'], list):
        # Массив ответов
        answers = {}
        for item in data['answers']:
            qid = item.get('question_id', item.get('slug', ''))
            val = item.get('value', item.get('text', ''))
            answers[qid] = val
    else:
        # Плоский формат
        answers = {k: v for k, v in data.items() if k not in ('answer_id', 'jsonrpc', 'id', 'method')}

    # Извлекаем токен — ищем по нескольким возможным ключам
    token = None
    for key in ('survey_token', 'hidden_survey_token', 'token'):
        token = answers.get(key) or data.get(key)
        if token:
            break

    if not token:
        logger.warning(f"Webhook: отсутствует survey_token. Keys: {list(answers.keys())}")
        raise HTTPException(status_code=400, detail="Отсутствует survey_token")

    # Ищем опрос по токену
    survey = db.query(ClientSurvey).filter(
        ClientSurvey.access_token == token,
        ClientSurvey.status != 'completed',
    ).first()

    if not survey:
        logger.warning(f"Webhook: опрос не найден или уже завершён, token={token[:8]}...")
        raise HTTPException(status_code=404, detail="Опрос не найден или уже завершён")

    # Проверяем срок действия
    if survey.expires_at and survey.expires_at < datetime.utcnow():
        survey.status = 'expired'
        db.commit()
        logger.warning(f"Webhook: опрос просрочен, survey_id={survey.id}")
        raise HTTPException(status_code=410, detail="Опрос просрочен")

    # Заполняем оценки
    _apply_scores(survey, answers)
    survey.status = 'completed'
    survey.completed_at = datetime.utcnow()
    survey.yandex_answer_id = str(data.get('answer_id', ''))

    db.commit()

    logger.info(
        f"Webhook: опрос завершён, survey_id={survey.id}, "
        f"contract_id={survey.contract_id}, NPS={survey.nps_score}"
    )

    return {"status": "ok", "survey_id": survey.id}


# ── Ручной импорт (fallback) ────────────────────────────────────────

@router.post("/manual-import")
async def manual_import_survey(
    req: ManualImportRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ручной импорт результатов опроса.
    Используется как fallback, если webhook Яндекс Форм не работает
    (например, при использовании бесплатного аккаунта без webhook).
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Только руководители могут импортировать")

    survey = db.query(ClientSurvey).filter(
        ClientSurvey.access_token == req.survey_token,
    ).first()

    if not survey:
        raise HTTPException(status_code=404, detail="Опрос с таким токеном не найден")

    if survey.status == 'completed':
        raise HTTPException(status_code=400, detail="Опрос уже завершён")

    survey.nps_score = req.nps_score
    survey.csat_score = req.csat_score
    survey.design_score = req.design_score
    survey.deadline_score = req.deadline_score
    survey.communication_score = req.communication_score
    survey.expectations_score = req.expectations_score
    survey.supervision_score = req.supervision_score
    survey.comment = req.comment
    survey.status = 'completed'
    survey.completed_at = datetime.utcnow()

    db.commit()

    logger.info(
        f"Ручной импорт: survey_id={survey.id}, "
        f"contract_id={survey.contract_id}, by={current_user.full_name}"
    )

    return _survey_to_response(survey)


# ── Список всех опросов (для админки) ────────────────────────────────

@router.get("/list")
async def list_surveys(
    project_type: Optional[str] = Query(None, pattern='^(individual|template|supervision)$'),
    status: Optional[str] = Query(None, pattern='^(pending|sent|completed|expired)$'),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Список опросов с фильтрацией. Доступно только руководителям."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Нет доступа")

    query = db.query(ClientSurvey)

    if project_type:
        query = query.filter(ClientSurvey.project_type == project_type)
    if status:
        query = query.filter(ClientSurvey.status == status)

    total = query.count()
    surveys = query.order_by(
        ClientSurvey.created_at.desc()
    ).offset(offset).limit(limit).all()

    return {
        "items": [_survey_to_response(s) for s in surveys],
        "total": total,
    }

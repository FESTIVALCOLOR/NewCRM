import logging
from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, extract
from typing import List, Optional

from database import (
    get_db, Employee, Contract, Payment, Rate, Salary,
    CRMCard, SupervisionCard, ActivityLog
)
from auth import get_current_user
from permissions import require_permission
from schemas import PaymentCreate, PaymentUpdate, PaymentResponse, PaymentManualUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["payments"])


# =========================
# СТАТИЧЕСКИЕ ENDPOINTS (ПЕРЕД динамическими /{payment_id})
# =========================


@router.get("/")
async def get_all_payments(
    year: Optional[int] = None,
    payment_type: Optional[str] = None,
    month: Optional[int] = None,
    include_null_month: Optional[bool] = False,  # ДОБАВЛЕНО 06.02.2026: включить платежи без месяца
    contract_id: Optional[int] = None,   # ДОБАВЛЕНО 21.02.2026: фильтр по договору
    employee_id: Optional[int] = None,   # ДОБАВЛЕНО 21.02.2026: фильтр по сотруднику
    is_paid: Optional[bool] = None,      # ДОБАВЛЕНО 21.02.2026: фильтр по статусу оплаты
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить все платежи с фильтрами (включая оклады из таблицы salaries)"""
    try:
        result = []

        # 1. Платежи из таблицы payments (CRM и Надзор)
        payments_query = db.query(Payment)

        if year:
            if include_null_month:
                # ИСПРАВЛЕНИЕ 06.02.2026: Включаем платежи с NULL report_month (В работе)
                payments_query = payments_query.filter(
                    or_(
                        Payment.report_month.like(f'{year}%'),
                        Payment.report_month.is_(None)
                    )
                )
            else:
                payments_query = payments_query.filter(Payment.report_month.like(f'{year}%'))
        if month:
            payments_query = payments_query.filter(Payment.report_month.like(f'{year}-{month:02d}%' if year else f'%-{month:02d}%'))
        if payment_type and payment_type != 'Оклад':
            payments_query = payments_query.filter(Payment.payment_type == payment_type)
        if contract_id is not None:
            payments_query = payments_query.filter(Payment.contract_id == contract_id)
        if employee_id is not None:
            payments_query = payments_query.filter(Payment.employee_id == employee_id)
        if is_paid is not None:
            payments_query = payments_query.filter(Payment.is_paid == is_paid)

        payments = payments_query.all()

        # Batch-load all related entities to avoid N+1 queries
        employee_ids = list(set(p.employee_id for p in payments if p.employee_id))
        contract_ids = list(set(p.contract_id for p in payments if p.contract_id))
        crm_card_ids = list(set(p.crm_card_id for p in payments if p.crm_card_id))
        supervision_card_ids = list(set(p.supervision_card_id for p in payments if p.supervision_card_id))

        employees_map = {e.id: e for e in db.query(Employee).filter(Employee.id.in_(employee_ids)).all()} if employee_ids else {}
        contracts_map = {c.id: c for c in db.query(Contract).filter(Contract.id.in_(contract_ids)).all()} if contract_ids else {}
        crm_cards_map = {c.id: c for c in db.query(CRMCard).filter(CRMCard.id.in_(crm_card_ids)).all()} if crm_card_ids else {}
        supervision_cards_map = {c.id: c for c in db.query(SupervisionCard).filter(SupervisionCard.id.in_(supervision_card_ids)).all()} if supervision_card_ids else {}

        # Also load contracts referenced by CRM cards and supervision cards
        crm_contract_ids = list(set(c.contract_id for c in crm_cards_map.values() if c.contract_id))
        sup_contract_ids = list(set(c.contract_id for c in supervision_cards_map.values() if c.contract_id))
        extra_contract_ids = [cid for cid in crm_contract_ids + sup_contract_ids if cid not in contracts_map]
        if extra_contract_ids:
            extra_contracts = {c.id: c for c in db.query(Contract).filter(Contract.id.in_(extra_contract_ids)).all()}
            contracts_map.update(extra_contracts)

        for p in payments:
            employee = employees_map.get(p.employee_id)

            # Получаем данные контракта через CRM карточку или напрямую
            contract = None
            if p.crm_card_id:
                crm_card = crm_cards_map.get(p.crm_card_id)
                if crm_card:
                    contract = contracts_map.get(crm_card.contract_id)
            elif p.supervision_card_id:
                supervision_card = supervision_cards_map.get(p.supervision_card_id)
                if supervision_card:
                    contract = contracts_map.get(supervision_card.contract_id)
            elif p.contract_id:
                contract = contracts_map.get(p.contract_id)

            # Определяем source
            if p.crm_card_id:
                source = 'CRM'
            elif p.supervision_card_id:
                source = 'CRM Надзор'
            else:
                source = 'CRM'  # Если нет ни crm_card_id ни supervision_card_id, но есть contract_id

            # ИСПРАВЛЕНИЕ 06.02.2026: Для платежей надзора project_type = 'Авторский надзор'
            if p.supervision_card_id:
                payment_project_type = 'Авторский надзор'
            else:
                payment_project_type = contract.project_type if contract else None

            result.append({
                'id': p.id,
                'contract_id': p.contract_id,
                'crm_card_id': p.crm_card_id,
                'supervision_card_id': p.supervision_card_id,
                'employee_id': p.employee_id,
                'employee_name': employee.full_name if employee else 'Неизвестный',
                'position': employee.position if employee else '',
                'role': p.role,
                'stage_name': p.stage_name,
                'calculated_amount': float(p.calculated_amount) if p.calculated_amount else 0,
                'final_amount': float(p.final_amount) if p.final_amount else 0,
                'amount': float(p.final_amount) if p.final_amount else 0,
                'payment_type': p.payment_type,
                'payment_subtype': p.payment_type,  # Тип выплаты: Аванс, Доплата, Полная оплата
                'source': source,
                'report_month': p.report_month,
                'payment_status': p.payment_status if p.payment_status else 'pending',
                'is_paid': p.is_paid,
                'created_at': p.created_at.isoformat() if p.created_at else None,
                # Данные из контракта
                'project_type': payment_project_type,
                'agent_type': contract.agent_type if contract else None,
                'address': contract.address if contract else None,
                'contract_number': contract.contract_number if contract else None,
                'area': float(contract.area) if contract and contract.area else None,
                'city': contract.city if contract else None,
                'reassigned': p.reassigned if hasattr(p, 'reassigned') else False,
            })

        # 2. Оклады из таблицы salaries (если не фильтруем по payment_type отличному от Оклад)
        if not payment_type or payment_type == 'Оклад':
            salaries_query = db.query(Salary)

            if year:
                if include_null_month:
                    # ИСПРАВЛЕНИЕ 06.02.2026: Включаем оклады с NULL report_month
                    salaries_query = salaries_query.filter(
                        or_(
                            Salary.report_month.like(f'{year}%'),
                            Salary.report_month.is_(None)
                        )
                    )
                else:
                    salaries_query = salaries_query.filter(Salary.report_month.like(f'{year}%'))
            if month:
                salaries_query = salaries_query.filter(Salary.report_month.like(f'{year}-{month:02d}%' if year else f'%-{month:02d}%'))
            if employee_id is not None:
                salaries_query = salaries_query.filter(Salary.employee_id == employee_id)
            if contract_id is not None:
                salaries_query = salaries_query.filter(Salary.contract_id == contract_id)
            if is_paid is not None:
                # В таблице salaries статус хранится как payment_status ('paid'/'pending')
                if is_paid:
                    salaries_query = salaries_query.filter(Salary.payment_status == 'paid')
                else:
                    salaries_query = salaries_query.filter(Salary.payment_status != 'paid')

            salaries = salaries_query.all()

            # Batch-load employees and contracts for salaries to avoid N+1 queries
            sal_employee_ids = list(set(s.employee_id for s in salaries if s.employee_id))
            sal_contract_ids = list(set(s.contract_id for s in salaries if s.contract_id))
            sal_employees_map = {e.id: e for e in db.query(Employee).filter(Employee.id.in_(sal_employee_ids)).all()} if sal_employee_ids else {}
            # Reuse already loaded contracts and load any missing ones
            missing_contract_ids = [cid for cid in sal_contract_ids if cid not in contracts_map]
            if missing_contract_ids:
                extra = {c.id: c for c in db.query(Contract).filter(Contract.id.in_(missing_contract_ids)).all()}
                contracts_map.update(extra)

            for s in salaries:
                employee = sal_employees_map.get(s.employee_id)
                contract = contracts_map.get(s.contract_id) if s.contract_id else None

                result.append({
                    'id': s.id,
                    'contract_id': s.contract_id,
                    'crm_card_id': None,
                    'supervision_card_id': None,
                    'employee_id': s.employee_id,
                    'employee_name': employee.full_name if employee else 'Неизвестный',
                    'position': employee.position if employee else '',
                    'role': s.payment_type,  # payment_type в salaries = роль
                    'stage_name': s.stage_name,
                    'calculated_amount': float(s.amount) if s.amount else 0,
                    'final_amount': float(s.amount) if s.amount else 0,
                    'amount': float(s.amount) if s.amount else 0,
                    'payment_type': s.payment_type,
                    'payment_subtype': 'Оклад',  # Всегда Оклад для salaries
                    'source': 'Оклад',
                    'report_month': s.report_month,
                    'payment_status': s.payment_status if s.payment_status else 'pending',
                    'is_paid': s.payment_status == 'paid' if s.payment_status else False,
                    'created_at': s.created_at.isoformat() if s.created_at else None,
                    # Данные из контракта
                    'project_type': s.project_type if s.project_type else (contract.project_type if contract else None),
                    'agent_type': contract.agent_type if contract else None,
                    'address': contract.address if contract else None,
                    'contract_number': contract.contract_number if contract else None,
                    'area': float(contract.area) if contract and contract.area else None,
                    'city': contract.city if contract else None,
                    'reassigned': False,  # Оклады не переназначаются
                    'comments': s.comments,  # Комментарий из оклада
                })

        return result

    except Exception as e:
        logger.exception(f"Ошибка при получении платежей: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# ИСПРАВЛЕНИЕ 30.01.2026: Endpoint перемещен ПЕРЕД /{payment_id}
# чтобы FastAPI не перехватывал 'calculate' как payment_id
@router.get("/calculate")
async def calculate_payment_amount(
    contract_id: int,
    employee_id: int,
    role: str,
    stage_name: Optional[str] = None,
    supervision_card_id: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Рассчитать сумму оплаты на основе тарифов - ПОЛНАЯ ЛОГИКА"""
    try:
        # Получаем договор
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            return {'amount': 0, 'error': 'Contract not found'}

        area = float(contract.area) if contract.area else 0
        project_type = contract.project_type
        city = contract.city

        # ========== АВТОРСКИЙ НАДЗОР ==========
        if supervision_card_id:
            rate = db.query(Rate).filter(
                Rate.project_type == 'Авторский надзор',
                Rate.role == role
            )
            if stage_name:
                rate = rate.filter(or_(Rate.stage_name == stage_name, Rate.stage_name.is_(None)))
            rate = rate.order_by(
                # Приоритет: сначала с конкретной стадией, потом без стадии
                Rate.stage_name.desc().nullslast()
            ).first()

            if rate and rate.rate_per_m2:
                amount = area * float(rate.rate_per_m2)
                return {'amount': amount, 'rate_per_m2': float(rate.rate_per_m2)}
            return {'amount': 0}

        # ========== ЗАМЕРЩИК ==========
        if role == 'Замерщик':
            rate = db.query(Rate).filter(
                Rate.role == 'Замерщик',
                Rate.city == city
            ).first()
            if rate and rate.surveyor_price:
                return {'amount': float(rate.surveyor_price), 'surveyor_price': float(rate.surveyor_price)}
            return {'amount': 0}

        # ========== ИНДИВИДУАЛЬНЫЙ ==========
        if project_type == 'Индивидуальный':
            logger.debug(f"CALC Индивидуальный проект: role={role}, area={area}, stage_name={stage_name}")
            query = db.query(Rate).filter(
                Rate.project_type == 'Индивидуальный',
                Rate.role == role
            )
            if stage_name:
                # Сначала ищем с конкретной стадией
                rate = query.filter(Rate.stage_name == stage_name).first()
                logger.debug(f"CALC Поиск с stage_name='{stage_name}': rate={rate}")
                # Если не найден - ищем без стадии
                if not rate:
                    rate = query.filter(Rate.stage_name.is_(None)).first()
                    logger.debug(f"CALC Поиск с stage_name IS NULL: rate={rate}")
            else:
                rate = query.filter(Rate.stage_name.is_(None)).first()
                logger.debug(f"CALC Поиск без stage_name (IS NULL): rate={rate}")

            if rate and rate.rate_per_m2:
                amount = area * float(rate.rate_per_m2)
                logger.debug(f"CALC Найден тариф: rate_per_m2={rate.rate_per_m2}, amount={amount}")
                return {'amount': amount, 'rate_per_m2': float(rate.rate_per_m2)}
            logger.debug("CALC Тариф НЕ найден или rate_per_m2=0, возвращаем 0")
            return {'amount': 0}

        # ========== ШАБЛОННЫЙ ==========
        if project_type == 'Шаблонный':
            rate = db.query(Rate).filter(
                Rate.project_type == 'Шаблонный',
                Rate.role == role,
                Rate.area_from <= area,
                or_(Rate.area_to >= area, Rate.area_to.is_(None))
            ).order_by(Rate.area_from.asc()).first()

            if rate and rate.fixed_price:
                return {'amount': float(rate.fixed_price), 'fixed_price': float(rate.fixed_price)}
            return {'amount': 0}

        # ========== АВТОРСКИЙ НАДЗОР (по типу проекта) ==========
        if project_type == 'Авторский надзор':
            query = db.query(Rate).filter(
                Rate.project_type == 'Авторский надзор',
                Rate.role == role
            )
            if stage_name:
                query = query.filter(or_(Rate.stage_name == stage_name, Rate.stage_name.is_(None)))
            rate = query.first()

            if rate and rate.rate_per_m2:
                amount = area * float(rate.rate_per_m2)
                return {'amount': amount, 'rate_per_m2': float(rate.rate_per_m2)}
            return {'amount': 0}

        return {'amount': 0}

    except Exception as e:
        logger.error(f"Error calculating payment: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'amount': 0, 'error': str(e)}


@router.get("/summary")
async def get_payments_summary(
    year: int,
    month: Optional[int] = None,
    quarter: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить сводку по платежам"""
    try:
        from sqlalchemy import extract

        query = db.query(Payment).filter(extract('year', Payment.created_at) == year)

        if month:
            query = query.filter(extract('month', Payment.created_at) == month)
        if quarter:
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            query = query.filter(extract('month', Payment.created_at).between(start_month, end_month))

        payments = query.all()

        # Суммы по статусам
        paid_amount = sum(p.final_amount or 0 for p in payments if p.is_paid)
        pending_amount = sum(p.final_amount or 0 for p in payments if not p.is_paid)

        # По ролям
        by_role = {}
        for p in payments:
            role = p.role or 'Не указано'
            if role not in by_role:
                by_role[role] = {'paid': 0, 'pending': 0, 'count': 0}
            by_role[role]['count'] += 1
            if p.is_paid:
                by_role[role]['paid'] += p.final_amount or 0
            else:
                by_role[role]['pending'] += p.final_amount or 0

        return {
            'year': year,
            'month': month,
            'quarter': quarter,
            'total_paid': paid_amount,
            'total_pending': pending_amount,
            'total': paid_amount + pending_amount,
            'by_role': by_role,
            'payments_count': len(payments)
        }

    except Exception as e:
        logger.exception(f"Ошибка при получении сводки платежей: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/by-type")
async def get_payments_by_type(
    payment_type: str,
    project_type_filter: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить платежи по типу выплаты и фильтру типа проекта

    Сигнатура совпадает с database/db_manager.py:_get_payments_by_type_from_db()

    Args:
        payment_type: Тип выплаты ('Индивидуальные проекты', 'Шаблонные проекты', 'Оклады', 'Авторский надзор')
        project_type_filter: Фильтр типа проекта ('Индивидуальный', 'Шаблонный', 'Авторский надзор', None)

    Returns:
        Список платежей с полями:
            - id, contract_id, employee_id, employee_name, position
            - role, stage_name, final_amount, payment_type
            - report_month, payment_status
            - contract_number, address, area, city, agent_type
            - source ('CRM' или 'Оклад')
            - card_stage (для CRM)
    """
    try:
        result = []

        # Оклады - только из таблицы salaries
        if payment_type == 'Оклады':
            salaries = db.query(Salary).all()
            for s in salaries:
                employee = db.query(Employee).filter(Employee.id == s.employee_id).first()
                contract = db.query(Contract).filter(Contract.id == s.contract_id).first() if s.contract_id else None

                result.append({
                    'id': s.id,
                    'contract_id': s.contract_id,
                    'employee_id': s.employee_id,
                    'employee_name': employee.full_name if employee else 'Неизвестный',
                    'position': employee.position if employee else '',
                    'role': s.payment_type,
                    'stage_name': s.stage_name,
                    'final_amount': float(s.amount) if s.amount else 0,
                    'amount': float(s.amount) if s.amount else 0,
                    'payment_type': s.payment_type,
                    'report_month': s.report_month,
                    'payment_status': s.payment_status,
                    'project_type': s.project_type,
                    'contract_number': contract.contract_number if contract else None,
                    'address': contract.address if contract else None,
                    'area': float(contract.area) if contract and contract.area else None,
                    'city': contract.city if contract else None,
                    'agent_type': contract.agent_type if contract else None,
                    'source': 'Оклад',
                    'card_stage': None,
                    'comments': s.comments  # Добавлено поле комментария
                })

        # Авторский надзор - из payments с supervision_card + salaries
        elif project_type_filter == 'Авторский надзор':
            # Платежи из CRM надзора - ИСПРАВЛЕНО 06.02.2026
            payments = db.query(Payment).filter(
                Payment.supervision_card_id.isnot(None)
            ).all()

            for p in payments:
                employee = db.query(Employee).filter(Employee.id == p.employee_id).first()
                supervision_card = db.query(SupervisionCard).filter(SupervisionCard.id == p.supervision_card_id).first()
                contract = db.query(Contract).filter(Contract.id == supervision_card.contract_id).first() if supervision_card else None

                result.append({
                    'id': p.id,
                    'contract_id': p.contract_id,
                    'crm_card_id': p.crm_card_id,
                    'supervision_card_id': p.supervision_card_id,
                    'employee_id': p.employee_id,
                    'employee_name': employee.full_name if employee else 'Неизвестный',
                    'position': employee.position if employee else '',
                    'role': p.role,
                    'stage_name': p.stage_name,
                    'calculated_amount': float(p.calculated_amount) if p.calculated_amount else 0,
                    'final_amount': float(p.final_amount) if p.final_amount else 0,
                    'amount': float(p.final_amount) if p.final_amount else 0,
                    'payment_type': p.payment_type,
                    'payment_subtype': p.payment_type,
                    'report_month': p.report_month,
                    'payment_status': p.payment_status,
                    'contract_number': contract.contract_number if contract else None,
                    'address': contract.address if contract else None,
                    'area': float(contract.area) if contract and contract.area else None,
                    'city': contract.city if contract else None,
                    'agent_type': contract.agent_type if contract else None,
                    'project_type': contract.project_type if contract else 'Авторский надзор',
                    'source': 'CRM Надзор',
                    'card_stage': supervision_card.column_name if supervision_card else None,
                    'reassigned': p.reassigned if hasattr(p, 'reassigned') else False
                })

            # Добавляем оклады с типом "Авторский надзор"
            salaries = db.query(Salary).filter(Salary.project_type == project_type_filter).all()
            for s in salaries:
                employee = db.query(Employee).filter(Employee.id == s.employee_id).first()
                contract = db.query(Contract).filter(Contract.id == s.contract_id).first() if s.contract_id else None

                result.append({
                    'id': s.id,
                    'contract_id': s.contract_id,
                    'employee_id': s.employee_id,
                    'employee_name': employee.full_name if employee else 'Неизвестный',
                    'position': employee.position if employee else '',
                    'role': s.payment_type,
                    'stage_name': s.stage_name,
                    'final_amount': float(s.amount) if s.amount else 0,
                    'amount': float(s.amount) if s.amount else 0,
                    'payment_type': 'Оклад',
                    'report_month': s.report_month,
                    'payment_status': s.payment_status,
                    'contract_number': contract.contract_number if contract else None,
                    'address': contract.address if contract else None,
                    'area': float(contract.area) if contract and contract.area else None,
                    'city': contract.city if contract else None,
                    'agent_type': contract.agent_type if contract else None,
                    'source': 'Оклад',
                    'card_stage': None,
                    'comments': s.comments  # Добавлено поле комментария
                })

        # Индивидуальные и шаблонные проекты - из payments с crm_card + salaries
        elif project_type_filter:
            # Платежи из CRM
            payments_query = db.query(Payment).join(
                CRMCard, Payment.crm_card_id == CRMCard.id
            ).join(
                Contract, CRMCard.contract_id == Contract.id
            ).filter(
                Contract.project_type == project_type_filter
            )

            for p in payments_query.all():
                employee = db.query(Employee).filter(Employee.id == p.employee_id).first()
                crm_card = db.query(CRMCard).filter(CRMCard.id == p.crm_card_id).first()
                contract = db.query(Contract).filter(Contract.id == crm_card.contract_id).first() if crm_card else None

                result.append({
                    'id': p.id,
                    'contract_id': p.contract_id,
                    'employee_id': p.employee_id,
                    'employee_name': employee.full_name if employee else 'Неизвестный',
                    'position': employee.position if employee else '',
                    'role': p.role,
                    'stage_name': p.stage_name,
                    'final_amount': float(p.final_amount) if p.final_amount else 0,
                    'amount': float(p.final_amount) if p.final_amount else 0,
                    'payment_type': p.payment_type,
                    'report_month': p.report_month,
                    'payment_status': p.payment_status,
                    'contract_number': contract.contract_number if contract else None,
                    'address': contract.address if contract else None,
                    'area': float(contract.area) if contract and contract.area else None,
                    'city': contract.city if contract else None,
                    'agent_type': contract.agent_type if contract else None,
                    'source': 'CRM',
                    'card_stage': crm_card.column_name if crm_card else None,
                    'reassigned': p.reassigned if hasattr(p, 'reassigned') else False,
                    'old_employee_id': p.old_employee_id if hasattr(p, 'old_employee_id') else None
                })

            # Добавляем оклады с этим типом проекта
            salaries = db.query(Salary).filter(Salary.project_type == project_type_filter).all()
            for s in salaries:
                employee = db.query(Employee).filter(Employee.id == s.employee_id).first()
                contract = db.query(Contract).filter(Contract.id == s.contract_id).first() if s.contract_id else None

                result.append({
                    'id': s.id,
                    'contract_id': s.contract_id,
                    'employee_id': s.employee_id,
                    'employee_name': employee.full_name if employee else 'Неизвестный',
                    'position': employee.position if employee else '',
                    'role': s.payment_type,
                    'stage_name': s.stage_name,
                    'final_amount': float(s.amount) if s.amount else 0,
                    'amount': float(s.amount) if s.amount else 0,
                    'payment_type': 'Оклад',
                    'report_month': s.report_month,
                    'payment_status': s.payment_status,
                    'contract_number': contract.contract_number if contract else None,
                    'address': contract.address if contract else None,
                    'area': float(contract.area) if contract and contract.area else None,
                    'city': contract.city if contract else None,
                    'agent_type': contract.agent_type if contract else None,
                    'source': 'Оклад',
                    'card_stage': None,
                    'comments': s.comments  # Добавлено поле комментария
                })

        # Сортируем по id в обратном порядке
        result.sort(key=lambda x: x['id'], reverse=True)
        return result

    except Exception as e:
        logger.exception(f"Ошибка при получении платежей по типу: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/all-optimized")
async def get_all_payments_optimized(
    year: Optional[int] = None,
    month: Optional[int] = None,
    quarter: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Оптимизированная загрузка всех выплат - один запрос вместо 132"""
    try:
        # Базовый запрос для payments
        query = db.query(Payment).join(Employee, Payment.employee_id == Employee.id)

        # Фильтрация по периоду
        if year and month:
            report_month_str = f"{year}-{month:02d}"
            query = query.filter(Payment.report_month == report_month_str)
        elif year and quarter:
            months = [(quarter - 1) * 3 + i for i in range(1, 4)]
            month_strs = [f"{year}-{m:02d}" for m in months]
            query = query.filter(Payment.report_month.in_(month_strs))
        elif year:
            query = query.filter(Payment.report_month.like(f"{year}-%"))

        payments = query.all()

        # Batch-load all contracts to avoid N+1 queries
        contract_ids = list(set(p.contract_id for p in payments if p.contract_id))
        contracts_list = db.query(Contract).filter(Contract.id.in_(contract_ids)).all() if contract_ids else []
        contracts_map = {c.id: c for c in contracts_list}

        result = []
        for p in payments:
            contract = contracts_map.get(p.contract_id)

            result.append({
                'id': p.id,
                'contract_id': p.contract_id,
                'employee_id': p.employee_id,
                'employee_name': p.employee.full_name if p.employee else '',
                'position': p.employee.position if p.employee else '',
                'role': p.role,
                'stage_name': p.stage_name,
                'calculated_amount': float(p.calculated_amount) if p.calculated_amount else 0,
                'final_amount': float(p.final_amount) if p.final_amount else 0,
                'amount': float(p.final_amount) if p.final_amount else 0,
                'payment_type': p.payment_type,
                'payment_status': p.payment_status,
                'report_month': p.report_month or '',
                'source': 'CRM',
                'project_type': contract.project_type if contract else '',
                'address': contract.address if contract else '',
                'agent_type': contract.agent_type if contract else ''
            })

        return result

    except Exception as e:
        logger.exception(f"Ошибка при получении оптимизированных платежей: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/recalculate")
async def recalculate_payments(
    contract_id: Optional[int] = None,
    role: Optional[str] = None,
    current_user: Employee = Depends(require_permission("payments.update")),
    db: Session = Depends(get_db)
):
    """Пересчет выплат по текущим тарифам"""
    try:
        # Получаем выплаты для пересчета
        query = db.query(Payment)

        if contract_id:
            query = query.filter(Payment.contract_id == contract_id)
        if role:
            query = query.filter(Payment.role == role)

        payments = query.all()
        updated = 0
        errors = []

        for payment in payments:
            try:
                # Получаем договор
                contract = db.query(Contract).filter(Contract.id == payment.contract_id).first()
                if not contract:
                    continue

                area = float(contract.area) if contract.area else 0
                project_type = contract.project_type
                city = contract.city

                new_amount = 0

                # Замерщик
                if payment.role == 'Замерщик':
                    rate = db.query(Rate).filter(
                        Rate.role == 'Замерщик',
                        Rate.city == city
                    ).first()
                    if rate and rate.surveyor_price:
                        new_amount = float(rate.surveyor_price)

                # Индивидуальный
                elif project_type == 'Индивидуальный':
                    query_rate = db.query(Rate).filter(
                        Rate.project_type == 'Индивидуальный',
                        Rate.role == payment.role
                    )
                    if payment.stage_name:
                        rate = query_rate.filter(Rate.stage_name == payment.stage_name).first()
                        if not rate:
                            rate = query_rate.filter(Rate.stage_name.is_(None)).first()
                    else:
                        rate = query_rate.filter(Rate.stage_name.is_(None)).first()

                    if rate and rate.rate_per_m2:
                        new_amount = area * float(rate.rate_per_m2)

                # Шаблонный
                elif project_type == 'Шаблонный':
                    rate = db.query(Rate).filter(
                        Rate.project_type == 'Шаблонный',
                        Rate.role == payment.role,
                        Rate.area_from <= area,
                        or_(Rate.area_to >= area, Rate.area_to.is_(None))
                    ).order_by(Rate.area_from.asc()).first()

                    if rate and rate.fixed_price:
                        new_amount = float(rate.fixed_price)

                # Авторский надзор
                elif project_type == 'Авторский надзор' or payment.supervision_card_id:
                    rate = db.query(Rate).filter(
                        Rate.project_type == 'Авторский надзор',
                        Rate.role == payment.role
                    ).first()

                    if rate and rate.rate_per_m2:
                        new_amount = area * float(rate.rate_per_m2)

                # Обновляем если сумма изменилась
                if new_amount != payment.calculated_amount:
                    old_amount = payment.calculated_amount
                    payment.calculated_amount = new_amount
                    payment.final_amount = new_amount
                    updated += 1
                    logger.debug(f"RECALC Payment ID={payment.id}: {old_amount} -> {new_amount}")

            except Exception as e:
                errors.append({'payment_id': payment.id, 'error': str(e)})

        db.commit()

        return {
            'status': 'success',
            'updated': updated,
            'total': len(payments),
            'errors': errors
        }

    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при пересчете платежей: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    current_user: Employee = Depends(require_permission("payments.create")),
    db: Session = Depends(get_db)
):
    """Создать платеж"""
    # Проверяем существование договора
    if payment_data.contract_id:
        contract = db.query(Contract).filter(Contract.id == payment_data.contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Договор не найден")

    # Проверяем существование сотрудника
    if payment_data.employee_id:
        employee = db.query(Employee).filter(Employee.id == payment_data.employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")

    # Защита от дублей: проверяем нет ли уже платежа с теми же параметрами
    if payment_data.contract_id and payment_data.employee_id and payment_data.stage_name:
        duplicate_query = db.query(Payment).filter(
            Payment.contract_id == payment_data.contract_id,
            Payment.employee_id == payment_data.employee_id,
            Payment.stage_name == payment_data.stage_name,
            Payment.role == payment_data.role
        )
        if payment_data.crm_card_id:
            duplicate_query = duplicate_query.filter(Payment.crm_card_id == payment_data.crm_card_id)
        if payment_data.supervision_card_id:
            duplicate_query = duplicate_query.filter(Payment.supervision_card_id == payment_data.supervision_card_id)
        existing = duplicate_query.first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Платёж уже существует (id={existing.id}). Используйте PUT для обновления."
            )

    try:
        # Получаем данные и устанавливаем значения по умолчанию для NOT NULL полей
        data = payment_data.model_dump(exclude_unset=True)

        # Устанавливаем значения по умолчанию для NOT NULL полей
        if data.get('calculated_amount') is None:
            data['calculated_amount'] = 0.0
        if data.get('final_amount') is None:
            data['final_amount'] = data.get('calculated_amount', 0.0)
        # payment_status остаётся NULL - платёж ещё не оплачен
        # Статус 'paid' устанавливается кнопкой "Оплачено" в UI

        payment = Payment(**data)
        db.add(payment)
        db.commit()
        db.refresh(payment)

        log = ActivityLog(
            employee_id=current_user.id,
            action_type="create",
            entity_type="payment",
            entity_id=payment.id
        )
        db.add(log)
        db.commit()

        return payment

    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при создании платежа: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/contract/{contract_id}")
async def get_payments_for_contract(
    contract_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить платежи по договору"""
    # Получаем статус договора для определения отчетного месяца
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    contract_status = contract.status if contract else ''

    payments = db.query(Payment).filter(Payment.contract_id == contract_id).all()

    # Добавляем имя сотрудника к каждому платежу
    result = []
    for payment in payments:
        payment_dict = {
            'id': payment.id,
            'contract_id': payment.contract_id,
            'crm_card_id': payment.crm_card_id,
            'supervision_card_id': payment.supervision_card_id,
            'employee_id': payment.employee_id,
            'role': payment.role,
            'stage_name': payment.stage_name,
            'calculated_amount': float(payment.calculated_amount) if payment.calculated_amount else 0,
            'manual_amount': float(payment.manual_amount) if payment.manual_amount else None,
            'final_amount': float(payment.final_amount) if payment.final_amount else 0,
            'is_manual': payment.is_manual,
            'payment_type': payment.payment_type,
            'report_month': payment.report_month,
            'payment_status': payment.payment_status if payment.payment_status else 'pending',  # ИСПРАВЛЕНИЕ: Статус по умолчанию
            'is_paid': payment.is_paid,
            'paid_date': payment.paid_date.isoformat() if payment.paid_date else None,
            'paid_by': payment.paid_by,
            'reassigned': payment.reassigned if payment.reassigned else False,
            'old_employee_id': payment.old_employee_id,
            'created_at': payment.created_at.isoformat() if payment.created_at else None,
            'updated_at': payment.updated_at.isoformat() if payment.updated_at else None,
        }

        # Получаем имя сотрудника
        employee = db.query(Employee).filter(Employee.id == payment.employee_id).first()
        payment_dict['employee_name'] = employee.full_name if employee else 'Неизвестный'
        payment_dict['position'] = employee.position if employee else ''  # ИСПРАВЛЕНИЕ: Добавлена должность

        # ИСПРАВЛЕНИЕ: Добавлены поля source и amount для совместимости
        payment_dict['source'] = 'CRM' if payment.crm_card_id else 'Оклад'
        payment_dict['amount'] = payment_dict['final_amount']  # Алиас

        # ИСПРАВЛЕНИЕ 25.01.2026: Добавлен contract_status для отображения "В работе" вместо "Не установлен"
        payment_dict['contract_status'] = contract_status

        result.append(payment_dict)

    return result


@router.patch("/contract/{contract_id}/report-month")
async def set_payments_report_month(
    contract_id: int,
    data: dict,
    current_user: Employee = Depends(require_permission("payments.update")),
    db: Session = Depends(get_db)
):
    """Установить отчетный месяц для всех платежей договора без месяца"""
    report_month = data.get('report_month')
    if not report_month:
        raise HTTPException(status_code=400, detail="report_month обязателен")

    # Обновляем все платежи без отчетного месяца
    result = db.query(Payment).filter(
        Payment.contract_id == contract_id,
        or_(Payment.report_month == None, Payment.report_month == '')
    ).update(
        {'report_month': report_month},
        synchronize_session='fetch'
    )

    db.commit()

    return {"status": "success", "updated_count": result}


@router.get("/supervision/{contract_id}")
async def get_payments_for_supervision(
    contract_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить платежи для надзора - ИСПРАВЛЕНО 06.02.2026"""
    # ИСПРАВЛЕНИЕ: Фильтруем по supervision_card_id через JOIN с SupervisionCard
    # Платежи надзора имеют payment_type='Полная оплата' или другой тип
    payments = db.query(Payment).join(
        SupervisionCard, Payment.supervision_card_id == SupervisionCard.id
    ).filter(
        SupervisionCard.contract_id == contract_id
    ).all()

    result = []
    for payment in payments:
        employee = db.query(Employee).filter(Employee.id == payment.employee_id).first()
        result.append({
            'id': payment.id,
            'contract_id': payment.contract_id,
            'supervision_card_id': payment.supervision_card_id,
            'employee_id': payment.employee_id,
            'employee_name': employee.full_name if employee else 'Неизвестный',
            'role': payment.role,
            'stage_name': payment.stage_name,
            'calculated_amount': float(payment.calculated_amount) if payment.calculated_amount else 0,
            'manual_amount': float(payment.manual_amount) if payment.manual_amount else None,
            'final_amount': float(payment.final_amount) if payment.final_amount else 0,
            'is_manual': payment.is_manual,
            'payment_type': payment.payment_type,
            'report_month': payment.report_month,
            'payment_status': payment.payment_status,
            'is_paid': payment.is_paid,
            'reassigned': payment.reassigned if hasattr(payment, 'reassigned') else False,
            'old_employee_id': payment.old_employee_id if hasattr(payment, 'old_employee_id') else None,
        })

    return result


@router.get("/by-supervision-card/{supervision_card_id}")
async def get_payments_by_supervision_card(
    supervision_card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ДОБАВЛЕНО 30.01.2026: Получить платежи по ID карточки надзора"""
    payments = db.query(Payment).filter(
        Payment.supervision_card_id == supervision_card_id
    ).all()

    result = []
    for payment in payments:
        employee = db.query(Employee).filter(Employee.id == payment.employee_id).first()
        result.append({
            'id': payment.id,
            'contract_id': payment.contract_id,
            'supervision_card_id': payment.supervision_card_id,
            'employee_id': payment.employee_id,
            'employee_name': employee.full_name if employee else 'Неизвестный',
            'role': payment.role,
            'stage_name': payment.stage_name,
            'calculated_amount': float(payment.calculated_amount) if payment.calculated_amount else 0,
            'manual_amount': float(payment.manual_amount) if payment.manual_amount else None,
            'final_amount': float(payment.final_amount) if payment.final_amount else 0,
            'is_manual': payment.is_manual,
            'payment_type': payment.payment_type,
            'report_month': payment.report_month,
            'payment_status': payment.payment_status,
            'is_paid': payment.is_paid,
            'reassigned': payment.reassigned if hasattr(payment, 'reassigned') else False,
            'old_employee_id': payment.old_employee_id if hasattr(payment, 'old_employee_id') else None,
        })

    return result


@router.get("/crm/{contract_id}")
async def get_payments_for_crm(
    contract_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить выплаты для CRM (не надзор)"""
    payments = db.query(Payment).filter(
        Payment.contract_id == contract_id,
        Payment.supervision_card_id == None
    ).all()

    result = []
    for p in payments:
        employee = db.query(Employee).filter(Employee.id == p.employee_id).first()
        result.append({
            'id': p.id,
            'contract_id': p.contract_id,
            'crm_card_id': p.crm_card_id,
            'employee_id': p.employee_id,
            'employee_name': employee.full_name if employee else 'Неизвестный',
            'position': employee.position if employee else '',
            'role': p.role,
            'stage_name': p.stage_name,
            'calculated_amount': float(p.calculated_amount) if p.calculated_amount else 0,
            'final_amount': float(p.final_amount) if p.final_amount else 0,
            'amount': float(p.final_amount) if p.final_amount else 0,
            'payment_type': p.payment_type,
            'report_month': p.report_month,
            'payment_status': p.payment_status,
            'is_paid': p.is_paid,
            'source': 'CRM'
        })

    return result


# =========================
# ДИНАМИЧЕСКИЕ ENDPOINTS (/{payment_id}) — ВСЕГДА ПОСЛЕДНИМИ
# =========================


# ВАЖНО: Этот endpoint должен быть ПОСЛЕ всех статических /...
@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment_by_id(
    payment_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить платеж по ID"""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Платеж не найден")
    # Добавляем employee_name через JOIN
    employee = db.query(Employee).filter(Employee.id == payment.employee_id).first()
    payment.employee_name = employee.full_name if employee else 'Неизвестный'
    return payment


@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    current_user: Employee = Depends(require_permission("payments.update")),
    db: Session = Depends(get_db)
):
    """Обновить платеж"""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Платеж не найден")

    for field, value in payment_data.model_dump(exclude_unset=True).items():
        setattr(payment, field, value)

    payment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(payment)

    return payment


@router.delete("/{payment_id}")
async def delete_payment(
    payment_id: int,
    current_user: Employee = Depends(require_permission("payments.delete")),
    db: Session = Depends(get_db)
):
    """Удалить платеж"""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Платеж не найден")

    log = ActivityLog(
        employee_id=current_user.id,
        action_type="delete",
        entity_type="payment",
        entity_id=payment_id
    )
    db.add(log)

    db.delete(payment)
    db.commit()

    return {"status": "success", "message": "Платеж удален"}


@router.patch("/{payment_id}/manual")
async def update_payment_manual(
    payment_id: int,
    data: PaymentManualUpdateRequest,
    current_user: Employee = Depends(require_permission("payments.update")),
    db: Session = Depends(get_db)
):
    """Обновить платеж вручную"""
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Платеж не найден")

        payment.manual_amount = data.amount
        payment.final_amount = data.amount
        payment.is_manual = True
        payment.report_month = data.report_month
        payment.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(payment)

        return {
            'id': payment.id,
            'manual_amount': float(payment.manual_amount),
            'final_amount': float(payment.final_amount),
            'report_month': payment.report_month
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при обновлении платежа: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/{payment_id}/mark-paid")
async def mark_payment_as_paid(
    payment_id: int,
    employee_id: int = Body(embed=True),
    current_user: Employee = Depends(require_permission("payments.update")),
    db: Session = Depends(get_db)
):
    """Отметить платеж как выплаченный"""
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Платеж не найден")

        payment.is_paid = True
        payment.paid_date = datetime.utcnow()
        payment.paid_by = current_user.id
        payment.payment_status = 'paid'
        payment.updated_at = datetime.utcnow()

        db.commit()

        return {
            'id': payment.id,
            'is_paid': payment.is_paid,
            'paid_date': payment.paid_date.isoformat(),
            'paid_by': payment.paid_by
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при отметке платежа как оплаченного: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

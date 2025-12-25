# -*- coding: utf-8 -*-
"""
API роуты для CRM Supervision - для добавления в server/main.py
Добавить после роутов CRM
"""

# ===================================
# CRM SUPERVISION (Авторский надзор)
# ===================================

@app.get("/api/supervision/cards")
async def get_supervision_cards(
    status: str = "active",  # "active" или "archived"
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить список карточек авторского надзора
    status: "active" - только активные (статус АВТОРСКИЙ НАДЗОР)
            "archived" - архивные (СДАН, РАСТОРГНУТ)
    """
    try:
        if status == "active":
            # Только активные карточки (статус договора = АВТОРСКИЙ НАДЗОР)
            cards = db.query(SupervisionCard).join(
                Contract, SupervisionCard.contract_id == Contract.id
            ).filter(
                Contract.status == 'АВТОРСКИЙ НАДЗОР'
            ).order_by(
                SupervisionCard.id.desc()
            ).all()
        else:
            # Архивные карточки
            cards = db.query(SupervisionCard).join(
                Contract, SupervisionCard.contract_id == Contract.id
            ).filter(
                Contract.status.in_(['СДАН', 'РАСТОРГНУТ'])
            ).order_by(
                SupervisionCard.id.desc()
            ).all()

        # Формируем ответ с дополнительными данными
        result = []
        for card in cards:
            contract = card.contract

            # Получаем имена менеджеров
            senior_manager_name = card.senior_manager.full_name if card.senior_manager else None
            dan_name = card.dan.full_name if card.dan else None

            card_data = {
                'id': card.id,
                'contract_id': card.contract_id,
                'column_name': card.column_name,
                'deadline': str(card.deadline) if card.deadline else None,
                'tags': card.tags,
                'senior_manager_id': card.senior_manager_id,
                'dan_id': card.dan_id,
                'dan_completed': card.dan_completed,
                'is_paused': card.is_paused,
                'pause_reason': card.pause_reason,
                'paused_at': card.paused_at.isoformat() if card.paused_at else None,

                # Имена менеджеров
                'senior_manager_name': senior_manager_name,
                'dan_name': dan_name,

                # Данные договора
                'contract_number': contract.contract_number,
                'address': contract.address,
                'area': contract.area,
                'city': contract.city,
                'agent_type': contract.agent_type,
                'contract_status': contract.status,
                'termination_reason': contract.termination_reason if status == "archived" else None,

                # Метаданные
                'created_at': card.created_at.isoformat() if card.created_at else None,
                'updated_at': card.updated_at.isoformat() if card.updated_at else None,
            }
            result.append(card_data)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения карточек надзора: {str(e)}")


@app.get("/api/supervision/cards/{card_id}")
async def get_supervision_card(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить одну карточку надзора"""
    try:
        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        return {
            'id': card.id,
            'contract_id': card.contract_id,
            'column_name': card.column_name,
            'deadline': str(card.deadline) if card.deadline else None,
            'tags': card.tags,
            'senior_manager_id': card.senior_manager_id,
            'dan_id': card.dan_id,
            'dan_completed': card.dan_completed,
            'is_paused': card.is_paused,
            'pause_reason': card.pause_reason,
            'paused_at': card.paused_at.isoformat() if card.paused_at else None,
            'created_at': card.created_at.isoformat() if card.created_at else None,
            'updated_at': card.updated_at.isoformat() if card.updated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения карточки надзора: {str(e)}")


@app.patch("/api/supervision/cards/{card_id}")
async def update_supervision_card(
    card_id: int,
    updates: SupervisionCardUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить поля карточки надзора"""
    try:
        # Проверка прав
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования карточек надзора")

        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        # Обновляем только переданные поля
        update_data = updates.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(card, field, value)

        db.commit()
        db.refresh(card)

        return {
            'id': card.id,
            'contract_id': card.contract_id,
            'column_name': card.column_name,
            'deadline': str(card.deadline) if card.deadline else None,
            'tags': card.tags,
            'senior_manager_id': card.senior_manager_id,
            'dan_id': card.dan_id,
            'dan_completed': card.dan_completed,
            'is_paused': card.is_paused,
            'pause_reason': card.pause_reason,
            'paused_at': card.paused_at.isoformat() if card.paused_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка обновления карточки надзора: {str(e)}")


@app.patch("/api/supervision/cards/{card_id}/column")
async def move_supervision_card_to_column(
    card_id: int,
    move_request: SupervisionColumnMoveRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Переместить карточку надзора в другую колонку"""
    try:
        # Проверка прав
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        old_column = card.column_name
        card.column_name = move_request.column_name

        db.commit()
        db.refresh(card)

        return {
            'id': card.id,
            'contract_id': card.contract_id,
            'column_name': card.column_name,
            'old_column_name': old_column,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка перемещения карточки надзора: {str(e)}")


@app.post("/api/supervision/cards/{card_id}/pause")
async def pause_supervision_card(
    card_id: int,
    pause_request: SupervisionPauseRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Приостановить карточку надзора"""
    try:
        # Проверка прав
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        card.is_paused = True
        card.pause_reason = pause_request.pause_reason
        card.paused_at = datetime.utcnow()

        db.commit()
        db.refresh(card)

        return {
            'id': card.id,
            'is_paused': card.is_paused,
            'pause_reason': card.pause_reason,
            'paused_at': card.paused_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка приостановки карточки: {str(e)}")


@app.post("/api/supervision/cards/{card_id}/resume")
async def resume_supervision_card(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Возобновить карточку надзора"""
    try:
        # Проверка прав
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        card.is_paused = False
        card.pause_reason = None
        card.paused_at = None

        db.commit()
        db.refresh(card)

        return {
            'id': card.id,
            'is_paused': card.is_paused,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка возобновления карточки: {str(e)}")

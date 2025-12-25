# -*- coding: utf-8 -*-
"""
API роуты для CRM карточек - для добавления в server/main.py
Добавить после роутов для contracts
"""

# ===================================
# CRM КАРТОЧКИ
# ===================================

@app.get("/api/crm/cards")
async def get_crm_cards(
    project_type: str,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить список CRM карточек по типу проекта
    Только активные карточки (исключая СДАН, РАСТОРГНУТ, АВТОРСКИЙ НАДЗОР)
    """
    try:
        # Основной запрос с joins
        cards = db.query(CRMCard).join(
            Contract, CRMCard.contract_id == Contract.id
        ).filter(
            Contract.project_type == project_type,
            or_(
                Contract.status == None,
                Contract.status == '',
                ~Contract.status.in_(['СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР'])
            )
        ).order_by(
            CRMCard.order_position,
            CRMCard.id
        ).all()

        # Формируем ответ с дополнительными данными
        result = []
        for card in cards:
            contract = card.contract

            # Получаем имена менеджеров
            senior_manager_name = card.senior_manager.full_name if card.senior_manager else None
            sdp_name = card.sdp.full_name if card.sdp else None
            gap_name = card.gap.full_name if card.gap else None
            manager_name = card.manager.full_name if card.manager else None
            surveyor_name = card.surveyor.full_name if card.surveyor else None

            # Получаем дизайнера и чертёжника из stage_executors
            designer_executor = db.query(StageExecutor).filter(
                StageExecutor.crm_card_id == card.id,
                StageExecutor.stage_name.ilike('%концепция%')
            ).order_by(StageExecutor.id.desc()).first()

            draftsman_executor = db.query(StageExecutor).filter(
                StageExecutor.crm_card_id == card.id,
                or_(
                    StageExecutor.stage_name.ilike('%чертежи%'),
                    StageExecutor.stage_name.ilike('%планировочные%')
                )
            ).order_by(StageExecutor.id.desc()).first()

            card_data = {
                'id': card.id,
                'contract_id': card.contract_id,
                'column_name': card.column_name,
                'deadline': str(card.deadline) if card.deadline else None,
                'tags': card.tags,
                'is_approved': card.is_approved,
                'approval_deadline': str(card.approval_deadline) if card.approval_deadline else None,
                'approval_stages': card.approval_stages,
                'project_data_link': card.project_data_link,
                'tech_task_file': card.tech_task_file,
                'tech_task_date': str(card.tech_task_date) if card.tech_task_date else None,
                'survey_date': str(card.survey_date) if card.survey_date else None,

                # IDs менеджеров
                'senior_manager_id': card.senior_manager_id,
                'sdp_id': card.sdp_id,
                'gap_id': card.gap_id,
                'manager_id': card.manager_id,
                'surveyor_id': card.surveyor_id,

                # Имена менеджеров
                'senior_manager_name': senior_manager_name,
                'sdp_name': sdp_name,
                'gap_name': gap_name,
                'manager_name': manager_name,
                'surveyor_name': surveyor_name,

                # Данные договора
                'contract_number': contract.contract_number,
                'address': contract.address,
                'area': contract.area,
                'city': contract.city,
                'agent_type': contract.agent_type,
                'project_type': contract.project_type,
                'contract_status': contract.status,

                # Дизайнер
                'designer_name': designer_executor.executor.full_name if designer_executor else None,
                'designer_completed': designer_executor.completed if designer_executor else False,
                'designer_deadline': str(designer_executor.deadline) if designer_executor and designer_executor.deadline else None,

                # Чертёжник
                'draftsman_name': draftsman_executor.executor.full_name if draftsman_executor else None,
                'draftsman_completed': draftsman_executor.completed if draftsman_executor else False,
                'draftsman_deadline': str(draftsman_executor.deadline) if draftsman_executor and draftsman_executor.deadline else None,

                # Метаданные
                'order_position': card.order_position,
                'created_at': card.created_at.isoformat() if card.created_at else None,
                'updated_at': card.updated_at.isoformat() if card.updated_at else None,
            }
            result.append(card_data)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения CRM карточек: {str(e)}")


@app.get("/api/crm/cards/{card_id}")
async def get_crm_card(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить одну CRM карточку с полной информацией"""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Получаем всех исполнителей стадий
        stage_executors = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id
        ).all()

        executor_data = []
        for se in stage_executors:
            executor_data.append({
                'id': se.id,
                'stage_name': se.stage_name,
                'executor_id': se.executor_id,
                'executor_name': se.executor.full_name,
                'assigned_by': se.assigned_by,
                'assigned_date': se.assigned_date.isoformat() if se.assigned_date else None,
                'deadline': str(se.deadline) if se.deadline else None,
                'submitted_date': se.submitted_date.isoformat() if se.submitted_date else None,
                'completed': se.completed,
                'completed_date': se.completed_date.isoformat() if se.completed_date else None,
            })

        return {
            'id': card.id,
            'contract_id': card.contract_id,
            'column_name': card.column_name,
            'deadline': str(card.deadline) if card.deadline else None,
            'tags': card.tags,
            'is_approved': card.is_approved,
            'senior_manager_id': card.senior_manager_id,
            'sdp_id': card.sdp_id,
            'gap_id': card.gap_id,
            'manager_id': card.manager_id,
            'surveyor_id': card.surveyor_id,
            'approval_deadline': str(card.approval_deadline) if card.approval_deadline else None,
            'approval_stages': card.approval_stages,
            'project_data_link': card.project_data_link,
            'tech_task_file': card.tech_task_file,
            'tech_task_date': str(card.tech_task_date) if card.tech_task_date else None,
            'survey_date': str(card.survey_date) if card.survey_date else None,
            'order_position': card.order_position,
            'stage_executors': executor_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения карточки: {str(e)}")


@app.patch("/api/crm/cards/{card_id}")
async def update_crm_card(
    card_id: int,
    updates: CRMCardUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить поля CRM карточки (частичное обновление)"""
    try:
        # Проверка прав
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования CRM карточек")

        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Обновляем только переданные поля
        update_data = updates.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(card, field, value)

        # Автоматический пересчёт deadline если изменились даты
        # (Для упрощения пока оставляем клиенту)

        db.commit()
        db.refresh(card)

        return {
            'id': card.id,
            'contract_id': card.contract_id,
            'column_name': card.column_name,
            'deadline': str(card.deadline) if card.deadline else None,
            'tags': card.tags,
            'is_approved': card.is_approved,
            'senior_manager_id': card.senior_manager_id,
            'sdp_id': card.sdp_id,
            'gap_id': card.gap_id,
            'manager_id': card.manager_id,
            'surveyor_id': card.surveyor_id,
            'approval_deadline': str(card.approval_deadline) if card.approval_deadline else None,
            'approval_stages': card.approval_stages,
            'project_data_link': card.project_data_link,
            'tech_task_file': card.tech_task_file,
            'tech_task_date': str(card.tech_task_date) if card.tech_task_date else None,
            'survey_date': str(card.survey_date) if card.survey_date else None,
            'order_position': card.order_position,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка обновления карточки: {str(e)}")


@app.patch("/api/crm/cards/{card_id}/column")
async def move_crm_card_to_column(
    card_id: int,
    move_request: ColumnMoveRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Переместить CRM карточку в другую колонку"""
    try:
        # Проверка прав
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        old_column = card.column_name
        card.column_name = move_request.column_name

        # Сброс completed флагов при перемещении (опционально)
        # if old_column != move_request.column_name:
        #     stage_executors = db.query(StageExecutor).filter(
        #         StageExecutor.crm_card_id == card_id
        #     ).all()
        #     for se in stage_executors:
        #         se.completed = False
        #         se.completed_date = None

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
        raise HTTPException(status_code=500, detail=f"Ошибка перемещения карточки: {str(e)}")


@app.post("/api/crm/cards/{card_id}/stage-executor")
async def assign_stage_executor(
    card_id: int,
    executor_data: StageExecutorCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Назначить исполнителя на стадию"""
    try:
        # Проверка прав
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        # Проверяем существование карточки
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Проверяем существование исполнителя
        executor = db.query(Employee).filter(Employee.id == executor_data.executor_id).first()
        if not executor:
            raise HTTPException(status_code=404, detail="Исполнитель не найден")

        # Создаём назначение
        stage_executor = StageExecutor(
            crm_card_id=card_id,
            stage_name=executor_data.stage_name,
            executor_id=executor_data.executor_id,
            assigned_by=current_user.id,
            deadline=executor_data.deadline,
            assigned_date=datetime.utcnow()
        )

        db.add(stage_executor)
        db.commit()
        db.refresh(stage_executor)

        return {
            'id': stage_executor.id,
            'crm_card_id': stage_executor.crm_card_id,
            'stage_name': stage_executor.stage_name,
            'executor_id': stage_executor.executor_id,
            'executor_name': executor.full_name,
            'assigned_by': stage_executor.assigned_by,
            'assigned_date': stage_executor.assigned_date.isoformat(),
            'deadline': str(stage_executor.deadline) if stage_executor.deadline else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка назначения исполнителя: {str(e)}")


@app.patch("/api/crm/cards/{card_id}/stage-executor/{stage_name}")
async def complete_stage(
    card_id: int,
    stage_name: str,
    update_data: StageExecutorUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить статус выполнения стадии"""
    try:
        # Ищем последнее назначение для данной стадии
        stage_executor = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id,
            StageExecutor.stage_name == stage_name
        ).order_by(StageExecutor.id.desc()).first()

        if not stage_executor:
            raise HTTPException(status_code=404, detail="Назначение стадии не найдено")

        # Обновляем поля
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(stage_executor, field, value)

        # Если завершаем, автоматически ставим completed_date
        if update_data.completed and not update_data.completed_date:
            stage_executor.completed_date = datetime.utcnow()

        db.commit()
        db.refresh(stage_executor)

        return {
            'id': stage_executor.id,
            'crm_card_id': stage_executor.crm_card_id,
            'stage_name': stage_executor.stage_name,
            'executor_id': stage_executor.executor_id,
            'completed': stage_executor.completed,
            'completed_date': stage_executor.completed_date.isoformat() if stage_executor.completed_date else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка обновления стадии: {str(e)}")

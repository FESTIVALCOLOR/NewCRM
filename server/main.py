"""
FastAPI приложение - главный файл
REST API для многопользовательской CRM
"""
import logging
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timedelta
from typing import List, Optional
import io

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from config import get_settings
from server.database import (
    get_db, init_db,
    Employee, Client, Contract, Notification, UserSession, ActivityLog,
    CRMCard, StageExecutor, SupervisionCard, SupervisionProjectHistory,
    Payment, Rate, Salary, ProjectFile, ActionHistory
)
from server.schemas import (
    LoginRequest, TokenResponse,
    EmployeeResponse, EmployeeCreate, EmployeeUpdate,
    ClientResponse, ClientCreate, ClientUpdate,
    ContractResponse, ContractCreate, ContractUpdate,
    NotificationResponse, SyncRequest, SyncResponse,
    # CRM
    CRMCardCreate, CRMCardUpdate, CRMCardResponse,
    ColumnMoveRequest, StageExecutorCreate, StageExecutorUpdate, StageExecutorResponse,
    # Supervision
    SupervisionCardCreate, SupervisionCardUpdate, SupervisionCardResponse,
    SupervisionColumnMoveRequest, SupervisionPauseRequest, SupervisionHistoryResponse,
    # Payments
    PaymentCreate, PaymentUpdate, PaymentResponse,
    # Rates
    RateCreate, RateUpdate, RateResponse,
    # Salaries
    SalaryCreate, SalaryUpdate, SalaryResponse,
    # Files
    ProjectFileCreate, ProjectFileResponse,
    # Action History
    ActionHistoryCreate, ActionHistoryResponse,
    # Extended Request Schemas
    PaymentManualUpdateRequest, TemplateRateRequest, IndividualRateRequest,
    SupervisionRateRequest, SurveyorRateRequest
)
from server.auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user
)

settings = get_settings()

# Создание приложения
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="REST API для многопользовательской CRM Interior Studio"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    print(f"[INFO] Запуск {settings.app_name} v{settings.app_version}")
    init_db()
    print("[OK] База данных инициализирована")


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy"}


# =========================
# АУТЕНТИФИКАЦИЯ
# =========================

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Вход в систему"""
    # Поиск сотрудника
    employee = db.query(Employee).filter(Employee.login == form_data.username).first()
    if not employee or not verify_password(form_data.password, employee.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Создание токена
    access_token = create_access_token(data={"sub": str(employee.id)})

    # Обновление статуса
    employee.last_login = datetime.utcnow()
    employee.is_online = True
    employee.current_session_token = access_token

    # Создание сессии
    session = UserSession(
        employee_id=employee.id,
        session_token=access_token,
        login_time=datetime.utcnow()
    )
    db.add(session)

    # Лог активности
    log = ActivityLog(
        employee_id=employee.id,
        session_id=session.id,
        action_type="login",
        entity_type="auth",
        entity_id=employee.id
    )
    db.add(log)

    db.commit()

    return TokenResponse(
        access_token=access_token,
        employee_id=employee.id,
        full_name=employee.full_name,
        role=employee.role or ""
    )


@app.post("/api/auth/logout")
async def logout(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Выход из системы"""
    current_user.is_online = False
    current_user.current_session_token = None

    # Закрываем сессию
    session = db.query(UserSession).filter(
        UserSession.employee_id == current_user.id,
        UserSession.is_active == True
    ).first()
    if session:
        session.is_active = False
        session.logout_time = datetime.utcnow()

    # Лог
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="logout",
        entity_type="auth",
        entity_id=current_user.id
    )
    db.add(log)

    db.commit()

    return {"message": "Успешный выход"}


@app.get("/api/auth/me", response_model=EmployeeResponse)
async def get_me(current_user: Employee = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return current_user


# =========================
# СОТРУДНИКИ
# =========================

@app.get("/api/employees", response_model=List[EmployeeResponse])
async def get_employees(
    skip: int = 0,
    limit: int = 100,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список сотрудников"""
    employees = db.query(Employee).offset(skip).limit(limit).all()
    return employees


@app.get("/api/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить сотрудника по ID"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    return employee


@app.post("/api/employees", response_model=EmployeeResponse)
async def create_employee(
    employee_data: EmployeeCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать нового сотрудника"""
    # Проверка прав (только руководитель)
    if current_user.role != "Руководитель студии":
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    # Проверка уникальности логина
    existing = db.query(Employee).filter(Employee.login == employee_data.login).first()
    if existing:
        raise HTTPException(status_code=400, detail="Логин уже занят")

    # Создание
    employee = Employee(
        **employee_data.model_dump(exclude={'password'}),
        password_hash=get_password_hash(employee_data.password)
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)

    # Лог
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="create",
        entity_type="employee",
        entity_id=employee.id
    )
    db.add(log)
    db.commit()

    return employee


@app.put("/api/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить сотрудника"""
    # Проверка прав (только руководители)
    allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    # Обновление полей
    update_data = employee_data.model_dump(exclude_unset=True)

    # Если обновляется пароль
    if 'password' in update_data:
        update_data['password_hash'] = get_password_hash(update_data.pop('password'))

    for field, value in update_data.items():
        setattr(employee, field, value)

    employee.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(employee)

    # Лог
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="update",
        entity_type="employee",
        entity_id=employee.id
    )
    db.add(log)
    db.commit()

    return employee


@app.delete("/api/employees/{employee_id}")
async def delete_employee(
    employee_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить сотрудника"""
    # Проверка прав (только Руководитель студии может удалять)
    if current_user.role != 'Руководитель студии':
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления сотрудников")

    # Нельзя удалить самого себя
    if employee_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    # Лог перед удалением
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="delete",
        entity_type="employee",
        entity_id=employee_id
    )
    db.add(log)

    db.delete(employee)
    db.commit()

    return {"status": "success", "message": "Сотрудник удален"}


# =========================
# КЛИЕНТЫ
# =========================

@app.get("/api/clients", response_model=List[ClientResponse])
async def get_clients(
    skip: int = 0,
    limit: int = 100,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список клиентов"""
    clients = db.query(Client).offset(skip).limit(limit).all()
    return clients


@app.get("/api/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить клиента по ID"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return client


@app.post("/api/clients", response_model=ClientResponse)
async def create_client(
    client_data: ClientCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать нового клиента"""
    client = Client(**client_data.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)

    # Лог
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="create",
        entity_type="client",
        entity_id=client.id
    )
    db.add(log)
    db.commit()

    return client


@app.put("/api/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    client_data: ClientUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить клиента"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    # Обновление полей
    for field, value in client_data.model_dump(exclude_unset=True).items():
        setattr(client, field, value)

    client.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(client)

    # Лог
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="update",
        entity_type="client",
        entity_id=client.id
    )
    db.add(log)
    db.commit()

    return client


@app.delete("/api/clients/{client_id}")
async def delete_client(
    client_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить клиента"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    # Лог перед удалением
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="delete",
        entity_type="client",
        entity_id=client_id
    )
    db.add(log)

    db.delete(client)
    db.commit()

    return {"status": "success", "message": "Клиент удален"}


# =========================
# ДОГОВОРЫ
# =========================

@app.get("/api/contracts", response_model=List[ContractResponse])
async def get_contracts(
    skip: int = 0,
    limit: int = 100,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список договоров"""
    contracts = db.query(Contract).offset(skip).limit(limit).all()
    return contracts


@app.get("/api/contracts/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить договор по ID"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")
    return contract


@app.post("/api/contracts", response_model=ContractResponse)
async def create_contract(
    contract_data: ContractCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать новый договор"""
    contract = Contract(**contract_data.model_dump())
    db.add(contract)
    db.commit()
    db.refresh(contract)

    # Автоматически создаем CRM карточку для нового договора
    # (кроме Авторского надзора - для него создается SupervisionCard)
    if contract.project_type != 'Авторский надзор':
        crm_card = CRMCard(
            contract_id=contract.id,
            column_name='Новый заказ',
            manager_id=current_user.id
        )
        db.add(crm_card)
        db.commit()
        print(f"[OK] Создана CRM карточка для договора {contract.id}")

    # Лог
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="create",
        entity_type="contract",
        entity_id=contract.id
    )
    db.add(log)
    db.commit()

    return contract


@app.put("/api/contracts/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: int,
    contract_data: ContractUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить договор"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    # Обновление полей
    for field, value in contract_data.model_dump(exclude_unset=True).items():
        setattr(contract, field, value)

    contract.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(contract)

    # Лог
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="update",
        entity_type="contract",
        entity_id=contract.id
    )
    db.add(log)
    db.commit()

    return contract


@app.delete("/api/contracts/{contract_id}")
async def delete_contract(
    contract_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить договор"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    # Удаляем связанные CRM карточки
    crm_cards = db.query(CRMCard).filter(CRMCard.contract_id == contract_id).all()
    for card in crm_cards:
        # Удаляем связанные stage_executors
        db.query(StageExecutor).filter(StageExecutor.card_id == card.id).delete()
        # Удаляем саму карточку
        db.delete(card)

    # Удаляем связанные SupervisionCard
    supervision_cards = db.query(SupervisionCard).filter(SupervisionCard.contract_id == contract_id).all()
    for card in supervision_cards:
        # Удаляем связанную историю
        db.query(SupervisionProjectHistory).filter(SupervisionProjectHistory.supervision_card_id == card.id).delete()
        db.delete(card)

    # Удаляем связанные платежи
    db.query(Payment).filter(Payment.contract_id == contract_id).delete()

    # Удаляем связанные файлы проекта
    db.query(ProjectFile).filter(ProjectFile.contract_id == contract_id).delete()

    # Лог перед удалением
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="delete",
        entity_type="contract",
        entity_id=contract_id
    )
    db.add(log)

    db.delete(contract)
    db.commit()

    return {"status": "success", "message": "Договор удален"}


# =========================
# СИНХРОНИЗАЦИЯ
# =========================

@app.post("/api/sync", response_model=SyncResponse)
async def sync_data(
    sync_request: SyncRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Синхронизация данных
    Возвращает все изменения после указанного timestamp
    """
    response = SyncResponse(timestamp=datetime.utcnow())

    # Клиенты
    if 'clients' in sync_request.entity_types:
        clients = db.query(Client).filter(
            Client.updated_at > sync_request.last_sync_timestamp
        ).all()
        response.clients = clients

    # Договоры
    if 'contracts' in sync_request.entity_types:
        contracts = db.query(Contract).filter(
            Contract.updated_at > sync_request.last_sync_timestamp
        ).all()
        response.contracts = contracts

    # Сотрудники
    if 'employees' in sync_request.entity_types:
        employees = db.query(Employee).filter(
            Employee.updated_at > sync_request.last_sync_timestamp
        ).all()
        response.employees = employees

    # Уведомления
    notifications = db.query(Notification).filter(
        Notification.employee_id == current_user.id,
        Notification.created_at > sync_request.last_sync_timestamp
    ).all()
    response.notifications = notifications

    return response


# =========================
# УВЕДОМЛЕНИЯ
# =========================

@app.get("/api/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить уведомления текущего пользователя"""
    query = db.query(Notification).filter(Notification.employee_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read == False)

    notifications = query.order_by(Notification.created_at.desc()).all()
    return notifications


@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отметить уведомление как прочитанное"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.employee_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()

    return {"message": "Уведомление прочитано"}


# =========================
# CRM КАРТОЧКИ
# =========================

@app.get("/api/crm/cards")
async def get_crm_cards(
    project_type: str,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список CRM карточек по типу проекта"""
    try:
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

        result = []
        for card in cards:
            contract = card.contract
            senior_manager_name = card.senior_manager.full_name if card.senior_manager else None
            sdp_name = card.sdp.full_name if card.sdp else None
            gap_name = card.gap.full_name if card.gap else None
            manager_name = card.manager.full_name if card.manager else None
            surveyor_name = card.surveyor.full_name if card.surveyor else None

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
                'senior_manager_id': card.senior_manager_id,
                'sdp_id': card.sdp_id,
                'gap_id': card.gap_id,
                'manager_id': card.manager_id,
                'surveyor_id': card.surveyor_id,
                'senior_manager_name': senior_manager_name,
                'sdp_name': sdp_name,
                'gap_name': gap_name,
                'manager_name': manager_name,
                'surveyor_name': surveyor_name,
                'contract_number': contract.contract_number,
                'address': contract.address,
                'area': contract.area,
                'city': contract.city,
                'agent_type': contract.agent_type,
                'project_type': contract.project_type,
                'contract_status': contract.status,
                'designer_name': designer_executor.executor.full_name if designer_executor else None,
                'designer_completed': designer_executor.completed if designer_executor else False,
                'designer_deadline': str(designer_executor.deadline) if designer_executor and designer_executor.deadline else None,
                'draftsman_name': draftsman_executor.executor.full_name if draftsman_executor else None,
                'draftsman_completed': draftsman_executor.completed if draftsman_executor else False,
                'draftsman_deadline': str(draftsman_executor.deadline) if draftsman_executor and draftsman_executor.deadline else None,
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
    """Получить одну CRM карточку"""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

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


@app.post("/api/crm/cards")
async def create_crm_card(
    card_data: CRMCardCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать новую CRM карточку"""
    try:
        card = CRMCard(**card_data.model_dump())
        db.add(card)
        db.commit()
        db.refresh(card)

        log = ActivityLog(
            employee_id=current_user.id,
            action_type="create",
            entity_type="crm_card",
            entity_id=card.id
        )
        db.add(log)
        db.commit()

        return card

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания карточки: {str(e)}")


@app.patch("/api/crm/cards/{card_id}")
async def update_crm_card(
    card_id: int,
    updates: CRMCardUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить CRM карточку"""
    try:
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        update_data = updates.model_dump(exclude_unset=True)
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
            'is_approved': card.is_approved,
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
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

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
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        executor = db.query(Employee).filter(Employee.id == executor_data.executor_id).first()
        if not executor:
            raise HTTPException(status_code=404, detail="Исполнитель не найден")

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
        stage_executor = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id,
            StageExecutor.stage_name == stage_name
        ).order_by(StageExecutor.id.desc()).first()

        if not stage_executor:
            raise HTTPException(status_code=404, detail="Назначение стадии не найдено")

        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(stage_executor, field, value)

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


@app.delete("/api/crm/cards/{card_id}")
async def delete_crm_card(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить CRM карточку"""
    try:
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Удаляем связанные stage_executors
        db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id).delete()

        # Удаляем связанные платежи
        db.query(Payment).filter(Payment.crm_card_id == card_id).delete()

        # Лог перед удалением
        log = ActivityLog(
            employee_id=current_user.id,
            action_type="delete",
            entity_type="crm_card",
            entity_id=card_id
        )
        db.add(log)

        db.delete(card)
        db.commit()

        return {"status": "success", "message": "CRM карточка удалена"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления карточки: {str(e)}")


@app.delete("/api/crm/stage-executors/{executor_id}")
async def delete_stage_executor(
    executor_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить назначение исполнителя на стадию"""
    try:
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        executor = db.query(StageExecutor).filter(StageExecutor.id == executor_id).first()
        if not executor:
            raise HTTPException(status_code=404, detail="Назначение не найдено")

        # Лог перед удалением
        log = ActivityLog(
            employee_id=current_user.id,
            action_type="delete",
            entity_type="stage_executor",
            entity_id=executor_id
        )
        db.add(log)

        db.delete(executor)
        db.commit()

        return {"status": "success", "message": "Назначение исполнителя удалено"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления назначения: {str(e)}")


# =========================
# SUPERVISION (Авторский надзор)
# =========================

@app.get("/api/supervision/cards")
async def get_supervision_cards(
    status: str = "active",
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список карточек авторского надзора"""
    try:
        if status == "active":
            cards = db.query(SupervisionCard).join(
                Contract, SupervisionCard.contract_id == Contract.id
            ).filter(
                Contract.status == 'АВТОРСКИЙ НАДЗОР'
            ).order_by(
                SupervisionCard.id.desc()
            ).all()
        else:
            cards = db.query(SupervisionCard).join(
                Contract, SupervisionCard.contract_id == Contract.id
            ).filter(
                Contract.status.in_(['СДАН', 'РАСТОРГНУТ'])
            ).order_by(
                SupervisionCard.id.desc()
            ).all()

        result = []
        for card in cards:
            contract = card.contract
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
                'senior_manager_name': senior_manager_name,
                'dan_name': dan_name,
                'contract_number': contract.contract_number,
                'address': contract.address,
                'area': contract.area,
                'city': contract.city,
                'agent_type': contract.agent_type,
                'contract_status': contract.status,
                'termination_reason': contract.termination_reason if status == "archived" else None,
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


@app.post("/api/supervision/cards")
async def create_supervision_card(
    card_data: SupervisionCardCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать карточку надзора"""
    try:
        card = SupervisionCard(**card_data.model_dump())
        db.add(card)
        db.commit()
        db.refresh(card)

        log = ActivityLog(
            employee_id=current_user.id,
            action_type="create",
            entity_type="supervision_card",
            entity_id=card.id
        )
        db.add(log)
        db.commit()

        return card

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания карточки надзора: {str(e)}")


@app.patch("/api/supervision/cards/{card_id}")
async def update_supervision_card(
    card_id: int,
    updates: SupervisionCardUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить карточку надзора"""
    try:
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        update_data = updates.model_dump(exclude_unset=True)
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
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        card.is_paused = True
        card.pause_reason = pause_request.pause_reason
        card.paused_at = datetime.utcnow()

        # Добавляем запись в историю
        history = SupervisionProjectHistory(
            supervision_card_id=card_id,
            entry_type="pause",
            message=f"Приостановлено: {pause_request.pause_reason}",
            created_by=current_user.id
        )
        db.add(history)

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
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        card.is_paused = False
        card.pause_reason = None
        card.paused_at = None

        # Добавляем запись в историю
        history = SupervisionProjectHistory(
            supervision_card_id=card_id,
            entry_type="resume",
            message="Возобновлено",
            created_by=current_user.id
        )
        db.add(history)

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


@app.get("/api/supervision/cards/{card_id}/history", response_model=List[SupervisionHistoryResponse])
async def get_supervision_card_history(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить историю карточки надзора"""
    try:
        history = db.query(SupervisionProjectHistory).filter(
            SupervisionProjectHistory.supervision_card_id == card_id
        ).order_by(SupervisionProjectHistory.created_at.desc()).all()

        return history

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения истории: {str(e)}")


# =========================
# ПЛАТЕЖИ
# =========================

@app.get("/api/payments/contract/{contract_id}")
async def get_payments_for_contract(
    contract_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить платежи по договору"""
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
            'payment_status': payment.payment_status,
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

        result.append(payment_dict)

    return result


@app.post("/api/payments", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать платеж"""
    try:
        payment = Payment(**payment_data.model_dump())
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
        raise HTTPException(status_code=500, detail=f"Ошибка создания платежа: {str(e)}")


@app.put("/api/payments/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    current_user: Employee = Depends(get_current_user),
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


@app.delete("/api/payments/{payment_id}")
async def delete_payment(
    payment_id: int,
    current_user: Employee = Depends(get_current_user),
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


# =========================
# ТАРИФЫ
# =========================

@app.get("/api/rates", response_model=List[RateResponse])
async def get_rates(
    project_type: Optional[str] = None,
    role: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить тарифы"""
    query = db.query(Rate)
    if project_type:
        query = query.filter(Rate.project_type == project_type)
    if role:
        query = query.filter(Rate.role == role)
    return query.all()


@app.get("/api/rates/{rate_id}", response_model=RateResponse)
async def get_rate(
    rate_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить тариф по ID"""
    rate = db.query(Rate).filter(Rate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Тариф не найден")
    return rate


@app.post("/api/rates", response_model=RateResponse)
async def create_rate(
    rate_data: RateCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать тариф"""
    rate = Rate(**rate_data.model_dump())
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


@app.put("/api/rates/{rate_id}", response_model=RateResponse)
async def update_rate(
    rate_id: int,
    rate_data: RateUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить тариф"""
    rate = db.query(Rate).filter(Rate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Тариф не найден")

    for field, value in rate_data.model_dump(exclude_unset=True).items():
        setattr(rate, field, value)

    rate.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rate)

    return rate


@app.delete("/api/rates/{rate_id}")
async def delete_rate(
    rate_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить тариф"""
    rate = db.query(Rate).filter(Rate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Тариф не найден")

    db.delete(rate)
    db.commit()

    return {"status": "success", "message": "Тариф удален"}


# =========================
# ЗАРПЛАТЫ
# =========================

@app.get("/api/salaries", response_model=List[SalaryResponse])
async def get_salaries(
    report_month: Optional[str] = None,
    employee_id: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить зарплаты"""
    query = db.query(Salary)
    if report_month:
        query = query.filter(Salary.report_month == report_month)
    if employee_id:
        query = query.filter(Salary.employee_id == employee_id)
    return query.all()


@app.get("/api/salaries/{salary_id}", response_model=SalaryResponse)
async def get_salary(
    salary_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить зарплату по ID"""
    salary = db.query(Salary).filter(Salary.id == salary_id).first()
    if not salary:
        raise HTTPException(status_code=404, detail="Запись о зарплате не найдена")
    return salary


@app.post("/api/salaries", response_model=SalaryResponse)
async def create_salary(
    salary_data: SalaryCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать запись о зарплате"""
    salary = Salary(**salary_data.model_dump())
    db.add(salary)
    db.commit()
    db.refresh(salary)
    return salary


@app.put("/api/salaries/{salary_id}", response_model=SalaryResponse)
async def update_salary(
    salary_id: int,
    salary_data: SalaryUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить запись о зарплате"""
    salary = db.query(Salary).filter(Salary.id == salary_id).first()
    if not salary:
        raise HTTPException(status_code=404, detail="Запись о зарплате не найдена")

    for field, value in salary_data.model_dump(exclude_unset=True).items():
        setattr(salary, field, value)

    db.commit()
    db.refresh(salary)

    return salary


@app.delete("/api/salaries/{salary_id}")
async def delete_salary(
    salary_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить запись о зарплате"""
    salary = db.query(Salary).filter(Salary.id == salary_id).first()
    if not salary:
        raise HTTPException(status_code=404, detail="Запись о зарплате не найдена")

    db.delete(salary)
    db.commit()

    return {"status": "success", "message": "Запись о зарплате удалена"}


# =========================
# ИСТОРИЯ ДЕЙСТВИЙ
# =========================

@app.get("/api/action-history/{entity_type}/{entity_id}", response_model=List[ActionHistoryResponse])
async def get_action_history(
    entity_type: str,
    entity_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить историю действий по сущности"""
    history = db.query(ActionHistory).filter(
        ActionHistory.entity_type == entity_type,
        ActionHistory.entity_id == entity_id
    ).order_by(ActionHistory.action_date.desc()).all()
    return history


@app.post("/api/action-history", response_model=ActionHistoryResponse)
async def create_action_history(
    history_data: ActionHistoryCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать запись в истории действий"""
    history = ActionHistory(
        user_id=current_user.id,
        **history_data.model_dump()
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history


@app.get("/api/action-history", response_model=List[ActionHistoryResponse])
async def get_all_action_history(
    entity_type: Optional[str] = None,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить всю историю действий"""
    query = db.query(ActionHistory)
    if entity_type:
        query = query.filter(ActionHistory.entity_type == entity_type)
    if user_id:
        query = query.filter(ActionHistory.user_id == user_id)
    return query.order_by(ActionHistory.action_date.desc()).offset(skip).limit(limit).all()


# =========================
# ФАЙЛЫ ПРОЕКТА
# =========================

@app.get("/api/files/contract/{contract_id}", response_model=List[ProjectFileResponse])
async def get_contract_files(
    contract_id: int,
    stage: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить файлы договора"""
    query = db.query(ProjectFile).filter(ProjectFile.contract_id == contract_id)
    if stage:
        query = query.filter(ProjectFile.stage == stage)
    return query.order_by(ProjectFile.file_order).all()


@app.post("/api/files", response_model=ProjectFileResponse)
async def create_file_record(
    file_data: ProjectFileCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать запись о файле"""
    file_record = ProjectFile(**file_data.model_dump())
    db.add(file_record)
    db.commit()
    db.refresh(file_record)
    return file_record


@app.delete("/api/files/{file_id}")
async def delete_file_record(
    file_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить запись о файле"""
    file_record = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="Файл не найден")

    db.delete(file_record)
    db.commit()

    return {"status": "success", "message": "Запись о файле удалена"}


# =========================
# YANDEX DISK API
# =========================

try:
    from yandex_disk_service import get_yandex_disk_service
    yandex_disk_available = True
except ImportError:
    yandex_disk_available = False
    logger.warning("YandexDiskService not available")


@app.post("/api/files/upload")
async def upload_file_to_yandex(
    file: UploadFile = File(...),
    yandex_path: str = None,
    current_user: Employee = Depends(get_current_user),
):
    """Загрузить файл на Яндекс.Диск"""
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")

    try:
        yd_service = get_yandex_disk_service()
        file_bytes = await file.read()

        if not yandex_path:
            yandex_path = f"/uploads/{file.filename}"

        result = yd_service.upload_file_from_bytes(file_bytes, yandex_path)

        if result:
            public_link = yd_service.get_public_link(yandex_path)
            return {
                "status": "success",
                "yandex_path": yandex_path,
                "public_link": public_link,
                "file_name": file.filename
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to upload file")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")


@app.post("/api/files/folder")
async def create_yandex_folder(
    folder_path: str,
    current_user: Employee = Depends(get_current_user),
):
    """Создать папку на Яндекс.Диске"""
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")

    try:
        yd_service = get_yandex_disk_service()
        result = yd_service.create_folder(folder_path)

        return {
            "status": "success" if result else "exists",
            "folder_path": folder_path
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Folder creation error: {str(e)}")


@app.get("/api/files/public-link")
async def get_public_link(
    yandex_path: str,
    current_user: Employee = Depends(get_current_user),
):
    """Получить публичную ссылку на файл"""
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")

    try:
        yd_service = get_yandex_disk_service()
        public_link = yd_service.get_public_link(yandex_path)

        if public_link:
            return {
                "status": "success",
                "public_link": public_link,
                "yandex_path": yandex_path
            }
        else:
            raise HTTPException(status_code=404, detail="File not found or cannot create public link")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting public link: {str(e)}")


@app.get("/api/files/list")
async def list_yandex_files(
    folder_path: str,
    current_user: Employee = Depends(get_current_user),
):
    """Получить список файлов в папке Яндекс.Диска"""
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")

    try:
        yd_service = get_yandex_disk_service()
        files = yd_service.list_files(folder_path)

        return {
            "status": "success",
            "folder_path": folder_path,
            "files": files
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")


@app.delete("/api/files/yandex")
async def delete_yandex_file(
    yandex_path: str,
    current_user: Employee = Depends(get_current_user),
):
    """Удалить файл с Яндекс.Диска"""
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")

    try:
        yd_service = get_yandex_disk_service()
        result = yd_service.delete_file(yandex_path)

        return {
            "status": "success" if result else "not_found",
            "yandex_path": yandex_path
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


# =========================
# СТАТИСТИКА И ОТЧЕТЫ
# =========================

@app.get("/api/statistics/dashboard")
async def get_dashboard_statistics(
    year: Optional[int] = None,
    month: Optional[int] = None,
    quarter: Optional[int] = None,
    agent_type: Optional[str] = None,
    city: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статистику для дашборда"""
    try:
        from sqlalchemy import func, extract, and_

        # Базовый запрос договоров
        query = db.query(Contract)

        # Фильтры
        if year:
            query = query.filter(extract('year', Contract.created_at) == year)
        if month:
            query = query.filter(extract('month', Contract.created_at) == month)
        if quarter:
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            query = query.filter(extract('month', Contract.created_at).between(start_month, end_month))
        if agent_type and agent_type != 'Все':
            query = query.filter(Contract.agent_type == agent_type)
        if city and city != 'Все':
            query = query.filter(Contract.city == city)

        contracts = query.all()

        # Подсчет статистики
        total_contracts = len(contracts)
        total_amount = sum(c.total_amount or 0 for c in contracts)
        total_area = sum(c.area or 0 for c in contracts)

        # По типам проектов
        individual_count = len([c for c in contracts if c.project_type == 'Индивидуальный'])
        template_count = len([c for c in contracts if c.project_type == 'Шаблонный'])

        # По статусам
        status_counts = {}
        for c in contracts:
            status = c.status or 'Новый заказ'
            status_counts[status] = status_counts.get(status, 0) + 1

        # По городам
        city_counts = {}
        for c in contracts:
            c_city = c.city or 'Не указан'
            city_counts[c_city] = city_counts.get(c_city, 0) + 1

        # По месяцам (для графиков)
        monthly_data = {}
        for c in contracts:
            if c.created_at:
                month_key = c.created_at.strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = {'count': 0, 'amount': 0}
                monthly_data[month_key]['count'] += 1
                monthly_data[month_key]['amount'] += c.total_amount or 0

        # Активные CRM карточки
        active_cards = db.query(CRMCard).join(Contract).filter(
            ~Contract.status.in_(['СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР'])
        ).count()

        # Карточки надзора
        supervision_cards = db.query(SupervisionCard).join(Contract).filter(
            Contract.status == 'АВТОРСКИЙ НАДЗОР'
        ).count()

        return {
            'total_contracts': total_contracts,
            'total_amount': total_amount,
            'total_area': total_area,
            'individual_count': individual_count,
            'template_count': template_count,
            'status_counts': status_counts,
            'city_counts': city_counts,
            'monthly_data': monthly_data,
            'active_crm_cards': active_cards,
            'supervision_cards': supervision_cards
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")


@app.get("/api/statistics/employees")
async def get_employee_statistics(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статистику по сотрудникам"""
    try:
        from sqlalchemy import func, extract

        employees = db.query(Employee).filter(Employee.status == 'активный').all()

        result = []
        for emp in employees:
            # Подсчет назначений на этапы
            stage_query = db.query(StageExecutor).filter(StageExecutor.executor_id == emp.id)
            if year:
                stage_query = stage_query.filter(extract('year', StageExecutor.assigned_date) == year)
            if month:
                stage_query = stage_query.filter(extract('month', StageExecutor.assigned_date) == month)

            total_stages = stage_query.count()
            completed_stages = stage_query.filter(StageExecutor.completed == True).count()

            # Зарплаты
            salary_query = db.query(Salary).filter(Salary.employee_id == emp.id)
            if year and month:
                report_month = f"{year}-{month:02d}"
                salary_query = salary_query.filter(Salary.report_month == report_month)

            total_salary = sum(s.amount or 0 for s in salary_query.all())

            result.append({
                'id': emp.id,
                'full_name': emp.full_name,
                'position': emp.position,
                'total_stages': total_stages,
                'completed_stages': completed_stages,
                'completion_rate': (completed_stages / total_stages * 100) if total_stages > 0 else 0,
                'total_salary': total_salary
            })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")


@app.get("/api/statistics/contracts-by-period")
async def get_contracts_by_period(
    year: int,
    group_by: str = "month",  # month, quarter, status
    project_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить договоры сгруппированные по периоду"""
    try:
        from sqlalchemy import func, extract

        query = db.query(Contract).filter(extract('year', Contract.created_at) == year)

        if project_type and project_type != 'Все':
            query = query.filter(Contract.project_type == project_type)

        contracts = query.all()

        if group_by == "month":
            result = {i: {'count': 0, 'amount': 0} for i in range(1, 13)}
            for c in contracts:
                if c.created_at:
                    m = c.created_at.month
                    result[m]['count'] += 1
                    result[m]['amount'] += c.total_amount or 0

        elif group_by == "quarter":
            result = {i: {'count': 0, 'amount': 0} for i in range(1, 5)}
            for c in contracts:
                if c.created_at:
                    q = (c.created_at.month - 1) // 3 + 1
                    result[q]['count'] += 1
                    result[q]['amount'] += c.total_amount or 0

        elif group_by == "status":
            result = {}
            for c in contracts:
                status = c.status or 'Новый заказ'
                if status not in result:
                    result[status] = {'count': 0, 'amount': 0}
                result[status]['count'] += 1
                result[status]['amount'] += c.total_amount or 0

        else:
            result = {}

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения данных: {str(e)}")


@app.get("/api/statistics/agent-types")
async def get_agent_types(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список типов агентов"""
    try:
        result = db.query(Contract.agent_type).distinct().filter(
            Contract.agent_type != None,
            Contract.agent_type != ''
        ).all()
        return ['Все'] + [r[0] for r in result if r[0]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@app.get("/api/statistics/cities")
async def get_cities(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список городов"""
    try:
        result = db.query(Contract.city).distinct().filter(
            Contract.city != None,
            Contract.city != ''
        ).all()
        return ['Все'] + [r[0] for r in result if r[0]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@app.get("/api/salaries/report")
async def get_salary_report(
    report_month: Optional[str] = None,
    employee_id: Optional[int] = None,
    payment_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить отчет по зарплатам"""
    try:
        query = db.query(Salary)

        if report_month:
            query = query.filter(Salary.report_month == report_month)
        if employee_id:
            query = query.filter(Salary.employee_id == employee_id)
        if payment_type:
            query = query.filter(Salary.payment_type == payment_type)

        salaries = query.all()

        # Группировка по сотрудникам
        employee_totals = {}
        for s in salaries:
            emp_id = s.employee_id
            if emp_id not in employee_totals:
                emp = db.query(Employee).filter(Employee.id == emp_id).first()
                employee_totals[emp_id] = {
                    'employee_id': emp_id,
                    'employee_name': emp.full_name if emp else 'Неизвестный',
                    'position': emp.position if emp else '',
                    'total_amount': 0,
                    'advance_payment': 0,
                    'records': []
                }

            employee_totals[emp_id]['total_amount'] += s.amount or 0
            employee_totals[emp_id]['advance_payment'] += s.advance_payment or 0
            employee_totals[emp_id]['records'].append({
                'id': s.id,
                'payment_type': s.payment_type,
                'stage_name': s.stage_name,
                'amount': s.amount,
                'report_month': s.report_month,
                'payment_status': s.payment_status
            })

        return {
            'report_month': report_month,
            'total_amount': sum(e['total_amount'] for e in employee_totals.values()),
            'employees': list(employee_totals.values())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения отчета: {str(e)}")


@app.get("/api/payments/summary")
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
        raise HTTPException(status_code=500, detail=f"Ошибка получения сводки: {str(e)}")


# =========================
# CRM EXTENDED ENDPOINTS
# =========================

@app.post("/api/crm/cards/{card_id}/reset-stages")
async def reset_crm_card_stages(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Сбросить выполнение стадий карточки"""
    try:
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Сбрасываем все stage_executors
        stage_executors = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id).all()
        for se in stage_executors:
            se.completed = False
            se.completed_date = None
            se.submitted_date = None

        db.commit()

        return {"status": "success", "message": "Стадии сброшены", "card_id": card_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сброса стадий: {str(e)}")


@app.post("/api/crm/cards/{card_id}/reset-approval")
async def reset_crm_card_approval(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Сбросить стадии согласования карточки"""
    try:
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Сбрасываем согласования
        card.is_approved = False
        card.approval_stages = None
        card.approval_deadline = None

        db.commit()

        return {"status": "success", "message": "Согласования сброшены", "card_id": card_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сброса согласований: {str(e)}")


# =========================
# SUPERVISION EXTENDED ENDPOINTS
# =========================

@app.post("/api/supervision/cards/{card_id}/reset-stages")
async def reset_supervision_card_stages(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Сбросить выполнение стадий надзора"""
    try:
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        # Сбрасываем dan_completed
        card.dan_completed = False

        db.commit()

        return {"status": "success", "message": "Стадии надзора сброшены", "card_id": card_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сброса стадий надзора: {str(e)}")


@app.post("/api/supervision/cards/{card_id}/complete-stage")
async def complete_supervision_stage(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Завершить стадию надзора"""
    try:
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов', 'ДАН']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        card.dan_completed = True

        # Добавляем запись в историю
        history = SupervisionProjectHistory(
            supervision_card_id=card_id,
            entry_type="stage_completed",
            message="Стадия завершена",
            created_by=current_user.id
        )
        db.add(history)

        db.commit()

        return {"status": "success", "message": "Стадия завершена", "card_id": card_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка завершения стадии: {str(e)}")


@app.delete("/api/supervision/orders/{supervision_card_id}")
async def delete_supervision_order(
    supervision_card_id: int,
    contract_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить заказ надзора"""
    try:
        allowed_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")

        card = db.query(SupervisionCard).filter(SupervisionCard.id == supervision_card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        # Удаляем историю
        db.query(SupervisionProjectHistory).filter(
            SupervisionProjectHistory.supervision_card_id == supervision_card_id
        ).delete()

        # Удаляем связанные платежи
        db.query(Payment).filter(Payment.supervision_card_id == supervision_card_id).delete()

        # Удаляем карточку
        db.delete(card)
        db.commit()

        return {"status": "success", "message": "Заказ надзора удален"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления заказа надзора: {str(e)}")


@app.get("/api/payments/supervision/{contract_id}")
async def get_payments_for_supervision(
    contract_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить платежи для надзора"""
    payments = db.query(Payment).filter(
        Payment.contract_id == contract_id,
        Payment.payment_type == 'supervision'
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
        })

    return result


@app.patch("/api/payments/{payment_id}/manual")
async def update_payment_manual(
    payment_id: int,
    data: PaymentManualUpdateRequest,
    current_user: Employee = Depends(get_current_user),
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
        raise HTTPException(status_code=500, detail=f"Ошибка обновления платежа: {str(e)}")


@app.patch("/api/payments/{payment_id}/mark-paid")
async def mark_payment_as_paid(
    payment_id: int,
    employee_id: int,
    current_user: Employee = Depends(get_current_user),
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
        raise HTTPException(status_code=500, detail=f"Ошибка отметки платежа: {str(e)}")


@app.get("/api/crm/cards/{card_id}/submitted-stages")
async def get_submitted_stages(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить отправленные стадии карточки"""
    stages = db.query(StageExecutor).filter(
        StageExecutor.crm_card_id == card_id,
        StageExecutor.submitted_date != None
    ).all()

    return [{
        'id': s.id,
        'stage_name': s.stage_name,
        'executor_id': s.executor_id,
        'executor_name': s.executor.full_name if s.executor else None,
        'submitted_date': s.submitted_date.isoformat() if s.submitted_date else None,
        'completed': s.completed,
        'completed_date': s.completed_date.isoformat() if s.completed_date else None,
    } for s in stages]


@app.get("/api/crm/cards/{card_id}/stage-history")
async def get_stage_history(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить историю стадий карточки"""
    # История из ActionHistory для данной карточки
    history = db.query(ActionHistory).filter(
        ActionHistory.entity_type == 'stage_executor',
        ActionHistory.entity_id == card_id
    ).order_by(ActionHistory.action_date.desc()).all()

    return [{
        'id': h.id,
        'action_type': h.action_type,
        'old_value': h.old_value,
        'new_value': h.new_value,
        'action_date': h.action_date.isoformat() if h.action_date else None,
        'user_id': h.user_id
    } for h in history]


@app.get("/api/supervision/addresses")
async def get_supervision_addresses(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить адреса надзора"""
    try:
        result = db.query(Contract.address).join(
            SupervisionCard, SupervisionCard.contract_id == Contract.id
        ).distinct().filter(
            Contract.address != None,
            Contract.address != ''
        ).all()
        return [r[0] for r in result if r[0]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@app.get("/api/supervision/cards/{card_id}/contract")
async def get_contract_id_by_supervision_card(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить ID договора по ID карточки надзора"""
    card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка надзора не найдена")
    return {"contract_id": card.contract_id}


@app.get("/api/statistics/projects")
async def get_project_statistics(
    project_type: str,
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    agent_type: Optional[str] = None,
    city: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статистику проектов"""
    try:
        from sqlalchemy import func, extract

        query = db.query(Contract).filter(Contract.project_type == project_type)

        if year:
            query = query.filter(extract('year', Contract.created_at) == year)
        if month:
            query = query.filter(extract('month', Contract.created_at) == month)
        if quarter:
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            query = query.filter(extract('month', Contract.created_at).between(start_month, end_month))
        if agent_type and agent_type != 'Все':
            query = query.filter(Contract.agent_type == agent_type)
        if city and city != 'Все':
            query = query.filter(Contract.city == city)

        contracts = query.all()

        total_count = len(contracts)
        total_area = sum(c.area or 0 for c in contracts)
        total_amount = sum(c.total_amount or 0 for c in contracts)

        active_count = len([c for c in contracts if c.status not in ['СДАН', 'РАСТОРГНУТ']])
        completed_count = len([c for c in contracts if c.status == 'СДАН'])
        cancelled_count = len([c for c in contracts if c.status == 'РАСТОРГНУТ'])

        return {
            'project_type': project_type,
            'total_count': total_count,
            'total_area': total_area,
            'total_amount': total_amount,
            'active_count': active_count,
            'completed_count': completed_count,
            'cancelled_count': cancelled_count,
            'overdue_count': 0  # TODO: реализовать подсчет просроченных
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")


@app.get("/api/statistics/supervision")
async def get_supervision_statistics(
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    agent_type: Optional[str] = None,
    city: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статистику авторского надзора"""
    try:
        from sqlalchemy import extract

        query = db.query(SupervisionCard).join(Contract)

        if year:
            query = query.filter(extract('year', SupervisionCard.created_at) == year)
        if month:
            query = query.filter(extract('month', SupervisionCard.created_at) == month)
        if quarter:
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            query = query.filter(extract('month', SupervisionCard.created_at).between(start_month, end_month))
        if agent_type and agent_type != 'Все':
            query = query.filter(Contract.agent_type == agent_type)
        if city and city != 'Все':
            query = query.filter(Contract.city == city)

        cards = query.all()

        total_count = len(cards)
        active_count = len([c for c in cards if c.contract.status == 'АВТОРСКИЙ НАДЗОР'])
        completed_count = len([c for c in cards if c.contract.status == 'СДАН'])
        paused_count = len([c for c in cards if c.is_paused])

        return {
            'total_count': total_count,
            'active_count': active_count,
            'completed_count': completed_count,
            'paused_count': paused_count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики надзора: {str(e)}")


@app.get("/api/statistics/supervision/filtered")
async def get_supervision_statistics_filtered(
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    agent_type: Optional[str] = None,
    city: Optional[str] = None,
    address: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить отфильтрованную статистику надзора"""
    try:
        from sqlalchemy import extract

        query = db.query(SupervisionCard).join(Contract)

        if year:
            query = query.filter(extract('year', SupervisionCard.created_at) == year)
        if month:
            query = query.filter(extract('month', SupervisionCard.created_at) == month)
        if quarter:
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            query = query.filter(extract('month', SupervisionCard.created_at).between(start_month, end_month))
        if agent_type and agent_type != 'Все':
            query = query.filter(Contract.agent_type == agent_type)
        if city and city != 'Все':
            query = query.filter(Contract.city == city)
        if address:
            query = query.filter(Contract.address.ilike(f'%{address}%'))

        cards = query.all()

        total_count = len(cards)
        total_area = sum(c.contract.area or 0 for c in cards)

        return {
            'total_count': total_count,
            'total_area': total_area,
            'cards': [{
                'id': c.id,
                'contract_number': c.contract.contract_number,
                'address': c.contract.address,
                'area': c.contract.area,
                'status': c.contract.status
            } for c in cards]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")


# =========================
# RATES EXTENDED ENDPOINTS
# =========================

@app.get("/api/rates/template")
async def get_template_rates(
    role: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить шаблонные тарифы"""
    query = db.query(Rate).filter(Rate.project_type == 'Шаблонный')
    if role:
        query = query.filter(Rate.role == role)
    return query.all()


@app.post("/api/rates/template")
async def save_template_rate(
    data: TemplateRateRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Сохранить шаблонный тариф"""
    try:
        # Проверяем существующий тариф
        existing = db.query(Rate).filter(
            Rate.project_type == 'Шаблонный',
            Rate.role == data.role,
            Rate.area_from == data.area_from,
            Rate.area_to == data.area_to
        ).first()

        if existing:
            existing.price = data.price
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            rate = Rate(
                project_type='Шаблонный',
                role=data.role,
                area_from=data.area_from,
                area_to=data.area_to,
                price=data.price
            )
            db.add(rate)
            db.commit()
            db.refresh(rate)
            return rate

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения тарифа: {str(e)}")


@app.post("/api/rates/individual")
async def save_individual_rate(
    data: IndividualRateRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Сохранить индивидуальный тариф"""
    try:
        # Проверяем существующий тариф
        query = db.query(Rate).filter(
            Rate.project_type == 'Индивидуальный',
            Rate.role == data.role
        )
        if data.stage_name:
            query = query.filter(Rate.stage_name == data.stage_name)

        existing = query.first()

        if existing:
            existing.rate_per_m2 = data.rate_per_m2
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            rate = Rate(
                project_type='Индивидуальный',
                role=data.role,
                rate_per_m2=data.rate_per_m2,
                stage_name=data.stage_name
            )
            db.add(rate)
            db.commit()
            db.refresh(rate)
            return rate

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения тарифа: {str(e)}")


@app.delete("/api/rates/individual")
async def delete_individual_rate(
    role: str,
    stage_name: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить индивидуальный тариф"""
    try:
        query = db.query(Rate).filter(
            Rate.project_type == 'Индивидуальный',
            Rate.role == role
        )
        if stage_name:
            query = query.filter(Rate.stage_name == stage_name)

        deleted = query.delete()
        db.commit()

        return {"status": "success", "deleted_count": deleted}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления тарифа: {str(e)}")


@app.post("/api/rates/supervision")
async def save_supervision_rate(
    data: SupervisionRateRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Сохранить тариф надзора"""
    try:
        # Ищем существующий тариф
        existing = db.query(Rate).filter(
            Rate.project_type == 'Авторский надзор',
            Rate.stage_name == data.stage_name
        ).first()

        if existing:
            existing.executor_rate = data.executor_rate
            existing.manager_rate = data.manager_rate
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            rate = Rate(
                project_type='Авторский надзор',
                stage_name=data.stage_name,
                executor_rate=data.executor_rate,
                manager_rate=data.manager_rate
            )
            db.add(rate)
            db.commit()
            db.refresh(rate)
            return rate

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения тарифа: {str(e)}")


@app.post("/api/rates/surveyor")
async def save_surveyor_rate(
    data: SurveyorRateRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Сохранить тариф замерщика"""
    try:
        existing = db.query(Rate).filter(
            Rate.role == 'Замерщик',
            Rate.city == data.city
        ).first()

        if existing:
            existing.price = data.price
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            rate = Rate(
                role='Замерщик',
                city=data.city,
                price=data.price
            )
            db.add(rate)
            db.commit()
            db.refresh(rate)
            return rate

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения тарифа: {str(e)}")


@app.get("/api/agents")
async def get_all_agents(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список всех агентов"""
    agents = db.query(Employee).filter(
        or_(
            Employee.position == 'Агент',
            Employee.secondary_position == 'Агент'
        )
    ).all()
    return agents


@app.get("/api/reports/employee")
async def get_employee_report_data(
    employee_id: int,
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить данные для отчета сотрудника"""
    try:
        from sqlalchemy import extract

        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")

        # Получаем назначения на стадии
        stage_query = db.query(StageExecutor).filter(StageExecutor.executor_id == employee_id)
        if year:
            stage_query = stage_query.filter(extract('year', StageExecutor.assigned_date) == year)
        if month:
            stage_query = stage_query.filter(extract('month', StageExecutor.assigned_date) == month)

        stages = stage_query.all()

        # Получаем платежи
        payment_query = db.query(Payment).filter(Payment.employee_id == employee_id)
        if year and month:
            report_month = f"{year}-{month:02d}"
            payment_query = payment_query.filter(Payment.report_month == report_month)

        payments = payment_query.all()

        total_stages = len(stages)
        completed_stages = len([s for s in stages if s.completed])
        total_payments = sum(p.final_amount or 0 for p in payments)

        return {
            'employee_id': employee_id,
            'employee_name': employee.full_name,
            'position': employee.position,
            'total_stages': total_stages,
            'completed_stages': completed_stages,
            'completion_rate': (completed_stages / total_stages * 100) if total_stages > 0 else 0,
            'total_payments': total_payments,
            'stages': [{
                'id': s.id,
                'stage_name': s.stage_name,
                'completed': s.completed,
                'assigned_date': s.assigned_date.isoformat() if s.assigned_date else None,
                'completed_date': s.completed_date.isoformat() if s.completed_date else None,
            } for s in stages],
            'payments': [{
                'id': p.id,
                'payment_type': p.payment_type,
                'amount': float(p.final_amount) if p.final_amount else 0,
                'report_month': p.report_month,
                'is_paid': p.is_paid
            } for p in payments]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения отчета: {str(e)}")


@app.post("/api/supervision/cards/{card_id}/history")
async def add_supervision_history(
    card_id: int,
    entry_type: str,
    message: str,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Добавить запись в историю надзора"""
    try:
        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        history = SupervisionProjectHistory(
            supervision_card_id=card_id,
            entry_type=entry_type,
            message=message,
            created_by=current_user.id
        )
        db.add(history)
        db.commit()
        db.refresh(history)

        return {
            'id': history.id,
            'supervision_card_id': history.supervision_card_id,
            'entry_type': history.entry_type,
            'message': history.message,
            'created_at': history.created_at.isoformat() if history.created_at else None,
            'created_by': history.created_by
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка добавления истории: {str(e)}")


@app.get("/api/payments")
async def get_all_payments(
    year: Optional[int] = None,
    payment_type: Optional[str] = None,
    month: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить все платежи с фильтрами"""
    try:
        from sqlalchemy import extract

        query = db.query(Payment)

        if year:
            query = query.filter(extract('year', Payment.created_at) == year)
        if month:
            query = query.filter(extract('month', Payment.created_at) == month)
        if payment_type:
            query = query.filter(Payment.payment_type == payment_type)

        payments = query.all()

        result = []
        for p in payments:
            employee = db.query(Employee).filter(Employee.id == p.employee_id).first()
            result.append({
                'id': p.id,
                'contract_id': p.contract_id,
                'crm_card_id': p.crm_card_id,
                'supervision_card_id': p.supervision_card_id,
                'employee_id': p.employee_id,
                'employee_name': employee.full_name if employee else 'Неизвестный',
                'role': p.role,
                'stage_name': p.stage_name,
                'calculated_amount': float(p.calculated_amount) if p.calculated_amount else 0,
                'final_amount': float(p.final_amount) if p.final_amount else 0,
                'payment_type': p.payment_type,
                'report_month': p.report_month,
                'is_paid': p.is_paid,
                'created_at': p.created_at.isoformat() if p.created_at else None,
            })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения платежей: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

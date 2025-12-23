"""
FastAPI приложение - главный файл
REST API для многопользовательской CRM
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from config import get_settings
from database import get_db, init_db, Employee, Client, Contract, Notification, UserSession, ActivityLog
from schemas import (
    LoginRequest, TokenResponse,
    EmployeeResponse, EmployeeCreate, EmployeeUpdate,
    ClientResponse, ClientCreate, ClientUpdate,
    ContractResponse, ContractCreate, ContractUpdate,
    NotificationResponse, SyncRequest, SyncResponse
)
from auth import (
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
    access_token = create_access_token(data={"sub": employee.id})

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

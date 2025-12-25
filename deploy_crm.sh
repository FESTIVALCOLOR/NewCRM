#!/bin/bash
# Скрипт автоматического развертывания CRM на сервере
# Выполнить на сервере: bash deploy_crm.sh

set -e  # Остановить при ошибке

echo "=========================================="
echo "Развертывание CRM интеграции"
echo "=========================================="
echo ""

# Шаг 1: Проверка текущей директории
echo "[1/6] Проверка рабочей директории..."
if [ ! -d "/opt/interior_studio/server" ]; then
    echo "ОШИБКА: Директория /opt/interior_studio/server не найдена!"
    exit 1
fi
cd /opt/interior_studio
echo "✓ Директория: $(pwd)"
echo ""

# Шаг 2: Создание резервных копий
echo "[2/6] Создание резервных копий..."
cp server/database.py server/database.py.backup.$(date +%Y%m%d_%H%M%S)
cp server/schemas.py server/schemas.py.backup.$(date +%Y%m%d_%H%M%S)
cp server/main.py server/main.py.backup.$(date +%Y%m%d_%H%M%S)
echo "✓ Резервные копии созданы"
echo ""

# Шаг 3: Добавление моделей в database.py
echo "[3/6] Обновление server/database.py..."
cat >> server/database.py << 'MODELS_EOF'

# =========================
# CRM КАРТОЧКИ
# =========================

class CRMCard(Base):
    __tablename__ = "crm_cards"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    column_name = Column(String, nullable=False)
    deadline = Column(Date, nullable=True)
    tags = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=False)

    # Менеджеры и исполнители
    senior_manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    sdp_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    gap_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    surveyor_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # Дополнительные поля
    approval_deadline = Column(Date, nullable=True)
    approval_stages = Column(Text, nullable=True)
    project_data_link = Column(Text, nullable=True)
    tech_task_file = Column(Text, nullable=True)
    tech_task_date = Column(Date, nullable=True)
    survey_date = Column(Date, nullable=True)

    # Метаданные
    order_position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contract = relationship("Contract", back_populates="crm_card")
    senior_manager = relationship("Employee", foreign_keys=[senior_manager_id])
    sdp = relationship("Employee", foreign_keys=[sdp_id])
    gap = relationship("Employee", foreign_keys=[gap_id])
    manager = relationship("Employee", foreign_keys=[manager_id])
    surveyor = relationship("Employee", foreign_keys=[surveyor_id])
    stage_executors = relationship("StageExecutor", back_populates="crm_card", cascade="all, delete-orphan")


class StageExecutor(Base):
    __tablename__ = "stage_executors"

    id = Column(Integer, primary_key=True, index=True)
    crm_card_id = Column(Integer, ForeignKey("crm_cards.id"), nullable=False)
    stage_name = Column(String, nullable=False)
    executor_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("employees.id"), nullable=False)

    # Даты
    assigned_date = Column(DateTime, default=datetime.utcnow)
    deadline = Column(Date, nullable=True)
    submitted_date = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)
    completed_date = Column(DateTime, nullable=True)

    # Relationships
    crm_card = relationship("CRMCard", back_populates="stage_executors")
    executor = relationship("Employee", foreign_keys=[executor_id])
    assigner = relationship("Employee", foreign_keys=[assigned_by])
MODELS_EOF

echo "✓ Модели добавлены в database.py"
echo ""

# Шаг 4: Добавление схем в schemas.py
echo "[4/6] Обновление server/schemas.py..."
cat >> server/schemas.py << 'SCHEMAS_EOF'


# =========================
# CRM КАРТОЧКИ
# =========================

class CRMCardBase(BaseModel):
    contract_id: int
    column_name: str
    deadline: Optional[str] = None
    tags: Optional[str] = None
    is_approved: bool = False
    senior_manager_id: Optional[int] = None
    sdp_id: Optional[int] = None
    gap_id: Optional[int] = None
    manager_id: Optional[int] = None
    surveyor_id: Optional[int] = None
    approval_deadline: Optional[str] = None
    approval_stages: Optional[str] = None
    project_data_link: Optional[str] = None
    tech_task_file: Optional[str] = None
    tech_task_date: Optional[str] = None
    survey_date: Optional[str] = None
    order_position: int = 0


class CRMCardCreate(CRMCardBase):
    pass


class CRMCardUpdate(BaseModel):
    column_name: Optional[str] = None
    deadline: Optional[str] = None
    tags: Optional[str] = None
    is_approved: Optional[bool] = None
    senior_manager_id: Optional[int] = None
    sdp_id: Optional[int] = None
    gap_id: Optional[int] = None
    manager_id: Optional[int] = None
    surveyor_id: Optional[int] = None
    approval_deadline: Optional[str] = None
    approval_stages: Optional[str] = None
    project_data_link: Optional[str] = None
    tech_task_file: Optional[str] = None
    tech_task_date: Optional[str] = None
    survey_date: Optional[str] = None
    order_position: Optional[int] = None


class ColumnMoveRequest(BaseModel):
    column_name: str


class StageExecutorCreate(BaseModel):
    stage_name: str
    executor_id: int
    deadline: Optional[str] = None


class StageExecutorUpdate(BaseModel):
    deadline: Optional[str] = None
    submitted_date: Optional[datetime] = None
    completed: Optional[bool] = None
    completed_date: Optional[datetime] = None
SCHEMAS_EOF

echo "✓ Схемы добавлены в schemas.py"
echo ""

# Шаг 5: Создание таблиц в PostgreSQL
echo "[5/6] Создание таблиц в PostgreSQL..."
docker exec -i interior_studio-db-1 psql -U interior_admin -d interior_studio_db << 'SQL_EOF'
-- Таблица CRM карточек
CREATE TABLE IF NOT EXISTS crm_cards (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    column_name VARCHAR(100) NOT NULL,
    deadline DATE,
    tags TEXT,
    is_approved BOOLEAN DEFAULT FALSE,
    senior_manager_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    sdp_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    gap_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    manager_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    surveyor_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    approval_deadline DATE,
    approval_stages TEXT,
    project_data_link TEXT,
    tech_task_file TEXT,
    tech_task_date DATE,
    survey_date DATE,
    order_position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_crm_cards_contract_id ON crm_cards(contract_id);
CREATE INDEX IF NOT EXISTS idx_crm_cards_column_name ON crm_cards(column_name);

-- Таблица исполнителей стадий
CREATE TABLE IF NOT EXISTS stage_executors (
    id SERIAL PRIMARY KEY,
    crm_card_id INTEGER NOT NULL REFERENCES crm_cards(id) ON DELETE CASCADE,
    stage_name VARCHAR(100) NOT NULL,
    executor_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    assigned_by INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deadline DATE,
    submitted_date TIMESTAMP,
    completed BOOLEAN DEFAULT FALSE,
    completed_date TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stage_executors_crm_card_id ON stage_executors(crm_card_id);

-- Триггер для updated_at
CREATE OR REPLACE FUNCTION update_crm_cards_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_crm_cards_updated_at
    BEFORE UPDATE ON crm_cards
    FOR EACH ROW
    EXECUTE FUNCTION update_crm_cards_updated_at();

\d crm_cards
\d stage_executors
SQL_EOF

echo "✓ Таблицы созданы в PostgreSQL"
echo ""

# Шаг 6: Перезапуск Docker
echo "[6/6] Перезапуск Docker контейнеров..."
docker-compose build api
docker-compose down
docker-compose up -d
echo "✓ Docker контейнеры перезапущены"
echo ""

# Проверка статуса
echo "=========================================="
echo "Проверка статуса..."
echo "=========================================="
sleep 5
docker-compose ps
echo ""

echo "=========================================="
echo "✓ Развертывание завершено!"
echo "=========================================="
echo ""
echo "Проверьте логи: docker-compose logs -f api"
echo "Тестирование: curl -k https://localhost/api/crm/cards?project_type=Индивидуальный"

-- SQL миграция для создания таблиц crm_cards и stage_executors в PostgreSQL

-- Таблица CRM карточек
CREATE TABLE IF NOT EXISTS crm_cards (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    column_name VARCHAR(100) NOT NULL,
    deadline DATE,
    tags TEXT,
    is_approved BOOLEAN DEFAULT FALSE,

    -- Менеджеры
    senior_manager_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    sdp_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    gap_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    manager_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    surveyor_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,

    -- Дополнительные поля
    approval_deadline DATE,
    approval_stages TEXT,  -- JSON строка
    project_data_link TEXT,
    tech_task_file TEXT,
    tech_task_date DATE,
    survey_date DATE,

    -- Метаданные
    order_position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для crm_cards
CREATE INDEX IF NOT EXISTS idx_crm_cards_contract_id ON crm_cards(contract_id);
CREATE INDEX IF NOT EXISTS idx_crm_cards_column_name ON crm_cards(column_name);
CREATE INDEX IF NOT EXISTS idx_crm_cards_senior_manager_id ON crm_cards(senior_manager_id);

-- Таблица исполнителей стадий
CREATE TABLE IF NOT EXISTS stage_executors (
    id SERIAL PRIMARY KEY,
    crm_card_id INTEGER NOT NULL REFERENCES crm_cards(id) ON DELETE CASCADE,
    stage_name VARCHAR(100) NOT NULL,
    executor_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    assigned_by INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,

    -- Даты
    assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deadline DATE,
    submitted_date TIMESTAMP,
    completed BOOLEAN DEFAULT FALSE,
    completed_date TIMESTAMP
);

-- Индексы для stage_executors
CREATE INDEX IF NOT EXISTS idx_stage_executors_crm_card_id ON stage_executors(crm_card_id);
CREATE INDEX IF NOT EXISTS idx_stage_executors_executor_id ON stage_executors(executor_id);
CREATE INDEX IF NOT EXISTS idx_stage_executors_stage_name ON stage_executors(stage_name);

-- Триггер для автоматического обновления updated_at
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

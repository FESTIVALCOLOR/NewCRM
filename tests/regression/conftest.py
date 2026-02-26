# -*- coding: utf-8 -*-
"""
Фикстуры для regression-тестов Interior Studio CRM.

Предоставляет:
- mock_db: временная SQLite БД с реальной production-схемой
- mock_api_client: замоканный API-клиент (без зависимостей от PyQt5)
- regression_logger: настроенный логгер для regression-тестов
"""

import json
import logging
import sqlite3
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, MagicMock

import pytest

# Добавляем корень проекта в sys.path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# ФИКСТУРА: mock_db — временная SQLite БД с реальной production-схемой
# ============================================================================

@pytest.fixture
def mock_db(tmp_path):
    """
    Создаёт временную SQLite БД с полной production-схемой.

    Включает все таблицы: employees, clients, contracts, crm_cards,
    supervision_cards, payments, offline_queue, action_history и др.

    Возвращает объект sqlite3.Connection с row_factory = sqlite3.Row.
    """
    db_path = tmp_path / "regression_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript('''
        -- Сотрудники
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            password TEXT,
            password_hash TEXT,
            full_name TEXT NOT NULL,
            position TEXT,
            department TEXT,
            role TEXT DEFAULT 'user',
            is_active INTEGER DEFAULT 1,
            status TEXT DEFAULT 'активный',
            phone TEXT,
            email TEXT,
            address TEXT,
            birth_date TEXT,
            secondary_position TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Клиенты
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_type TEXT NOT NULL DEFAULT 'Физическое лицо',
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            passport_series TEXT,
            passport_number TEXT,
            passport_issued_by TEXT,
            passport_issued_date TEXT,
            registration_address TEXT,
            organization_type TEXT,
            organization_name TEXT,
            inn TEXT,
            ogrn TEXT,
            account_details TEXT,
            responsible_person TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Договоры
        CREATE TABLE contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_number TEXT UNIQUE NOT NULL,
            client_id INTEGER NOT NULL,
            project_type TEXT NOT NULL,
            project_subtype TEXT,
            floors INTEGER DEFAULT 1,
            agent_type TEXT,
            city TEXT,
            address TEXT,
            area REAL DEFAULT 0,
            total_amount REAL DEFAULT 0,
            advance_payment REAL DEFAULT 0,
            additional_payment REAL DEFAULT 0,
            third_payment REAL DEFAULT 0,
            contract_date TEXT,
            contract_period INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Новый заказ',
            termination_reason TEXT,
            status_changed_date DATE,
            comments TEXT,
            contract_file_link TEXT,
            tech_task_link TEXT,
            tech_task_file_name TEXT,
            tech_task_yandex_path TEXT,
            measurement_image_link TEXT,
            measurement_file_name TEXT,
            measurement_yandex_path TEXT,
            measurement_date TEXT,
            yandex_folder_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        -- CRM карточки
        CREATE TABLE crm_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER UNIQUE NOT NULL,
            column_name TEXT NOT NULL DEFAULT 'Новый заказ',
            priority TEXT DEFAULT 'Средний',
            deadline DATE,
            approval_deadline DATE,
            approval_stages TEXT,
            project_data_link TEXT,
            tags TEXT,
            is_approved INTEGER DEFAULT 0,
            on_pause INTEGER DEFAULT 0,
            pause_date TEXT,
            column_before_pause TEXT,
            senior_manager_id INTEGER,
            sdp_id INTEGER,
            gap_id INTEGER,
            manager_id INTEGER,
            surveyor_id INTEGER,
            order_position INTEGER DEFAULT 0,
            tech_task_file TEXT,
            tech_task_date TEXT,
            measurement_file TEXT,
            measurement_date TEXT,
            survey_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE
        );

        -- Карточки авторского надзора
        CREATE TABLE supervision_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER UNIQUE NOT NULL,
            column_name TEXT NOT NULL DEFAULT 'Новый заказ',
            dan_id INTEGER,
            dan_completed INTEGER DEFAULT 0,
            is_paused INTEGER DEFAULT 0,
            pause_reason TEXT,
            paused_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE
        );

        -- Исполнители этапов
        CREATE TABLE stage_executors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crm_card_id INTEGER NOT NULL,
            stage_name TEXT NOT NULL,
            executor_id INTEGER NOT NULL,
            executor_type TEXT,
            role TEXT,
            assigned_by INTEGER,
            assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deadline DATE,
            completed INTEGER DEFAULT 0,
            completed_date TIMESTAMP,
            submitted_date TIMESTAMP,
            FOREIGN KEY (crm_card_id) REFERENCES crm_cards(id) ON DELETE CASCADE,
            FOREIGN KEY (executor_id) REFERENCES employees(id)
        );

        -- Платежи
        CREATE TABLE payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER,
            crm_card_id INTEGER,
            supervision_card_id INTEGER,
            employee_id INTEGER,
            role TEXT,
            stage_name TEXT,
            payment_type TEXT,
            calculated_amount REAL DEFAULT 0,
            manual_amount REAL,
            final_amount REAL DEFAULT 0,
            is_manual INTEGER DEFAULT 0,
            payment_status TEXT DEFAULT 'pending',
            is_paid INTEGER DEFAULT 0,
            report_month TEXT,
            reassigned INTEGER DEFAULT 0,
            old_employee_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id),
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        );

        -- Оклады
        CREATE TABLE salaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            amount REAL DEFAULT 0,
            report_month TEXT,
            payment_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        );

        -- Тарифы
        CREATE TABLE rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rate_type TEXT NOT NULL,
            role TEXT,
            stage_name TEXT,
            area_from REAL,
            area_to REAL,
            price REAL,
            executor_rate REAL,
            manager_rate REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Offline-очередь
        CREATE TABLE offline_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            data TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            sync_attempts INTEGER DEFAULT 0,
            last_error TEXT,
            signature TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            synced_at TIMESTAMP
        );

        -- История действий
        CREATE TABLE action_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            user_id INTEGER,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Справочник городов
        CREATE TABLE cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'активный',
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Файлы проектов
        CREATE TABLE project_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER NOT NULL,
            stage TEXT,
            file_type TEXT,
            public_link TEXT,
            yandex_path TEXT,
            file_name TEXT,
            preview_cache_path TEXT,
            variation INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE
        );
    ''')
    conn.commit()
    yield conn
    conn.close()


# ============================================================================
# ФИКСТУРА: mock_api_client — замоканный API-клиент
# ============================================================================

@pytest.fixture
def mock_api_client():
    """
    Замоканный API-клиент для regression-тестов.

    Предоставляет стандартные ответы на GET/POST/PUT/DELETE запросы
    без зависимости от PyQt5 и реальной сети.
    """
    client = MagicMock()

    # Стандартные успешные ответы
    client.is_online = True

    # GET-запросы возвращают пустой список по умолчанию
    client.get.return_value = Mock(
        status_code=200,
        json=Mock(return_value=[]),
        text="[]",
        ok=True,
    )

    # POST-запросы возвращают id созданного объекта
    client.post.return_value = Mock(
        status_code=201,
        json=Mock(return_value={"id": 1}),
        text='{"id": 1}',
        ok=True,
    )

    # PUT-запросы возвращают успех
    client.put.return_value = Mock(
        status_code=200,
        json=Mock(return_value={"updated": True}),
        text='{"updated": true}',
        ok=True,
    )

    # DELETE-запросы возвращают успех
    client.delete.return_value = Mock(
        status_code=200,
        json=Mock(return_value={"deleted": True}),
        text='{"deleted": true}',
        ok=True,
    )

    # Имитация ошибок
    def make_timeout():
        """Имитирует APITimeoutError"""
        from utils.api_client.exceptions import APITimeoutError
        raise APITimeoutError("Таймаут соединения")

    def make_connection_error():
        """Имитирует APIConnectionError"""
        from utils.api_client.exceptions import APIConnectionError
        raise APIConnectionError("Сервер недоступен")

    def make_business_error(status_code=400, message="Ошибка валидации"):
        """Имитирует бизнес-ошибку"""
        from utils.api_client.exceptions import APIResponseError
        raise APIResponseError(message, status_code=status_code)

    client.simulate_timeout = make_timeout
    client.simulate_connection_error = make_connection_error
    client.simulate_business_error = make_business_error

    return client


# ============================================================================
# ФИКСТУРА: regression_logger — логгер для regression-тестов
# ============================================================================

@pytest.fixture
def regression_logger(tmp_path):
    """
    Настроенный логгер для regression-тестов.

    Пишет в файл regression_test.log во временной директории.
    Возвращает объект logging.Logger.
    """
    log_file = tmp_path / "regression_test.log"
    logger = logging.getLogger(f"regression_{id(tmp_path)}")
    logger.setLevel(logging.DEBUG)

    # Убираем старые хэндлеры, чтобы не было дублей между тестами
    logger.handlers.clear()

    handler = logging.FileHandler(str(log_file), encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.log_file = log_file  # Доступ к файлу лога из теста
    yield logger

    handler.close()
    logger.removeHandler(handler)

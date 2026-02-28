# -*- coding: utf-8 -*-
"""
pytest-qt offscreen конфигурация для UI тестов Interior Studio CRM.

Все тесты запускаются в headless режиме (QT_QPA_PLATFORM=offscreen).
Каждый тест получает изолированную SQLite БД через tmp_path.
Production БД и сервер НЕ затрагиваются.
"""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# Добавить корень проекта в sys.path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from database.db_manager import DatabaseManager


# ========== Сброс debounce_click между тестами ==========

@pytest.fixture(autouse=True)
def _clear_debounce():
    """Сброс глобального состояния debounce_click между тестами."""
    from utils.button_debounce import _last_click_time
    _last_click_time.clear()
    yield
    _last_click_time.clear()


# ========== SAFETY NET: запрет доступа к production БД ==========

@pytest.fixture(autouse=True)
def _block_real_db(monkeypatch):
    """Блокирует создание DatabaseManager с реальным путём к production БД."""
    original_init = DatabaseManager.__init__

    def safe_init(self, *args, **kwargs):
        db_path = kwargs.get('db_path', args[0] if args else 'interior_studio.db')
        db_path_str = str(db_path).lower()
        # Разрешаем только tmp-пути и :memory:
        if db_path_str == ':memory:' or 'tmp' in db_path_str or 'temp' in db_path_str:
            original_init(self, *args, **kwargs)
        else:
            raise RuntimeError(
                f"ТЕСТ пытается открыть production БД: {db_path}. "
                f"Используйте фикстуру test_db(tmp_path) вместо прямого создания DatabaseManager."
            )

    monkeypatch.setattr(DatabaseManager, '__init__', safe_init)


@pytest.fixture(autouse=True)
def _block_real_api(monkeypatch):
    """Блокирует реальные HTTP-запросы к серверу из тестов."""
    import requests

    def blocked_request(*args, **kwargs):
        raise RuntimeError(
            "ТЕСТ пытается выполнить реальный HTTP-запрос. "
            "Используйте mock_data_access или mock API client."
        )

    monkeypatch.setattr(requests, 'get', blocked_request)
    monkeypatch.setattr(requests, 'post', blocked_request)
    monkeypatch.setattr(requests, 'put', blocked_request)
    monkeypatch.setattr(requests, 'delete', blocked_request)
    monkeypatch.setattr(requests, 'patch', blocked_request)


# ========== БАЗОВЫЕ ФИКСТУРЫ ==========

@pytest.fixture(scope="session")
def qapp():
    """Единственный экземпляр QApplication на всю сессию тестов."""
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def test_db(tmp_path):
    """Изолированная SQLite БД в tmp_path — удаляется после каждого теста."""
    import database.db_manager as dbm
    # Пропустить миграции в __init__ (таблиц ещё нет)
    dbm._migrations_completed = True
    db = DatabaseManager(db_path=str(tmp_path / "test.db"))
    # Создать все таблицы
    db.initialize_database()
    # Запустить все миграции на существующих таблицах
    # run_migrations пропускается если нет database/migrations.py,
    # поэтому вызываем миграции employees напрямую
    db.add_approval_deadline_field()
    db.add_approval_stages_field()
    db.create_approval_deadlines_table()
    db.add_project_data_link_field()
    db.add_third_payment_field()
    db.add_birth_date_column()
    db.add_address_column()
    db.add_secondary_position_column()
    db.add_status_changed_date_column()
    db.add_tech_task_fields()
    db.add_survey_date_column()
    db.create_supervision_table_migration()
    db.fix_supervision_cards_column_name()
    db.create_supervision_history_table()
    db.create_manager_acceptance_table()
    db.create_payments_system_tables()
    db.add_reassigned_field_to_payments()
    db.add_submitted_date_to_stage_executors()
    db.add_stage_field_to_payments()
    db.add_contract_file_columns()
    db.create_project_files_table()
    db.create_project_templates_table()
    db.create_timeline_tables()
    db.add_project_subtype_to_contracts()
    db.add_floors_to_contracts()
    db.create_stage_workflow_state_table()
    db.create_performance_indexes()
    dbm._migrations_completed = True
    yield db


@pytest.fixture
def data_access(test_db):
    """DataAccess с реальной tmp БД — все записи удаляются с tmp_path."""
    from utils.data_access import DataAccess
    da = DataAccess(api_client=None, db=test_db)
    yield da


@pytest.fixture
def mock_data_access():
    """Mock DataAccess — ничего не пишет в реальную БД."""
    da = MagicMock()
    # Списки
    da.get_all_clients.return_value = []
    da.get_all_contracts.return_value = []
    da.get_all_employees.return_value = []
    da.get_crm_cards.return_value = []
    da.get_supervision_cards_active.return_value = []
    da.get_supervision_cards_archived.return_value = []
    da.get_payments_for_contract.return_value = []
    da.get_project_timeline.return_value = []
    da.get_action_history.return_value = []
    da.get_supervision_history.return_value = []
    da.get_supervision_timeline.return_value = []
    # Создание
    da.create_client.return_value = {"id": 1}
    da.create_contract.return_value = {"id": 1}
    da.create_employee.return_value = {"id": 1}
    da.create_crm_card.return_value = {"id": 1}
    da.create_payment.return_value = {"id": 1}
    # Обновление
    da.update_client.return_value = {"id": 1}
    da.update_contract.return_value = {"id": 1}
    da.update_employee.return_value = {"id": 1}
    # Режим
    da.is_online = False
    da.db = MagicMock()
    return da


# ========== ФИКСТУРЫ РОЛЕЙ (9 должностей + 2 двойные роли) ==========

@pytest.fixture
def mock_employee_admin():
    """Руководитель студии — полный доступ"""
    return {"id": 1, "full_name": "Тестов Админ", "login": "admin",
            "position": "Руководитель студии", "secondary_position": "",
            "department": "Административный отдел",
            "status": "активный", "offline_mode": False}


@pytest.fixture
def mock_employee_senior_manager():
    """Старший менеджер проектов — полный доступ"""
    return {"id": 2, "full_name": "Старший Менеджер", "login": "sr_manager",
            "position": "Старший менеджер проектов", "secondary_position": "",
            "department": "Административный отдел",
            "status": "активный", "offline_mode": False}


@pytest.fixture
def mock_employee_sdp():
    """СДП — управленческий уровень"""
    return {"id": 3, "full_name": "СДП Тестов", "login": "sdp",
            "position": "СДП", "secondary_position": "",
            "department": "Проектный отдел",
            "status": "активный", "offline_mode": False}


@pytest.fixture
def mock_employee_gap():
    """ГАП — управленческий уровень"""
    return {"id": 4, "full_name": "ГАП Тестов", "login": "gap",
            "position": "ГАП", "secondary_position": "",
            "department": "Проектный отдел",
            "status": "активный", "offline_mode": False}


@pytest.fixture
def mock_employee_manager():
    """Менеджер — управленческий уровень"""
    return {"id": 5, "full_name": "Менеджер Тестов", "login": "manager",
            "position": "Менеджер", "secondary_position": "",
            "department": "Административный отдел",
            "status": "активный", "offline_mode": False}


@pytest.fixture
def mock_employee_designer():
    """Дизайнер — исполнительский уровень"""
    return {"id": 6, "full_name": "Дизайнеров Тест", "login": "designer",
            "position": "Дизайнер", "secondary_position": "",
            "department": "Проектный отдел",
            "status": "активный", "offline_mode": False}


@pytest.fixture
def mock_employee_draftsman():
    """Чертёжник — исполнительский уровень"""
    return {"id": 7, "full_name": "Чертёжник Тестов", "login": "draftsman",
            "position": "Чертёжник", "secondary_position": "",
            "department": "Исполнительный отдел",
            "status": "активный", "offline_mode": False}


@pytest.fixture
def mock_employee_surveyor():
    """Замерщик — исполнительский уровень"""
    return {"id": 8, "full_name": "Замерщик Тестов", "login": "surveyor",
            "position": "Замерщик", "secondary_position": "",
            "department": "Исполнительный отдел",
            "status": "активный", "offline_mode": False}


@pytest.fixture
def mock_employee_dan():
    """ДАН — надзор (read-only)"""
    return {"id": 9, "full_name": "ДАН Тестов", "login": "dan",
            "position": "ДАН", "secondary_position": "",
            "department": "Проектный отдел",
            "status": "активный", "offline_mode": False}


@pytest.fixture
def mock_employee_designer_manager():
    """Двойная роль: Дизайнер + Менеджер (расширенный доступ)"""
    return {"id": 10, "full_name": "Дизайнер-Менеджер", "login": "des_mgr",
            "position": "Дизайнер", "secondary_position": "Менеджер",
            "department": "Проектный отдел",
            "status": "активный", "offline_mode": False}


@pytest.fixture
def mock_employee_designer_draftsman():
    """Двойная роль: Дизайнер + Чертёжник (файлы всех стадий)"""
    return {"id": 11, "full_name": "Дизайнер-Чертёжник", "login": "des_draft",
            "position": "Дизайнер", "secondary_position": "Чертёжник",
            "department": "Проектный отдел",
            "status": "активный", "offline_mode": False}


# ========== ОБЩИЕ ФИКСТУРЫ ==========

@pytest.fixture
def parent_widget(qtbot, mock_data_access, mock_employee_admin):
    """Родительский виджет с mock данными для тестов вкладок."""
    from PyQt5.QtWidgets import QWidget
    w = QWidget()
    w.data = mock_data_access
    w.employee = mock_employee_admin
    w.db = mock_data_access.db
    w.api_client = None
    qtbot.addWidget(w)
    return w


@pytest.fixture
def sample_client_individual():
    """Тестовые данные: клиент физическое лицо"""
    return {
        "id": 100,
        "client_type": "Физическое лицо",
        "full_name": "Иванов Иван Иванович",
        "phone": "+7 (999) 123-45-67",
        "email": "ivanov@test.ru",
        "address": "г. Санкт-Петербург, ул. Тестовая, д.1",
        "passport_series": "4012",
        "passport_number": "123456",
        "passport_issued_by": "ОВД Тестового района",
        "passport_issue_date": "2020-01-15",
        "notes": "Тестовый клиент"
    }


@pytest.fixture
def sample_client_legal():
    """Тестовые данные: клиент юридическое лицо"""
    return {
        "id": 101,
        "client_type": "Юридическое лицо",
        "organization_name": "ООО Тест",
        "organization_type": "ООО",
        "inn": "7712345678",
        "ogrn": "1027700123456",
        "legal_address": "г. Москва, ул. Тестовая, д.2",
        "responsible_person": "Петров П.П.",
        "phone": "+7 (495) 987-65-43",
        "email": "info@test-company.ru"
    }


@pytest.fixture
def sample_contract_individual():
    """Тестовые данные: индивидуальный договор (поля как в fill_data)"""
    return {
        "id": 200,
        "contract_number": "ИП-ПОЛ-12345/26",
        "project_type": "Индивидуальный",
        "project_subtype": "Полный проект",
        "client_id": 100,
        "client_name": "Иванов Иван Иванович",
        "contract_date": "2026-01-15",
        "city": "СПБ",
        "address": "г. СПб, ул. Тестовая, д.1",
        "area": 85.5,
        "total_amount": 500000,
        "advance_payment": 150000,
        "additional_payment": 200000,
        "third_payment": 150000,
        "contract_period": 45,
        "agent_type": "",
        "status": "active"
    }


@pytest.fixture
def sample_contract_template():
    """Тестовые данные: шаблонный договор (поля как в fill_data)"""
    return {
        "id": 201,
        "contract_number": "ШП-СТДЗ-12346/26",
        "project_type": "Шаблонный",
        "project_subtype": "Стандарт",
        "client_id": 100,
        "client_name": "Иванов Иван Иванович",
        "contract_date": "2026-02-01",
        "city": "МСК",
        "address": "г. Москва, ул. Шаблонная, д.5",
        "area": 120,
        "total_amount": 300000,
        "advance_payment": 300000,
        "floors": 2,
        "contract_period": 30,
        "agent_type": "",
        "status": "active"
    }


@pytest.fixture
def sample_crm_card():
    """Тестовые данные: CRM карточка"""
    return {
        "id": 300,
        "contract_id": 200,
        "contract_number": "ИП-ПОЛ-12345/26",
        "contract_type": "Индивидуальный проект",
        "contract_subtype": "Полный проект",
        "client_name": "Иванов Иван Иванович",
        "address": "г. СПб, ул. Тестовая, д.1",
        "city": "СПБ",
        "area": 85.5,
        "column_name": "Новые",
        "agent_name": "",
        "survey_date": None,
        "tech_task_date": None,
        "yandex_folder_path": "",
        "status": "active"
    }


@pytest.fixture
def sample_employee():
    """Тестовые данные: сотрудник"""
    return {
        "id": 400,
        "full_name": "Тестовый Сотрудник",
        "login": "test_emp",
        "position": "Дизайнер",
        "secondary_position": "",
        "department": "Проектный отдел",
        "status": "активный",
        "salary": 50000,
        "hire_date": "2025-06-01"
    }


# ========== ХУКИ ДЛЯ ПРОГРЕСС-БАРА ==========

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Итоговая статистика после прогона."""
    passed = len(terminalreporter.stats.get('passed', []))
    failed = len(terminalreporter.stats.get('failed', []))
    errors = len(terminalreporter.stats.get('error', []))
    skipped = len(terminalreporter.stats.get('skipped', []))
    total = passed + failed + errors
    print(f"\n{'=' * 60}")
    print(f"  ИТОГО: {total} | Passed: {passed} | Failed: {failed} | Errors: {errors} | Skipped: {skipped}")
    if total > 0:
        pct = passed / total * 100
        bar_len = 40
        filled = int(bar_len * passed / total)
        bar = '#' * filled + '-' * (bar_len - filled)
        print(f"  [{bar}] {pct:.1f}%")
    print(f"{'=' * 60}")

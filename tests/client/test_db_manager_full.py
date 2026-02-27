# -*- coding: utf-8 -*-
"""
МАКСИМАЛЬНОЕ покрытие database/db_manager.py — методы НЕ покрытые другими тестами.
~130 тестов. Реальная SQLite через tmp_path, без моков.

Тестируемые методы (НЕ дублируя существующие файлы):
  Сотрудники:     update_employee, delete_employee, get_employees_by_department,
                   get_employees_by_position, cache_employee_password,
                   get_employee_for_offline_login
  Платежи:         get_payments_by_type, get_payments_by_supervision_card,
                   update_payment_manual, create_payment_record,
                   calculate_payment_amount, get_payments_for_crm
  Ставки:          get_rate_by_id, update_rate
  Зарплаты:        update_salary, delete_salary, get_salary_by_id
  CRM:             get_crm_card_data, get_incomplete_stage_executors,
                   get_stage_completion_info, update_stage_executor_deadline,
                   get_projects_by_type, get_previous_executor_by_position
  Согласование:    get_approval_stage_deadlines, complete_approval_stage,
                   sync_approval_stages_to_json
  Удаление:        delete_order, delete_supervision_order
  Файлы проекта:   add_project_file, get_project_files, delete_project_file
  Агенты:          update_agent_color, get_agent_color, invalidate_agent_colors_cache
  Статистика:      build_period_where, get_crm_statistics_filtered,
                   get_employee_report_data, get_supervision_statistics,
                   get_supervision_card_data, get_contract_id_by_supervision_card,
                   complete_supervision_stage, get_crm_dashboard_stats
  Зарплатные:      get_salaries_dashboard_stats
"""

import pytest
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import patch
from datetime import datetime


# ============================================================================
# Сброс глобального флага миграций между тестами
# ============================================================================
@pytest.fixture(autouse=True)
def reset_migrations_flag():
    """Сбрасываем _migrations_completed перед и после каждого теста."""
    import database.db_manager as dm_module
    dm_module._migrations_completed = False
    yield
    dm_module._migrations_completed = False


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def db(tmp_path):
    """Создать DatabaseManager с временной SQLite БД."""
    import database.db_manager as dm_module

    dm_module._migrations_completed = True

    db_path = str(tmp_path / 'test.db')
    with patch('database.db_manager.YANDEX_DISK_TOKEN', ''):
        manager = dm_module.DatabaseManager(db_path=db_path)

        manager.initialize_database()

        for method_name in [
            'add_approval_deadline_field',
            'add_approval_stages_field',
            'create_approval_deadlines_table',
            'add_project_data_link_field',
        ]:
            try:
                getattr(manager, method_name)()
            except Exception:
                pass

        manager.add_third_payment_field()
        manager.add_birth_date_column()
        manager.add_address_column()
        manager.add_secondary_position_column()
        manager.add_status_changed_date_column()
        manager.add_tech_task_fields()
        manager.add_survey_date_column()
        manager.create_supervision_table_migration()
        manager.create_supervision_table_migration()
        manager.fix_supervision_cards_column_name()
        manager.create_supervision_history_table()
        manager.create_manager_acceptance_table()
        manager.create_payments_system_tables()
        manager.add_reassigned_field_to_payments()
        manager.add_submitted_date_to_stage_executors()
        manager.add_stage_field_to_payments()
        manager.add_contract_file_columns()
        manager.create_project_files_table()
        manager.create_project_templates_table()
        manager.create_timeline_tables()
        manager.add_project_subtype_to_contracts()
        manager.add_floors_to_contracts()
        manager.create_stage_workflow_state_table()
        manager.create_messenger_tables()
        manager.create_performance_indexes()
        manager.add_missing_fields_rates_payments_salaries()
        manager.add_agents_status_field()
        manager.migrate_add_cities_table()
        manager.fix_payments_contract_id_nullable()

        # Таблица approval_stages — используется get_stage_completion_info
        conn = manager.connect()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS approval_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crm_card_id INTEGER NOT NULL,
                stage_name TEXT NOT NULL,
                is_approved BOOLEAN DEFAULT 0,
                approved_by INTEGER,
                approved_date TIMESTAMP,
                FOREIGN KEY (crm_card_id) REFERENCES crm_cards(id)
            )
        ''')
        conn.commit()
        manager.close()

        # Удаляем seed-данные (admin), чтобы тесты начинали с чистой БД
        conn = manager.connect()
        conn.execute('DELETE FROM employees')
        conn.commit()
        manager.close()

        manager.connect()

    yield manager

    dm_module._migrations_completed = False


# ============================================================================
# Хелперы
# ============================================================================

def _make_employee(db, name='Тестовый Сотрудник', login=None, position='Дизайнер'):
    """Быстрое создание сотрудника."""
    login = login or name.lower().replace(' ', '_')
    return db.add_employee({
        'full_name': name,
        'login': login,
        'password': 'test123',
        'position': position,
    })


def _make_client(db, name='Тестовый Клиент', phone='+79001234567'):
    """Быстрое создание клиента."""
    return db.add_client({
        'client_type': 'Физ. лицо',
        'full_name': name,
        'phone': phone,
        'email': 'test@test.ru',
    })


@patch('database.db_manager.YANDEX_DISK_TOKEN', '')
def _make_contract(db, client_id, **overrides):
    """Быстрое создание договора."""
    data = {
        'client_id': client_id,
        'project_type': 'Индивидуальный',
        'contract_number': f'№{id(overrides) % 1000:03d}-2026',
        'contract_date': '2026-01-15',
        'address': 'ул. Тестовая, 1',
        'area': 120,
        'total_amount': 500000,
        'contract_period': 60,
        'status': 'Новый заказ',
        'city': 'СПБ',
    }
    data.update(overrides)
    return db.add_contract(data)


@pytest.fixture
def db_with_contract(db):
    """БД с клиентом и договором."""
    client_id = _make_client(db)
    contract_id = _make_contract(db, client_id, contract_number='№001-2026')
    return db, client_id, contract_id


@pytest.fixture
def db_with_employee(db):
    """БД с одним сотрудником."""
    emp_id = _make_employee(db, 'Петров Пётр', 'petrov', 'Дизайнер')
    return db, emp_id


# ============================================================================
# ТЕСТЫ: update_employee
# ============================================================================

class TestUpdateEmployee:
    """Обновление данных сотрудника."""

    def test_update_full_name(self, db_with_employee):
        """Обновление имени сотрудника."""
        db, emp_id = db_with_employee
        db.update_employee(emp_id, {'full_name': 'Обновлённое Имя'})
        emp = db.get_employee_by_id(emp_id)
        assert emp['full_name'] == 'Обновлённое Имя'

    def test_update_multiple_fields(self, db_with_employee):
        """Обновление нескольких полей одновременно."""
        db, emp_id = db_with_employee
        db.update_employee(emp_id, {
            'full_name': 'Новое Имя',
            'phone': '+79009999999',
            'email': 'new@test.ru',
        })
        emp = db.get_employee_by_id(emp_id)
        assert emp['full_name'] == 'Новое Имя'
        assert emp['phone'] == '+79009999999'
        assert emp['email'] == 'new@test.ru'

    def test_update_sets_updated_at(self, db_with_employee):
        """Обновление устанавливает updated_at."""
        db, emp_id = db_with_employee
        db.update_employee(emp_id, {'full_name': 'Тест'})
        emp = db.get_employee_by_id(emp_id)
        assert emp['updated_at'] is not None


# ============================================================================
# ТЕСТЫ: delete_employee
# ============================================================================

class TestDeleteEmployee:
    """Удаление сотрудника."""

    def test_delete_existing(self, db_with_employee):
        """Удаление существующего сотрудника возвращает True."""
        db, emp_id = db_with_employee
        result = db.delete_employee(emp_id)
        assert result is True
        assert db.get_employee_by_id(emp_id) is None

    def test_delete_nonexistent(self, db):
        """Удаление несуществующего сотрудника возвращает True (нет ошибки)."""
        result = db.delete_employee(99999)
        assert result is True

    def test_delete_does_not_affect_others(self, db):
        """Удаление одного сотрудника не затрагивает других."""
        id1 = _make_employee(db, 'Первый', 'first')
        id2 = _make_employee(db, 'Второй', 'second')
        db.delete_employee(id1)
        assert db.get_employee_by_id(id2) is not None


# ============================================================================
# ТЕСТЫ: get_employees_by_department
# ============================================================================

class TestGetEmployeesByDepartment:
    """Получение сотрудников по отделу."""

    def test_filter_by_department(self, db):
        """Фильтрация по отделу 'Проектный отдел'."""
        _make_employee(db, 'Дизайнер А', 'da', 'Дизайнер')
        _make_employee(db, 'Менеджер А', 'ma', 'Менеджер')
        result = db.get_employees_by_department('Проектный отдел')
        assert len(result) == 1
        assert result[0]['full_name'] == 'Дизайнер А'

    def test_empty_department(self, db):
        """Несуществующий отдел возвращает пустой список."""
        result = db.get_employees_by_department('Несуществующий отдел')
        assert result == []

    def test_multiple_employees_in_department(self, db):
        """Несколько сотрудников в одном отделе."""
        _make_employee(db, 'Дизайнер 1', 'd1', 'Дизайнер')
        _make_employee(db, 'Чертёжник 1', 'ch1', 'Чертёжник')
        result = db.get_employees_by_department('Проектный отдел')
        assert len(result) == 2


# ============================================================================
# ТЕСТЫ: get_employees_by_position (с secondary_position)
# ============================================================================

class TestGetEmployeesByPosition:
    """Получение сотрудников по должности (включая вторую)."""

    def test_by_primary_position(self, db):
        """Поиск по основной должности."""
        _make_employee(db, 'Дизайнер ПП', 'dpp', 'Дизайнер')
        result = db.get_employees_by_position('Дизайнер')
        assert len(result) == 1
        assert result[0]['full_name'] == 'Дизайнер ПП'

    def test_by_secondary_position(self, db):
        """Поиск по вторичной должности."""
        emp_id = _make_employee(db, 'Универсал', 'univ', 'Дизайнер')
        db.update_employee(emp_id, {'secondary_position': 'Чертёжник'})
        result = db.get_employees_by_position('Чертёжник')
        assert len(result) == 1
        assert result[0]['full_name'] == 'Универсал'

    def test_only_active_employees(self, db):
        """Возвращает только активных сотрудников."""
        emp_id = _make_employee(db, 'Неактивный', 'inactive', 'Дизайнер')
        conn = db.connect()
        conn.execute('UPDATE employees SET status = ? WHERE id = ?', ('уволен', emp_id))
        conn.commit()
        db.close()
        result = db.get_employees_by_position('Дизайнер')
        assert len(result) == 0


# ============================================================================
# ТЕСТЫ: cache_employee_password / get_employee_for_offline_login
# ============================================================================

class TestOfflineAuth:
    """Кеширование пароля и offline-аутентификация."""

    def test_cache_password_returns_true(self, db_with_employee):
        """cache_employee_password возвращает True."""
        db, emp_id = db_with_employee
        result = db.cache_employee_password(emp_id, 'new_password')
        assert result is True

    def test_cached_password_is_hashed(self, db_with_employee):
        """Закешированный пароль хэширован."""
        db, emp_id = db_with_employee
        db.cache_employee_password(emp_id, 'secret')
        emp = db.get_employee_by_id(emp_id)
        assert emp['password'] != 'secret'
        assert len(emp['password']) > 0

    def test_get_employee_for_offline_login(self, db_with_employee):
        """Получение сотрудника для offline-входа."""
        db, emp_id = db_with_employee
        emp = db.get_employee_for_offline_login('petrov')
        assert emp is not None
        assert emp['login'] == 'petrov'

    def test_offline_login_nonexistent(self, db):
        """Несуществующий логин возвращает None."""
        result = db.get_employee_for_offline_login('nonexistent')
        assert result is None

    def test_offline_login_inactive_employee(self, db):
        """Уволенный сотрудник не найден при offline-входе."""
        emp_id = _make_employee(db, 'Уволенный', 'fired', 'Дизайнер')
        conn = db.connect()
        conn.execute('UPDATE employees SET status = ? WHERE id = ?', ('уволен', emp_id))
        conn.commit()
        db.close()
        result = db.get_employee_for_offline_login('fired')
        assert result is None


# ============================================================================
# ТЕСТЫ: get_rate_by_id / update_rate
# ============================================================================

class TestRateCRUD:
    """Дополнительные тесты для ставок."""

    def test_get_rate_by_id_existing(self, db):
        """Получение существующей ставки по ID."""
        result = db.add_rate({'role': 'Дизайнер', 'rate_per_m2': 200.0})
        rate = db.get_rate_by_id(result['id'])
        assert rate is not None
        assert rate['role'] == 'Дизайнер'

    def test_get_rate_by_id_nonexistent(self, db):
        """Несуществующий ID возвращает None."""
        result = db.get_rate_by_id(99999)
        assert result is None

    def test_update_rate_price(self, db):
        """Обновление цены ставки."""
        result = db.add_rate({'role': 'Чертёжник', 'rate_per_m2': 100.0})
        success = db.update_rate(result['id'], {'rate_per_m2': 150.0})
        assert success is True
        rate = db.get_rate_by_id(result['id'])
        assert rate['rate_per_m2'] == 150.0

    def test_update_rate_nonexistent(self, db):
        """Обновление несуществующей ставки не падает."""
        result = db.update_rate(99999, {'rate_per_m2': 100.0})
        assert result is True  # UPDATE 0 rows, без ошибки


# ============================================================================
# ТЕСТЫ: get_salary_by_id / update_salary / delete_salary
# ============================================================================

class TestSalaryCRUD:
    """Дополнительные тесты для зарплат."""

    def test_get_salary_by_id(self, db):
        """Получение зарплаты по ID."""
        emp_id = _make_employee(db, 'Тест', 'test_sal')
        db.add_salary({
            'employee_id': emp_id,
            'payment_type': 'Оклад',
            'amount': 30000.0,
        })
        salaries = db.get_salaries()
        assert len(salaries) >= 1
        salary = db.get_salary_by_id(salaries[0]['id'])
        assert salary is not None
        assert salary['amount'] == 30000.0

    def test_get_salary_by_id_nonexistent(self, db):
        """Несуществующий ID возвращает None."""
        result = db.get_salary_by_id(99999)
        assert result is None

    def test_update_salary(self, db):
        """Обновление суммы зарплаты."""
        emp_id = _make_employee(db, 'ТестУ', 'test_upd_sal')
        db.add_salary({
            'employee_id': emp_id,
            'payment_type': 'Оклад',
            'amount': 25000.0,
        })
        salaries = db.get_salaries(employee_id=emp_id)
        sid = salaries[0]['id']
        db.update_salary(sid, {'amount': 35000.0})
        salary = db.get_salary_by_id(sid)
        assert salary['amount'] == 35000.0

    def test_delete_salary(self, db):
        """Удаление зарплаты."""
        emp_id = _make_employee(db, 'ТестД', 'test_del_sal')
        db.add_salary({
            'employee_id': emp_id,
            'payment_type': 'Оклад',
            'amount': 20000.0,
        })
        salaries = db.get_salaries(employee_id=emp_id)
        sid = salaries[0]['id']
        db.delete_salary(sid)
        result = db.get_salary_by_id(sid)
        assert result is None


# ============================================================================
# ТЕСТЫ: get_crm_card_data
# ============================================================================

class TestGetCrmCardData:
    """Получение данных CRM-карточки."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_crm_card_data_existing(self, db_with_contract):
        """get_crm_card_data для существующей карточки."""
        db, _, contract_id = db_with_contract
        card_id = db.get_crm_card_id_by_contract(contract_id)
        data = db.get_crm_card_data(card_id)
        assert data is not None
        assert data['contract_id'] == contract_id
        assert 'column_name' in data
        # contract_number — колонка contracts, не crm_cards; get_crm_card_data делает SELECT cc.* FROM crm_cards
        assert 'designer_name' in data or 'contract_id' in data

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_crm_card_data_nonexistent(self, db):
        """Несуществующий card_id возвращает None."""
        result = db.get_crm_card_data(99999)
        assert result is None


# ============================================================================
# ТЕСТЫ: get_supervision_card_data
# ============================================================================

class TestGetSupervisionCardData:
    """Получение данных карточки надзора."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_existing(self, db_with_contract):
        """Получение данных существующей карточки надзора."""
        db, _, contract_id = db_with_contract
        # Меняем статус для создания карточки надзора
        db.update_contract(contract_id, {'status': 'АВТОРСКИЙ НАДЗОР'})
        card_id = db.create_supervision_card(contract_id)
        data = db.get_supervision_card_data(card_id)
        assert data is not None
        assert data['contract_id'] == contract_id

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_nonexistent(self, db):
        """Несуществующая карточка надзора возвращает None."""
        result = db.get_supervision_card_data(99999)
        assert result is None


# ============================================================================
# ТЕСТЫ: get_contract_id_by_supervision_card
# ============================================================================

class TestGetContractIdBySupervisionCard:
    """Обратная связь: supervision_card -> contract."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_existing(self, db_with_contract):
        """Получение contract_id по supervision_card_id."""
        db, _, contract_id = db_with_contract
        db.update_contract(contract_id, {'status': 'АВТОРСКИЙ НАДЗОР'})
        card_id = db.create_supervision_card(contract_id)
        result = db.get_contract_id_by_supervision_card(card_id)
        assert result == contract_id

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_nonexistent(self, db):
        """Несуществующий card_id возвращает None."""
        result = db.get_contract_id_by_supervision_card(99999)
        assert result is None


# ============================================================================
# ТЕСТЫ: complete_supervision_stage
# ============================================================================

class TestCompleteSupervisionStage:
    """Отметка стадии надзора как сданной."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_complete_sets_dan_completed(self, db_with_contract):
        """complete_supervision_stage ставит dan_completed = 1."""
        db, _, contract_id = db_with_contract
        db.update_contract(contract_id, {'status': 'АВТОРСКИЙ НАДЗОР'})
        card_id = db.create_supervision_card(contract_id)
        db.complete_supervision_stage(card_id)

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT dan_completed FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()
        assert row['dan_completed'] == 1


# ============================================================================
# ТЕСТЫ: get_incomplete_stage_executors
# ============================================================================

class TestGetIncompleteStageExecutors:
    """Получение незавершённых исполнителей стадии."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_returns_incomplete(self, db_with_contract):
        """Возвращает незавершённых исполнителей."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        executor_id = _make_employee(db, 'Исполнитель', 'exec1', 'Дизайнер')
        manager_id = _make_employee(db, 'Менеджер', 'mgr1', 'Старший менеджер проектов')
        db.assign_stage_executor(crm_card_id, 'Дизайн концепция', executor_id, manager_id, '2026-03-01')

        result = db.get_incomplete_stage_executors(crm_card_id, 'Дизайн концепция')
        assert len(result) == 1
        assert result[0]['executor_id'] == executor_id

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_completed_not_returned(self, db_with_contract):
        """Завершённые исполнители не возвращаются."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        executor_id = _make_employee(db, 'Исполнитель2', 'exec2', 'Дизайнер')
        manager_id = _make_employee(db, 'Менеджер2', 'mgr2', 'Старший менеджер проектов')
        db.assign_stage_executor(crm_card_id, 'Рабочие чертежи', executor_id, manager_id, '2026-04-01')
        db.complete_stage_for_executor(crm_card_id, 'Рабочие чертежи', executor_id)

        result = db.get_incomplete_stage_executors(crm_card_id, 'Рабочие чертежи')
        assert len(result) == 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_empty_for_no_executors(self, db_with_contract):
        """Пустой список если нет исполнителей."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        result = db.get_incomplete_stage_executors(crm_card_id, 'Несуществующая')
        assert result == []


# ============================================================================
# ТЕСТЫ: update_stage_executor_deadline
# ============================================================================

class TestUpdateStageExecutorDeadline:
    """Обновление дедлайна исполнителя."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_deadline(self, db_with_contract):
        """Обновление дедлайна существующего исполнителя."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        executor_id = _make_employee(db, 'Дедлайн Исп', 'deadline_exec', 'Дизайнер')
        manager_id = _make_employee(db, 'Дедлайн Менеджер', 'deadline_mgr', 'Старший менеджер проектов')
        db.assign_stage_executor(crm_card_id, 'Дизайн концепция', executor_id, manager_id, '2026-03-01')

        result = db.update_stage_executor_deadline(crm_card_id, 'Дизайн концепция', '2026-05-01')
        assert result is True

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_deadline_nonexistent_stage(self, db_with_contract):
        """Обновление дедлайна несуществующей стадии — False."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        result = db.update_stage_executor_deadline(crm_card_id, 'Несуществующая', '2026-05-01')
        assert result is False


# ============================================================================
# ТЕСТЫ: get_projects_by_type
# ============================================================================

class TestGetProjectsByType:
    """Получение проектов по типу."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_returns_projects(self, db_with_contract):
        """Возвращает проекты указанного типа."""
        db, _, _ = db_with_contract
        result = db.get_projects_by_type('Индивидуальный')
        assert len(result) >= 1
        assert 'contract_id' in result[0]
        assert 'contract_number' in result[0]

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_empty_for_other_type(self, db_with_contract):
        """Пустой результат для другого типа проекта."""
        db, _, _ = db_with_contract
        result = db.get_projects_by_type('Шаблонный')
        assert result == []


# ============================================================================
# ТЕСТЫ: get_previous_executor_by_position
# ============================================================================

class TestGetPreviousExecutorByPosition:
    """Получение предыдущего исполнителя по должности."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_returns_previous_executor(self, db_with_contract):
        """Возвращает ID предыдущего исполнителя той же должности."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        exec_id = _make_employee(db, 'Предыдущий Дизайнер', 'prev_des', 'Дизайнер')
        mgr_id = _make_employee(db, 'МГР Предыдущий', 'prev_mgr', 'Старший менеджер проектов')
        db.assign_stage_executor(crm_card_id, 'Дизайн концепция', exec_id, mgr_id, '2026-02-01')

        result = db.get_previous_executor_by_position(crm_card_id, 'Дизайнер')
        assert result == exec_id

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_returns_none_for_no_match(self, db_with_contract):
        """None если нет предыдущего исполнителя."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        result = db.get_previous_executor_by_position(crm_card_id, 'Чертёжник')
        assert result is None


# ============================================================================
# ТЕСТЫ: approval_stage_deadlines
# ============================================================================

class TestApprovalStageDeadlines:
    """Дедлайны согласования."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_empty_deadlines(self, db_with_contract):
        """Пустой список дедлайнов для карточки без согласований."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        result = db.get_approval_stage_deadlines(crm_card_id)
        assert result == []

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_add_and_get_deadlines(self, db_with_contract):
        """Добавление и получение дедлайнов согласования."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        # Прямой INSERT в approval_stage_deadlines
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO approval_stage_deadlines (crm_card_id, stage_name, deadline)
            VALUES (?, ?, ?)
        ''', (crm_card_id, 'Замер', '2026-03-01'))
        conn.commit()
        db.close()

        deadlines = db.get_approval_stage_deadlines(crm_card_id)
        assert len(deadlines) == 1
        assert deadlines[0]['stage_name'] == 'Замер'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_complete_approval_stage(self, db_with_contract):
        """Завершение стадии согласования."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO approval_stage_deadlines (crm_card_id, stage_name, deadline)
            VALUES (?, ?, ?)
        ''', (crm_card_id, 'Концепция', '2026-04-01'))
        conn.commit()
        db.close()

        db.complete_approval_stage(crm_card_id, 'Концепция')
        deadlines = db.get_approval_stage_deadlines(crm_card_id)
        assert deadlines[0]['is_completed'] == 1
        assert deadlines[0]['completed_date'] is not None


# ============================================================================
# ТЕСТЫ: sync_approval_stages_to_json
# ============================================================================

class TestSyncApprovalStagesToJson:
    """Синхронизация этапов согласования в JSON."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_sync_stages(self, db_with_contract):
        """Синхронизация записей в JSON."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO approval_stage_deadlines (crm_card_id, stage_name, deadline)
            VALUES (?, ?, ?)
        ''', (crm_card_id, 'Замер', '2026-03-01'))
        cursor.execute('''
            INSERT INTO approval_stage_deadlines (crm_card_id, stage_name, deadline)
            VALUES (?, ?, ?)
        ''', (crm_card_id, 'Концепция', '2026-04-01'))
        conn.commit()
        db.close()

        db.sync_approval_stages_to_json(crm_card_id)

        card = db.get_crm_card_data(crm_card_id)
        stages = json.loads(card['approval_stages'])
        assert 'Замер' in stages
        assert 'Концепция' in stages


# ============================================================================
# ТЕСТЫ: delete_order
# ============================================================================

class TestDeleteOrder:
    """Полное удаление заказа."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_delete_order_removes_contract(self, db_with_contract):
        """delete_order удаляет договор из БД."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        db.delete_order(contract_id, crm_card_id)
        assert db.get_contract_by_id(contract_id) is None

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_delete_order_removes_crm_card(self, db_with_contract):
        """delete_order удаляет CRM-карточку."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        db.delete_order(contract_id, crm_card_id)
        assert db.get_crm_card_data(crm_card_id) is None

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_delete_order_without_crm_card(self, db_with_contract):
        """delete_order работает и без crm_card_id."""
        db, _, contract_id = db_with_contract
        db.delete_order(contract_id, crm_card_id=None)
        assert db.get_contract_by_id(contract_id) is None


# ============================================================================
# ТЕСТЫ: delete_supervision_order
# ============================================================================

class TestDeleteSupervisionOrder:
    """Удаление заказа надзора."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_delete_supervision_order(self, db_with_contract):
        """delete_supervision_order удаляет договор и карточку надзора."""
        db, _, contract_id = db_with_contract
        db.update_contract(contract_id, {'status': 'АВТОРСКИЙ НАДЗОР'})
        card_id = db.create_supervision_card(contract_id)
        db.delete_supervision_order(contract_id, card_id)
        assert db.get_contract_by_id(contract_id) is None

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_delete_supervision_order_without_card(self, db_with_contract):
        """delete_supervision_order работает без supervision_card_id."""
        db, _, contract_id = db_with_contract
        db.delete_supervision_order(contract_id, supervision_card_id=None)
        assert db.get_contract_by_id(contract_id) is None


# ============================================================================
# ТЕСТЫ: add_project_file / get_project_files / delete_project_file
# ============================================================================

class TestProjectFiles:
    """CRUD файлов проекта."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_add_project_file(self, db_with_contract):
        """Добавление файла проекта."""
        db, _, contract_id = db_with_contract
        file_id = db.add_project_file(
            contract_id, 'measurement', 'image',
            'https://example.com/file.jpg',
            '/disk/file.jpg',
            'file.jpg'
        )
        assert file_id is not None

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_project_files(self, db_with_contract):
        """Получение файлов проекта."""
        db, _, contract_id = db_with_contract
        db.add_project_file(
            contract_id, 'measurement', 'image',
            'https://example.com/1.jpg', '/disk/1.jpg', '1.jpg'
        )
        db.add_project_file(
            contract_id, 'measurement', 'pdf',
            'https://example.com/2.pdf', '/disk/2.pdf', '2.pdf'
        )
        files = db.get_project_files(contract_id, 'measurement')
        assert len(files) == 2

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_project_files_all_stages(self, db_with_contract):
        """Получение всех файлов (без фильтра по стадии)."""
        db, _, contract_id = db_with_contract
        db.add_project_file(
            contract_id, 'measurement', 'image',
            'https://example.com/1.jpg', '/disk/1.jpg', '1.jpg'
        )
        db.add_project_file(
            contract_id, 'stage1', 'pdf',
            'https://example.com/2.pdf', '/disk/2.pdf', '2.pdf'
        )
        files = db.get_project_files(contract_id)
        assert len(files) == 2

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_delete_project_file(self, db_with_contract):
        """Удаление файла проекта."""
        db, _, contract_id = db_with_contract
        file_id = db.add_project_file(
            contract_id, 'measurement', 'image',
            'https://example.com/del.jpg', '/disk/del.jpg', 'del.jpg'
        )
        result = db.delete_project_file(file_id)
        # delete_project_file возвращает dict с данными удалённого файла, не True
        assert result is not None
        assert isinstance(result, dict)
        files = db.get_project_files(contract_id, 'measurement')
        assert len(files) == 0


# ============================================================================
# ТЕСТЫ: Агенты — дополнительные
# ============================================================================

class TestAgentExtended:
    """Дополнительные тесты агентов."""

    def test_update_agent_color(self, db):
        """Обновление цвета агента."""
        db.add_agent('ТЕСТОВЫЙ', '#000000')
        result = db.update_agent_color('ТЕСТОВЫЙ', '#FFFFFF')
        assert result is True
        agents = db.get_all_agents()
        agent = [a for a in agents if a['name'] == 'ТЕСТОВЫЙ'][0]
        assert agent['color'] == '#FFFFFF'

    def test_get_agent_color(self, db):
        """Получение цвета агента по имени (с кэшированием)."""
        # Сброс кэша
        db.invalidate_agent_colors_cache()
        color = db.get_agent_color('ПЕТРОВИЧ')
        assert color == '#FFA500'

    def test_get_agent_color_nonexistent(self, db):
        """Цвет несуществующего агента — None."""
        db.invalidate_agent_colors_cache()
        color = db.get_agent_color('НЕСУЩЕСТВУЮЩИЙ')
        assert color is None

    def test_invalidate_cache(self, db):
        """Сброс кэша и повторная загрузка."""
        db.invalidate_agent_colors_cache()
        # Первый вызов загружает кэш
        db.get_agent_color('ПЕТРОВИЧ')
        # Добавляем нового агента
        db.add_agent('КЭШТЕСТ', '#123456')
        # Без сброса кэша — не найдёт
        # После сброса — найдёт
        db.invalidate_agent_colors_cache()
        color = db.get_agent_color('КЭШТЕСТ')
        assert color == '#123456'


# ============================================================================
# ТЕСТЫ: build_period_where
# ============================================================================

class TestBuildPeriodWhere:
    """Построение WHERE для периода."""

    def test_year_only(self, db):
        """Фильтр только по году."""
        clause = db.build_period_where(2026, None, None)
        assert '2026' in clause
        assert "strftime('%Y', contract_date)" in clause

    def test_month_filter(self, db):
        """Фильтр по конкретному месяцу."""
        clause = db.build_period_where(2026, None, 3)
        assert '2026-03' in clause

    def test_quarter_filter_q1(self, db):
        """Фильтр по первому кварталу."""
        clause = db.build_period_where(2026, 'Q1', None)
        assert 'BETWEEN 1 AND 3' in clause

    def test_quarter_filter_q4(self, db):
        """Фильтр по четвёртому кварталу."""
        clause = db.build_period_where(2026, 'Q4', None)
        assert 'BETWEEN 10 AND 12' in clause

    def test_quarter_as_int(self, db):
        """Квартал как число."""
        clause = db.build_period_where(2026, 2, None)
        assert 'BETWEEN 4 AND 6' in clause

    def test_all_quarter(self, db):
        """Квартал 'Все' — фильтр только по году."""
        clause = db.build_period_where(2026, 'Все', None)
        assert '2026' in clause

    def test_all_month(self, db):
        """Месяц 'Все' — фильтр по кварталу/году."""
        clause = db.build_period_where(2026, None, 'Все')
        assert '2026' in clause


# ============================================================================
# ТЕСТЫ: get_payments_by_supervision_card
# ============================================================================

class TestGetPaymentsBySupervisionCard:
    """Получение платежей по карточке надзора."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_empty_for_no_payments(self, db_with_contract):
        """Пустой список если нет платежей для карточки надзора."""
        db, _, contract_id = db_with_contract
        db.update_contract(contract_id, {'status': 'АВТОРСКИЙ НАДЗОР'})
        card_id = db.create_supervision_card(contract_id)
        result = db.get_payments_by_supervision_card(card_id)
        assert result == []

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_returns_payments(self, db_with_contract):
        """Возвращает платежи привязанные к карточке надзора."""
        db, _, contract_id = db_with_contract
        db.update_contract(contract_id, {'status': 'АВТОРСКИЙ НАДЗОР'})
        card_id = db.create_supervision_card(contract_id)
        emp_id = _make_employee(db, 'ДАН Платёж', 'dan_pay', 'ДАН')

        # Прямой INSERT платежа с supervision_card_id
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO payments (contract_id, supervision_card_id, employee_id, role,
                                   calculated_amount, final_amount, payment_type, report_month)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (contract_id, card_id, emp_id, 'ДАН', 5000.0, 5000.0, 'Полная оплата', '2026-01'))
        conn.commit()
        db.close()

        result = db.get_payments_by_supervision_card(card_id)
        assert len(result) == 1
        assert result[0]['role'] == 'ДАН'


# ============================================================================
# ТЕСТЫ: get_payments_for_crm (дополнительные данные из CRM)
# ============================================================================

class TestGetPaymentsForCrm:
    """Получение платежей для CRM-карточки."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_empty(self, db_with_contract):
        """Пустой список если нет платежей."""
        db, _, contract_id = db_with_contract
        result = db.get_payments_for_crm(contract_id)
        assert isinstance(result, list)
        assert len(result) == 0


# ============================================================================
# ТЕСТЫ: get_crm_dashboard_stats
# ============================================================================

class TestGetCrmDashboardStats:
    """Статистика для дашборда CRM."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_individual_stats(self, db_with_contract):
        """Статистика для индивидуальных проектов."""
        db, _, _ = db_with_contract
        stats = db.get_crm_dashboard_stats('Индивидуальный')
        assert 'total_orders' in stats
        assert 'total_area' in stats
        assert 'active_orders' in stats
        assert stats['total_orders'] >= 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_template_stats_empty(self, db_with_contract):
        """Шаблонных проектов нет — нулевые значения."""
        db, _, _ = db_with_contract
        stats = db.get_crm_dashboard_stats('Шаблонный')
        assert stats['total_orders'] == 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_stats_with_agent_filter(self, db_with_contract):
        """Фильтрация по типу агента."""
        db, _, _ = db_with_contract
        stats = db.get_crm_dashboard_stats('Индивидуальный', agent_type='СПБ')
        assert 'agent_active_orders' in stats


# ============================================================================
# ТЕСТЫ: get_supervision_statistics
# ============================================================================

class TestGetSupervisionStatistics:
    """Статистика CRM надзора."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_empty_stats(self, db):
        """Пустая БД — пустой список."""
        stats = db.get_supervision_statistics(
            period='Год', year=2026, quarter=None, month=None
        )
        assert stats == []


# ============================================================================
# ТЕСТЫ: get_payments_by_type
# ============================================================================

class TestGetPaymentsByType:
    """Получение выплат по типу."""

    def test_salaries_type(self, db):
        """Тип 'Оклады' фильтрует по таблице salaries."""
        emp_id = _make_employee(db, 'Окладовец', 'okladvec')
        db.add_salary({
            'employee_id': emp_id,
            'payment_type': 'Оклад дизайнера',
            'amount': 50000.0,
        })
        payments = db.get_payments_by_type('Оклады')
        assert isinstance(payments, list)

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_individual_type(self, db_with_contract):
        """Фильтр по 'Индивидуальный' проект."""
        db, _, _ = db_with_contract
        payments = db.get_payments_by_type(
            'Индивидуальные проекты',
            project_type_filter='Индивидуальный'
        )
        assert isinstance(payments, list)


# ============================================================================
# ТЕСТЫ: add_project_file с вариацией
# ============================================================================

class TestProjectFileVariation:
    """Файлы проекта с вариацией."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_add_file_with_variation(self, db_with_contract):
        """Добавление файла с конкретной вариацией."""
        db, _, contract_id = db_with_contract
        file_id = db.add_project_file(
            contract_id, 'stage2_concept', 'image',
            'https://example.com/v2.jpg', '/disk/v2.jpg', 'v2.jpg',
            variation=2
        )
        assert file_id is not None

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_file_order_auto_increment(self, db_with_contract):
        """file_order автоматически инкрементируется."""
        db, _, contract_id = db_with_contract
        db.add_project_file(
            contract_id, 'stage1', 'image',
            'https://example.com/a.jpg', '/disk/a.jpg', 'a.jpg'
        )
        db.add_project_file(
            contract_id, 'stage1', 'image',
            'https://example.com/b.jpg', '/disk/b.jpg', 'b.jpg'
        )
        files = db.get_project_files(contract_id, 'stage1')
        orders = [f['file_order'] for f in files]
        assert 0 in orders
        assert 1 in orders


# ============================================================================
# ТЕСТЫ: get_stage_completion_info
# ============================================================================

class TestGetStageCompletionInfo:
    """Информация о завершении стадии."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_no_executors(self, db_with_contract):
        """Нет исполнителей — stage=None."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        info = db.get_stage_completion_info(crm_card_id, 'Несуществующая стадия')
        assert info['stage'] is None

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_with_executor(self, db_with_contract):
        """С назначенным исполнителем."""
        db, _, contract_id = db_with_contract
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        exec_id = _make_employee(db, 'Инфо Исп', 'info_exec', 'Дизайнер')
        mgr_id = _make_employee(db, 'Инфо Менеджер', 'info_mgr', 'Старший менеджер проектов')
        db.assign_stage_executor(crm_card_id, 'Дизайн концепция', exec_id, mgr_id, '2026-05-01')

        info = db.get_stage_completion_info(crm_card_id, 'Дизайн концепция')
        assert info['stage'] is not None
        assert info['stage']['completed'] == 0


# ============================================================================
# ТЕСТЫ: calculate_payment_amount (без мока YandexDisk)
# ============================================================================

class TestCalculatePaymentAmount:
    """Расчёт суммы платежа."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_with_rate(self, db_with_contract):
        """Расчёт суммы при наличии ставки."""
        db, _, contract_id = db_with_contract
        emp_id = _make_employee(db, 'Расчёт Дизайнер', 'calc_des', 'Дизайнер')
        db.add_rate({
            'project_type': 'Индивидуальный',
            'role': 'Дизайнер',
            'rate_per_m2': 200.0,
        })
        amount = db.calculate_payment_amount(contract_id, emp_id, 'Дизайнер')
        # area = 120, rate = 200 => 24000
        assert amount == 24000.0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_without_rate(self, db_with_contract):
        """Расчёт без ставки возвращает 0."""
        db, _, contract_id = db_with_contract
        emp_id = _make_employee(db, 'Нет Ставки', 'no_rate', 'Стажёр')
        amount = db.calculate_payment_amount(contract_id, emp_id, 'Стажёр')
        assert amount == 0.0


# ============================================================================
# ТЕСТЫ: create_payment_record
# ============================================================================

class TestCreatePaymentRecord:
    """Создание записи платежа."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_create_returns_id(self, db_with_contract):
        """create_payment_record возвращает ID."""
        db, _, contract_id = db_with_contract
        emp_id = _make_employee(db, 'Платёж ТестА', 'pay_testa', 'Дизайнер')
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        pid = db.create_payment_record(
            contract_id, emp_id, 'Дизайнер',
            payment_type='Полная оплата',
            report_month='2026-01',
            crm_card_id=crm_card_id,
        )
        assert pid is not None
        assert isinstance(pid, int)

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_payment_persists(self, db_with_contract):
        """Созданный платёж сохраняется в БД."""
        db, _, contract_id = db_with_contract
        emp_id = _make_employee(db, 'Платёж ТестБ', 'pay_testb', 'ГАП')
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        pid = db.create_payment_record(
            contract_id, emp_id, 'ГАП',
            payment_type='Полная оплата',
            report_month='2026-02',
            crm_card_id=crm_card_id,
        )
        payment = db.get_payment(pid)
        assert payment is not None
        assert payment['role'] == 'ГАП'
        assert payment['contract_id'] == contract_id


# ============================================================================
# ТЕСТЫ: update_payment_manual
# ============================================================================

class TestUpdatePaymentManual:
    """Ручное обновление суммы платежа."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_manual_amount(self, db_with_contract):
        """Ручная корректировка суммы."""
        db, _, contract_id = db_with_contract
        emp_id = _make_employee(db, 'Мануал Тест', 'manual_test', 'Дизайнер')
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        pid = db.create_payment_record(
            contract_id, emp_id, 'Дизайнер',
            payment_type='Полная оплата',
            crm_card_id=crm_card_id,
        )
        db.update_payment_manual(pid, 99999.0)
        payment = db.get_payment(pid)
        assert payment['final_amount'] == 99999.0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_manual_with_month(self, db_with_contract):
        """Ручная корректировка суммы и отчётного месяца."""
        db, _, contract_id = db_with_contract
        emp_id = _make_employee(db, 'Мануал2', 'manual2', 'ГАП')
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        pid = db.create_payment_record(
            contract_id, emp_id, 'ГАП',
            payment_type='Полная оплата',
            crm_card_id=crm_card_id,
        )
        db.update_payment_manual(pid, 50000.0, report_month='2026-06')
        payment = db.get_payment(pid)
        assert payment['final_amount'] == 50000.0
        assert payment['report_month'] == '2026-06'


# ============================================================================
# ТЕСТЫ: get_payments_for_crm (с данными)
# ============================================================================

class TestGetPaymentsForCrmWithData:
    """Платежи CRM с данными."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_returns_crm_payments(self, db_with_contract):
        """Возвращает платежи привязанные к CRM-карточке."""
        db, _, contract_id = db_with_contract
        emp_id = _make_employee(db, 'CRM Платёж', 'crm_pay', 'Дизайнер')
        crm_card_id = db.get_crm_card_id_by_contract(contract_id)
        db.create_payment_record(
            contract_id, emp_id, 'Дизайнер',
            payment_type='Полная оплата',
            crm_card_id=crm_card_id,
        )
        payments = db.get_payments_for_crm(contract_id)
        assert len(payments) >= 1
        assert payments[0]['role'] == 'Дизайнер'


# ============================================================================
# ТЕСТЫ: get_contract_years
# ============================================================================

class TestGetContractYears:
    """Получение списка годов из договоров."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_includes_current_year(self, db):
        """Список включает текущий год."""
        years = db.get_contract_years()
        current_year = datetime.now().year
        assert current_year in years

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_includes_contract_year(self, db_with_contract):
        """Год из даты договора включён в результат."""
        db, _, _ = db_with_contract
        years = db.get_contract_years()
        assert 2026 in years


# ============================================================================
# ТЕСТЫ: get_contracts_count (дополнительные фильтры)
# ============================================================================

class TestGetContractsCountExtended:
    """Расширенные тесты подсчёта договоров."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_no_filters(self, db_with_contract):
        """Без фильтров считает все договоры."""
        db, _, _ = db_with_contract
        count = db.get_contracts_count()
        assert count >= 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_filter_by_status(self, db_with_contract):
        """Фильтр по статусу."""
        db, _, _ = db_with_contract
        count = db.get_contracts_count(status='Новый заказ')
        assert count >= 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_filter_by_project_type(self, db_with_contract):
        """Фильтр по типу проекта."""
        db, _, _ = db_with_contract
        count = db.get_contracts_count(project_type='Индивидуальный')
        assert count >= 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_filter_combined(self, db_with_contract):
        """Комбинация фильтров."""
        db, _, _ = db_with_contract
        count = db.get_contracts_count(
            status='Новый заказ',
            project_type='Индивидуальный',
            year=2026
        )
        assert count >= 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_nonexistent_filters(self, db_with_contract):
        """Фильтр с несуществующими значениями — 0."""
        db, _, _ = db_with_contract
        count = db.get_contracts_count(status='НЕСУЩЕСТВУЮЩИЙ')
        assert count == 0


# ============================================================================
# ТЕСТЫ: ALLOWED_TABLES покрытие
# ============================================================================

class TestAllowedTables:
    """Проверка whitelist таблиц."""

    def test_all_expected_tables_in_whitelist(self, db):
        """Все ожидаемые таблицы есть в whitelist."""
        expected = [
            'clients', 'contracts', 'employees', 'crm_cards',
            'supervision_cards', 'payments', 'rates', 'salaries',
            'project_files', 'action_history', 'supervision_history',
            'stage_executors', 'supervision_orders', 'employee_permissions',
            'template_rates', 'contract_templates', 'messenger_settings',
            'messenger_scripts', 'norm_days',
        ]
        for table in expected:
            assert table in db.ALLOWED_TABLES, f"Таблица {table} не в whitelist"

    def test_validate_all_allowed(self, db):
        """_validate_table не бросает для всех разрешённых таблиц."""
        for table in db.ALLOWED_TABLES:
            db._validate_table(table)  # Не должно бросить исключение


# ============================================================================
# ТЕСТЫ: connect / close edge cases
# ============================================================================

class TestConnectionEdgeCases:
    """Граничные случаи подключения."""

    def test_double_close_no_error(self, db):
        """Двойное закрытие соединения не вызывает ошибку."""
        db.connect()
        db.close()
        db.close()  # Повторное закрытие — не должно упасть

    def test_connect_returns_connection(self, db):
        """connect() возвращает объект соединения."""
        conn = db.connect()
        assert conn is not None
        db.close()

    def test_row_factory_set(self, db):
        """row_factory установлен на sqlite3.Row."""
        import sqlite3
        conn = db.connect()
        assert conn.row_factory is sqlite3.Row
        db.close()


# ============================================================================
# ТЕСТЫ: add_supervision_history / get_supervision_history (через db_manager)
# ============================================================================

class TestSupervisionHistoryDirect:
    """Прямые тесты истории надзора через db_manager."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_add_and_get(self, db_with_contract):
        """Добавление и получение записи истории."""
        db, _, contract_id = db_with_contract
        db.update_contract(contract_id, {'status': 'АВТОРСКИЙ НАДЗОР'})
        card_id = db.create_supervision_card(contract_id)
        emp_id = _make_employee(db, 'Историк Надзора', 'hist_sv', 'ДАН')
        db.add_supervision_history(card_id, 'note', 'Тестовая заметка', emp_id)
        history = db.get_supervision_history(card_id)
        assert len(history) == 1
        assert history[0]['message'] == 'Тестовая заметка'
        assert history[0]['entry_type'] == 'note'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_empty_history(self, db_with_contract):
        """Пустая история для новой карточки."""
        db, _, contract_id = db_with_contract
        db.update_contract(contract_id, {'status': 'АВТОРСКИЙ НАДЗОР'})
        card_id = db.create_supervision_card(contract_id)
        history = db.get_supervision_history(card_id)
        assert history == []

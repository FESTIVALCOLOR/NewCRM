# -*- coding: utf-8 -*-
"""
Покрытие database/db_manager.py — платежи, зарплаты, ставки.
~30 тестов. Реальная SQLite через tmp_path.

Тестируемые методы:
  Платежи:  add_payment, get_payment, update_payment, delete_payment,
            get_all_payments, get_year_payments, get_payments_for_contract,
            mark_payment_as_paid
  Зарплаты: add_salary, get_salaries
  Ставки:   get_rates, add_rate
"""

import pytest
import sys
import os

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
    """Создать DatabaseManager с временной SQLite БД.

    Порядок:
    1. Создаём DatabaseManager БЕЗ миграций (таблиц ещё нет)
    2. initialize_database() — основные таблицы
    3. Все ALTER-миграции вручную
    """
    import database.db_manager as dm_module

    # Подавляем миграции в конструкторе (таблиц ещё нет)
    dm_module._migrations_completed = True

    db_path = str(tmp_path / 'test.db')
    with patch('database.db_manager.YANDEX_DISK_TOKEN', ''):
        manager = dm_module.DatabaseManager(db_path=db_path)

        # Основные таблицы
        manager.initialize_database()

        # ALTER-миграции (таблицы уже есть)
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

        manager.connect()

    yield manager

    dm_module._migrations_completed = False


@pytest.fixture
def employee_id(db):
    """Создать тестового сотрудника, вернуть его ID."""
    emp_data = {
        'full_name': 'Тестовый Дизайнер',
        'login': 'designer1',
        'password': 'pass123',
        'position': 'Дизайнер',
    }
    eid = db.add_employee(emp_data)
    return eid


@pytest.fixture
def client_id(db):
    """Создать тестового клиента, вернуть ID."""
    client_data = {
        'client_type': 'Физ. лицо',
        'full_name': 'Клиент Тестов',
        'phone': '+79001234567',
        'email': 'client@test.ru',
    }
    return db.add_client(client_data)


@pytest.fixture
def contract_id(db, client_id):
    """Создать тестовый договор, вернуть ID."""
    contract_data = {
        'client_id': client_id,
        'project_type': 'Индивидуальный',
        'contract_number': '№001-2025',
        'contract_date': '2025-06-01',
        'address': 'ул. Тестовая, 1',
        'area': 100,
        'total_amount': 500000,
        'contract_period': 60,
        'status': 'Новый заказ',
        'city': 'Москва',
    }
    with patch('database.db_manager.YANDEX_DISK_TOKEN', ''):
        cid = db.add_contract(contract_data)
    return cid


@pytest.fixture
def crm_card_id(db, contract_id):
    """Получить CRM-карточку, автоматически созданную для договора."""
    return db.get_crm_card_id_by_contract(contract_id)


@pytest.fixture
def payment_id(db, contract_id, employee_id, crm_card_id):
    """Создать тестовый платёж через прямой INSERT и вернуть ID."""
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO payments
    (contract_id, crm_card_id, employee_id, role, stage_name,
     calculated_amount, final_amount, payment_type, report_month)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (contract_id, crm_card_id, employee_id, 'Дизайнер', 'Планировка',
          50000.0, 50000.0, 'Полная оплата', '2025-06'))
    conn.commit()
    pid = cursor.lastrowid
    db.close()
    db.connect()
    return pid


# ==================== Вспомогательные данные ====================

def _make_salary_data(employee_id, contract_id=None, **overrides):
    """Хелпер: минимальный набор полей для add_salary."""
    data = {
        'contract_id': contract_id,
        'employee_id': employee_id,
        'payment_type': 'Оклад дизайнера',
        'stage_name': 'Планировка',
        'amount': 30000.0,
        'advance_payment': 0,
        'report_month': '2025-06',
        'comments': 'Тестовая зарплата',
        'project_type': 'Индивидуальный',
    }
    data.update(overrides)
    return data


def _make_rate_data(**overrides):
    """Хелпер: минимальный набор полей для add_rate."""
    data = {
        'project_type': 'Индивидуальный',
        'role': 'Дизайнер',
        'stage_name': 'Планировка',
        'rate_per_m2': 150.0,
    }
    data.update(overrides)
    return data


# ============================================================================
# ТЕСТЫ: get_payment / add_payment
# ============================================================================

class TestGetPayment:
    """Получение платежа по ID."""

    def test_get_payment_существующий(self, db, payment_id):
        """get_payment возвращает dict для существующего платежа"""
        result = db.get_payment(payment_id)
        assert result is not None
        assert result['id'] == payment_id
        assert result['role'] == 'Дизайнер'

    def test_get_payment_несуществующий(self, db):
        """get_payment возвращает None для несуществующего ID"""
        result = db.get_payment(99999)
        assert result is None

    def test_get_payment_содержит_все_поля(self, db, payment_id):
        """Возвращённый dict содержит ключевые поля"""
        result = db.get_payment(payment_id)
        for field in ['id', 'contract_id', 'employee_id', 'role',
                       'calculated_amount', 'final_amount', 'payment_type']:
            assert field in result, f"Поле {field} отсутствует"


class TestAddPayment:
    """Создание платежа через add_payment (обёртка create_payment_record)."""

    def test_add_payment_с_тарифом(self, db, contract_id, employee_id, crm_card_id):
        """add_payment создаёт платёж и возвращает ID (при наличии ставки)"""
        # Создаём ставку для расчёта суммы
        db.add_rate({
            'project_type': 'Индивидуальный',
            'role': 'Дизайнер',
            'rate_per_m2': 200.0,
        })

        pid = db.add_payment({
            'contract_id': contract_id,
            'employee_id': employee_id,
            'role': 'Дизайнер',
            'payment_type': 'Полная оплата',
            'report_month': '2025-07',
            'crm_card_id': crm_card_id,
        })
        assert pid is not None
        assert isinstance(pid, int)

    def test_add_payment_без_тарифа_нулевая_сумма(self, db, contract_id, employee_id, crm_card_id):
        """add_payment создаёт платёж с нулевой суммой если тариф не найден"""
        pid = db.add_payment({
            'contract_id': contract_id,
            'employee_id': employee_id,
            'role': 'Неизвестная роль',
            'payment_type': 'Полная оплата',
            'report_month': '2025-08',
            'crm_card_id': crm_card_id,
        })
        # Платёж создаётся даже без тарифа (сумма = 0)
        assert pid is not None
        payment = db.get_payment(pid)
        assert payment['calculated_amount'] == 0.0


# ============================================================================
# ТЕСТЫ: update_payment
# ============================================================================

class TestUpdatePayment:
    """Обновление платежа."""

    def test_update_payment_меняет_сумму(self, db, payment_id):
        """update_payment обновляет final_amount"""
        result = db.update_payment(payment_id, {'final_amount': 75000.0})
        assert result is True
        payment = db.get_payment(payment_id)
        assert payment['final_amount'] == 75000.0

    def test_update_payment_меняет_report_month(self, db, payment_id):
        """update_payment обновляет report_month"""
        db.update_payment(payment_id, {'report_month': '2025-09'})
        payment = db.get_payment(payment_id)
        assert payment['report_month'] == '2025-09'

    def test_update_payment_несуществующий_id(self, db):
        """update_payment для несуществующего ID не падает"""
        result = db.update_payment(99999, {'final_amount': 100.0})
        # Метод возвращает True даже если строка не найдена (UPDATE 0 rows)
        assert result is True

    def test_update_payment_несколько_полей(self, db, payment_id):
        """update_payment может обновить несколько полей за раз"""
        db.update_payment(payment_id, {
            'final_amount': 60000.0,
            'payment_type': 'Аванс',
            'report_month': '2025-12',
        })
        payment = db.get_payment(payment_id)
        assert payment['final_amount'] == 60000.0
        assert payment['payment_type'] == 'Аванс'
        assert payment['report_month'] == '2025-12'


# ============================================================================
# ТЕСТЫ: delete_payment
# ============================================================================

class TestDeletePayment:
    """Удаление платежа."""

    def test_delete_payment_удаляет(self, db, payment_id):
        """delete_payment удаляет запись из таблицы payments"""
        db.delete_payment(payment_id)
        result = db.get_payment(payment_id)
        assert result is None

    def test_delete_payment_несуществующий_id(self, db):
        """delete_payment для несуществующего ID не падает"""
        # Не должно бросить исключение
        db.delete_payment(99999)

    def test_delete_payment_не_удаляет_другие(self, db, contract_id, employee_id, crm_card_id):
        """delete_payment удаляет только указанный платёж"""
        # Создаём два платежа прямым INSERT
        conn = db.connect()
        cursor = conn.cursor()
        for i in range(2):
            cursor.execute('''
            INSERT INTO payments
            (contract_id, crm_card_id, employee_id, role, stage_name,
             calculated_amount, final_amount, payment_type, report_month)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (contract_id, crm_card_id, employee_id, 'Дизайнер',
                  f'Стадия {i}', 10000.0, 10000.0, 'Оплата', '2025-06'))
        conn.commit()
        # Получаем ID обоих платежей
        cursor.execute('SELECT id FROM payments ORDER BY id')
        ids = [row['id'] for row in cursor.fetchall()]
        db.close()
        db.connect()

        assert len(ids) >= 2
        # Удаляем первый
        db.delete_payment(ids[0])
        # Второй должен остаться
        assert db.get_payment(ids[1]) is not None


# ============================================================================
# ТЕСТЫ: mark_payment_as_paid
# ============================================================================

class TestMarkPaymentAsPaid:
    """Отметка платежа как оплаченного."""

    def test_mark_payment_as_paid_устанавливает_флаги(self, db, payment_id, employee_id):
        """mark_payment_as_paid ставит is_paid=1, payment_status='paid'"""
        db.mark_payment_as_paid(payment_id, employee_id)
        payment = db.get_payment(payment_id)
        assert payment['is_paid'] == 1
        assert payment['payment_status'] == 'paid'
        assert payment['paid_by'] == employee_id

    def test_mark_payment_as_paid_устанавливает_дату(self, db, payment_id, employee_id):
        """mark_payment_as_paid заполняет paid_date"""
        db.mark_payment_as_paid(payment_id, employee_id)
        payment = db.get_payment(payment_id)
        assert payment['paid_date'] is not None

    def test_mark_payment_as_paid_несуществующий_id(self, db, employee_id):
        """mark_payment_as_paid для несуществующего ID не падает"""
        # Не должно бросить исключение
        db.mark_payment_as_paid(99999, employee_id)


# ============================================================================
# ТЕСТЫ: get_payments_for_contract
# ============================================================================

class TestGetPaymentsForContract:
    """Получение платежей по договору."""

    def test_get_payments_for_contract_возвращает_список(self, db, contract_id, payment_id):
        """get_payments_for_contract возвращает непустой список"""
        payments = db.get_payments_for_contract(contract_id)
        assert isinstance(payments, list)
        assert len(payments) >= 1

    def test_get_payments_for_contract_пустой_для_нового(self, db):
        """Для несуществующего договора возвращается пустой список"""
        payments = db.get_payments_for_contract(99999)
        assert payments == []

    def test_get_payments_for_contract_содержит_employee_name(self, db, contract_id, payment_id):
        """Результат JOIN содержит employee_name"""
        payments = db.get_payments_for_contract(contract_id)
        assert len(payments) >= 1
        assert 'employee_name' in payments[0]
        assert payments[0]['employee_name'] == 'Тестовый Дизайнер'


# ============================================================================
# ТЕСТЫ: get_all_payments (с фильтрами month/year)
# ============================================================================

class TestGetAllPayments:
    """Получение всех выплат за период (UNION payments + salaries)."""

    def test_get_all_payments_находит_платёж_по_месяцу(self, db, payment_id):
        """get_all_payments находит платёж по совпадению report_month"""
        payments = db.get_all_payments(month=6, year=2025)
        # payment_id создан с report_month='2025-06'
        ids = [p['id'] for p in payments if p['source'] == 'CRM']
        assert payment_id in ids

    def test_get_all_payments_не_находит_чужой_месяц(self, db, payment_id):
        """get_all_payments не возвращает платёж за другой месяц"""
        payments = db.get_all_payments(month=1, year=2024)
        ids = [p['id'] for p in payments]
        assert payment_id not in ids

    def test_get_all_payments_включает_зарплаты(self, db, employee_id, contract_id):
        """get_all_payments включает записи из salaries"""
        db.add_salary(_make_salary_data(employee_id, contract_id, report_month='2025-06'))
        payments = db.get_all_payments(month=6, year=2025)
        sources = [p['source'] for p in payments]
        assert 'Оклад' in sources


# ============================================================================
# ТЕСТЫ: get_year_payments
# ============================================================================

class TestGetYearPayments:
    """Получение платежей за год."""

    def test_get_year_payments_находит_за_год(self, db, payment_id):
        """get_year_payments находит платёж за указанный год"""
        payments = db.get_year_payments(2025)
        ids = [p['id'] for p in payments]
        assert payment_id in ids

    def test_get_year_payments_не_находит_другой_год(self, db, payment_id):
        """get_year_payments не возвращает платёж за другой год"""
        payments = db.get_year_payments(2024)
        ids = [p['id'] for p in payments]
        assert payment_id not in ids


# ============================================================================
# ТЕСТЫ: add_salary / get_salaries
# ============================================================================

class TestSalaries:
    """CRUD зарплат."""

    def test_add_salary_создаёт_запись(self, db, employee_id, contract_id):
        """add_salary создаёт запись в таблице salaries"""
        db.add_salary(_make_salary_data(employee_id, contract_id))
        salaries = db.get_salaries()
        assert len(salaries) >= 1

    def test_get_salaries_без_фильтров(self, db, employee_id):
        """get_salaries без фильтров возвращает все записи"""
        db.add_salary(_make_salary_data(employee_id))
        db.add_salary(_make_salary_data(employee_id, report_month='2025-07'))
        salaries = db.get_salaries()
        assert len(salaries) >= 2

    def test_get_salaries_фильтр_report_month(self, db, employee_id):
        """get_salaries фильтрует по report_month"""
        db.add_salary(_make_salary_data(employee_id, report_month='2025-06'))
        db.add_salary(_make_salary_data(employee_id, report_month='2025-07'))
        salaries = db.get_salaries(report_month='2025-06')
        assert all(s['report_month'] == '2025-06' for s in salaries)

    def test_get_salaries_фильтр_employee_id(self, db, employee_id):
        """get_salaries фильтрует по employee_id"""
        # Создаём второго сотрудника
        eid2 = db.add_employee({
            'full_name': 'Второй Сотрудник',
            'login': 'second',
            'password': 'pass',
            'position': 'ГАП',
        })
        db.add_salary(_make_salary_data(employee_id))
        db.add_salary(_make_salary_data(eid2))
        salaries = db.get_salaries(employee_id=employee_id)
        assert all(s['employee_id'] == employee_id for s in salaries)

    def test_get_salaries_пустой_результат(self, db):
        """get_salaries возвращает пустой список если нет данных"""
        salaries = db.get_salaries()
        assert salaries == []

    def test_add_salary_с_минимальными_данными(self, db, employee_id):
        """add_salary работает с минимальным набором полей"""
        db.add_salary({
            'employee_id': employee_id,
            'payment_type': 'Оклад',
            'amount': 25000.0,
        })
        salaries = db.get_salaries(employee_id=employee_id)
        assert len(salaries) == 1
        assert salaries[0]['amount'] == 25000.0

    def test_add_salary_сохраняет_project_type(self, db, employee_id):
        """add_salary сохраняет project_type"""
        db.add_salary(_make_salary_data(employee_id, project_type='Шаблонный'))
        salaries = db.get_salaries(employee_id=employee_id)
        assert salaries[0]['project_type'] == 'Шаблонный'


# ============================================================================
# ТЕСТЫ: get_rates / add_rate
# ============================================================================

class TestRates:
    """CRUD ставок."""

    def test_add_rate_возвращает_dict_с_id(self, db):
        """add_rate возвращает dict с ключом id"""
        result = db.add_rate(_make_rate_data())
        assert result is not None
        assert 'id' in result
        assert isinstance(result['id'], int)

    def test_get_rates_без_фильтров(self, db):
        """get_rates без фильтров возвращает все ставки"""
        db.add_rate(_make_rate_data(role='Дизайнер'))
        db.add_rate(_make_rate_data(role='ГАП'))
        rates = db.get_rates()
        assert len(rates) >= 2

    def test_get_rates_фильтр_project_type(self, db):
        """get_rates фильтрует по project_type"""
        db.add_rate(_make_rate_data(project_type='Индивидуальный'))
        db.add_rate(_make_rate_data(project_type='Шаблонный', role='ГАП'))
        rates = db.get_rates(project_type='Шаблонный')
        assert all(r['project_type'] == 'Шаблонный' for r in rates)

    def test_get_rates_фильтр_role(self, db):
        """get_rates фильтрует по role"""
        db.add_rate(_make_rate_data(role='Чертёжник'))
        db.add_rate(_make_rate_data(role='ГАП'))
        rates = db.get_rates(role='Чертёжник')
        assert all(r['role'] == 'Чертёжник' for r in rates)

    def test_get_rates_пустой_результат(self, db):
        """get_rates возвращает пустой список если нет данных"""
        rates = db.get_rates(project_type='Несуществующий')
        assert rates == []

    def test_add_rate_с_area_range(self, db):
        """add_rate корректно сохраняет area_from/area_to"""
        result = db.add_rate(_make_rate_data(
            project_type='Шаблонный',
            area_from=50.0,
            area_to=100.0,
            fixed_price=35000.0,
        ))
        rates = db.get_rates(project_type='Шаблонный')
        assert len(rates) >= 1
        rate = [r for r in rates if r['id'] == result['id']][0]
        assert rate['area_from'] == 50.0
        assert rate['area_to'] == 100.0
        assert rate['fixed_price'] == 35000.0


# ============================================================================
# ТЕСТЫ: CRUD цикл платежей (полный сценарий)
# ============================================================================

class TestPaymentCRUDCycle:
    """Полный CRUD цикл: создание → чтение → обновление → удаление."""

    def test_полный_цикл_платежа(self, db, contract_id, employee_id, crm_card_id):
        """Создание → чтение → обновление → оплата → удаление"""
        # Создаём ставку для ненулевой суммы
        db.add_rate({
            'project_type': 'Индивидуальный',
            'role': 'ГАП',
            'rate_per_m2': 100.0,
        })

        # 1. Создание
        pid = db.add_payment({
            'contract_id': contract_id,
            'employee_id': employee_id,
            'role': 'ГАП',
            'payment_type': 'Полная оплата',
            'report_month': '2025-10',
            'crm_card_id': crm_card_id,
        })
        assert pid is not None

        # 2. Чтение
        payment = db.get_payment(pid)
        assert payment is not None
        assert payment['role'] == 'ГАП'
        # Площадь 100 м² * 100 ₽/м² = 10000
        assert payment['calculated_amount'] == 10000.0

        # 3. Обновление
        db.update_payment(pid, {'final_amount': 12000.0, 'report_month': '2025-11'})
        payment = db.get_payment(pid)
        assert payment['final_amount'] == 12000.0
        assert payment['report_month'] == '2025-11'

        # 4. Отметка как оплаченного
        db.mark_payment_as_paid(pid, employee_id)
        payment = db.get_payment(pid)
        assert payment['is_paid'] == 1

        # 5. Удаление
        db.delete_payment(pid)
        assert db.get_payment(pid) is None


# ============================================================================
# ТЕСТЫ: Edge cases
# ============================================================================

class TestEdgeCases:
    """Граничные случаи и обработка ошибок."""

    def test_get_payment_отрицательный_id(self, db):
        """get_payment с отрицательным ID возвращает None"""
        result = db.get_payment(-1)
        assert result is None

    def test_update_payment_пустой_data(self, db, payment_id):
        """update_payment с пустым dict не ломает запись"""
        # _build_set_clause с пустым dict — может быть ошибка SQL
        # Проверяем, что оригинальная запись не повреждена
        original = db.get_payment(payment_id)
        try:
            db.update_payment(payment_id, {})
        except Exception:
            pass  # Ожидаемо может упасть на пустом SET
        # Запись должна остаться нетронутой
        current = db.get_payment(payment_id)
        assert current['final_amount'] == original['final_amount']

    def test_get_salaries_двойной_фильтр(self, db, employee_id):
        """get_salaries с обоими фильтрами сужает результат"""
        db.add_salary(_make_salary_data(employee_id, report_month='2025-06'))
        db.add_salary(_make_salary_data(employee_id, report_month='2025-07'))
        salaries = db.get_salaries(report_month='2025-06', employee_id=employee_id)
        assert len(salaries) == 1
        assert salaries[0]['report_month'] == '2025-06'

    def test_add_rate_без_необязательных_полей(self, db):
        """add_rate работает только с обязательными полями"""
        result = db.add_rate({'role': 'Замерщик'})
        assert result is not None
        assert result['role'] == 'Замерщик'

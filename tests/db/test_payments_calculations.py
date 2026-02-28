# -*- coding: utf-8 -*-
"""
DB Tests: Платежи и расчёты DatabaseManager
Проверяет CRUD платежей, расчёт сумм по тарифам, фильтрацию.
"""

import pytest
import sys
import os
from unittest.mock import patch
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ============================================================
# Вспомогательные функции для создания тестовых данных
# ============================================================

def _create_client(db):
    """Создание тестового клиента."""
    return db.add_client({
        'client_type': 'Физическое лицо',
        'full_name': '__TEST__Pay Клиент',
        'phone': '+79991234567',
    })


def _create_employee(db, position='Дизайнер', name='__TEST__Pay Сотрудник', login=None):
    """Создание тестового сотрудника."""
    if not login:
        import random
        login = f'__test_pay_{random.randint(10000, 99999)}'
    return db.add_employee({
        'full_name': name,
        'phone': '+79990000002',
        'position': position,
        'login': login,
        'password': 'test123',
    })


@patch('database.db_manager.YANDEX_DISK_TOKEN', '')
def _create_contract(db, client_id, project_type='Индивидуальный', area=75.0, city='СПБ'):
    """Создание тестового договора."""
    import random
    return db.add_contract({
        'client_id': client_id,
        'project_type': project_type,
        'agent_type': 'ФЕСТИВАЛЬ',
        'city': city,
        'contract_number': f'__TEST__PAY_{random.randint(10000, 99999)}',
        'address': 'Тестовый адрес платежа',
        'area': area,
        'total_amount': 300000,
        'status': 'Новый заказ',
        'contract_period': 90,
        'contract_date': '2026-01-15',
    })


def _insert_rate(db, project_type, role, rate_per_m2=None, fixed_price=None,
                 stage_name=None, area_from=None, area_to=None, city=None, surveyor_price=None):
    """Создание тестового тарифа напрямую через SQL."""
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO rates (project_type, role, rate_per_m2, fixed_price, stage_name,
                          area_from, area_to, city, surveyor_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (project_type, role, rate_per_m2, fixed_price, stage_name,
          area_from, area_to, city, surveyor_price))
    conn.commit()
    rate_id = cursor.lastrowid
    db.close()
    return rate_id


# ============================================================
# Тесты CRUD платежей
# ============================================================

class TestPaymentsCRUD:
    """CRUD операции с платежами."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_add_payment(self, db):
        """Создание платежа через add_payment."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер addpay', '__test_addpay')
        card_id = db.get_crm_card_id_by_contract(contract_id)

        payment_id = db.add_payment({
            'contract_id': contract_id,
            'employee_id': emp_id,
            'role': 'Дизайнер',
            'stage_name': 'Дизайн-концепция',
            'payment_type': 'Полная оплата',
            'report_month': '2026-01',
            'crm_card_id': card_id,
        })

        assert payment_id is not None
        assert payment_id > 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_payment(self, db):
        """Получение платежа по ID."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер getpay', '__test_getpay')
        card_id = db.get_crm_card_id_by_contract(contract_id)

        payment_id = db.add_payment({
            'contract_id': contract_id,
            'employee_id': emp_id,
            'role': 'Дизайнер',
            'payment_type': 'Полная оплата',
            'report_month': '2026-02',
            'crm_card_id': card_id,
        })

        payment = db.get_payment(payment_id)
        assert payment is not None
        assert payment['id'] == payment_id
        assert payment['employee_id'] == emp_id
        assert payment['role'] == 'Дизайнер'

    def test_get_payment_nonexistent(self, db):
        """Получение несуществующего платежа."""
        result = db.get_payment(999999)
        assert result is None

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_payment(self, db):
        """Обновление платежа."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер updpay', '__test_updpay')
        card_id = db.get_crm_card_id_by_contract(contract_id)

        payment_id = db.add_payment({
            'contract_id': contract_id,
            'employee_id': emp_id,
            'role': 'Дизайнер',
            'payment_type': 'Полная оплата',
            'report_month': '2026-01',
            'crm_card_id': card_id,
        })

        result = db.update_payment(payment_id, {'report_month': '2026-03'})
        assert result is True

        payment = db.get_payment(payment_id)
        assert payment['report_month'] == '2026-03'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_delete_payment(self, db):
        """Удаление платежа."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер delpay', '__test_delpay')
        card_id = db.get_crm_card_id_by_contract(contract_id)

        payment_id = db.add_payment({
            'contract_id': contract_id,
            'employee_id': emp_id,
            'role': 'Дизайнер',
            'payment_type': 'Полная оплата',
            'report_month': '2026-01',
            'crm_card_id': card_id,
        })

        db.delete_payment(payment_id)
        assert db.get_payment(payment_id) is None

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_mark_payment_as_paid(self, db):
        """Отметка платежа как оплаченного."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер mark', '__test_mark')
        card_id = db.get_crm_card_id_by_contract(contract_id)

        payment_id = db.add_payment({
            'contract_id': contract_id,
            'employee_id': emp_id,
            'role': 'Дизайнер',
            'payment_type': 'Полная оплата',
            'report_month': '2026-01',
            'crm_card_id': card_id,
        })

        db.mark_payment_as_paid(payment_id, paid_by_id=emp_id)

        payment = db.get_payment(payment_id)
        assert payment['is_paid'] == 1
        assert payment['payment_status'] == 'paid'
        assert payment['paid_by'] == emp_id

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_payment_manual(self, db):
        """Ручное обновление суммы платежа."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер manual', '__test_manual')
        card_id = db.get_crm_card_id_by_contract(contract_id)

        payment_id = db.add_payment({
            'contract_id': contract_id,
            'employee_id': emp_id,
            'role': 'Дизайнер',
            'payment_type': 'Полная оплата',
            'report_month': '2026-01',
            'crm_card_id': card_id,
        })

        db.update_payment_manual(payment_id, 50000.0, report_month='2026-02')

        payment = db.get_payment(payment_id)
        assert payment['manual_amount'] == 50000.0
        assert payment['final_amount'] == 50000.0
        assert payment['is_manual'] == 1
        assert payment['report_month'] == '2026-02'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_payment_manual_no_month(self, db):
        """Ручное обновление без изменения месяца."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер manualnm', '__test_manualnm')
        card_id = db.get_crm_card_id_by_contract(contract_id)

        payment_id = db.add_payment({
            'contract_id': contract_id,
            'employee_id': emp_id,
            'role': 'Дизайнер',
            'payment_type': 'Полная оплата',
            'report_month': '2026-01',
            'crm_card_id': card_id,
        })

        db.update_payment_manual(payment_id, 75000.0)

        payment = db.get_payment(payment_id)
        assert payment['final_amount'] == 75000.0
        # report_month не изменился
        assert payment['report_month'] == '2026-01'


class TestPaymentsQueries:
    """Запросы платежей (фильтрация по контракту, надзору, месяцу, году)."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_payments_for_contract(self, db):
        """Получение платежей по договору."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер fcontract', '__test_fcontr')
        card_id = db.get_crm_card_id_by_contract(contract_id)

        db.add_payment({
            'contract_id': contract_id,
            'employee_id': emp_id,
            'role': 'Дизайнер',
            'payment_type': 'Полная оплата',
            'report_month': '2026-01',
            'crm_card_id': card_id,
        })

        payments = db.get_payments_for_contract(contract_id)
        assert isinstance(payments, list)
        assert len(payments) >= 1
        assert 'employee_name' in payments[0]  # JOIN с employees

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_payments_for_supervision(self, db):
        """Получение платежей для надзора."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        emp_id = _create_employee(db, 'ДАН', '__TEST__ДАН supv', '__test_dan_supv')

        # Создаём карточку надзора
        supervision_card_id = db.create_supervision_card(contract_id)

        # Создаём платёж с supervision_card_id
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO payments (contract_id, supervision_card_id, employee_id, role,
                                 calculated_amount, final_amount, payment_type, report_month)
            VALUES (?, ?, ?, 'ДАН', 10000, 10000, 'Полная оплата', '2026-02')
        ''', (contract_id, supervision_card_id, emp_id))
        conn.commit()
        db.close()

        payments = db.get_payments_for_supervision(contract_id)
        assert isinstance(payments, list)
        assert len(payments) >= 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_all_payments_month(self, db):
        """Получение всех выплат за месяц."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер allpay', '__test_allpay')
        card_id = db.get_crm_card_id_by_contract(contract_id)

        db.add_payment({
            'contract_id': contract_id,
            'employee_id': emp_id,
            'role': 'Дизайнер',
            'payment_type': 'Полная оплата',
            'report_month': '2026-03',
            'crm_card_id': card_id,
        })

        payments = db.get_all_payments(month=3, year=2026)
        assert isinstance(payments, list)
        # Должен быть хотя бы один платёж за март 2026
        assert len(payments) >= 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_year_payments(self, db):
        """Получение платежей за год."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер yearpay', '__test_yearpay')
        card_id = db.get_crm_card_id_by_contract(contract_id)

        db.add_payment({
            'contract_id': contract_id,
            'employee_id': emp_id,
            'role': 'Дизайнер',
            'payment_type': 'Полная оплата',
            'report_month': '2026-06',
            'crm_card_id': card_id,
        })

        payments = db.get_year_payments(year=2026)
        assert isinstance(payments, list)
        assert len(payments) >= 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_payments_by_type_salary(self, db):
        """Получение платежей типа 'Оклады'."""
        emp_id = _create_employee(db, 'Менеджер', '__TEST__Менеджер salary', '__test_salary')

        db.add_salary({
            'employee_id': emp_id,
            'payment_type': 'Оклад менеджера',
            'amount': 40000,
            'report_month': '2026-01',
            'project_type': 'Индивидуальный',
        })

        payments = db.get_payments_by_type('Оклады')
        assert isinstance(payments, list)
        assert len(payments) >= 1


class TestPaymentCalculations:
    """Расчёт суммы оплаты на основе тарифов."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_calculate_payment_individual_rate_per_m2(self, db):
        """Расчёт для индивидуального проекта: rate_per_m2 * площадь."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, 'Индивидуальный', area=100.0)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер calcind', '__test_calcind')

        # Создаём тариф: 150 руб/м²
        _insert_rate(db, 'Индивидуальный', 'Дизайнер', rate_per_m2=150.0)

        amount = db.calculate_payment_amount(contract_id, emp_id, 'Дизайнер')
        assert amount == 100.0 * 150.0  # 15000

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_calculate_payment_individual_with_stage(self, db):
        """Расчёт для индивидуального проекта с конкретной стадией."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, 'Индивидуальный', area=80.0)
        emp_id = _create_employee(db, 'Чертёжник', '__TEST__Чертёжник calcstg', '__test_calcstg')

        # Тариф для конкретной стадии
        _insert_rate(db, 'Индивидуальный', 'Чертёжник', rate_per_m2=100.0, stage_name='Рабочие чертежи')

        amount = db.calculate_payment_amount(contract_id, emp_id, 'Чертёжник', stage_name='Рабочие чертежи')
        assert amount == 80.0 * 100.0  # 8000

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_calculate_payment_template_fixed_price(self, db):
        """Расчёт для шаблонного проекта: фиксированная цена по диапазону площади."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, 'Шаблонный', area=60.0)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер calctemp', '__test_calctemp')

        # Тариф: от 50 до 100 м² — 25000 руб
        _insert_rate(db, 'Шаблонный', 'Дизайнер', fixed_price=25000.0, area_from=50, area_to=100)

        amount = db.calculate_payment_amount(contract_id, emp_id, 'Дизайнер')
        assert amount == 25000.0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_calculate_payment_no_rate(self, db):
        """Расчёт без тарифа — возвращает 0."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, 'Индивидуальный', area=100.0)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер norate', '__test_norate')

        # Не создаём тариф
        amount = db.calculate_payment_amount(contract_id, emp_id, 'Дизайнер')
        assert amount == 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_calculate_payment_surveyor(self, db):
        """Расчёт для замерщика: фиксированная цена по городу."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, 'Индивидуальный', area=100.0, city='МСК')
        emp_id = _create_employee(db, 'Замерщик', '__TEST__Замерщик calc', '__test_survcalc')

        _insert_rate(db, 'Индивидуальный', 'Замерщик', city='МСК', surveyor_price=5000.0)

        amount = db.calculate_payment_amount(contract_id, emp_id, 'Замерщик')
        assert amount == 5000.0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_calculate_payment_supervision(self, db):
        """Расчёт для надзора: rate_per_m2 из тарифов 'Авторский надзор'."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, 'Индивидуальный', area=120.0)
        emp_id = _create_employee(db, 'ДАН', '__TEST__ДАН calcsup', '__test_calcdsup')

        # Создаём карточку надзора
        sv_card_id = db.create_supervision_card(contract_id)

        # Тариф для надзора
        _insert_rate(db, 'Авторский надзор', 'ДАН', rate_per_m2=200.0)

        amount = db.calculate_payment_amount(contract_id, emp_id, 'ДАН', supervision_card_id=sv_card_id)
        assert amount == 120.0 * 200.0  # 24000

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_create_payment_record(self, db):
        """Создание записи о выплате с автоматическим расчётом."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, 'Индивидуальный', area=50.0)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер cprec', '__test_cprec')
        card_id = db.get_crm_card_id_by_contract(contract_id)

        # Тариф: 200 руб/м²
        _insert_rate(db, 'Индивидуальный', 'Дизайнер', rate_per_m2=200.0)

        payment_id = db.create_payment_record(
            contract_id, emp_id, 'Дизайнер',
            payment_type='Полная оплата',
            report_month='2026-02',
            crm_card_id=card_id
        )

        assert payment_id is not None
        payment = db.get_payment(payment_id)
        assert payment['calculated_amount'] == 50.0 * 200.0  # 10000
        assert payment['final_amount'] == 50.0 * 200.0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_create_payment_record_zero_rate(self, db):
        """Создание оплаты с нулевым тарифом — платёж всё равно создаётся."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, 'Индивидуальный', area=50.0)
        emp_id = _create_employee(db, 'ГАП', '__TEST__ГАП zero', '__test_gapzero')
        card_id = db.get_crm_card_id_by_contract(contract_id)

        # Не создаём тариф — сумма будет 0
        payment_id = db.create_payment_record(
            contract_id, emp_id, 'ГАП',
            payment_type='Полная оплата',
            crm_card_id=card_id
        )

        assert payment_id is not None
        payment = db.get_payment(payment_id)
        assert payment['calculated_amount'] == 0

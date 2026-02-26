# -*- coding: utf-8 -*-
"""
DB Tests: Статистика и аналитика DatabaseManager
Проверяет get_general_statistics, get_crm_statistics, get_dashboard_statistics,
get_employee_report_data, global_search, get_funnel_statistics, get_executor_load.
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
        'full_name': '__TEST__Stat Клиент',
        'phone': '+79991234567',
    })


def _create_employee(db, position='Дизайнер', name='__TEST__Stat Сотрудник', login=None):
    """Создание тестового сотрудника."""
    if not login:
        import random
        login = f'__test_stat_{random.randint(10000, 99999)}'
    return db.add_employee({
        'full_name': name,
        'phone': '+79990000004',
        'position': position,
        'login': login,
        'password': 'test123',
    })


@patch('database.db_manager.YANDEX_DISK_TOKEN', '')
def _create_contract(db, client_id, project_type='Индивидуальный', status='Новый заказ',
                     contract_number=None, area=75.0, agent_type='ФЕСТИВАЛЬ', city='СПБ'):
    """Создание тестового договора."""
    if not contract_number:
        import random
        contract_number = f'__TEST__STAT_{random.randint(10000, 99999)}'
    return db.add_contract({
        'client_id': client_id,
        'project_type': project_type,
        'agent_type': agent_type,
        'city': city,
        'contract_number': contract_number,
        'address': 'Тестовый адрес статистики',
        'area': area,
        'total_amount': 300000,
        'status': status,
        'contract_period': 90,
        'contract_date': '2026-01-15',
    })


# ============================================================
# Тесты общей статистики
# ============================================================

class TestGeneralStatistics:
    """Общая статистика."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_general_statistics_empty(self, db):
        """Общая статистика на пустой БД."""
        stats = db.get_general_statistics(year=2026, quarter=None, month=None)
        assert isinstance(stats, dict)
        assert 'total_completed' in stats
        assert 'total_area' in stats
        assert 'active_projects' in stats
        assert 'cancelled_projects' in stats
        assert 'by_project_type' in stats
        assert 'by_city' in stats
        assert stats['total_completed'] == 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_general_statistics_with_data(self, db):
        """Общая статистика с данными."""
        client_id = _create_client(db)
        _create_contract(db, client_id, 'Индивидуальный', 'СДАН', '__TEST__STAT_GEN1', area=100.0)
        _create_contract(db, client_id, 'Индивидуальный', 'Новый заказ', '__TEST__STAT_GEN2', area=50.0)

        stats = db.get_general_statistics(year=2026, quarter=None, month=None)
        assert stats['total_completed'] >= 1
        assert stats['active_projects'] >= 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_general_statistics_by_quarter(self, db):
        """Статистика по кварталу."""
        client_id = _create_client(db)
        _create_contract(db, client_id, 'Индивидуальный', 'СДАН', '__TEST__STAT_Q1', area=80.0)

        stats = db.get_general_statistics(year=2026, quarter='Q1', month=None)
        assert isinstance(stats, dict)
        # Контракт с contract_date 2026-01-15 попадает в Q1
        assert stats['total_completed'] >= 1


class TestDashboardStatistics:
    """Статистика дашборда."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_dashboard_statistics_empty(self, db):
        """Дашборд на пустой БД."""
        stats = db.get_dashboard_statistics()
        assert isinstance(stats, dict)
        assert 'individual_orders' in stats
        assert 'template_orders' in stats
        assert 'supervision_orders' in stats
        assert stats['individual_orders'] == 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_dashboard_statistics_with_data(self, db):
        """Дашборд с данными."""
        client_id = _create_client(db)
        _create_contract(db, client_id, 'Индивидуальный', 'Новый заказ', '__TEST__DASH_1', area=100.0)
        _create_contract(db, client_id, 'Шаблонный', 'Новый заказ', '__TEST__DASH_2', area=50.0)

        stats = db.get_dashboard_statistics()
        assert stats['individual_orders'] >= 1
        assert stats['individual_area'] >= 100.0
        assert stats['template_orders'] >= 1
        assert stats['template_area'] >= 50.0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_dashboard_statistics_filtered_by_year(self, db):
        """Дашборд с фильтром по году."""
        client_id = _create_client(db)
        _create_contract(db, client_id, 'Индивидуальный', 'Новый заказ', '__TEST__DASH_Y1', area=100.0)

        stats = db.get_dashboard_statistics(year=2026)
        assert stats['individual_orders'] >= 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_dashboard_statistics_filtered_by_project_type(self, db):
        """Дашборд с фильтром по типу агента."""
        client_id = _create_client(db)
        _create_contract(db, client_id, 'Индивидуальный', 'Новый заказ', '__TEST__DASH_PT', area=100.0,
                         agent_type='ФЕСТИВАЛЬ')

        stats = db.get_dashboard_statistics(project_type='ФЕСТИВАЛЬ')
        assert stats['individual_orders'] >= 1


class TestCRMStatistics:
    """Статистика CRM."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_crm_statistics(self, db):
        """Статистика CRM по типу проекта."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, 'Индивидуальный', 'Новый заказ', '__TEST__CRMST1')
        card_id = db.get_crm_card_id_by_contract(contract_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер crmstat', '__test_crmstat')
        manager = _create_employee(db, 'Менеджер', '__TEST__Менеджер crmstat', '__test_crmstatm')

        db.assign_stage_executor(card_id, 'Дизайн-концепция', emp_id, assigned_by=manager, deadline='2026-03-01')

        stats = db.get_crm_statistics('Индивидуальный', 'Год', 2026, None)
        assert isinstance(stats, list)
        assert len(stats) >= 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_crm_statistics_filtered(self, db):
        """Статистика CRM с фильтрацией."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, 'Индивидуальный', 'Новый заказ', '__TEST__CRMSTF1')
        card_id = db.get_crm_card_id_by_contract(contract_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер crmstatf', '__test_crmstatf')
        manager = _create_employee(db, 'Менеджер', '__TEST__Менеджер crmstatf', '__test_crmstatfm')

        db.assign_stage_executor(card_id, 'Дизайн-концепция', emp_id, assigned_by=manager, deadline='2026-03-01')

        stats = db.get_crm_statistics_filtered(
            project_type='Индивидуальный',
            period='Год',
            year=2026,
            quarter=None,
            month=None,
            project_id=None,
            executor_id=emp_id,
            stage_name=None,
            status_filter=None
        )
        assert isinstance(stats, list)
        assert len(stats) >= 1


class TestSupervisionStatistics:
    """Статистика надзора."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_supervision_statistics(self, db):
        """Статистика CRM надзора."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        db.create_supervision_card(contract_id)

        stats = db.get_supervision_statistics(period='Год', year=2026, quarter=None, month=None)
        assert isinstance(stats, list)

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_supervision_statistics_filtered(self, db):
        """Статистика надзора с фильтрами."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        card_id = db.create_supervision_card(contract_id)

        stats = db.get_supervision_statistics_filtered(
            period='Год', year=2026, quarter=None, month=None,
            address_id=None, stage=None, executor_id=None, manager_id=None, status=None
        )
        assert isinstance(stats, list)
        assert len(stats) >= 1


class TestEmployeeReport:
    """Отчёт по сотрудникам."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_employee_report_data(self, db):
        """Отчёт по сотрудникам — структура ответа."""
        report = db.get_employee_report_data(
            project_type='Индивидуальный',
            period='Год',
            year=2026,
            quarter=None,
            month=None
        )
        assert isinstance(report, dict)
        assert 'completed' in report
        assert 'area' in report
        assert 'deadlines' in report
        assert 'salaries' in report
        assert isinstance(report['completed'], list)

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_employee_report_data_with_data(self, db):
        """Отчёт с реальными данными."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, 'Индивидуальный', 'Новый заказ', '__TEST__EMPREP1', area=80.0)
        card_id = db.get_crm_card_id_by_contract(contract_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер emprep', '__test_emprep')
        manager = _create_employee(db, 'Менеджер', '__TEST__Менеджер emprep', '__test_emprepm')

        db.assign_stage_executor(card_id, 'Дизайн-концепция', emp_id, assigned_by=manager, deadline='2026-03-01')
        db.complete_stage_for_executor(card_id, 'Дизайн-концепция', emp_id)

        report = db.get_employee_report_data('Индивидуальный', 'Год', 2026, None, None)
        assert len(report['completed']) >= 1


class TestGlobalSearch:
    """Глобальный поиск."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_global_search_by_client_name(self, db):
        """Поиск по имени клиента."""
        db.add_client({
            'client_type': 'Физическое лицо',
            'full_name': '__TEST__Иванов Поиск',
            'phone': '+79991111111',
        })

        result = db.global_search('Иванов Поиск')
        assert isinstance(result, dict)
        assert 'results' in result
        assert 'total' in result
        assert result['total'] >= 1
        assert result['results'][0]['type'] == 'client'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_global_search_by_contract_number(self, db):
        """Поиск по номеру договора."""
        client_id = _create_client(db)
        _create_contract(db, client_id, contract_number='__TEST__SEARCH_42')

        result = db.global_search('SEARCH_42')
        assert result['total'] >= 1
        # Должен найти и контракт, и CRM-карточку
        types = [r['type'] for r in result['results']]
        assert 'contract' in types

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_global_search_by_address(self, db):
        """Поиск по адресу."""
        client_id = _create_client(db)
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO contracts (client_id, project_type, contract_number, address, area, status)
            VALUES (?, 'Индивидуальный', '__TEST__ADDR_99', 'Невский проспект 999', 50, 'Новый заказ')
        """, (client_id,))
        conn.commit()
        db.close()

        result = db.global_search('Невский проспект 999')
        assert result['total'] >= 1

    def test_global_search_short_query(self, db):
        """Поиск с коротким запросом (< 2 символов) — пустой результат."""
        result = db.global_search('А')
        assert result['total'] == 0
        assert result['results'] == []

    def test_global_search_empty_query(self, db):
        """Поиск с пустым запросом."""
        result = db.global_search('')
        assert result['total'] == 0


class TestFunnelStatistics:
    """Статистика воронки."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_funnel_statistics_empty(self, db):
        """Воронка на пустой БД (кроме admin)."""
        result = db.get_funnel_statistics()
        assert isinstance(result, dict)
        assert 'funnel' in result
        assert 'total' in result

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_funnel_statistics_with_data(self, db):
        """Воронка с данными."""
        client_id = _create_client(db)
        _create_contract(db, client_id, 'Индивидуальный', 'Новый заказ', '__TEST__FUNNEL_1')
        _create_contract(db, client_id, 'Индивидуальный', 'Новый заказ', '__TEST__FUNNEL_2')

        result = db.get_funnel_statistics(project_type='Индивидуальный')
        assert result['total'] >= 2
        assert 'Новый заказ' in result['funnel']

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_funnel_statistics_by_year(self, db):
        """Воронка с фильтром по году."""
        client_id = _create_client(db)
        _create_contract(db, client_id, 'Индивидуальный', 'Новый заказ', '__TEST__FUNNEL_Y1')

        result = db.get_funnel_statistics(year=2026)
        assert result['total'] >= 1


class TestExecutorLoad:
    """Нагрузка на исполнителей."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_executor_load_empty(self, db):
        """Нагрузка без данных."""
        result = db.get_executor_load()
        assert isinstance(result, list)

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_executor_load_with_data(self, db):
        """Нагрузка с назначенными стадиями."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер load', '__test_load')
        manager = _create_employee(db, 'Менеджер', '__TEST__Менеджер load', '__test_loadm')

        db.assign_stage_executor(card_id, 'Дизайн-концепция', emp_id, assigned_by=manager, deadline='2026-03-01')

        result = db.get_executor_load()
        assert len(result) >= 1
        assert result[0]['active_stages'] >= 1


class TestContractYearsAndAgentTypes:
    """Годы договоров и типы агентов."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_contract_years(self, db):
        """Получение списка годов из договоров."""
        client_id = _create_client(db)
        _create_contract(db, client_id)

        years = db.get_contract_years()
        assert isinstance(years, list)
        assert 2026 in years
        # Текущий год и следующий год всегда включены
        current_year = datetime.now().year
        assert current_year in years

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_agent_types(self, db):
        """Получение списка типов агентов."""
        client_id = _create_client(db)
        _create_contract(db, client_id, agent_type='ФЕСТИВАЛЬ')

        agents = db.get_agent_types()
        assert isinstance(agents, list)
        assert 'ФЕСТИВАЛЬ' in agents

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_agent_types_empty(self, db):
        """Типы агентов на пустой БД (без договоров)."""
        agents = db.get_agent_types()
        assert isinstance(agents, list)


class TestSalariesDashboardStats:
    """Статистика зарплат на дашборде."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_salaries_dashboard_stats_empty(self, db):
        """Статистика зарплат на пустой БД."""
        stats = db.get_salaries_dashboard_stats()
        assert isinstance(stats, dict)
        assert 'total_paid' in stats
        assert stats['total_paid'] == 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_salaries_dashboard_stats_with_paid(self, db):
        """Статистика зарплат с оплаченными платежами."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер salstat', '__test_salstat')
        card_id = db.get_crm_card_id_by_contract(contract_id)

        payment_id = db.add_payment({
            'contract_id': contract_id,
            'employee_id': emp_id,
            'role': 'Дизайнер',
            'payment_type': 'Полная оплата',
            'report_month': '2026-01',
            'crm_card_id': card_id,
        })

        # Устанавливаем final_amount и отмечаем как paid
        db.update_payment_manual(payment_id, 10000.0, report_month='2026-01')
        db.mark_payment_as_paid(payment_id, paid_by_id=emp_id)

        stats = db.get_salaries_dashboard_stats(year=2026, month=1)
        assert stats['total_paid'] >= 10000.0
        assert stats['paid_by_year'] >= 10000.0
        assert stats['paid_by_month'] >= 10000.0

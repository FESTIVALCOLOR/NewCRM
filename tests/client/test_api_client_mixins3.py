# -*- coding: utf-8 -*-
"""Тесты для api_client миксинов: statistics, compat, rates, messenger, timeline, salaries"""

import pytest
from unittest.mock import MagicMock, patch


class FakeClient:
    """Клиент-заглушка для тестирования миксинов"""
    def __init__(self):
        self.base_url = 'http://test:8000'
        self._request = MagicMock()
        self._handle_response = MagicMock(return_value={'ok': True})


class FakeCompatClient:
    """Клиент-заглушка с методами, вызываемыми CompatMixin"""
    def __init__(self):
        self.base_url = 'http://test:8000'
        self._request = MagicMock()
        self._handle_response = MagicMock(return_value={'ok': True})
        # Методы из других миксинов, которые вызывает CompatMixin
        self.get_employee = MagicMock(return_value={'id': 1, 'full_name': 'Тест'})
        self.get_client = MagicMock(return_value={'id': 1, 'name': 'Клиент'})
        self.login = MagicMock(return_value={'access_token': 'token123'})
        self.get_current_user = MagicMock(return_value={'id': 1, 'login': 'admin'})
        self.create_crm_card = MagicMock(return_value={'id': 10})
        self.create_supervision_card = MagicMock(return_value={'id': 20})
        self.create_rate = MagicMock(return_value={'id': 30})
        self.get_rate = MagicMock(return_value={'id': 1, 'price': 500})
        self.get_salary = MagicMock(return_value={'id': 1, 'amount': 50000})
        self.create_payment = MagicMock(return_value={'id': 40})
        self.create_file_record = MagicMock(return_value={'id': 50})
        self.delete_file_record = MagicMock(return_value=True)
        self.get_supervision_card = MagicMock(return_value={'id': 1})
        self.move_crm_card = MagicMock()
        self.move_supervision_card = MagicMock()
        self.get_supervision_cards = MagicMock(return_value=[])
        self.get_supervision_statistics = MagicMock(return_value={})
        self.get_crm_card = MagicMock(return_value={'id': 1, 'contract_id': 100})
        self.get_employees = MagicMock(return_value=[
            {'id': 1, 'login': 'admin', 'department': 'IT'},
            {'id': 2, 'login': 'user1', 'department': 'Design'}
        ])
        self.get_contracts = MagicMock(return_value=[
            {'id': 1, 'contract_number': '№1-2026', 'city': 'Москва', 'agent_type': 'Прямой'},
            {'id': 2, 'contract_number': '№2-2026', 'city': 'СПб', 'agent_type': 'Партнёр'}
        ])
        self.get_crm_cards = MagicMock(return_value=[
            {'id': 1, 'contract_id': 100, 'contract_number': '№1-2026', 'address': 'ул. Тест', 'city': 'Москва'}
        ])
        self.delete_crm_card = MagicMock()
        self.delete_contract = MagicMock()
        self.assign_stage_executor = MagicMock()


# ─── StatisticsMixin ─────────────────────────────────────────────────────

class TestStatisticsMixin:
    """Тесты StatisticsMixin"""

    @pytest.fixture
    def client(self):
        from utils.api_client.statistics_mixin import StatisticsMixin

        class C(StatisticsMixin, FakeClient):
            pass

        return C()

    def test_get_dashboard_statistics_no_params(self, client):
        client.get_dashboard_statistics()
        client._request.assert_called_once()
        args = client._request.call_args
        assert 'statistics/dashboard' in args[0][1]

    def test_get_dashboard_statistics_with_params(self, client):
        client.get_dashboard_statistics(year=2026, month=3, agent_type='Агент')
        args = client._request.call_args
        assert args[1]['params']['year'] == 2026
        assert args[1]['params']['month'] == 3
        assert args[1]['params']['agent_type'] == 'Агент'

    def test_get_employee_statistics(self, client):
        client.get_employee_statistics(year=2026)
        args = client._request.call_args
        assert 'statistics/employees' in args[0][1]

    def test_get_contracts_by_period(self, client):
        client.get_contracts_by_period(year=2025, group_by='quarter', project_type='Индивидуальный')
        args = client._request.call_args
        assert args[1]['params']['year'] == 2025
        assert args[1]['params']['group_by'] == 'quarter'

    def test_get_project_statistics(self, client):
        client.get_project_statistics('Индивидуальный', year=2025, quarter=2, city='Москва')
        args = client._request.call_args
        assert args[1]['params']['project_type'] == 'Индивидуальный'

    def test_get_supervision_statistics(self, client):
        client.get_supervision_statistics(year=2026)
        args = client._request.call_args
        assert 'statistics/supervision' in args[0][1]

    def test_get_crm_statistics(self, client):
        client.get_crm_statistics('Индивидуальный', 'month', 2026, month=1)
        args = client._request.call_args
        assert 'statistics/crm' in args[0][1]

    def test_get_general_statistics(self, client):
        client.get_general_statistics(2026, quarter=1)
        args = client._request.call_args
        assert 'statistics/general' in args[0][1]

    def test_get_funnel_statistics(self, client):
        client.get_funnel_statistics(year=2026)
        args = client._request.call_args
        assert 'statistics/funnel' in args[0][1]

    def test_get_executor_load(self, client):
        client.get_executor_load(year=2026, month=3)
        args = client._request.call_args
        assert 'statistics/executor-load' in args[0][1]

    def test_get_clients_dashboard_stats(self, client):
        client.get_clients_dashboard_stats(year=2026, agent_type='Партнер')
        args = client._request.call_args
        assert 'dashboard/clients' in args[0][1]

    def test_get_contracts_dashboard_stats(self, client):
        client.get_contracts_dashboard_stats()
        args = client._request.call_args
        assert 'dashboard/contracts' in args[0][1]

    def test_get_crm_dashboard_stats(self, client):
        client.get_crm_dashboard_stats('Шаблонный', agent_type='Прямой')
        args = client._request.call_args
        assert 'dashboard/crm' in args[0][1]

    def test_get_employees_dashboard_stats(self, client):
        client.get_employees_dashboard_stats()
        client._request.assert_called_once()

    def test_get_salaries_dashboard_stats(self, client):
        client.get_salaries_dashboard_stats(year=2026, month=1)
        args = client._request.call_args
        assert 'dashboard/salaries' in args[0][1]

    def test_get_agent_types(self, client):
        client.get_agent_types()
        args = client._request.call_args
        assert 'agent-types' in args[0][1]

    def test_get_contract_years(self, client):
        client.get_contract_years()
        args = client._request.call_args
        assert 'contract-years' in args[0][1]

    def test_get_salaries_payment_type_stats(self, client):
        client.get_salaries_payment_type_stats('individual', year=2026)
        args = client._request.call_args
        assert 'salaries-by-type' in args[0][1]

    def test_get_salaries_all_payments_stats(self, client):
        client.get_salaries_all_payments_stats(year=2026, month=3)
        args = client._request.call_args
        assert 'salaries-all' in args[0][1]

    def test_get_employee_report_data(self, client):
        client.get_employee_report_data('Индивидуальный', 'month', 2026, month=1)
        args = client._request.call_args
        assert 'employee-report' in args[0][1]


# ─── CompatMixin ─────────────────────────────────────────────────────────

class TestCompatMixin:
    """Тесты CompatMixin — тонкие обёртки поверх других миксинов"""

    @pytest.fixture
    def client(self):
        from utils.api_client.compat_mixin import CompatMixin

        class C(CompatMixin, FakeCompatClient):
            pass

        return C()

    def test_get_employee_by_id(self, client):
        result = client.get_employee_by_id(1)
        client.get_employee.assert_called_once_with(1)
        assert result['id'] == 1

    def test_get_client_by_id(self, client):
        result = client.get_client_by_id(42)
        client.get_client.assert_called_once_with(42)

    def test_get_employee_by_login_success(self, client):
        result = client.get_employee_by_login('admin', 'pass123')
        client.login.assert_called_once_with('admin', 'pass123')
        client.get_current_user.assert_called_once()
        assert result is not None

    def test_get_employee_by_login_no_token(self, client):
        client.login.return_value = {}
        result = client.get_employee_by_login('admin', 'wrong')
        assert result is None

    def test_get_employee_by_login_exception(self, client):
        client.login.side_effect = Exception('err')
        result = client.get_employee_by_login('admin', 'pass')
        assert result is None

    def test_add_crm_card(self, client):
        result = client.add_crm_card({'contract_id': 1, 'column_name': 'Замер'})
        client.create_crm_card.assert_called_once_with({'contract_id': 1, 'column_name': 'Замер'})
        assert result == 10

    def test_add_crm_card_none_result(self, client):
        client.create_crm_card.return_value = None
        result = client.add_crm_card({'contract_id': 1})
        assert result is None

    def test_add_supervision_card(self, client):
        result = client.add_supervision_card({'contract_id': 1})
        client.create_supervision_card.assert_called_once()
        assert result == 20

    def test_add_rate(self, client):
        result = client.add_rate({'role': 'Дизайнер', 'price': 500})
        client.create_rate.assert_called_once()
        assert result == 30

    def test_get_rate_by_id(self, client):
        result = client.get_rate_by_id(1)
        client.get_rate.assert_called_once_with(1)
        assert result['price'] == 500

    def test_get_salary_by_id(self, client):
        result = client.get_salary_by_id(5)
        client.get_salary.assert_called_once_with(5)

    def test_add_payment(self, client):
        result = client.add_payment({'amount': 10000})
        client.create_payment.assert_called_once()
        assert result == 40

    def test_add_contract_file(self, client):
        result = client.add_contract_file({'name': 'file.pdf'})
        client.create_file_record.assert_called_once()
        assert result == 50

    def test_delete_contract_file(self, client):
        result = client.delete_contract_file(1)
        client.delete_file_record.assert_called_once_with(1)

    def test_get_supervision_card_data(self, client):
        result = client.get_supervision_card_data(1)
        client.get_supervision_card.assert_called_once_with(1)

    def test_sync_approval_stages_to_json(self, client):
        result = client.sync_approval_stages_to_json(1)
        assert result is True

    def test_update_crm_card_column(self, client):
        result = client.update_crm_card_column(1, 'Дизайн')
        client.move_crm_card.assert_called_once_with(1, 'Дизайн')
        assert result is True

    def test_update_crm_card_column_exception(self, client):
        client.move_crm_card.side_effect = Exception('err')
        result = client.update_crm_card_column(1, 'Дизайн')
        assert result is False

    def test_update_supervision_card_column(self, client):
        result = client.update_supervision_card_column(1, 'Этап 1')
        client.move_supervision_card.assert_called_once_with(1, 'Этап 1')
        assert result is True

    def test_update_supervision_card_column_exception(self, client):
        client.move_supervision_card.side_effect = Exception('err')
        result = client.update_supervision_card_column(1, 'Этап 1')
        assert result is False

    def test_get_supervision_cards_active(self, client):
        client.get_supervision_cards_active()
        client.get_supervision_cards.assert_called_once_with(status="active")

    def test_get_supervision_cards_archived(self, client):
        client.get_supervision_cards_archived()
        client.get_supervision_cards.assert_called_once_with(status="archived")

    def test_check_login_exists_true(self, client):
        result = client.check_login_exists('admin')
        assert result is True

    def test_check_login_exists_false(self, client):
        result = client.check_login_exists('nonexistent')
        assert result is False

    def test_check_login_exists_exception(self, client):
        client.get_employees.side_effect = Exception('err')
        result = client.check_login_exists('admin')
        assert result is False

    def test_get_next_contract_number(self, client):
        result = client.get_next_contract_number(2026)
        assert result == 3  # max из №1-2026 и №2-2026 = 2, следующий = 3

    def test_get_next_contract_number_no_contracts(self, client):
        client.get_contracts.return_value = []
        result = client.get_next_contract_number(2026)
        assert result == 1

    def test_get_next_contract_number_exception(self, client):
        client.get_contracts.side_effect = Exception('err')
        result = client.get_next_contract_number(2026)
        assert result == 1

    def test_get_crm_card_id_by_contract(self, client):
        result = client.get_crm_card_id_by_contract(100)
        assert result == 1

    def test_get_crm_card_id_by_contract_not_found(self, client):
        result = client.get_crm_card_id_by_contract(999)
        assert result is None

    def test_get_crm_card_id_by_contract_exception(self, client):
        client.get_crm_cards.side_effect = Exception('err')
        result = client.get_crm_card_id_by_contract(100)
        assert result is None

    def test_delete_order_with_crm_card(self, client):
        result = client.delete_order(1, crm_card_id=2)
        client.delete_crm_card.assert_called_once_with(2)
        client.delete_contract.assert_called_once_with(1)
        assert result is True

    def test_delete_order_without_crm_card(self, client):
        result = client.delete_order(1)
        client.delete_crm_card.assert_not_called()
        client.delete_contract.assert_called_once_with(1)
        assert result is True

    def test_delete_order_exception(self, client):
        client.delete_contract.side_effect = Exception('err')
        result = client.delete_order(1)
        assert result is False

    def test_get_projects_by_type(self, client):
        result = client.get_projects_by_type('Индивидуальный')
        assert len(result) == 1
        assert result[0]['contract_id'] == 100

    def test_get_projects_by_type_exception(self, client):
        client.get_crm_cards.side_effect = Exception('err')
        result = client.get_projects_by_type('Индивидуальный')
        assert result == []

    def test_get_unique_cities(self, client):
        result = client.get_unique_cities()
        assert 'Москва' in result
        assert 'СПб' in result

    def test_get_unique_cities_exception(self, client):
        client.get_contracts.side_effect = Exception('err')
        result = client.get_unique_cities()
        assert result == []

    def test_get_unique_agent_types(self, client):
        result = client.get_unique_agent_types()
        assert 'Прямой' in result

    def test_get_unique_agent_types_exception(self, client):
        client.get_contracts.side_effect = Exception('err')
        result = client.get_unique_agent_types()
        assert result == []

    def test_get_payments(self, client):
        client.get_payments()
        client._request.assert_called_once()
        assert 'payments' in client._request.call_args[0][1]

    def test_get_payments_by_contract(self, client):
        client.get_payments_by_contract(1)
        args = client._request.call_args
        assert args[1]['params']['contract_id'] == 1

    def test_get_payments_by_employee(self, client):
        client.get_payments_by_employee(1)
        args = client._request.call_args
        assert args[1]['params']['employee_id'] == 1

    def test_get_unpaid_payments(self, client):
        client.get_unpaid_payments()
        args = client._request.call_args
        assert args[1]['params']['is_paid'] is False

    def test_get_all_payments(self, client):
        client.get_all_payments(month=1, year=2026)
        args = client._request.call_args
        assert 'payments' in args[0][1]

    def test_get_all_payments_no_params(self, client):
        client.get_all_payments()
        args = client._request.call_args
        assert args[1].get('params') is None

    def test_get_all_payments_optimized(self, client):
        client.get_all_payments_optimized(year=2026, month=3, quarter=1)
        args = client._request.call_args
        assert 'all-optimized' in args[0][1]

    def test_get_all_payments_optimized_exception(self, client):
        client._request.side_effect = Exception('err')
        result = client.get_all_payments_optimized(year=2026)
        assert result == []

    def test_get_payments_summary(self, client):
        client.get_payments_summary(2026, month=3)
        args = client._request.call_args
        assert 'summary' in args[0][1]

    def test_get_rates_by_project_type(self, client):
        client.get_rates_by_project_type('Индивидуальный')
        args = client._request.call_args
        assert args[1]['params']['project_type'] == 'Индивидуальный'

    def test_get_salaries_by_employee(self, client):
        client.get_salaries_by_employee(1)
        args = client._request.call_args
        assert args[1]['params']['employee_id'] == 1

    def test_get_files_by_contract(self, client):
        client.get_files_by_contract(1)
        args = client._request.call_args
        assert 'files/contract/1' in args[0][1]

    def test_get_file_templates(self, client):
        client.get_file_templates()
        args = client._request.call_args
        assert 'file-templates' in args[0][1]

    def test_get_file_templates_exception(self, client):
        client._request.side_effect = Exception('err')
        result = client.get_file_templates()
        assert result == []

    def test_get_cities(self, client):
        client.get_cities()
        args = client._request.call_args
        assert 'cities' in args[0][1]

    def test_assign_stage_executor_db(self, client):
        result = client.assign_stage_executor_db(1, 'Замер', 2, assigned_by=3)
        client.assign_stage_executor.assert_called_once()
        assert result is True

    def test_assign_stage_executor_db_with_deadline(self, client):
        result = client.assign_stage_executor_db(1, 'Замер', 2, assigned_by=3, deadline='2026-03-01')
        call_data = client.assign_stage_executor.call_args[0][1]
        assert call_data['deadline'] == '2026-03-01'

    def test_assign_stage_executor_db_exception(self, client):
        client.assign_stage_executor.side_effect = Exception('err')
        result = client.assign_stage_executor_db(1, 'Замер', 2, assigned_by=3)
        assert result is False

    def test_get_contract_id_by_crm_card(self, client):
        result = client.get_contract_id_by_crm_card(1)
        assert result == 100

    def test_get_contract_id_by_crm_card_exception(self, client):
        client.get_crm_card.side_effect = Exception('err')
        result = client.get_contract_id_by_crm_card(1)
        assert result is None

    def test_get_contracts_by_project_type(self, client):
        client.get_contracts_by_project_type('Шаблонный')
        args = client._request.call_args
        assert args[1]['params']['project_type'] == 'Шаблонный'

    def test_get_previous_executor_by_position(self, client):
        client._handle_response.return_value = {'executor_id': 5}
        result = client.get_previous_executor_by_position(1, 'Дизайнер')
        assert result == 5

    def test_get_previous_executor_by_position_exception(self, client):
        client._request.side_effect = Exception('err')
        result = client.get_previous_executor_by_position(1, 'Дизайнер')
        assert result is None

    def test_get_employees_by_department(self, client):
        result = client.get_employees_by_department('IT')
        assert len(result) == 1
        assert result[0]['login'] == 'admin'

    def test_get_supervision_statistics_report(self, client):
        client.get_supervision_statistics_report(2026, quarter=1)
        client.get_supervision_statistics.assert_called_once_with(2026, 1, None, None, None)

    def test_get_crm_card_data(self, client):
        result = client.get_crm_card_data(1)
        client.get_crm_card.assert_called_with(1)
        assert result['contract_id'] == 100


# ─── RatesMixin ──────────────────────────────────────────────────────────

class TestRatesMixin:
    """Тесты RatesMixin"""

    @pytest.fixture
    def client(self):
        from utils.api_client.rates_mixin import RatesMixin

        class C(RatesMixin, FakeClient):
            pass

        return C()

    def test_get_rates(self, client):
        client.get_rates(project_type='Индивидуальный', role='Дизайнер')
        args = client._request.call_args
        assert 'rates' in args[0][1]

    def test_get_rate(self, client):
        client.get_rate(1)
        client._request.assert_called_once()

    def test_create_rate(self, client):
        client.create_rate({'role': 'Дизайнер', 'price': 500})
        client._request.assert_called_once()

    def test_update_rate(self, client):
        client.update_rate(1, {'price': 600})
        client._request.assert_called_once()

    def test_delete_rate(self, client):
        client.delete_rate(1)
        client._request.assert_called_once()

    def test_get_template_rates(self, client):
        client.get_template_rates(role='Дизайнер')
        client._request.assert_called_once()

    def test_save_template_rate(self, client):
        client.save_template_rate('Дизайнер', 50, 100, 500)
        client._request.assert_called_once()

    def test_save_individual_rate(self, client):
        client.save_individual_rate('Дизайнер', 500, stage_name='Дизайн')
        client._request.assert_called_once()

    def test_delete_individual_rate(self, client):
        client.delete_individual_rate('Дизайнер', stage_name='Дизайн')
        client._request.assert_called_once()

    def test_save_supervision_rate(self, client):
        client.save_supervision_rate('Этап 1', 300, 200)
        client._request.assert_called_once()

    def test_save_surveyor_rate(self, client):
        client.save_surveyor_rate('Москва', 5000)
        client._request.assert_called_once()


# ─── MessengerMixin ──────────────────────────────────────────────────────

class TestMessengerMixin:
    """Тесты MessengerMixin"""

    @pytest.fixture
    def client(self):
        from utils.api_client.messenger_mixin import MessengerMixin

        class C(MessengerMixin, FakeClient):
            pass

        return C()

    def test_create_messenger_chat(self, client):
        client.create_messenger_chat(1, 'telegram', members=[{'id': 1}])
        client._request.assert_called_once()
        args = client._request.call_args
        assert args[1]['json']['crm_card_id'] == 1

    def test_create_messenger_chat_defaults(self, client):
        client.create_messenger_chat(1)
        args = client._request.call_args
        assert args[1]['json']['messenger_type'] == 'telegram'
        assert args[1]['json']['members'] == []

    def test_bind_messenger_chat(self, client):
        client.bind_messenger_chat(1, 'https://t.me/+abc', members=[])
        client._request.assert_called_once()
        args = client._request.call_args
        assert args[1]['json']['invite_link'] == 'https://t.me/+abc'

    def test_get_messenger_chat_by_card(self, client):
        client.get_messenger_chat_by_card(1)
        client._request.assert_called_once()

    def test_get_messenger_chat_by_card_exception(self, client):
        client._request.side_effect = Exception('err')
        result = client.get_messenger_chat_by_card(1)
        assert result is None

    def test_get_supervision_chat(self, client):
        client.get_supervision_chat(1)
        client._request.assert_called_once()

    def test_get_supervision_chat_exception(self, client):
        client._request.side_effect = Exception('err')
        result = client.get_supervision_chat(1)
        assert result is None

    def test_create_supervision_chat(self, client):
        client.create_supervision_chat(1, 'telegram', members=[])
        client._request.assert_called_once()
        args = client._request.call_args
        assert args[1]['json']['supervision_card_id'] == 1

    def test_delete_messenger_chat(self, client):
        client.delete_messenger_chat(1)
        client._request.assert_called_once()

    def test_send_messenger_message(self, client):
        client.send_messenger_message(1, 'Привет', deadline_date='2026-03-01')
        args = client._request.call_args
        assert args[1]['json']['text'] == 'Привет'
        assert args[1]['json']['deadline_date'] == '2026-03-01'

    def test_send_messenger_message_no_deadline(self, client):
        client.send_messenger_message(1, 'Привет')
        args = client._request.call_args
        assert 'deadline_date' not in args[1]['json']

    def test_send_messenger_files(self, client):
        client.send_messenger_files(1, file_ids=[1, 2])
        args = client._request.call_args
        assert args[1]['json']['file_ids'] == [1, 2]

    def test_send_messenger_invites(self, client):
        client.send_messenger_invites(1, member_ids=[1, 2])
        args = client._request.call_args
        assert args[1]['json']['member_ids'] == [1, 2]

    def test_trigger_script(self, client):
        client._request.return_value = MagicMock(status_code=200)
        result = client.trigger_script(1, 'welcome', entity_type='crm')
        assert result is True

    def test_trigger_script_exception(self, client):
        client._request.side_effect = Exception('err')
        result = client.trigger_script(1, 'welcome')
        assert result is False

    def test_get_messenger_scripts(self, client):
        client.get_messenger_scripts(project_type='Индивидуальный')
        args = client._request.call_args
        assert args[1]['params']['project_type'] == 'Индивидуальный'

    def test_get_messenger_scripts_no_params(self, client):
        client.get_messenger_scripts()
        args = client._request.call_args
        assert args[1]['params'] == {}

    def test_create_messenger_script(self, client):
        client.create_messenger_script({'name': 'Test', 'text': 'Hello'})
        client._request.assert_called_once()

    def test_update_messenger_script(self, client):
        client.update_messenger_script(1, {'text': 'Updated'})
        client._request.assert_called_once()

    def test_delete_messenger_script(self, client):
        client.delete_messenger_script(1)
        client._request.assert_called_once()

    def test_toggle_messenger_script(self, client):
        client.toggle_messenger_script(1)
        client._request.assert_called_once()

    def test_get_messenger_settings(self, client):
        client.get_messenger_settings()
        client._request.assert_called_once()

    def test_update_messenger_settings(self, client):
        client.update_messenger_settings([{'key': 'val'}])
        args = client._request.call_args
        assert args[1]['json']['settings'] == [{'key': 'val'}]

    def test_get_messenger_status(self, client):
        client.get_messenger_status()
        client._request.assert_called_once()

    def test_get_messenger_status_exception(self, client):
        client._request.side_effect = Exception('err')
        result = client.get_messenger_status()
        assert result['telegram_bot_available'] is False

    def test_mtproto_send_code(self, client):
        client.mtproto_send_code()
        client._request.assert_called_once()

    def test_mtproto_resend_sms(self, client):
        client.mtproto_resend_sms()
        client._request.assert_called_once()

    def test_mtproto_verify_code(self, client):
        client.mtproto_verify_code('12345')
        args = client._request.call_args
        assert args[1]['json']['code'] == '12345'

    def test_mtproto_session_status(self, client):
        client.mtproto_session_status()
        client._request.assert_called_once()

    def test_mtproto_session_status_exception(self, client):
        client._request.side_effect = Exception('err')
        result = client.mtproto_session_status()
        assert result == {"valid": False}


# ─── TimelineMixin ───────────────────────────────────────────────────────

class TestTimelineMixin:
    """Тесты TimelineMixin"""

    @pytest.fixture
    def client(self):
        from utils.api_client.timeline_mixin import TimelineMixin

        class C(TimelineMixin, FakeClient):
            pass

        return C()

    def test_get_project_timeline(self, client):
        client.get_project_timeline(1)
        client._request.assert_called_once()

    def test_init_project_timeline(self, client):
        client.init_project_timeline(1, {'stages': []})
        client._request.assert_called_once()

    def test_reinit_project_timeline(self, client):
        client.reinit_project_timeline(1, {'stages': []})
        client._request.assert_called_once()

    def test_update_timeline_entry(self, client):
        client.update_timeline_entry(1, 'DESIGN', {'status': 'done'})
        client._request.assert_called_once()

    def test_get_timeline_summary(self, client):
        client.get_timeline_summary(1)
        client._request.assert_called_once()

    def test_export_timeline_excel(self, client):
        client._request.return_value = MagicMock(content=b'excel', status_code=200)
        client.export_timeline_excel(1)
        client._request.assert_called_once()

    def test_export_timeline_pdf(self, client):
        client._request.return_value = MagicMock(content=b'pdf', status_code=200)
        client.export_timeline_pdf(1)
        client._request.assert_called_once()

    def test_get_supervision_timeline(self, client):
        client.get_supervision_timeline(1)
        client._request.assert_called_once()

    def test_init_supervision_timeline(self, client):
        client.init_supervision_timeline(1, {'stages': []})
        client._request.assert_called_once()

    def test_update_supervision_timeline_entry(self, client):
        client.update_supervision_timeline_entry(1, 'STAGE1', {'status': 'done'})
        client._request.assert_called_once()

    def test_get_supervision_timeline_summary(self, client):
        client.get_supervision_timeline_summary(1)
        client._request.assert_called_once()

    def test_export_supervision_timeline_excel(self, client):
        client._request.return_value = MagicMock(content=b'excel', status_code=200)
        client.export_supervision_timeline_excel(1)
        client._request.assert_called_once()

    def test_export_supervision_timeline_pdf(self, client):
        client._request.return_value = MagicMock(content=b'pdf', status_code=200)
        client.export_supervision_timeline_pdf(1)
        client._request.assert_called_once()


# ─── SalariesMixin ───────────────────────────────────────────────────────

class TestSalariesMixin:
    """Тесты SalariesMixin"""

    @pytest.fixture
    def client(self):
        from utils.api_client.salaries_mixin import SalariesMixin

        class C(SalariesMixin, FakeClient):
            pass

        return C()

    def test_get_salaries(self, client):
        client.get_salaries(report_month='2026-03', employee_id=1)
        client._request.assert_called_once()

    def test_get_salary(self, client):
        client.get_salary(1)
        client._request.assert_called_once()

    def test_create_salary(self, client):
        client.create_salary({'amount': 50000, 'employee_id': 1})
        client._request.assert_called_once()

    def test_update_salary(self, client):
        client.update_salary(1, {'amount': 60000})
        client._request.assert_called_once()

    def test_delete_salary(self, client):
        client.delete_salary(1)
        client._request.assert_called_once()

    def test_get_salary_report(self, client):
        client.get_salary_report(report_month='2026-03', payment_type='individual')
        client._request.assert_called_once()

    def test_add_salary(self, client):
        client.add_salary({'amount': 40000})
        client._request.assert_called_once()

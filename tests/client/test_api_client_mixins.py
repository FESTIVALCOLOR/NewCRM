# -*- coding: utf-8 -*-
"""
Покрытие api_client mixins: auth, clients, contracts, employees, crm.
~50 тестов.

Подход: мокаем _request через patch.object, проверяем HTTP method, URL, body.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------

@pytest.fixture
def api():
    """Создать APIClient с мок-запросами."""
    from utils.api_client import APIClient
    client = APIClient('http://test:8000')
    client.token = 'test-token'
    client.refresh_token = 'test-refresh'
    client.employee_id = 1
    # Отключаем авто-рефреш, чтобы не мешал тестам
    client._token_exp = None
    return client


def _make_response(status_code=200, json_data=None, headers=None):
    """Создать мок Response с нужными полями."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.headers = headers or {}
    resp.text = ''
    return resp


# ===========================================================================
# AuthMixin — 8 тестов
# ===========================================================================

class TestAuthMixin:
    """Тесты для AuthMixin: login, refresh, logout, get_current_user."""

    def test_login_success(self, api):
        """login — успешный вход, установка token/refresh_token/employee_id."""
        login_data = {
            'access_token': 'new-access',
            'refresh_token': 'new-refresh',
            'employee_id': 42,
        }
        mock_resp = _make_response(200, login_data)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.login('admin', 'secret')

        # Проверяем вызов _request
        req.assert_called_once()
        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert '/api/auth/login' in args[1]
        assert kwargs['data'] == {'username': 'admin', 'password': 'secret'}

        # Проверяем результат и побочные эффекты
        assert result == login_data
        assert api.token == 'new-access'
        assert api.refresh_token == 'new-refresh'
        assert api.employee_id == 42

    def test_login_sends_form_urlencoded(self, api):
        """login — отправляет Content-Type: application/x-www-form-urlencoded."""
        mock_resp = _make_response(200, {
            'access_token': 'tok', 'refresh_token': 'ref', 'employee_id': 1
        })
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.login('user', 'pass')

        _, kwargs = req.call_args
        assert kwargs['headers']['Content-Type'] == 'application/x-www-form-urlencoded'

    def test_refresh_access_token_success(self, api):
        """refresh_access_token — успешное обновление токена."""
        new_data = {
            'access_token': 'refreshed-access',
            'refresh_token': 'refreshed-refresh',
            'employee_id': 99,
        }
        mock_resp = _make_response(200, new_data)
        with patch.object(api, '_request', return_value=mock_resp):
            result = api.refresh_access_token()

        assert result is True
        assert api.token == 'refreshed-access'
        assert api.refresh_token == 'refreshed-refresh'
        assert api.employee_id == 99

    def test_refresh_access_token_fail_status(self, api):
        """refresh_access_token — сервер вернул не 200 → False."""
        mock_resp = _make_response(401)
        with patch.object(api, '_request', return_value=mock_resp):
            result = api.refresh_access_token()

        assert result is False

    def test_refresh_access_token_no_refresh_token(self, api):
        """refresh_access_token — нет refresh_token → сразу False."""
        api.refresh_token = None
        result = api.refresh_access_token()
        assert result is False

    def test_refresh_access_token_exception(self, api):
        """refresh_access_token — исключение при запросе → False."""
        with patch.object(api, '_request', side_effect=Exception('сеть')):
            result = api.refresh_access_token()
        assert result is False

    def test_logout_success(self, api):
        """logout — успешный выход, очистка токена."""
        mock_resp = _make_response(200)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.logout()

        req.assert_called_once()
        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert '/api/auth/logout' in args[1]
        assert result is True
        # Токены должны быть очищены
        assert api.token is None
        assert api.refresh_token is None

    def test_logout_failure_still_clears_token(self, api):
        """logout — при ошибке всё равно очищает токен (блок finally)."""
        with patch.object(api, '_request', side_effect=Exception('ошибка')):
            result = api.logout()

        assert result is False
        assert api.token is None

    def test_get_current_user(self, api):
        """get_current_user — GET /api/auth/me."""
        user_data = {'id': 1, 'username': 'admin', 'role': 'director'}
        mock_resp = _make_response(200, user_data)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_current_user()

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/auth/me')
        assert result == user_data


# ===========================================================================
# ClientsMixin — 9 тестов
# ===========================================================================

class TestClientsMixin:
    """Тесты для ClientsMixin: get, create, update, delete, paginated."""

    def test_get_clients(self, api):
        """get_clients — GET /api/clients с параметрами skip, limit."""
        clients = [{'id': 1, 'name': 'Иванов'}]
        mock_resp = _make_response(200, clients)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_clients(skip=10, limit=50)

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert '/api/clients' in args[1]
        assert kwargs['params'] == {'skip': 10, 'limit': 50}
        assert result == clients

    def test_get_clients_defaults(self, api):
        """get_clients — значения по умолчанию skip=0, limit=100."""
        mock_resp = _make_response(200, [])
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.get_clients()

        _, kwargs = req.call_args
        assert kwargs['params'] == {'skip': 0, 'limit': 100}

    def test_get_client(self, api):
        """get_client — GET /api/clients/{id}."""
        client_data = {'id': 5, 'name': 'Петров'}
        mock_resp = _make_response(200, client_data)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_client(5)

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/clients/5')
        assert result == client_data

    def test_create_client(self, api):
        """create_client — POST /api/clients с json body."""
        new_client = {'name': 'Сидоров', 'phone': '+79001234567'}
        created = {'id': 10, **new_client}
        mock_resp = _make_response(200, created)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.create_client(new_client)

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert '/api/clients' in args[1]
        assert kwargs['json'] == new_client
        assert result == created

    def test_update_client(self, api):
        """update_client — PUT /api/clients/{id} с json body."""
        updates = {'phone': '+79009999999'}
        updated = {'id': 3, 'name': 'Иванов', **updates}
        mock_resp = _make_response(200, updated)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.update_client(3, updates)

        args, kwargs = req.call_args
        assert args[0] == 'PUT'
        assert args[1].endswith('/api/clients/3')
        assert kwargs['json'] == updates
        assert result == updated

    def test_delete_client(self, api):
        """delete_client — DELETE /api/clients/{id}, возвращает True."""
        mock_resp = _make_response(200, {})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.delete_client(7)

        args, _ = req.call_args
        assert args[0] == 'DELETE'
        assert args[1].endswith('/api/clients/7')
        assert result is True

    def test_get_clients_paginated(self, api):
        """get_clients_paginated — возвращает (data, total) из X-Total-Count."""
        clients = [{'id': 1}, {'id': 2}]
        mock_resp = _make_response(200, clients, headers={'X-Total-Count': '150'})
        with patch.object(api, '_request', return_value=mock_resp):
            data, total = api.get_clients_paginated(skip=0, limit=2)

        assert data == clients
        assert total == 150

    def test_get_clients_paginated_no_header(self, api):
        """get_clients_paginated — нет X-Total-Count → total = len(data)."""
        clients = [{'id': 1}, {'id': 2}, {'id': 3}]
        mock_resp = _make_response(200, clients, headers={})
        with patch.object(api, '_request', return_value=mock_resp):
            data, total = api.get_clients_paginated()

        assert total == 3

    def test_get_clients_paginated_params(self, api):
        """get_clients_paginated — передаёт skip/limit в params."""
        mock_resp = _make_response(200, [], headers={'X-Total-Count': '0'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.get_clients_paginated(skip=20, limit=10)

        _, kwargs = req.call_args
        assert kwargs['params'] == {'skip': 20, 'limit': 10}


# ===========================================================================
# ContractsMixin — 11 тестов
# ===========================================================================

class TestContractsMixin:
    """Тесты для ContractsMixin: CRUD + count + paginated + files + check_number."""

    def test_get_contracts(self, api):
        """get_contracts — GET /api/contracts."""
        contracts = [{'id': 1, 'contract_number': 'D-001'}]
        mock_resp = _make_response(200, contracts)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_contracts(skip=5, limit=25)

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert '/api/contracts' in args[1]
        assert kwargs['params'] == {'skip': 5, 'limit': 25}
        assert result == contracts

    def test_get_contract(self, api):
        """get_contract — GET /api/contracts/{id}."""
        contract = {'id': 10, 'contract_number': 'D-010'}
        mock_resp = _make_response(200, contract)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_contract(10)

        args, _ = req.call_args
        assert args[1].endswith('/api/contracts/10')
        assert result == contract

    def test_create_contract(self, api):
        """create_contract — POST /api/contracts с json body."""
        data = {'contract_number': 'D-100', 'client_id': 5}
        created = {'id': 100, **data}
        mock_resp = _make_response(200, created)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.create_contract(data)

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert kwargs['json'] == data
        assert result == created

    def test_update_contract(self, api):
        """update_contract — PUT /api/contracts/{id}."""
        updates = {'status': 'В работе'}
        updated = {'id': 10, **updates}
        mock_resp = _make_response(200, updated)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.update_contract(10, updates)

        args, kwargs = req.call_args
        assert args[0] == 'PUT'
        assert args[1].endswith('/api/contracts/10')
        assert kwargs['json'] == updates
        assert result == updated

    def test_delete_contract(self, api):
        """delete_contract — DELETE /api/contracts/{id}, возвращает True."""
        mock_resp = _make_response(200, {})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.delete_contract(15)

        args, _ = req.call_args
        assert args[0] == 'DELETE'
        assert args[1].endswith('/api/contracts/15')
        assert result is True

    def test_get_contracts_count_no_filters(self, api):
        """get_contracts_count — без фильтров, пустые params."""
        mock_resp = _make_response(200, {'count': 42})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_contracts_count()

        args, kwargs = req.call_args
        assert args[1].endswith('/api/contracts/count')
        assert kwargs['params'] == {}
        assert result == 42

    def test_get_contracts_count_with_filters(self, api):
        """get_contracts_count — с фильтрами status, project_type, year."""
        mock_resp = _make_response(200, {'count': 7})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_contracts_count(
                status='В работе', project_type='Индивидуальный', year=2025
            )

        _, kwargs = req.call_args
        assert kwargs['params'] == {
            'status': 'В работе',
            'project_type': 'Индивидуальный',
            'year': 2025,
        }
        assert result == 7

    def test_get_contracts_count_non_dict_result(self, api):
        """get_contracts_count — сервер вернул не dict → 0."""
        mock_resp = _make_response(200, 'unexpected')
        with patch.object(api, '_request', return_value=mock_resp):
            result = api.get_contracts_count()
        assert result == 0

    def test_get_contracts_paginated(self, api):
        """get_contracts_paginated — возвращает (data, total)."""
        contracts = [{'id': 1}]
        mock_resp = _make_response(200, contracts, headers={'X-Total-Count': '88'})
        with patch.object(api, '_request', return_value=mock_resp):
            data, total = api.get_contracts_paginated(skip=0, limit=10)

        assert data == contracts
        assert total == 88

    def test_update_contract_files(self, api):
        """update_contract_files — PATCH /api/contracts/{id}/files."""
        files_data = {'measurement_image_link': 'http://example.com/img.jpg'}
        mock_resp = _make_response(200, {'id': 3, **files_data})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.update_contract_files(3, files_data)

        args, kwargs = req.call_args
        assert args[0] == 'PATCH'
        assert args[1].endswith('/api/contracts/3/files')
        assert kwargs['json'] == files_data

    def test_check_contract_number_exists_true(self, api):
        """check_contract_number_exists — номер найден → True."""
        contracts = [
            {'id': 1, 'contract_number': 'D-001'},
            {'id': 2, 'contract_number': 'D-002'},
        ]
        with patch.object(api, 'get_contracts', return_value=contracts):
            assert api.check_contract_number_exists('D-002') is True

    def test_check_contract_number_exists_false(self, api):
        """check_contract_number_exists — номер не найден → False."""
        contracts = [{'id': 1, 'contract_number': 'D-001'}]
        with patch.object(api, 'get_contracts', return_value=contracts):
            assert api.check_contract_number_exists('D-999') is False

    def test_check_contract_number_exists_exclude_id(self, api):
        """check_contract_number_exists — исключаем текущий id при редактировании."""
        contracts = [{'id': 5, 'contract_number': 'D-005'}]
        with patch.object(api, 'get_contracts', return_value=contracts):
            # Тот же номер, но exclude_id совпадает — не считается дублем
            assert api.check_contract_number_exists('D-005', exclude_id=5) is False

    def test_check_contract_number_exists_exception(self, api):
        """check_contract_number_exists — ошибка → False."""
        with patch.object(api, 'get_contracts', side_effect=Exception('сеть')):
            assert api.check_contract_number_exists('D-001') is False


# ===========================================================================
# EmployeesMixin — 8 тестов
# ===========================================================================

class TestEmployeesMixin:
    """Тесты для EmployeesMixin: CRUD + get_by_position."""

    def test_get_employees(self, api):
        """get_employees — GET /api/employees."""
        employees = [{'id': 1, 'name': 'Иванов'}]
        mock_resp = _make_response(200, employees)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_employees()

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert '/api/employees' in args[1]
        assert kwargs['params'] == {'skip': 0, 'limit': 100}
        assert result == employees

    def test_get_employees_custom_params(self, api):
        """get_employees — кастомные skip/limit."""
        mock_resp = _make_response(200, [])
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.get_employees(skip=10, limit=50)

        _, kwargs = req.call_args
        assert kwargs['params'] == {'skip': 10, 'limit': 50}

    def test_get_employee(self, api):
        """get_employee — GET /api/employees/{id}."""
        emp = {'id': 3, 'name': 'Петров', 'position': 'Дизайнер'}
        mock_resp = _make_response(200, emp)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_employee(3)

        args, _ = req.call_args
        assert args[1].endswith('/api/employees/3')
        assert result == emp

    def test_create_employee(self, api):
        """create_employee — POST /api/employees, success_codes=[200, 201]."""
        data = {'name': 'Новый', 'position': 'Менеджер'}
        created = {'id': 10, **data}
        mock_resp = _make_response(201, created)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            # _handle_response вызывается с success_codes=[200, 201]
            # поэтому 201 должен быть успешным
            result = api.create_employee(data)

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert kwargs['json'] == data
        assert result == created

    def test_update_employee(self, api):
        """update_employee — PUT /api/employees/{id}."""
        updates = {'position': 'Старший дизайнер'}
        updated = {'id': 3, 'name': 'Петров', **updates}
        mock_resp = _make_response(200, updated)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.update_employee(3, updates)

        args, kwargs = req.call_args
        assert args[0] == 'PUT'
        assert args[1].endswith('/api/employees/3')
        assert kwargs['json'] == updates
        assert result == updated

    def test_delete_employee(self, api):
        """delete_employee — DELETE /api/employees/{id}, возвращает True."""
        mock_resp = _make_response(200, {})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.delete_employee(8)

        args, _ = req.call_args
        assert args[0] == 'DELETE'
        assert args[1].endswith('/api/employees/8')
        assert result is True

    def test_get_employees_by_position(self, api):
        """get_employees_by_position — фильтрация по position на клиенте."""
        all_emps = [
            {'id': 1, 'name': 'A', 'position': 'Дизайнер', 'secondary_position': None},
            {'id': 2, 'name': 'B', 'position': 'Менеджер', 'secondary_position': 'Дизайнер'},
            {'id': 3, 'name': 'C', 'position': 'Менеджер', 'secondary_position': None},
        ]
        with patch.object(api, 'get_employees', return_value=all_emps):
            result = api.get_employees_by_position('Дизайнер')

        # Должны вернуться id=1 (position) и id=2 (secondary_position)
        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[1]['id'] == 2

    def test_get_employees_by_position_empty(self, api):
        """get_employees_by_position — нет совпадений → пустой список."""
        all_emps = [{'id': 1, 'position': 'Менеджер', 'secondary_position': None}]
        with patch.object(api, 'get_employees', return_value=all_emps):
            result = api.get_employees_by_position('Бухгалтер')
        assert result == []


# ===========================================================================
# CrmMixin — 14 тестов
# ===========================================================================

class TestCrmMixin:
    """Тесты для CrmMixin: карточки, стадии, workflow."""

    def test_get_crm_cards(self, api):
        """get_crm_cards — GET /api/crm/cards с project_type."""
        cards = [{'id': 1, 'column_name': 'Новый заказ'}]
        mock_resp = _make_response(200, cards)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_crm_cards('Индивидуальный')

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert '/api/crm/cards' in args[1]
        assert kwargs['params'] == {'project_type': 'Индивидуальный'}
        assert result == cards

    def test_get_crm_card_success(self, api):
        """get_crm_card — GET /api/crm/cards/{id} успешно."""
        card = {'id': 5, 'column_name': 'В работе'}
        mock_resp = _make_response(200, card)
        with patch.object(api, '_request', return_value=mock_resp):
            result = api.get_crm_card(5)
        assert result == card

    def test_create_crm_card(self, api):
        """create_crm_card — POST /api/crm/cards."""
        data = {'contract_id': 10, 'column_name': 'Новый заказ'}
        created = {'id': 20, **data}
        mock_resp = _make_response(200, created)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.create_crm_card(data)

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert kwargs['json'] == data
        assert result == created

    def test_update_crm_card(self, api):
        """update_crm_card — PATCH /api/crm/cards/{id}."""
        updates = {'column_name': 'Сдан'}
        mock_resp = _make_response(200, {'id': 5, **updates})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.update_crm_card(5, updates)

        args, kwargs = req.call_args
        assert args[0] == 'PATCH'
        assert args[1].endswith('/api/crm/cards/5')
        assert kwargs['json'] == updates

    def test_move_crm_card(self, api):
        """move_crm_card — PATCH /api/crm/cards/{id}/column."""
        mock_resp = _make_response(200, {'id': 5, 'column_name': 'В работе'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.move_crm_card(5, 'В работе')

        args, kwargs = req.call_args
        assert args[0] == 'PATCH'
        assert args[1].endswith('/api/crm/cards/5/column')
        assert kwargs['json'] == {'column_name': 'В работе'}

    def test_delete_crm_card(self, api):
        """delete_crm_card — DELETE /api/crm/cards/{id}."""
        mock_resp = _make_response(200, {})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.delete_crm_card(5)

        args, _ = req.call_args
        assert args[0] == 'DELETE'
        assert args[1].endswith('/api/crm/cards/5')
        assert result is True

    def test_assign_stage_executor(self, api):
        """assign_stage_executor — POST .../stage-executor."""
        stage_data = {'stage_name': 'Замер', 'executor_id': 3}
        mock_resp = _make_response(200, {'id': 1, **stage_data})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.assign_stage_executor(10, stage_data)

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert '/api/crm/cards/10/stage-executor' in args[1]
        assert kwargs['json'] == stage_data

    def test_complete_stage(self, api):
        """complete_stage — PATCH .../stage-executor/{stage_name}."""
        mock_resp = _make_response(200, {'completed': True})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.complete_stage(10, 'Замер', completed=True)

        args, kwargs = req.call_args
        assert args[0] == 'PATCH'
        assert '/stage-executor/Замер' in args[1]
        assert kwargs['json'] == {'completed': True}

    def test_get_archived_crm_cards(self, api):
        """get_archived_crm_cards — params содержат archived=True."""
        mock_resp = _make_response(200, [])
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.get_archived_crm_cards('Шаблонный')

        _, kwargs = req.call_args
        assert kwargs['params']['archived'] is True
        assert kwargs['params']['project_type'] == 'Шаблонный'

    def test_get_archived_crm_cards_no_type(self, api):
        """get_archived_crm_cards — без project_type."""
        mock_resp = _make_response(200, [])
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.get_archived_crm_cards()

        _, kwargs = req.call_args
        assert 'project_type' not in kwargs['params']
        assert kwargs['params']['archived'] is True

    def test_workflow_submit(self, api):
        """workflow_submit — POST .../workflow/submit."""
        mock_resp = _make_response(200, {'status': 'submitted'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.workflow_submit(7)

        args, _ = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/crm/cards/7/workflow/submit')

    def test_workflow_reject_with_path(self, api):
        """workflow_reject — передаёт revision_file_path."""
        mock_resp = _make_response(200, {'status': 'rejected'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.workflow_reject(7, corrections_path='/disk/corrections')

        _, kwargs = req.call_args
        assert kwargs['json'] == {'revision_file_path': '/disk/corrections'}

    def test_workflow_reject_no_path(self, api):
        """workflow_reject — без пути → пустой json."""
        mock_resp = _make_response(200, {'status': 'rejected'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.workflow_reject(7)

        _, kwargs = req.call_args
        assert kwargs['json'] == {}

    def test_complete_stage_for_executor_success(self, api):
        """complete_stage_for_executor — успех → True."""
        mock_resp = _make_response(200, {})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.complete_stage_for_executor(10, 'Замер', executor_id=3)

        assert result is True
        args, kwargs = req.call_args
        assert args[0] == 'PATCH'
        assert '/stage-executor/Замер/complete' in args[1]
        assert kwargs['json'] == {'executor_id': 3}

    def test_complete_stage_for_executor_fail(self, api):
        """complete_stage_for_executor — ошибка → False."""
        with patch.object(api, '_request', side_effect=Exception('ошибка')):
            result = api.complete_stage_for_executor(10, 'Замер', executor_id=3)
        assert result is False


# ===========================================================================
# Обработка ошибок — общие сценарии (5 тестов)
# ===========================================================================

class TestErrorHandling:
    """Тесты обработки ошибок _handle_response через миксины."""

    def test_auth_error_401(self, api):
        """401 → APIAuthError."""
        from utils.api_client.exceptions import APIAuthError
        mock_resp = _make_response(401)
        mock_resp.headers = {'content-type': 'application/json'}
        mock_resp.json.return_value = {'detail': 'Не авторизован'}
        with patch.object(api, '_request', return_value=mock_resp):
            with pytest.raises(APIAuthError):
                api.get_clients()

    def test_auth_error_403(self, api):
        """403 → APIAuthError с деталями."""
        from utils.api_client.exceptions import APIAuthError
        mock_resp = _make_response(403)
        mock_resp.headers = {'content-type': 'application/json'}
        mock_resp.json.return_value = {'detail': 'Доступ запрещён'}
        with patch.object(api, '_request', return_value=mock_resp):
            with pytest.raises(APIAuthError, match='Доступ запрещён'):
                api.get_employees()

    def test_server_error_500(self, api):
        """500 → APIResponseError."""
        from utils.api_client.exceptions import APIResponseError
        mock_resp = _make_response(500)
        mock_resp.headers = {'content-type': 'application/json'}
        mock_resp.json.return_value = {'detail': 'Internal error'}
        with patch.object(api, '_request', return_value=mock_resp):
            with pytest.raises(APIResponseError):
                api.get_contract(1)

    def test_connection_error_propagated(self, api):
        """APIConnectionError пробрасывается из _request."""
        from utils.api_client.exceptions import APIConnectionError
        with patch.object(api, '_request', side_effect=APIConnectionError('offline')):
            with pytest.raises(APIConnectionError):
                api.get_clients()

    def test_handle_response_no_json(self, api):
        """Ответ без JSON body (например DELETE) → True."""
        mock_resp = _make_response(200)
        mock_resp.json.side_effect = ValueError('No JSON')
        with patch.object(api, '_request', return_value=mock_resp):
            result = api.delete_client(1)
        assert result is True

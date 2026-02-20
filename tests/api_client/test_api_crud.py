# -*- coding: utf-8 -*-
"""
Mock-тесты CRUD методов APIClient — pytest + unittest.mock.

Реальный APIClient инстанцируется, но session.request замокан.
Проверяем: правильные URL, параметры, обработку ответов, ошибки.

ИТОГО: ~73 теста
"""

import pytest
import sys
import time
import requests
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, PropertyMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.api_client import (
    APIClient, APIError, APITimeoutError, APIConnectionError,
    APIAuthError, APIResponseError
)


# ─── Фикстуры ───────────────────────────────────────────────────

@pytest.fixture
def api():
    """APIClient с замоканной session — не делает реальных HTTP запросов."""
    client = APIClient("http://test:8000")
    client.token = "test_token"
    client.headers["Authorization"] = "Bearer test_token"
    client._last_offline_time = None
    client._first_request = False
    client._is_online = True
    return client


def _mock_resp(status_code=200, json_data=None, content=b'', headers=None):
    """Создать mock Response с нужным статусом и JSON."""
    resp = Mock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.content = content
    resp.text = str(json_data)
    resp.headers = headers or {'content-type': 'application/json'}
    return resp


# ═══════════════════════════════════════════════════════════════════
# TestClientsCRUD — Клиенты
# ═══════════════════════════════════════════════════════════════════

class TestClientsCRUD:
    """CRUD методы для клиентов."""

    def test_get_clients_url(self, api):
        """get_clients вызывает GET /api/clients с params."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, [])) as mock:
            api.get_clients(skip=10, limit=50)
            mock.assert_called_once()
            args, kwargs = mock.call_args
            assert args == ('GET', 'http://test:8000/api/clients')
            assert kwargs['params'] == {'skip': 10, 'limit': 50}

    def test_get_clients_returns_list(self, api):
        """get_clients возвращает список из ответа."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, [{'id': 1}, {'id': 2}])):
            result = api.get_clients()
            assert isinstance(result, list)
            assert len(result) == 2

    def test_get_client_by_id(self, api):
        """get_client формирует URL с ID."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 5})) as mock:
            result = api.get_client(5)
            args, _ = mock.call_args
            assert args[1] == 'http://test:8000/api/clients/5'
            assert result['id'] == 5

    def test_create_client_post(self, api):
        """create_client отправляет POST с json телом."""
        data = {'full_name': 'Тест', 'phone': '+7 (900) 000-00-00'}
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 1})) as mock:
            result = api.create_client(data)
            args, kwargs = mock.call_args
            assert args[0] == 'POST'
            assert kwargs['json'] == data
            assert result['id'] == 1

    def test_update_client_put(self, api):
        """update_client отправляет PUT."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 1})) as mock:
            api.update_client(1, {'full_name': 'Обновлено'})
            args, kwargs = mock.call_args
            assert args == ('PUT', 'http://test:8000/api/clients/1')
            assert kwargs['json'] == {'full_name': 'Обновлено'}

    def test_delete_client_returns_true(self, api):
        """delete_client возвращает True при 200."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})):
            assert api.delete_client(1) is True


# ═══════════════════════════════════════════════════════════════════
# TestContractsCRUD — Договоры
# ═══════════════════════════════════════════════════════════════════

class TestContractsCRUD:
    """CRUD методы для договоров."""

    def test_get_contracts_url(self, api):
        """get_contracts формирует правильный URL."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, [])) as mock:
            api.get_contracts()
            args, kwargs = mock.call_args
            assert args[1] == 'http://test:8000/api/contracts'

    def test_get_contract_by_id(self, api):
        """get_contract с конкретным ID."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 3})) as mock:
            result = api.get_contract(3)
            assert 'http://test:8000/api/contracts/3' in mock.call_args[0][1]
            assert result['id'] == 3

    def test_create_contract_post(self, api):
        """create_contract отправляет POST."""
        data = {'contract_number': '01/2026', 'client_id': 1}
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 1})) as mock:
            api.create_contract(data)
            assert mock.call_args[0][0] == 'POST'
            assert mock.call_args[1]['json'] == data

    def test_update_contract_put(self, api):
        """update_contract отправляет PUT."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})) as mock:
            api.update_contract(5, {'address': 'Новый адрес'})
            assert mock.call_args[0] == ('PUT', 'http://test:8000/api/contracts/5')

    def test_update_contract_files_patch(self, api):
        """update_contract_files отправляет PATCH."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})) as mock:
            api.update_contract_files(5, {'measurement_image_link': 'http://...'})
            assert mock.call_args[0] == ('PATCH', 'http://test:8000/api/contracts/5/files')

    def test_delete_contract(self, api):
        """delete_contract возвращает True."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})):
            assert api.delete_contract(1) is True

    def test_check_contract_number_exists(self, api):
        """check_contract_number_exists проверяет дубликат номера."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'exists': True})):
            result = api.check_contract_number_exists('01/2026')
            assert result is not None


# ═══════════════════════════════════════════════════════════════════
# TestEmployeesCRUD — Сотрудники
# ═══════════════════════════════════════════════════════════════════

class TestEmployeesCRUD:
    """CRUD методы для сотрудников."""

    def test_get_employees(self, api):
        """get_employees возвращает список."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, [{'id': 1}])):
            result = api.get_employees()
            assert isinstance(result, list)

    def test_get_employees_by_position(self, api):
        """get_employees_by_position фильтрует на клиенте."""
        employees = [
            {'id': 1, 'position': 'Дизайнер', 'secondary_position': None},
            {'id': 2, 'position': 'Менеджер', 'secondary_position': 'Дизайнер'},
            {'id': 3, 'position': 'СДП', 'secondary_position': None},
        ]
        with patch.object(api.session, 'request', return_value=_mock_resp(200, employees)):
            result = api.get_employees_by_position('Дизайнер')
            assert len(result) == 2  # id=1 (primary) + id=2 (secondary)

    def test_get_employee_by_id(self, api):
        """get_employee с ID."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 2, 'position': 'СДП'})):
            result = api.get_employee(2)
            assert result['position'] == 'СДП'

    def test_create_employee(self, api):
        """create_employee отправляет POST."""
        data = {'full_name': 'Новый', 'position': 'Менеджер', 'login': 'new'}
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 10})) as mock:
            api.create_employee(data)
            assert mock.call_args[0][0] == 'POST'

    def test_update_employee(self, api):
        """update_employee отправляет PUT."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})) as mock:
            api.update_employee(2, {'position': 'ГАП'})
            assert mock.call_args[0][0] == 'PUT'

    def test_delete_employee(self, api):
        """delete_employee возвращает True."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})):
            assert api.delete_employee(2) is True


# ═══════════════════════════════════════════════════════════════════
# TestCRMCardsCRUD — CRM карточки
# ═══════════════════════════════════════════════════════════════════

class TestCRMCardsCRUD:
    """CRUD методы для CRM карточек."""

    def test_get_crm_cards_with_type(self, api):
        """get_crm_cards передаёт project_type."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, [])) as mock:
            api.get_crm_cards('Индивидуальный')
            assert 'Индивидуальный' in str(mock.call_args)

    def test_get_crm_card_by_id(self, api):
        """get_crm_card формирует URL."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 7})):
            result = api.get_crm_card(7)
            assert result['id'] == 7

    def test_create_crm_card(self, api):
        """create_crm_card POST."""
        data = {'contract_id': 1, 'project_type': 'Индивидуальный'}
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 1})) as mock:
            api.create_crm_card(data)
            assert mock.call_args[0][0] == 'POST'

    def test_update_crm_card(self, api):
        """update_crm_card PUT/PATCH."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})):
            result = api.update_crm_card(1, {'column_name': 'В ожидании'})
            assert result is not None

    def test_move_crm_card(self, api):
        """move_crm_card вызывает специальный endpoint."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})) as mock:
            api.move_crm_card(1, 'Стадия 1')
            assert 'move' in mock.call_args[0][1] or 'Стадия 1' in str(mock.call_args)

    def test_delete_crm_card(self, api):
        """delete_crm_card DELETE."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})):
            assert api.delete_crm_card(1) is True

    def test_get_crm_cards_returns_list(self, api):
        """get_crm_cards возвращает список карточек."""
        cards = [{'id': 1, 'column_name': 'Новые'}, {'id': 2, 'column_name': 'В ожидании'}]
        with patch.object(api.session, 'request', return_value=_mock_resp(200, cards)):
            result = api.get_crm_cards('Шаблонный')
            assert len(result) == 2


# ═══════════════════════════════════════════════════════════════════
# TestSupervisionCRUD — Надзор
# ═══════════════════════════════════════════════════════════════════

class TestSupervisionCRUD:
    """CRUD методы для карточек надзора."""

    def test_get_supervision_cards(self, api):
        """get_supervision_cards с status."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, [])):
            result = api.get_supervision_cards('active')
            assert isinstance(result, list)

    def test_get_supervision_card_by_id(self, api):
        """get_supervision_card по ID."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 3})):
            result = api.get_supervision_card(3)
            assert result['id'] == 3

    def test_create_supervision_card(self, api):
        """create_supervision_card POST."""
        data = {'contract_id': 1}
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 1})) as mock:
            api.create_supervision_card(data)
            assert mock.call_args[0][0] == 'POST'

    def test_update_supervision_card(self, api):
        """update_supervision_card PUT."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})):
            result = api.update_supervision_card(1, {'status': 'paused'})
            assert result is not None

    def test_pause_supervision_card(self, api):
        """pause_supervision_card POST."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})) as mock:
            api.pause_supervision_card(1, 'Причина паузы')
            assert 'pause' in mock.call_args[0][1]

    def test_resume_supervision_card(self, api):
        """resume_supervision_card POST."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})) as mock:
            api.resume_supervision_card(1)
            assert 'resume' in mock.call_args[0][1]


# ═══════════════════════════════════════════════════════════════════
# TestPaymentsCRUD — Платежи
# ═══════════════════════════════════════════════════════════════════

class TestPaymentsCRUD:
    """CRUD методы для платежей."""

    def test_get_payments_for_contract(self, api):
        """get_payments_for_contract формирует URL с contract_id."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, [])) as mock:
            api.get_payments_for_contract(10)
            assert '10' in mock.call_args[0][1]

    def test_create_payment(self, api):
        """create_payment POST."""
        data = {'contract_id': 1, 'amount': 50000, 'payment_type': 'project'}
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 1})) as mock:
            api.create_payment(data)
            assert mock.call_args[0][0] == 'POST'

    def test_get_payment_by_id(self, api):
        """get_payment по ID."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 5, 'amount': 30000})):
            result = api.get_payment(5)
            assert result['amount'] == 30000

    def test_update_payment(self, api):
        """update_payment PUT."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})) as mock:
            api.update_payment(5, {'status': 'paid'})
            assert mock.call_args[0][0] == 'PUT'

    def test_delete_payment(self, api):
        """delete_payment DELETE."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})):
            result = api.delete_payment(5)
            assert result is not None

    def test_mark_payment_as_paid(self, api):
        """mark_payment_as_paid вызывает специальный endpoint."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})) as mock:
            api.mark_payment_as_paid(5, employee_id=1)
            assert 'paid' in mock.call_args[0][1] or 'mark' in mock.call_args[0][1]


# ═══════════════════════════════════════════════════════════════════
# TestRatesCRUD — Тарифы
# ═══════════════════════════════════════════════════════════════════

class TestRatesCRUD:
    """CRUD методы для тарифов."""

    def test_get_rates(self, api):
        """get_rates возвращает список."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, [])):
            result = api.get_rates()
            assert isinstance(result, list)

    def test_get_rates_with_filters(self, api):
        """get_rates передаёт фильтры."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, [])) as mock:
            api.get_rates(project_type='Индивидуальный', role='Дизайнер')
            assert mock.called

    def test_get_rate_by_id(self, api):
        """get_rate по ID."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 1, 'amount': 1000})):
            result = api.get_rate(1)
            assert result['amount'] == 1000

    def test_create_rate(self, api):
        """create_rate POST."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 1})) as mock:
            api.create_rate({'project_type': 'Индивидуальный', 'role': 'Дизайнер', 'amount': 500})
            assert mock.call_args[0][0] == 'POST'

    def test_delete_rate(self, api):
        """delete_rate DELETE."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})):
            assert api.delete_rate(1) is True


# ═══════════════════════════════════════════════════════════════════
# TestSalariesCRUD — Зарплаты
# ═══════════════════════════════════════════════════════════════════

class TestSalariesCRUD:
    """CRUD методы для зарплат."""

    def test_get_salaries(self, api):
        """get_salaries возвращает список."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, [])):
            result = api.get_salaries()
            assert isinstance(result, list)

    def test_get_salaries_with_filters(self, api):
        """get_salaries с фильтрами месяц/сотрудник."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, [])) as mock:
            api.get_salaries(report_month='2026-02', employee_id=1)
            assert mock.called

    def test_get_salary_by_id(self, api):
        """get_salary по ID."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 1})):
            result = api.get_salary(1)
            assert result['id'] == 1

    def test_create_salary(self, api):
        """create_salary POST."""
        data = {'employee_id': 1, 'amount': 80000, 'report_month': '2026-02'}
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 1})) as mock:
            api.create_salary(data)
            assert mock.call_args[0][0] == 'POST'

    def test_delete_salary(self, api):
        """delete_salary DELETE."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})):
            assert api.delete_salary(1) is True


# ═══════════════════════════════════════════════════════════════════
# TestFilesCRUD — Файлы
# ═══════════════════════════════════════════════════════════════════

class TestFilesCRUD:
    """CRUD методы для файлов."""

    def test_get_contract_files(self, api):
        """get_contract_files возвращает список."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, [])) as mock:
            result = api.get_contract_files(1)
            assert isinstance(result, list)

    def test_create_file_record(self, api):
        """create_file_record POST."""
        data = {'contract_id': 1, 'file_name': 'plan.pdf', 'stage': 'stage1'}
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'id': 1})) as mock:
            api.create_file_record(data)
            assert mock.call_args[0][0] == 'POST'

    def test_delete_file_record(self, api):
        """delete_file_record DELETE."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})):
            assert api.delete_file_record(1) is True


# ═══════════════════════════════════════════════════════════════════
# TestYandexDiskMethods — Яндекс.Диск
# ═══════════════════════════════════════════════════════════════════

class TestYandexDiskMethods:
    """Методы работы с Яндекс.Диском через API."""

    def test_upload_file_to_yandex(self, api):
        """upload_file_to_yandex отправляет файл."""
        resp = _mock_resp(200, {'status': 'success', 'public_link': 'http://yadi.sk/test'})
        with patch.object(api.session, 'request', return_value=resp) as mock:
            result = api.upload_file_to_yandex(b'content', 'test.pdf', '/test/path')
            assert mock.call_args[0][0] == 'POST'
            assert result['status'] == 'success'

    def test_create_yandex_folder(self, api):
        """create_yandex_folder POST."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'status': 'success'})) as mock:
            result = api.create_yandex_folder('/test/folder')
            assert result['status'] == 'success'

    def test_get_yandex_public_link(self, api):
        """get_yandex_public_link GET."""
        resp = _mock_resp(200, {'public_link': 'http://yadi.sk/xxx'})
        with patch.object(api.session, 'request', return_value=resp):
            result = api.get_yandex_public_link('/test/file.pdf')
            assert 'public_link' in result

    def test_list_yandex_files(self, api):
        """list_yandex_files GET."""
        resp = _mock_resp(200, {'files': [{'name': 'doc.pdf'}]})
        with patch.object(api.session, 'request', return_value=resp):
            result = api.list_yandex_files('/test/')
            assert 'files' in result

    def test_delete_yandex_file(self, api):
        """delete_yandex_file DELETE."""
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {'status': 'success'})):
            result = api.delete_yandex_file('/test/file.pdf')
            assert result['status'] == 'success'


# ═══════════════════════════════════════════════════════════════════
# TestTimelineMethods — Таблица сроков
# ═══════════════════════════════════════════════════════════════════

class TestTimelineMethods:
    """Методы таблицы сроков проекта."""

    def test_get_project_timeline(self, api):
        """get_project_timeline GET."""
        entries = [{'stage_code': 'stage1', 'norm_days': 10}]
        with patch.object(api.session, 'request', return_value=_mock_resp(200, entries)):
            result = api.get_project_timeline(1)
            assert len(result) == 1

    def test_init_project_timeline(self, api):
        """init_project_timeline POST /init."""
        data = {'project_type': 'Индивидуальный', 'area': 100.0}
        resp = _mock_resp(200, {'status': 'initialized', 'count': 5})
        with patch.object(api.session, 'request', return_value=resp) as mock:
            result = api.init_project_timeline(1, data)
            assert 'init' in mock.call_args[0][1]
            assert result['status'] == 'initialized'

    def test_reinit_project_timeline(self, api):
        """reinit_project_timeline POST /reinit."""
        data = {'project_type': 'Шаблонный', 'area': 80.0}
        resp = _mock_resp(200, {'status': 'reinitialized', 'count': 4})
        with patch.object(api.session, 'request', return_value=resp) as mock:
            result = api.reinit_project_timeline(1, data)
            assert 'reinit' in mock.call_args[0][1]
            assert result['status'] == 'reinitialized'

    def test_update_timeline_entry(self, api):
        """update_timeline_entry PUT /entry/{stage_code}."""
        data = {'actual_days': 12}
        with patch.object(api.session, 'request', return_value=_mock_resp(200, {})) as mock:
            api.update_timeline_entry(1, 'stage1', data)
            assert 'entry/stage1' in mock.call_args[0][1]
            assert mock.call_args[0][0] == 'PUT'

    def test_get_timeline_summary(self, api):
        """get_timeline_summary GET /summary."""
        resp = _mock_resp(200, {'total_days': 120, 'entries_count': 5})
        with patch.object(api.session, 'request', return_value=resp) as mock:
            result = api.get_timeline_summary(1)
            assert 'summary' in mock.call_args[0][1]
            assert result['entries_count'] == 5

    def test_export_timeline_excel(self, api):
        """export_timeline_excel возвращает bytes."""
        resp = _mock_resp(200, content=b'PK\x03\x04xlsx_content')
        with patch.object(api.session, 'request', return_value=resp):
            result = api.export_timeline_excel(1)
            assert isinstance(result, bytes)
            assert len(result) > 0

    def test_export_timeline_pdf(self, api):
        """export_timeline_pdf возвращает bytes."""
        resp = _mock_resp(200, content=b'%PDF-1.4 content')
        with patch.object(api.session, 'request', return_value=resp):
            result = api.export_timeline_pdf(1)
            assert isinstance(result, bytes)


# ═══════════════════════════════════════════════════════════════════
# TestErrorHandling — Обработка ошибок
# ═══════════════════════════════════════════════════════════════════

class TestErrorHandling:
    """Обработка HTTP ошибок."""

    def test_401_raises_auth_error(self, api):
        """HTTP 401 → APIAuthError."""
        resp = _mock_resp(401, {'detail': 'Unauthorized'})
        with patch.object(api.session, 'request', return_value=resp):
            with pytest.raises(APIAuthError):
                api.get_clients()

    def test_403_raises_auth_error(self, api):
        """HTTP 403 → APIAuthError."""
        resp = _mock_resp(403, {'detail': 'Forbidden'})
        with patch.object(api.session, 'request', return_value=resp):
            with pytest.raises(APIAuthError):
                api.get_clients()

    def test_404_raises_response_error(self, api):
        """HTTP 404 → APIResponseError."""
        resp = _mock_resp(404, {'detail': 'Not found'})
        with patch.object(api.session, 'request', return_value=resp):
            with pytest.raises(APIResponseError) as exc_info:
                api.get_client(999)
            assert exc_info.value.status_code == 404

    def test_500_raises_response_error(self, api):
        """HTTP 500 → APIResponseError."""
        resp = _mock_resp(500, {'detail': 'Internal error'})
        with patch.object(api.session, 'request', return_value=resp):
            with pytest.raises(APIResponseError) as exc_info:
                api.create_client({'full_name': 'Тест'})
            assert exc_info.value.status_code == 500

    def test_timeout_raises_timeout_error(self, api):
        """Таймаут → APITimeoutError после retry."""
        with patch.object(api.session, 'request', side_effect=requests.exceptions.Timeout):
            with pytest.raises(APITimeoutError):
                api.get_clients()

    def test_connection_error_raises(self, api):
        """ConnectionError → APIConnectionError после retry."""
        with patch.object(api.session, 'request', side_effect=requests.exceptions.ConnectionError):
            with pytest.raises(APIConnectionError):
                api.get_clients()


# ═══════════════════════════════════════════════════════════════════
# TestOfflineCache — Offline логика
# ═══════════════════════════════════════════════════════════════════

class TestOfflineCache:
    """Offline кеш и флаги."""

    def test_is_recently_offline_false_by_default(self, api):
        """_is_recently_offline = False когда _last_offline_time = None."""
        assert api._is_recently_offline() is False

    def test_mark_offline_sets_flag(self, api):
        """_mark_offline ставит _is_online = False и _last_offline_time."""
        api._mark_offline()
        assert api._is_online is False
        assert api._last_offline_time is not None

    def test_reset_offline_cache(self, api):
        """reset_offline_cache сбрасывает время offline."""
        api._mark_offline()
        api.reset_offline_cache()
        assert api._last_offline_time is None
        assert api._is_recently_offline() is False

    def test_recently_offline_skips_request(self, api):
        """Если недавно offline — сразу APIConnectionError без запроса."""
        api._last_offline_time = time.time()
        with pytest.raises(APIConnectionError, match="Offline режим"):
            api.get_clients()

    def test_force_online_check_success(self, api):
        """force_online_check возвращает True при 200."""
        with patch.object(api.session, 'get', return_value=_mock_resp(200, {})):
            assert api.force_online_check() is True
            assert api._is_online is True

    def test_force_online_check_failure(self, api):
        """force_online_check возвращает False при ошибке."""
        with patch.object(api.session, 'get', side_effect=Exception("no connection")):
            assert api.force_online_check() is False
            assert api._is_online is False

    def test_set_offline_mode(self, api):
        """set_offline_mode ставит принудительный offline."""
        api.set_offline_mode(True)
        assert api._is_online is False
        assert api._last_offline_time is not None

    def test_set_online_mode(self, api):
        """set_offline_mode(False) возвращает в online."""
        api.set_offline_mode(True)
        api.set_offline_mode(False)
        assert api._is_online is True
        assert api._last_offline_time is None

# -*- coding: utf-8 -*-
"""
Покрытие api_client mixins: supervision, payments, files, statistics, timeline, permissions, misc.
~50 тестов.

Подход: мокаем _request через patch.object, проверяем HTTP method, URL, body.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime

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


def _make_response(status_code=200, json_data=None, headers=None, content=b''):
    """Создать мок Response с нужными полями."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.headers = headers or {}
    resp.text = ''
    resp.content = content
    return resp


# ===========================================================================
# SupervisionMixin — 10 тестов
# ===========================================================================

class TestSupervisionMixin:
    """Тесты для SupervisionMixin: карточки надзора, пауза, возобновление, история."""

    def test_get_supervision_cards_default(self, api):
        """get_supervision_cards — GET /api/supervision/cards со статусом active по умолчанию."""
        cards = [{'id': 1, 'column_name': 'Авторский надзор'}]
        mock_resp = _make_response(200, cards)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_supervision_cards()

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert '/api/v1/supervision/cards' in args[1]
        assert kwargs['params'] == {'status': 'active'}
        assert result == cards

    def test_get_supervision_cards_archived(self, api):
        """get_supervision_cards — фильтр по статусу archived."""
        mock_resp = _make_response(200, [])
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.get_supervision_cards(status='archived')

        _, kwargs = req.call_args
        assert kwargs['params'] == {'status': 'archived'}

    def test_get_supervision_card(self, api):
        """get_supervision_card — GET /api/supervision/cards/{id}."""
        card = {'id': 5, 'column_name': 'В работе'}
        mock_resp = _make_response(200, card)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_supervision_card(5)

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/supervision/cards/5')
        assert result == card

    def test_create_supervision_card(self, api):
        """create_supervision_card — POST /api/supervision/cards с json body."""
        data = {'contract_id': 10, 'column_name': 'Новый'}
        created = {'id': 20, **data}
        mock_resp = _make_response(200, created)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.create_supervision_card(data)

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert '/api/v1/supervision/cards' in args[1]
        assert kwargs['json'] == data
        assert result == created

    def test_update_supervision_card(self, api):
        """update_supervision_card — PATCH /api/supervision/cards/{id}."""
        updates = {'column_name': 'Сдан'}
        mock_resp = _make_response(200, {'id': 5, **updates})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.update_supervision_card(5, updates)

        args, kwargs = req.call_args
        assert args[0] == 'PATCH'
        assert args[1].endswith('/api/v1/supervision/cards/5')
        assert kwargs['json'] == updates

    def test_move_supervision_card(self, api):
        """move_supervision_card — PATCH /api/supervision/cards/{id}/column."""
        mock_resp = _make_response(200, {'id': 5, 'column_name': 'Завершён'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.move_supervision_card(5, 'Завершён')

        args, kwargs = req.call_args
        assert args[0] == 'PATCH'
        assert args[1].endswith('/api/v1/supervision/cards/5/column')
        assert kwargs['json'] == {'column_name': 'Завершён'}

    def test_pause_supervision_card(self, api):
        """pause_supervision_card — POST /api/supervision/cards/{id}/pause с причиной."""
        mock_resp = _make_response(200, {'id': 3, 'paused': True})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.pause_supervision_card(3, 'Ожидание материалов')

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/v1/supervision/cards/3/pause')
        assert kwargs['json'] == {'pause_reason': 'Ожидание материалов'}

    def test_resume_supervision_card(self, api):
        """resume_supervision_card — POST /api/supervision/cards/{id}/resume без employee_id."""
        mock_resp = _make_response(200, {'id': 3, 'paused': False})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.resume_supervision_card(3)

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/v1/supervision/cards/3/resume')
        # Без employee_id — json=None
        assert kwargs['json'] is None

    def test_resume_supervision_card_with_employee(self, api):
        """resume_supervision_card — с employee_id передаёт его в json."""
        mock_resp = _make_response(200, {'id': 3})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.resume_supervision_card(3, employee_id=7)

        _, kwargs = req.call_args
        assert kwargs['json'] == {'employee_id': 7}

    def test_delete_supervision_order(self, api):
        """delete_supervision_order — DELETE с contract_id в params."""
        mock_resp = _make_response(200, {})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.delete_supervision_order(contract_id=10, supervision_card_id=5)

        args, kwargs = req.call_args
        assert args[0] == 'DELETE'
        assert '/api/v1/supervision/orders/5' in args[1]
        assert kwargs['params'] == {'contract_id': 10}
        assert result is True

    def test_get_supervision_history(self, api):
        """get_supervision_history — GET /api/supervision/cards/{id}/history."""
        history = [{'id': 1, 'entry_type': 'moved', 'message': 'Перемещено'}]
        mock_resp = _make_response(200, history)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_supervision_history(5)

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/supervision/cards/5/history')
        assert result == history

    def test_add_supervision_history(self, api):
        """add_supervision_history — POST с entry_type, message, created_by."""
        mock_resp = _make_response(200, {'id': 10})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.add_supervision_history(5, 'comment', 'Тестовый комментарий', 3)

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/v1/supervision/cards/5/history')
        assert kwargs['json'] == {
            'entry_type': 'comment',
            'message': 'Тестовый комментарий',
            'created_by': 3
        }

    def test_complete_supervision_stage(self, api):
        """complete_supervision_stage — POST /api/supervision/cards/{id}/complete-stage."""
        mock_resp = _make_response(200, {'status': 'completed'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.complete_supervision_stage(5, stage_name='Замер')

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/v1/supervision/cards/5/complete-stage')
        assert kwargs['json'] == {'stage_name': 'Замер'}

    def test_get_supervision_addresses(self, api):
        """get_supervision_addresses — GET /api/supervision/addresses."""
        addresses = ['ул. Ленина 1', 'пр. Мира 5']
        mock_resp = _make_response(200, addresses)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_supervision_addresses()

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/supervision/addresses')
        assert result == addresses


# ===========================================================================
# PaymentsMixin — 10 тестов
# ===========================================================================

class TestPaymentsMixin:
    """Тесты для PaymentsMixin: CRUD оплат, расчёт, пометка как выплаченных."""

    def test_get_payments_for_contract(self, api):
        """get_payments_for_contract — GET /api/payments/contract/{id}."""
        payments = [{'id': 1, 'amount': 50000}]
        mock_resp = _make_response(200, payments)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_payments_for_contract(10)

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/payments/contract/10')
        assert result == payments

    def test_create_payment(self, api):
        """create_payment — POST /api/payments с json body."""
        data = {'contract_id': 10, 'employee_id': 3, 'role': 'Дизайнер'}
        created = {'id': 100, **data}
        mock_resp = _make_response(200, created)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.create_payment(data)

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/v1/payments')
        assert kwargs['json'] == data
        assert result == created

    def test_get_payment(self, api):
        """get_payment — GET /api/payments/{id}."""
        payment = {'id': 5, 'amount': 30000}
        mock_resp = _make_response(200, payment)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_payment(5)

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/payments/5')
        assert result == payment

    def test_update_payment(self, api):
        """update_payment — PUT /api/payments/{id} с json body."""
        data = {'amount': 75000}
        mock_resp = _make_response(200, {'id': 5, **data})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.update_payment(5, data)

        args, kwargs = req.call_args
        assert args[0] == 'PUT'
        assert args[1].endswith('/api/v1/payments/5')
        assert kwargs['json'] == data

    def test_delete_payment(self, api):
        """delete_payment — DELETE /api/payments/{id}."""
        mock_resp = _make_response(200, {})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.delete_payment(5)

        args, _ = req.call_args
        assert args[0] == 'DELETE'
        assert args[1].endswith('/api/v1/payments/5')

    def test_mark_payment_as_paid(self, api):
        """mark_payment_as_paid — PATCH /api/payments/{id}/mark-paid с employee_id в params."""
        mock_resp = _make_response(200, {'id': 5, 'payment_status': 'Выплачено'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.mark_payment_as_paid(5, employee_id=3)

        args, kwargs = req.call_args
        assert args[0] == 'PATCH'
        assert args[1].endswith('/api/v1/payments/5/mark-paid')
        assert kwargs['params'] == {'employee_id': 3}

    def test_calculate_payment_amount(self, api):
        """calculate_payment_amount — GET /api/payments/calculate, возвращает float."""
        mock_resp = _make_response(200, {'amount': 45000.50})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.calculate_payment_amount(
                contract_id=10, employee_id=3, role='Дизайнер'
            )

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/payments/calculate')
        assert kwargs['params'] == {
            'contract_id': 10,
            'employee_id': 3,
            'role': 'Дизайнер'
        }
        assert result == 45000.50

    def test_calculate_payment_amount_with_stage(self, api):
        """calculate_payment_amount — с stage_name и supervision_card_id в params."""
        mock_resp = _make_response(200, {'amount': 10000})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.calculate_payment_amount(
                contract_id=10, employee_id=3, role='Дизайнер',
                stage_name='Замер', supervision_card_id=5
            )

        _, kwargs = req.call_args
        params = kwargs['params']
        assert params['stage_name'] == 'Замер'
        assert params['supervision_card_id'] == 5

    def test_calculate_payment_amount_error_returns_zero(self, api):
        """calculate_payment_amount — при ошибке возвращает 0."""
        with patch.object(api, '_request', side_effect=Exception('сеть')):
            result = api.calculate_payment_amount(10, 3, 'Дизайнер')
        assert result == 0

    def test_get_year_payments(self, api):
        """get_year_payments — GET /api/payments с year в params."""
        payments = [{'id': 1}, {'id': 2}]
        mock_resp = _make_response(200, payments)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_year_payments(2025)

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/payments')
        assert kwargs['params'] == {'year': 2025}
        assert result == payments

    def test_get_year_payments_include_null_month(self, api):
        """get_year_payments — include_null_month=True добавляет параметр."""
        mock_resp = _make_response(200, [])
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.get_year_payments(2025, include_null_month=True)

        _, kwargs = req.call_args
        assert kwargs['params'] == {'year': 2025, 'include_null_month': 'true'}

    def test_set_payments_report_month(self, api):
        """set_payments_report_month — PATCH .../contract/{id}/report-month."""
        mock_resp = _make_response(200, {'updated': 3})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.set_payments_report_month(10, '2025-06')

        args, kwargs = req.call_args
        assert args[0] == 'PATCH'
        assert '/api/v1/payments/contract/10/report-month' in args[1]
        assert kwargs['json'] == {'report_month': '2025-06'}

    def test_recalculate_payments(self, api):
        """recalculate_payments — POST /api/payments/recalculate с params."""
        mock_resp = _make_response(200, {'updated': 5})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.recalculate_payments(contract_id=10, role='Дизайнер')

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/v1/payments/recalculate')
        assert kwargs['params'] == {'contract_id': 10, 'role': 'Дизайнер'}


# ===========================================================================
# FilesMixin — 8 тестов
# ===========================================================================

class TestFilesMixin:
    """Тесты для FilesMixin: файлы договоров, загрузка на Яндекс.Диск."""

    def test_get_contract_files(self, api):
        """get_contract_files — GET /api/files/contract/{id}."""
        files = [{'id': 1, 'file_name': 'plan.pdf'}]
        mock_resp = _make_response(200, files)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_contract_files(10)

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/files/contract/10')
        assert kwargs['params'] == {}
        assert result == files

    def test_get_contract_files_with_stage(self, api):
        """get_contract_files — с фильтром по стадии."""
        mock_resp = _make_response(200, [])
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.get_contract_files(10, stage='Замер')

        _, kwargs = req.call_args
        assert kwargs['params'] == {'stage': 'Замер'}

    def test_create_file_record(self, api):
        """create_file_record — POST /api/files с json body."""
        data = {'contract_id': 10, 'file_name': 'doc.pdf', 'stage': 'Замер'}
        created = {'id': 50, **data}
        mock_resp = _make_response(200, created)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.create_file_record(data)

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/v1/files')
        assert kwargs['json'] == data
        assert result == created

    def test_delete_file_record(self, api):
        """delete_file_record — DELETE /api/files/{id}, возвращает True."""
        mock_resp = _make_response(200, {})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.delete_file_record(50)

        args, _ = req.call_args
        assert args[0] == 'DELETE'
        assert args[1].endswith('/api/v1/files/50')
        assert result is True

    def test_upload_file_to_yandex(self, api):
        """upload_file_to_yandex — POST /api/files/upload с multipart и yandex_path."""
        mock_resp = _make_response(200, {'public_link': 'https://disk.yandex.ru/file'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.upload_file_to_yandex(b'file-bytes', 'photo.jpg', '/disk/path/photo.jpg')

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/v1/files/upload')
        # Проверяем что files передаётся как кортеж (filename, bytes)
        assert 'files' in kwargs
        assert kwargs['files'] == {'file': ('photo.jpg', b'file-bytes')}
        assert kwargs['params'] == {'yandex_path': '/disk/path/photo.jpg'}

    def test_validate_files(self, api):
        """validate_files — POST /api/files/validate с file_ids."""
        mock_resp = _make_response(200, [{'id': 1, 'exists': True}])
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.validate_files([1, 2, 3], auto_clean=True)

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/v1/files/validate')
        assert kwargs['json'] == {'file_ids': [1, 2, 3], 'auto_clean': True}

    def test_create_yandex_folder(self, api):
        """create_yandex_folder — POST /api/files/folder с folder_path в params."""
        mock_resp = _make_response(200, {'status': 'created'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.create_yandex_folder('/disk/projects/new')

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/v1/files/folder')
        assert kwargs['params'] == {'folder_path': '/disk/projects/new'}

    def test_get_yandex_public_link(self, api):
        """get_yandex_public_link — GET /api/files/public-link с yandex_path."""
        mock_resp = _make_response(200, {'public_url': 'https://disk.yandex.ru/...'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_yandex_public_link('/disk/file.pdf')

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/files/public-link')
        assert kwargs['params'] == {'yandex_path': '/disk/file.pdf'}


# ===========================================================================
# StatisticsMixin — 8 тестов
# ===========================================================================

class TestStatisticsMixin:
    """Тесты для StatisticsMixin: дашборд, проекты, воронка, отчёты."""

    def test_get_dashboard_statistics(self, api):
        """get_dashboard_statistics — GET /api/statistics/dashboard с фильтрами."""
        stats = {'total_contracts': 42, 'total_revenue': 5000000}
        mock_resp = _make_response(200, stats)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_dashboard_statistics(year=2025, month=6)

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/statistics/dashboard')
        assert kwargs['params'] == {'year': 2025, 'month': 6}
        assert result == stats

    def test_get_dashboard_statistics_no_params(self, api):
        """get_dashboard_statistics — без параметров передаёт пустые params."""
        mock_resp = _make_response(200, {})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.get_dashboard_statistics()

        _, kwargs = req.call_args
        assert kwargs['params'] == {}

    def test_get_project_statistics(self, api):
        """get_project_statistics — GET /api/statistics/projects с project_type."""
        stats = {'count': 15, 'revenue': 3000000}
        mock_resp = _make_response(200, stats)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_project_statistics('Индивидуальный', year=2025)

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/statistics/projects')
        assert kwargs['params'] == {'project_type': 'Индивидуальный', 'year': 2025}
        assert result == stats

    def test_get_funnel_statistics(self, api):
        """get_funnel_statistics — GET /api/statistics/funnel."""
        funnel = {'Новый заказ': 5, 'В работе': 10, 'Сдан': 20}
        mock_resp = _make_response(200, funnel)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_funnel_statistics(year=2025)

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/statistics/funnel')
        assert kwargs['params'] == {'year': 2025}
        assert result == funnel

    def test_get_employee_report_data(self, api):
        """get_employee_report_data — GET /api/reports/employee-report с обязательными params."""
        report = {'completed': [], 'area': [], 'deadlines': [], 'salaries': []}
        mock_resp = _make_response(200, report)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_employee_report_data(
                project_type='Индивидуальный', period='За год', year=2025
            )

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/reports/employee-report')
        assert kwargs['params'] == {
            'project_type': 'Индивидуальный',
            'period': 'За год',
            'year': 2025
        }
        assert result == report

    def test_get_employee_report_data_with_quarter(self, api):
        """get_employee_report_data — с quarter и month в params."""
        mock_resp = _make_response(200, {})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.get_employee_report_data(
                project_type='Шаблонный', period='За квартал', year=2025,
                quarter=2, month=5
            )

        _, kwargs = req.call_args
        assert kwargs['params']['quarter'] == 2
        assert kwargs['params']['month'] == 5

    def test_get_supervision_statistics(self, api):
        """get_supervision_statistics — GET /api/statistics/supervision."""
        stats = {'active': 10, 'completed': 5}
        mock_resp = _make_response(200, stats)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_supervision_statistics(year=2025, city='Москва')

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/statistics/supervision')
        assert kwargs['params'] == {'year': 2025, 'city': 'Москва'}

    def test_get_general_statistics(self, api):
        """get_general_statistics — GET /api/statistics/general с year."""
        mock_resp = _make_response(200, {'total': 100})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_general_statistics(year=2025, quarter=3)

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/statistics/general')
        assert kwargs['params'] == {'year': 2025, 'quarter': 3}


# ===========================================================================
# TimelineMixin — 7 тестов
# ===========================================================================

class TestTimelineMixin:
    """Тесты для TimelineMixin: таблица сроков проекта и надзора."""

    def test_get_project_timeline(self, api):
        """get_project_timeline — GET /api/timeline/{contract_id}."""
        timeline = [{'stage_code': 'measurement', 'days': 5}]
        mock_resp = _make_response(200, timeline)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_project_timeline(10)

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/timeline/10')
        assert result == timeline

    def test_init_project_timeline(self, api):
        """init_project_timeline — POST /api/timeline/{contract_id}/init."""
        data = {'template': 'standard', 'start_date': '2025-01-01'}
        mock_resp = _make_response(200, {'status': 'created'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.init_project_timeline(10, data)

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/v1/timeline/10/init')
        assert kwargs['json'] == data

    def test_update_timeline_entry(self, api):
        """update_timeline_entry — PUT /api/timeline/{contract_id}/entry/{stage_code}."""
        data = {'actual_days': 7, 'status': 'Завершено'}
        mock_resp = _make_response(200, {'stage_code': 'measurement', **data})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.update_timeline_entry(10, 'measurement', data)

        args, kwargs = req.call_args
        assert args[0] == 'PUT'
        assert args[1].endswith('/api/v1/timeline/10/entry/measurement')
        assert kwargs['json'] == data

    def test_get_timeline_summary(self, api):
        """get_timeline_summary — GET /api/timeline/{contract_id}/summary."""
        summary = {'total_days': 90, 'overdue': 2}
        mock_resp = _make_response(200, summary)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_timeline_summary(10)

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/timeline/10/summary')
        assert result == summary

    def test_export_timeline_excel(self, api):
        """export_timeline_excel — GET .../export/excel, возвращает bytes при 200."""
        excel_content = b'\x50\x4b\x03\x04'  # ZIP-сигнатура xlsx
        mock_resp = _make_response(200, content=excel_content)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.export_timeline_excel(10)

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/timeline/10/export/excel')
        assert result == excel_content

    def test_get_supervision_timeline_dict_format(self, api):
        """get_supervision_timeline — dict с ключом 'entries' возвращается как есть."""
        data = {'entries': [{'stage': 'Замер'}], 'totals': {'total': 10}}
        mock_resp = _make_response(200, data)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_supervision_timeline(5)

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/supervision-timeline/5')
        assert result == data

    def test_get_supervision_timeline_list_format(self, api):
        """get_supervision_timeline — список оборачивается в dict."""
        entries = [{'stage': 'Замер'}, {'stage': 'Проект'}]
        mock_resp = _make_response(200, entries)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_supervision_timeline(5)

        assert result == {'entries': entries, 'totals': {}}


# ===========================================================================
# PermissionsMixin — 6 тестов
# ===========================================================================

class TestPermissionsMixin:
    """Тесты для PermissionsMixin: права сотрудников и матрица ролей."""

    def test_get_employee_permissions(self, api):
        """get_employee_permissions — GET /api/permissions/{employee_id}."""
        perms = {'employee_id': 3, 'permissions': ['view_clients', 'edit_clients']}
        mock_resp = _make_response(200, perms)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_employee_permissions(3)

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/permissions/3')
        assert result == perms

    def test_set_employee_permissions(self, api):
        """set_employee_permissions — PUT /api/permissions/{employee_id} с permissions."""
        permissions = ['view_clients', 'edit_clients', 'view_contracts']
        mock_resp = _make_response(200, {'status': 'updated'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.set_employee_permissions(3, permissions)

        args, kwargs = req.call_args
        assert args[0] == 'PUT'
        assert args[1].endswith('/api/v1/permissions/3')
        assert kwargs['json'] == {'permissions': permissions}

    def test_get_role_permissions_matrix(self, api):
        """get_role_permissions_matrix — GET /api/permissions/role-matrix."""
        matrix = {'Директор': ['*'], 'Дизайнер': ['view_clients']}
        mock_resp = _make_response(200, matrix)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_role_permissions_matrix()

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/permissions/role-matrix')
        assert result == matrix

    def test_save_role_permissions_matrix(self, api):
        """save_role_permissions_matrix — PUT /api/permissions/role-matrix с data."""
        data = {'Менеджер': ['view_clients', 'edit_clients']}
        mock_resp = _make_response(200, {'status': 'saved'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.save_role_permissions_matrix(data)

        args, kwargs = req.call_args
        assert args[0] == 'PUT'
        assert args[1].endswith('/api/v1/permissions/role-matrix')
        assert kwargs['json'] == data

    def test_get_permission_definitions(self, api):
        """get_permission_definitions — GET /api/permissions/definitions."""
        definitions = [
            {'code': 'view_clients', 'description': 'Просмотр клиентов'},
            {'code': 'edit_clients', 'description': 'Редактирование клиентов'},
        ]
        mock_resp = _make_response(200, definitions)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_permission_definitions()

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/permissions/definitions')
        assert result == definitions

    def test_reset_employee_permissions(self, api):
        """reset_employee_permissions — POST /api/permissions/{id}/reset-to-defaults."""
        mock_resp = _make_response(200, {'status': 'reset'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.reset_employee_permissions(3)

        args, _ = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/v1/permissions/3/reset-to-defaults')


# ===========================================================================
# MiscMixin — 11 тестов
# ===========================================================================

class TestMiscMixin:
    """Тесты для MiscMixin: health, search, агенты, города, уведомления."""

    def test_health_check_success(self, api):
        """health_check — GET /health, возвращает True при 200."""
        mock_resp = _make_response(200)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.health_check()

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/health')
        assert result is True

    def test_health_check_failure(self, api):
        """health_check — при исключении возвращает False, _is_online = False."""
        with patch.object(api, '_request', side_effect=Exception('timeout')):
            result = api.health_check()

        assert result is False
        assert api._is_online is False

    def test_search(self, api):
        """search — GET /api/search с q, limit, entity_types."""
        results = {'clients': [{'id': 1}], 'contracts': []}
        mock_resp = _make_response(200, results)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.search('Иванов', limit=20, entity_types='clients,contracts')

        args, kwargs = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/search')
        assert kwargs['params'] == {
            'q': 'Иванов',
            'limit': 20,
            'entity_types': 'clients,contracts'
        }
        assert result == results

    def test_search_default_limit(self, api):
        """search — limit по умолчанию 50, без entity_types."""
        mock_resp = _make_response(200, {})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            api.search('тест')

        _, kwargs = req.call_args
        assert kwargs['params'] == {'q': 'тест', 'limit': 50}

    def test_get_all_agents(self, api):
        """get_all_agents — GET /api/v1/agents."""
        agents = [{'id': 1, 'name': 'Агент 1', 'color': '#FF0000'}]
        mock_resp = _make_response(200, agents)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_all_agents()

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/agents')
        assert result == agents

    def test_add_agent(self, api):
        """add_agent — POST /api/v1/agents с name и color, возвращает True."""
        mock_resp = _make_response(200, {'id': 10, 'name': 'Новый', 'color': '#00FF00'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.add_agent('Новый', '#00FF00')

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/v1/agents')
        assert kwargs['json'] == {'name': 'Новый', 'color': '#00FF00'}
        assert result is True

    def test_add_agent_error(self, api):
        """add_agent — при ошибке возвращает False."""
        with patch.object(api, '_request', side_effect=Exception('ошибка')):
            result = api.add_agent('Тест', '#000')
        assert result is False

    def test_get_all_cities(self, api):
        """get_all_cities — GET /api/v1/cities."""
        cities = [{'id': 1, 'name': 'Москва'}, {'id': 2, 'name': 'СПб'}]
        mock_resp = _make_response(200, cities)
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.get_all_cities()

        args, _ = req.call_args
        assert args[0] == 'GET'
        assert args[1].endswith('/api/v1/cities')
        assert result == cities

    def test_get_all_cities_error_returns_empty(self, api):
        """get_all_cities — при ошибке возвращает пустой список."""
        with patch.object(api, '_request', side_effect=Exception('сеть')):
            result = api.get_all_cities()
        assert result == []

    def test_add_city(self, api):
        """add_city — POST /api/v1/cities с name, возвращает True."""
        mock_resp = _make_response(200, {'id': 5, 'name': 'Казань'})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.add_city('Казань')

        args, kwargs = req.call_args
        assert args[0] == 'POST'
        assert args[1].endswith('/api/v1/cities')
        assert kwargs['json'] == {'name': 'Казань'}
        assert result is True

    def test_delete_city(self, api):
        """delete_city — DELETE /api/v1/cities/{id}, возвращает True."""
        mock_resp = _make_response(200, {})
        with patch.object(api, '_request', return_value=mock_resp) as req:
            result = api.delete_city(5)

        args, _ = req.call_args
        assert args[0] == 'DELETE'
        assert args[1].endswith('/api/v1/cities/5')
        assert result is True

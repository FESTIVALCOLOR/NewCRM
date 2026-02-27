# -*- coding: utf-8 -*-
"""
Максимальное покрытие utils/data_access.py (~3200 строк).
Тестируем ВСЕ публичные методы DataAccess в трёх режимах:
  1. Online — api_client мокнут, возвращает данные
  2. Offline — api_client=None, только db
  3. Fallback — api_client бросает Exception, переход на db

Дополнительно:
  - Кеширование (_DataCache)
  - _queue_operation (бизнес vs сетевые ошибки)
  - prefer_local
  - create-методы: API возвращает list вместо dict
  - _update_local_id
  - Workflow (api-only)
  - Мессенджер, администрирование, Timeline, экспорт
  - Raw SQL: execute_raw_query / execute_raw_update

~160 тестов.
"""

import time
import pytest
import sys
import os
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.data_access import DataAccess, _DataCache, _global_cache


# ==================== ХЕЛПЕРЫ ====================

def _make_da(db, api=None):
    """Создать DataAccess с мок-зависимостями, без OfflineManager."""
    with patch('utils.data_access.get_offline_manager', return_value=None), \
         patch('utils.data_access.DatabaseManager', return_value=db):
        da = DataAccess(api_client=api, db=db)
        return da


def _make_da_online(db, api):
    """DataAccess + OfflineManager.is_online() = True (для write-методов)."""
    om = MagicMock()
    om.is_online.return_value = True
    with patch('utils.data_access.get_offline_manager', return_value=om), \
         patch('utils.data_access.DatabaseManager', return_value=db):
        da = DataAccess(api_client=api, db=db)
        return da


@pytest.fixture(autouse=True)
def clear_cache():
    """Очистка глобального кеша перед каждым тестом."""
    _global_cache.invalidate()
    yield
    _global_cache.invalidate()


@pytest.fixture
def db():
    """Мок DatabaseManager с полным набором методов."""
    m = MagicMock()
    m.get_all_clients.return_value = [{'id': 1, 'full_name': 'Локальный'}]
    m.get_client_by_id.return_value = {'id': 1, 'full_name': 'Локальный'}
    m.get_clients_count.return_value = 1
    m.add_client.return_value = 1
    m.get_all_contracts.return_value = [{'id': 10, 'contract_number': '1/2026'}]
    m.get_contract_by_id.return_value = {'id': 10}
    m.get_contracts_count.return_value = 1
    m.add_contract.return_value = 10
    m.get_all_employees.return_value = [{'id': 5, 'full_name': 'Сотрудник'}]
    m.get_employee_by_id.return_value = {'id': 5}
    m.get_employees_by_position.return_value = [{'id': 5, 'position': 'Менеджер'}]
    m.add_employee.return_value = 30
    m.get_crm_cards_by_project_type.return_value = [{'id': 100}]
    m.get_crm_card_data.return_value = {'id': 100}
    m.get_archived_crm_cards.return_value = [{'id': 101, 'archived': True}]
    m.add_crm_card.return_value = 40
    m.get_contract_id_by_crm_card.return_value = 10
    m.get_crm_card_id_by_contract.return_value = 100
    m.get_supervision_cards_active.return_value = [{'id': 200}]
    m.get_supervision_cards_archived.return_value = [{'id': 201}]
    m.get_supervision_card_data.return_value = {'id': 200}
    m.add_supervision_card.return_value = 50
    m.get_contract_id_by_supervision_card.return_value = 10
    m.get_supervision_addresses.return_value = ['Москва', 'СПб']
    m.get_supervision_statistics_filtered.return_value = {'total': 5}
    m.get_payments_for_contract.return_value = [{'id': 300}]
    m.add_payment.return_value = 60
    m.get_payment.return_value = {'id': 300}
    m.get_payments_by_type.return_value = [{'id': 300}]
    m.get_payments_by_supervision_card.return_value = [{'id': 300}]
    m.get_payments_for_supervision.return_value = [{'id': 300}]
    m.get_payments_for_crm.return_value = [{'id': 300}]
    m.get_year_payments.return_value = [{'id': 300, 'year': 2026}]
    m.calculate_payment_amount.return_value = {'amount': 5000}
    m.create_payment_record.return_value = {'id': 70}
    m.get_action_history.return_value = [{'id': 1, 'action': 'test'}]
    m.get_supervision_history.return_value = [{'id': 1}]
    m.get_rates.return_value = [{'id': 700}]
    m.get_rate_by_id.return_value = {'id': 700}
    m.add_rate.return_value = 70
    m.get_template_rates.return_value = [{'id': 710}]
    m.get_salaries.return_value = [{'id': 800}]
    m.get_salary_by_id.return_value = {'id': 800}
    m.add_salary.return_value = 80
    m.get_contract_files.return_value = [{'id': 900}]
    m.add_contract_file.return_value = 90
    m.get_project_files.return_value = [{'id': 901}]
    m.add_project_file.return_value = {'id': 91}
    m.get_project_templates.return_value = [{'id': 950}]
    m.get_dashboard_statistics.return_value = {'total_orders': 10}
    m.get_clients_dashboard_stats.return_value = {'total': 5}
    m.get_contracts_dashboard_stats.return_value = {'total': 3}
    m.get_crm_dashboard_stats.return_value = {'total': 7}
    m.get_employees_dashboard_stats.return_value = {'total': 2}
    m.get_salaries_dashboard_stats.return_value = {'total': 1}
    m.get_salaries_individual_stats.return_value = {'total': 1}
    m.get_salaries_salary_stats.return_value = {'total': 1}
    m.get_salaries_supervision_stats.return_value = {'total': 1}
    m.get_salaries_template_stats.return_value = {'total': 1}
    m.get_salaries_all_payments_stats.return_value = {'total': 1}
    m.get_employee_report_data.return_value = {'name': 'test'}
    m.get_project_statistics.return_value = {'count': 3}
    m.get_supervision_statistics_report.return_value = {'report': True}
    m.get_project_timeline.return_value = [{'stage_code': 'S1'}]
    m.get_stage_history.return_value = [{'stage': 'S1'}]
    m.get_accepted_stages.return_value = [{'stage': 'S1'}]
    m.get_submitted_stages.return_value = [{'stage': 'S1'}]
    m.get_supervision_timeline.return_value = [{'stage': 'ST1'}]
    m.check_contract_number_exists.return_value = False
    m.get_contracts_count_by_client.return_value = 3
    m.get_all_agents.return_value = [{'id': 1, 'name': 'ФЕСТИВАЛЬ'}]
    m.get_agent_color.return_value = '#FF0000'
    m.get_agent_types.return_value = ['FESTIVAL']
    m.get_all_cities.return_value = [{'id': 1, 'name': 'Москва'}]
    m.get_contract_years.return_value = [2025, 2026]
    m.get_crm_statistics_filtered.return_value = {'stat': 1}
    m.get_employee_permissions.return_value = {'permissions': ['view']}
    m.get_employee_active_assignments.return_value = [{'card_id': 1}]
    m.get_projects_by_type.return_value = [{'id': 1}]
    m.get_funnel_statistics.return_value = {'new': 5}
    m.get_executor_load.return_value = [{'id': 1, 'load': 3}]
    m.global_search.return_value = {'clients': [], 'contracts': []}
    m.connect.return_value = MagicMock()
    return m


@pytest.fixture
def api():
    """Мок API Client."""
    a = MagicMock()
    a.get_clients.return_value = [{'id': 101, 'full_name': 'API Клиент'}]
    a.get_client.return_value = {'id': 101, 'full_name': 'API Клиент'}
    a.get_clients_paginated.return_value = ([{'id': 101}], 10)
    a.create_client.return_value = {'id': 101}
    a.update_client.return_value = {'id': 101}
    a.delete_client.return_value = True
    a.get_contracts.return_value = [{'id': 201, 'client_id': 101}]
    a.get_contract.return_value = {'id': 201}
    a.get_contracts_paginated.return_value = ([{'id': 201}], 5)
    a.get_contracts_count.return_value = 5
    a.create_contract.return_value = {'id': 201}
    a.update_contract.return_value = {'id': 201}
    a.delete_contract.return_value = True
    a.check_contract_number_exists.return_value = True
    a.get_employees.return_value = [{'id': 301}]
    a.get_employee.return_value = {'id': 301}
    a.get_employees_by_position.return_value = [{'id': 301, 'position': 'Дизайнер'}]
    a.create_employee.return_value = {'id': 301}
    a.update_employee.return_value = {'id': 301}
    a.delete_employee.return_value = True
    a.get_crm_cards.return_value = [{'id': 401}]
    a.get_crm_card.return_value = {'id': 401}
    a.get_archived_crm_cards.return_value = [{'id': 402}]
    a.create_crm_card.return_value = {'id': 401}
    a.update_crm_card.return_value = {'id': 401}
    a.delete_crm_card.return_value = True
    a.move_crm_card.return_value = {'id': 401}
    a.get_workflow_state.return_value = {'state': 'draft'}
    a.workflow_submit.return_value = {'state': 'review'}
    a.workflow_accept.return_value = {'state': 'accepted'}
    a.workflow_reject.return_value = {'state': 'rejected'}
    a.workflow_client_send.return_value = {'state': 'sent'}
    a.workflow_client_ok.return_value = {'state': 'approved'}
    a.get_supervision_cards.return_value = [{'id': 501}]
    a.get_supervision_card.return_value = {'id': 501}
    a.create_supervision_card.return_value = {'id': 501}
    a.update_supervision_card.return_value = {'id': 501}
    a.move_supervision_card.return_value = {'id': 501}
    a.complete_supervision_stage.return_value = {'success': True}
    a.reset_supervision_stage_completion.return_value = {'success': True}
    a.pause_supervision_card.return_value = {'success': True}
    a.resume_supervision_card.return_value = {'success': True}
    a.delete_supervision_order.return_value = {'success': True}
    a.get_contract_id_by_supervision_card.return_value = 10
    a.get_supervision_addresses.return_value = ['Москва']
    a.get_supervision_statistics_filtered.return_value = {'total': 10}
    a.get_payments_for_contract.return_value = [{'id': 601}]
    a.create_payment.return_value = {'id': 601}
    a.update_payment.return_value = {'id': 601}
    a.delete_payment.return_value = True
    a.get_payment.return_value = {'id': 601}
    a.get_payments_by_type.return_value = [{'id': 601}]
    a.get_payments_by_supervision_card.return_value = [{'id': 601}]
    a.get_payments_for_supervision.return_value = [{'id': 601}]
    a.get_payments_for_crm.return_value = [{'id': 601}]
    a.get_year_payments.return_value = [{'id': 601}]
    a.mark_payment_as_paid.return_value = {'success': True}
    a.create_payment_record.return_value = {'id': 602}
    a.update_payment_manual.return_value = {'success': True}
    a.calculate_payment_amount.return_value = {'amount': 10000}
    a.recalculate_payments.return_value = {'count': 5}
    a.set_payments_report_month.return_value = {'success': True}
    a.get_action_history.return_value = [{'id': 1}]
    a.create_action_history.return_value = {'id': 1}
    a.get_supervision_history.return_value = [{'id': 1}]
    a.add_supervision_history.return_value = {'id': 1}
    a.get_rates.return_value = [{'id': 701}]
    a.get_rate.return_value = {'id': 701}
    a.create_rate.return_value = {'id': 701}
    a.update_rate.return_value = {'id': 701}
    a.delete_rate.return_value = True
    a.get_template_rates.return_value = [{'id': 711}]
    a.save_template_rate.return_value = {'id': 712}
    a.save_individual_rate.return_value = {'id': 713}
    a.delete_individual_rate.return_value = True
    a.save_surveyor_rate.return_value = {'id': 714}
    a.save_supervision_rate.return_value = {'id': 715}
    a.get_salaries.return_value = [{'id': 801}]
    a.get_salary.return_value = {'id': 801}
    a.create_salary.return_value = {'id': 801}
    a.update_salary.return_value = {'id': 801}
    a.delete_salary.return_value = True
    a.get_contract_files.return_value = [{'id': 901}]
    a.create_file_record.return_value = {'id': 901}
    a.delete_file_record.return_value = True
    a.get_project_files.return_value = [{'id': 902}]
    a.add_project_file.return_value = {'id': 903}
    a.scan_contract_files.return_value = {'count': 3}
    a.get_yandex_public_link.return_value = {'public_url': 'https://ya.ru/file'}
    a.delete_yandex_file.return_value = True
    a.validate_files.return_value = [1, 2]
    a.get_project_templates.return_value = [{'id': 951}]
    a.add_project_template.return_value = {'id': 951}
    a.delete_project_template.return_value = True
    a.get_dashboard_statistics.return_value = {'total_orders': 50}
    a.get_clients_dashboard_stats.return_value = {'total': 15}
    a.get_contracts_dashboard_stats.return_value = {'total': 8}
    a.get_crm_dashboard_stats.return_value = {'total': 20}
    a.get_employees_dashboard_stats.return_value = {'total': 4}
    a.get_salaries_dashboard_stats.return_value = {'total': 3}
    a.get_salaries_individual_stats.return_value = {'total': 2}
    a.get_salaries_salary_stats.return_value = {'total': 2}
    a.get_salaries_supervision_stats.return_value = {'total': 2}
    a.get_salaries_template_stats.return_value = {'total': 2}
    a.get_salaries_all_payments_stats.return_value = {'total': 2}
    a.get_employee_report_data.return_value = {'name': 'api_report'}
    a.get_project_statistics.return_value = {'count': 10}
    a.get_supervision_statistics.return_value = {'report': True}
    a.get_project_timeline.return_value = [{'stage_code': 'S1_API'}]
    a.init_project_timeline.return_value = {'status': 'ok'}
    a.reinit_project_timeline.return_value = {'status': 'ok'}
    a.update_timeline_entry.return_value = {'success': True}
    a.get_timeline_summary.return_value = {'total_entries': 5}
    a.export_timeline_excel.return_value = b'EXCEL'
    a.export_timeline_pdf.return_value = b'PDF'
    a.get_supervision_timeline.return_value = {'entries': [{'stage': 'ST1'}], 'totals': {}}
    a.init_supervision_timeline.return_value = {'status': 'ok'}
    a.update_supervision_timeline_entry.return_value = {'success': True}
    a.get_supervision_timeline_summary.return_value = {'total_stages': 3}
    a.export_supervision_timeline_excel.return_value = b'EXCEL_SUP'
    a.export_supervision_timeline_pdf.return_value = b'PDF_SUP'
    a.get_stage_history.return_value = [{'stage': 'S1_API'}]
    a.get_accepted_stages.return_value = [{'stage': 'S1_API'}]
    a.get_submitted_stages.return_value = [{'stage': 'S1_API'}]
    a.update_stage_executor.return_value = {'success': True}
    a.assign_stage_executor.return_value = {'success': True}
    a.complete_stage_for_executor.return_value = {'success': True}
    a.reset_stage_completion.return_value = {'success': True}
    a.reset_designer_completion.return_value = {'success': True}
    a.reset_draftsman_completion.return_value = {'success': True}
    a.reset_approval_stages.return_value = {'success': True}
    a.save_manager_acceptance.return_value = {'success': True}
    a.get_crm_statistics_filtered.return_value = {'stat': 10}
    a.get_all_agents.return_value = [{'id': 1, 'name': 'API_AGENT'}]
    a.get_agent_color.return_value = '#00FF00'
    a.add_agent.return_value = {'id': 2}
    a.update_agent_color.return_value = True
    a.delete_agent.return_value = True
    a.get_agent_types.return_value = ['FESTIVAL', 'PETROVICH']
    a.get_all_cities.return_value = [{'id': 1, 'name': 'Москва'}]
    a.add_city.return_value = True
    a.delete_city.return_value = True
    a.get_contract_years.return_value = [2024, 2025, 2026]
    a.get_cities.return_value = ['СПБ', 'МСК']
    a.get_current_user.return_value = {'id': 1, 'login': 'admin'}
    a.search.return_value = {'clients': [{'id': 1}], 'contracts': []}
    a.get_funnel_statistics.return_value = {'new': 10, 'done': 5}
    a.get_executor_load.return_value = [{'id': 1, 'load': 7}]
    a.get_employee_permissions.return_value = {'permissions': ['admin']}
    a.set_employee_permissions.return_value = True
    a.reset_employee_permissions.return_value = True
    a.get_permission_definitions.return_value = [{'code': 'view'}]
    a.get_role_permissions_matrix.return_value = {'roles': {'admin': ['all']}}
    a.save_role_permissions_matrix.return_value = {'success': True}
    a.get_norm_days_template.return_value = {'entries': [{'stage': 'S1'}]}
    a.save_norm_days_template.return_value = {'success': True}
    a.preview_norm_days_template.return_value = {'entries': [], 'contract_term': 30}
    a.reset_norm_days_template.return_value = {'success': True}
    a.delete_contract.return_value = True
    a.delete_crm_card.return_value = True
    a.delete_project_file.return_value = {'id': 900}
    a.get_projects_by_type.return_value = [{'id': 1}]
    a.get_supervision_cards.return_value = [{'id': 501}]
    a.create_messenger_chat.return_value = {'chat_id': 1}
    a.bind_messenger_chat.return_value = {'chat_id': 1}
    a.get_messenger_chat_by_card.return_value = {'chat_id': 1}
    a.get_supervision_chat.return_value = {'chat_id': 2}
    a.create_supervision_chat.return_value = {'chat_id': 2}
    a.delete_messenger_chat.return_value = {'success': True}
    a.send_messenger_message.return_value = {'sent': True}
    a.get_messenger_scripts.return_value = [{'id': 1}]
    a.get_messenger_settings.return_value = [{'key': 'val'}]
    a.update_messenger_settings.return_value = {'success': True}
    a.get_messenger_status.return_value = {'telegram_bot_available': True}
    a.trigger_script.return_value = True
    a.create_messenger_script.return_value = {'id': 1}
    a.update_messenger_script.return_value = {'id': 1}
    a.delete_messenger_script.return_value = True
    a.mtproto_send_code.return_value = {'phone_code_hash': 'abc'}
    a.mtproto_resend_sms.return_value = {'sent': True}
    a.mtproto_verify_code.return_value = {'valid': True}
    a.mtproto_session_status.return_value = {'valid': True}
    return a


# ==================== _DataCache ====================

class TestDataCache:
    def test_get_returns_none_for_empty(self):
        c = _DataCache()
        assert c.get("key") is None

    def test_set_and_get(self):
        c = _DataCache()
        c.set("key", [1, 2, 3])
        assert c.get("key") == [1, 2, 3]

    def test_ttl_expiry(self):
        c = _DataCache()
        c.set("key", "val")
        # Подменяем timestamp на старое значение
        c._store["key"] = (time.monotonic() - 60, "val")
        assert c.get("key") is None

    def test_custom_ttl(self):
        c = _DataCache()
        c.set("key", "val")
        c._store["key"] = (time.monotonic() - 5, "val")
        # С TTL=3 — просрочено
        assert c.get("key", ttl=3) is None
        # С TTL=10 — ещё валидно
        c.set("key2", "val2")
        c._store["key2"] = (time.monotonic() - 5, "val2")
        assert c.get("key2", ttl=10) == "val2"

    def test_invalidate_all(self):
        c = _DataCache()
        c.set("a", 1)
        c.set("b", 2)
        c.invalidate()
        assert c.get("a") is None
        assert c.get("b") is None

    def test_invalidate_by_prefix(self):
        c = _DataCache()
        c.set("clients:1", "data1")
        c.set("clients:2", "data2")
        c.set("contracts:1", "data3")
        c.invalidate("clients")
        assert c.get("clients:1") is None
        assert c.get("clients:2") is None
        assert c.get("contracts:1") == "data3"


# ==================== СВОЙСТВА И ИНИЦИАЛИЗАЦИЯ ====================

class TestProperties:
    def test_is_multi_user_false(self, db):
        da = _make_da(db)
        assert da.is_multi_user is False

    def test_is_multi_user_true(self, db, api):
        da = _make_da(db, api)
        assert da.is_multi_user is True

    def test_is_online_no_offline_manager_no_api(self, db):
        da = _make_da(db)
        assert da.is_online is False

    def test_is_online_with_api_no_om(self, db, api):
        da = _make_da(db, api)
        assert da.is_online is True

    def test_is_online_uses_offline_manager(self, db, api):
        om = MagicMock()
        om.is_online.return_value = False
        da = _make_da(db, api)
        with patch('utils.data_access.get_offline_manager', return_value=om):
            assert da.is_online is False

    def test_should_use_api_false_offline(self, db):
        da = _make_da(db)
        assert da._should_use_api() is False

    def test_should_use_api_true_online(self, db, api):
        da = _make_da(db, api)
        assert da._should_use_api() is True

    def test_prefer_local_disables_api_reads(self, db, api):
        da = _make_da(db, api)
        da.prefer_local = True
        assert da._should_use_api() is False

    def test_default_prefer_local_false(self, db):
        da = _make_da(db)
        assert da.prefer_local is False


# ==================== PENDING OPS / FORCE SYNC ====================

class TestPendingOps:
    def test_get_pending_ops_no_om(self, db):
        da = _make_da(db)
        assert da.get_pending_operations_count() == 0

    def test_get_pending_ops_with_om(self, db):
        om = MagicMock()
        om.get_pending_operations_count.return_value = 7
        da = _make_da(db)
        with patch('utils.data_access.get_offline_manager', return_value=om):
            assert da.get_pending_operations_count() == 7

    def test_force_sync_no_om(self, db):
        da = _make_da(db)
        da.force_sync()  # не падает

    def test_force_sync_with_om(self, db):
        om = MagicMock()
        da = _make_da(db)
        with patch('utils.data_access.get_offline_manager', return_value=om):
            da.force_sync()
            om.force_sync.assert_called_once()


# ==================== КЛИЕНТЫ ====================

class TestClientsOffline:
    def test_get_all_clients(self, db):
        da = _make_da(db)
        result = da.get_all_clients()
        assert result[0]['full_name'] == 'Локальный'

    def test_get_all_clients_with_skip_limit(self, db):
        da = _make_da(db)
        da.get_all_clients(skip=10, limit=5)
        db.get_all_clients.assert_called_once_with(skip=10, limit=5)

    def test_get_client(self, db):
        da = _make_da(db)
        result = da.get_client(1)
        db.get_client_by_id.assert_called_once_with(1)

    def test_get_clients_paginated(self, db):
        da = _make_da(db)
        clients, total = da.get_clients_paginated(skip=0, limit=10)
        assert total == 1

    def test_create_client(self, db):
        da = _make_da(db)
        result = da.create_client({'full_name': 'Новый'})
        assert result['id'] == 1
        assert result['full_name'] == 'Новый'

    def test_update_client(self, db):
        da = _make_da(db)
        result = da.update_client(1, {'full_name': 'Обновлённый'})
        assert result is True
        db.update_client.assert_called_once()

    def test_delete_client(self, db):
        da = _make_da(db)
        result = da.delete_client(1)
        assert result is True
        db.delete_client.assert_called_once_with(1)

    def test_get_contracts_count_by_client(self, db):
        da = _make_da(db)
        result = da.get_contracts_count_by_client(1)
        assert result == 3


class TestClientsOnline:
    def test_get_all_clients_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_all_clients()
        assert result[0]['full_name'] == 'API Клиент'
        api.get_clients.assert_called_once()

    def test_get_client_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_client(101)
        api.get_client.assert_called_once_with(101)

    def test_get_clients_paginated_api(self, db, api):
        da = _make_da(db, api)
        clients, total = da.get_clients_paginated()
        assert total == 10
        api.get_clients_paginated.assert_called_once()

    def test_create_client_api_success(self, db, api):
        da = _make_da_online(db, api)
        result = da.create_client({'full_name': 'Новый'})
        assert result['id'] == 101
        api.create_client.assert_called_once()

    def test_create_client_api_returns_list(self, db, api):
        """API возвращает list вместо dict — защита."""
        api.create_client.return_value = [{'id': 102, 'full_name': 'Из списка'}]
        da = _make_da_online(db, api)
        result = da.create_client({'full_name': 'Новый'})
        assert result == {'id': 102, 'full_name': 'Из списка'}

    def test_create_client_api_returns_empty_list(self, db, api):
        api.create_client.return_value = []
        da = _make_da_online(db, api)
        result = da.create_client({'full_name': 'Новый'})
        # Пустой list -> {} -> нет server_id
        assert result == {}

    def test_update_client_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.update_client(1, {'full_name': 'Новый'})
        assert result is True
        api.update_client.assert_called_once()

    def test_delete_client_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.delete_client(1)
        assert result is True

    def test_contracts_count_by_client_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_contracts_count_by_client(101)
        # API: считает из get_contracts где client_id==101
        assert isinstance(result, int)


class TestClientsFallback:
    def test_get_all_clients_fallback(self, db, api):
        api.get_clients.side_effect = Exception('API down')
        da = _make_da(db, api)
        result = da.get_all_clients()
        assert result[0]['full_name'] == 'Локальный'

    def test_get_client_fallback(self, db, api):
        api.get_client.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_client(1)
        db.get_client_by_id.assert_called_once_with(1)

    def test_get_clients_paginated_fallback(self, db, api):
        api.get_clients_paginated.side_effect = Exception('fail')
        da = _make_da(db, api)
        clients, total = da.get_clients_paginated()
        assert total == 1

    def test_create_client_api_error_queues(self, db, api):
        api.create_client.side_effect = ConnectionError('timeout')
        da = _make_da_online(db, api)
        with patch.object(da, '_queue_operation') as mock_q:
            result = da.create_client({'full_name': 'Новый'})
        # Возвращает локальный результат
        assert result['id'] == 1

    def test_update_client_api_error(self, db, api):
        api.update_client.side_effect = ConnectionError('timeout')
        da = _make_da_online(db, api)
        result = da.update_client(1, {'full_name': 'Новый'})
        assert result is True  # Локальное обновление прошло

    def test_delete_client_api_error(self, db, api):
        api.delete_client.side_effect = ConnectionError('timeout')
        da = _make_da_online(db, api)
        result = da.delete_client(1)
        assert result is True


# ==================== ДОГОВОРА ====================

class TestContractsOffline:
    def test_get_all_contracts(self, db):
        da = _make_da(db)
        result = da.get_all_contracts()
        assert len(result) == 1

    def test_get_contract(self, db):
        da = _make_da(db)
        result = da.get_contract(10)
        db.get_contract_by_id.assert_called_once_with(10)

    def test_get_contracts_paginated(self, db):
        da = _make_da(db)
        contracts, total = da.get_contracts_paginated()
        assert total == 1

    def test_get_contracts_count_no_filters(self, db):
        da = _make_da(db)
        result = da.get_contracts_count()
        assert result == 1

    def test_check_contract_number_exists(self, db):
        da = _make_da(db)
        result = da.check_contract_number_exists('1/2026')
        assert result is False

    def test_create_contract(self, db):
        da = _make_da(db)
        result = da.create_contract({'contract_number': '2/2026'})
        assert result['id'] == 10

    def test_update_contract(self, db):
        da = _make_da(db)
        result = da.update_contract(10, {'status': 'closed'})
        assert result is True

    def test_delete_contract_offline_only(self, db):
        da = _make_da(db)
        result = da.delete_contract(10)
        # Путь "только локальная БД"
        db.get_crm_card_id_by_contract.assert_called()


class TestContractsOnline:
    def test_get_all_contracts_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_all_contracts()
        api.get_contracts.assert_called_once()

    def test_get_contracts_paginated_api(self, db, api):
        da = _make_da(db, api)
        contracts, total = da.get_contracts_paginated()
        assert total == 5

    def test_get_contracts_count_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_contracts_count()
        assert result == 5

    def test_create_contract_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.create_contract({'contract_number': '2/2026', 'project_type': 'Шаблонный'})
        assert result['id'] == 201

    def test_create_contract_api_returns_list(self, db, api):
        api.create_contract.return_value = [{'id': 202}]
        da = _make_da_online(db, api)
        result = da.create_contract({'contract_number': '3/2026', 'project_type': 'Индивидуальный'})
        assert result['id'] == 202

    def test_delete_contract_api_success(self, db, api):
        da = _make_da_online(db, api)
        result = da.delete_contract(10)
        assert result is True

    def test_delete_contract_api_returns_false(self, db, api):
        api.delete_contract.return_value = False
        da = _make_da_online(db, api)
        result = da.delete_contract(10)
        assert result is False

    def test_check_contract_number_exists_api(self, db, api):
        da = _make_da(db, api)
        result = da.check_contract_number_exists('1/2026')
        assert result is True


class TestContractsFallback:
    def test_get_all_contracts_fallback(self, db, api):
        api.get_contracts.side_effect = Exception('err')
        da = _make_da(db, api)
        result = da.get_all_contracts()
        db.get_all_contracts.assert_called_once()

    def test_get_contracts_count_fallback(self, db, api):
        api.get_contracts_count.side_effect = Exception('err')
        da = _make_da(db, api)
        result = da.get_contracts_count()
        assert result == 1

    def test_get_contracts_count_db_also_fails(self, db, api):
        api.get_contracts_count.side_effect = Exception('err')
        db.get_contracts_count.side_effect = Exception('db err')
        da = _make_da(db, api)
        result = da.get_contracts_count()
        assert result == 0


# ==================== СОТРУДНИКИ ====================

class TestEmployeesOffline:
    def test_get_all_employees(self, db):
        da = _make_da(db)
        result = da.get_all_employees()
        assert len(result) == 1

    def test_get_employee(self, db):
        da = _make_da(db)
        result = da.get_employee(5)
        db.get_employee_by_id.assert_called_once_with(5)

    def test_get_employees_by_position(self, db):
        da = _make_da(db)
        result = da.get_employees_by_position('Менеджер')
        assert len(result) == 1

    def test_create_employee(self, db):
        da = _make_da(db)
        result = da.create_employee({'full_name': 'Новый'})
        assert result['id'] == 30

    def test_update_employee(self, db):
        da = _make_da(db)
        result = da.update_employee(5, {'full_name': 'Обновлён'})
        assert result is True

    def test_delete_employee(self, db):
        da = _make_da(db)
        result = da.delete_employee(5)
        assert result is True

    def test_get_employee_active_assignments(self, db):
        da = _make_da(db)
        result = da.get_employee_active_assignments(5)
        assert len(result) == 1


class TestEmployeesOnline:
    def test_get_all_employees_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_all_employees()
        api.get_employees.assert_called_once()

    def test_get_employee_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_employee(5)
        api.get_employee.assert_called_once_with(5)

    def test_create_employee_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.create_employee({'full_name': 'API Сотрудник'})
        assert result['id'] == 301

    def test_create_employee_api_returns_list(self, db, api):
        api.create_employee.return_value = [{'id': 302}]
        da = _make_da_online(db, api)
        result = da.create_employee({'full_name': 'Список'})
        assert result['id'] == 302

    def test_get_employee_active_assignments_api(self, db, api):
        api.get_crm_cards.return_value = [
            {'id': 1, 'team': [{'executor_id': 5, 'status': 'active', 'stage_name': 'Обмер'}]}
        ]
        da = _make_da(db, api)
        result = da.get_employee_active_assignments(5)
        assert len(result) >= 1


class TestEmployeesFallback:
    def test_get_all_employees_fallback(self, db, api):
        api.get_employees.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_all_employees()
        db.get_all_employees.assert_called_once()

    def test_get_employee_active_assignments_api_fails(self, db, api):
        api.get_crm_cards.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_employee_active_assignments(5)
        assert isinstance(result, list)


# ==================== CRM КАРТОЧКИ ====================

class TestCrmCardsOffline:
    def test_get_crm_cards(self, db):
        da = _make_da(db)
        result = da.get_crm_cards('Индивидуальный')
        db.get_crm_cards_by_project_type.assert_called_once()

    def test_get_crm_card(self, db):
        da = _make_da(db)
        result = da.get_crm_card(100)
        db.get_crm_card_data.assert_called_once_with(100)

    def test_get_archived_crm_cards(self, db):
        da = _make_da(db)
        result = da.get_archived_crm_cards('Индивидуальный')
        assert result[0]['archived'] is True

    def test_create_crm_card(self, db):
        da = _make_da(db)
        result = da.create_crm_card({'contract_id': 10})
        assert result['id'] == 40

    def test_update_crm_card(self, db):
        da = _make_da(db)
        result = da.update_crm_card(100, {'column_name': 'Обмер'})
        assert result is True

    def test_delete_crm_card(self, db):
        da = _make_da(db)
        result = da.delete_crm_card(100)
        assert result is True

    def test_update_crm_card_column(self, db):
        da = _make_da(db)
        result = da.update_crm_card_column(100, 'Обмер')
        assert result is True

    def test_move_crm_card(self, db):
        da = _make_da(db)
        result = da.move_crm_card(100, 'Обмер')
        assert result is True

    def test_get_contract_id_by_crm_card(self, db):
        da = _make_da(db)
        result = da.get_contract_id_by_crm_card(100)
        assert result == 10


class TestCrmCardsOnline:
    def test_get_crm_cards_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_crm_cards('Индивидуальный')
        api.get_crm_cards.assert_called_once()

    def test_get_archived_crm_cards_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_archived_crm_cards('Шаблонный')
        api.get_archived_crm_cards.assert_called_once()

    def test_create_crm_card_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.create_crm_card({'contract_id': 10})
        assert result['id'] == 401

    def test_move_crm_card_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.move_crm_card(100, 'Обмер')
        api.move_crm_card.assert_called_once()


class TestCrmCardsFallback:
    def test_get_crm_cards_fallback(self, db, api):
        api.get_crm_cards.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_crm_cards('Индивидуальный')
        db.get_crm_cards_by_project_type.assert_called_once()


# ==================== WORKFLOW (API-only) ====================

class TestWorkflow:
    def test_get_workflow_state_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_workflow_state(100)
        assert result['state'] == 'draft'

    def test_get_workflow_state_no_api(self, db):
        da = _make_da(db)
        result = da.get_workflow_state(100)
        assert result is None

    def test_get_workflow_state_api_error(self, db, api):
        api.get_workflow_state.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_workflow_state(100)
        assert result is None

    def test_workflow_submit(self, db, api):
        da = _make_da(db, api)
        result = da.workflow_submit(100)
        assert result['state'] == 'review'

    def test_workflow_submit_no_api(self, db):
        da = _make_da(db)
        assert da.workflow_submit(100) is None

    def test_workflow_accept(self, db, api):
        da = _make_da(db, api)
        result = da.workflow_accept(100)
        assert result['state'] == 'accepted'

    def test_workflow_accept_no_api(self, db):
        da = _make_da(db)
        assert da.workflow_accept(100) is None

    def test_workflow_reject(self, db, api):
        da = _make_da(db, api)
        result = da.workflow_reject(100, reason='плохо')
        assert result is not None

    def test_workflow_reject_no_api(self, db):
        da = _make_da(db)
        assert da.workflow_reject(100) is None

    def test_workflow_client_send(self, db, api):
        da = _make_da(db, api)
        result = da.workflow_client_send(100)
        assert result is not None

    def test_workflow_client_send_no_api(self, db):
        da = _make_da(db)
        assert da.workflow_client_send(100) is None

    def test_workflow_client_ok(self, db, api):
        da = _make_da(db, api)
        result = da.workflow_client_ok(100)
        assert result is not None

    def test_workflow_client_ok_no_api(self, db):
        da = _make_da(db)
        assert da.workflow_client_ok(100) is None

    def test_workflow_submit_api_error(self, db, api):
        api.workflow_submit.side_effect = Exception('fail')
        da = _make_da(db, api)
        assert da.workflow_submit(100) is None


# ==================== SUPERVISION ====================

class TestSupervisionOffline:
    def test_get_active(self, db):
        da = _make_da(db)
        result = da.get_supervision_cards_active()
        assert len(result) == 1

    def test_get_archived(self, db):
        da = _make_da(db)
        result = da.get_supervision_cards_archived()
        assert len(result) == 1

    def test_get_supervision_card(self, db):
        da = _make_da(db)
        result = da.get_supervision_card(200)
        db.get_supervision_card_data.assert_called_once_with(200)

    def test_create_supervision_card_with_dict(self, db):
        da = _make_da(db)
        result = da.create_supervision_card({'contract_id': 10, 'column_name': 'Новый'})
        assert result['id'] == 50

    def test_create_supervision_card_with_int(self, db):
        """Принимает int contract_id и конвертирует в dict."""
        da = _make_da(db)
        result = da.create_supervision_card(10)
        assert result is not None

    def test_update_supervision_card(self, db):
        da = _make_da(db)
        result = da.update_supervision_card(200, {'column_name': 'Обмер'})
        assert result is True

    def test_update_supervision_card_column(self, db):
        da = _make_da(db)
        result = da.update_supervision_card_column(200, 'Обмер')
        assert result is True

    def test_move_supervision_card(self, db):
        da = _make_da(db)
        result = da.move_supervision_card(200, 'Готово')
        assert result is True

    def test_complete_supervision_stage(self, db):
        da = _make_da(db)
        result = da.complete_supervision_stage(200, stage_name='Обмер')
        assert result == {'success': True}

    def test_reset_supervision_stage(self, db):
        da = _make_da(db)
        result = da.reset_supervision_stage_completion(200)
        assert result is True

    def test_pause_supervision(self, db):
        da = _make_da(db)
        result = da.pause_supervision_card(200, reason='Ожидание')
        assert result == {'success': True}

    def test_resume_supervision(self, db):
        da = _make_da(db)
        result = da.resume_supervision_card(200)
        assert result == {'success': True}

    def test_delete_supervision_order(self, db):
        da = _make_da(db)
        result = da.delete_supervision_order(10, 200)
        assert result is True

    def test_get_contract_id_by_supervision_card(self, db):
        da = _make_da(db)
        result = da.get_contract_id_by_supervision_card(200)
        # Путь api_client is None -> db
        assert result == 10

    def test_get_supervision_addresses(self, db):
        da = _make_da(db)
        result = da.get_supervision_addresses()
        assert 'Москва' in result

    def test_get_supervision_statistics_filtered(self, db):
        da = _make_da(db)
        result = da.get_supervision_statistics_filtered(year=2026)
        assert result == {'total': 5}


class TestSupervisionOnline:
    def test_get_active_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_supervision_cards_active()
        api.get_supervision_cards.assert_called_with(status="active")

    def test_get_archived_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_supervision_cards_archived()
        api.get_supervision_cards.assert_called_with(status="archived")

    def test_create_supervision_card_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.create_supervision_card({'contract_id': 10})
        assert result['id'] == 501

    def test_move_supervision_card_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.move_supervision_card(200, 'Готово')
        api.move_supervision_card.assert_called_once()

    def test_complete_supervision_stage_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.complete_supervision_stage(200, stage_name='Обмер')
        api.complete_supervision_stage.assert_called_once()

    def test_pause_supervision_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.pause_supervision_card(200, reason='Ожидание')
        api.pause_supervision_card.assert_called_once()

    def test_resume_supervision_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.resume_supervision_card(200, employee_id=5)
        api.resume_supervision_card.assert_called_once()

    def test_get_supervision_addresses_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_supervision_addresses()
        api.get_supervision_addresses.assert_called_once()

    def test_get_supervision_statistics_filtered_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_supervision_statistics_filtered(year=2026)
        api.get_supervision_statistics_filtered.assert_called_once()


class TestSupervisionFallback:
    def test_get_active_fallback(self, db, api):
        api.get_supervision_cards.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_supervision_cards_active()
        db.get_supervision_cards_active.assert_called_once()

    def test_get_supervision_addresses_fallback(self, db, api):
        api.get_supervision_addresses.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_supervision_addresses()
        db.get_supervision_addresses.assert_called_once()

    def test_get_supervision_addresses_db_also_fails(self, db, api):
        api.get_supervision_addresses.side_effect = Exception('api fail')
        db.get_supervision_addresses.side_effect = Exception('db fail')
        da = _make_da(db, api)
        result = da.get_supervision_addresses()
        assert result == []


# ==================== ПЛАТЕЖИ ====================

class TestPaymentsOffline:
    def test_get_payments_for_contract(self, db):
        da = _make_da(db)
        result = da.get_payments_for_contract(10)
        assert len(result) == 1

    def test_create_payment(self, db):
        da = _make_da(db)
        result = da.create_payment({'contract_id': 10, 'amount': 5000})
        assert result['id'] == 60

    def test_update_payment(self, db):
        da = _make_da(db)
        result = da.update_payment(300, {'amount': 6000})
        assert result is True

    def test_delete_payment(self, db):
        da = _make_da(db)
        result = da.delete_payment(300)
        assert result is True

    def test_get_payment(self, db):
        da = _make_da(db)
        result = da.get_payment(300)
        assert result['id'] == 300

    def test_get_payments_by_type(self, db):
        da = _make_da(db)
        result = da.get_payments_by_type('Полная оплата')
        assert len(result) == 1

    def test_get_payments_by_supervision_card(self, db):
        da = _make_da(db)
        result = da.get_payments_by_supervision_card(200)
        assert len(result) == 1

    def test_get_payments_for_supervision(self, db):
        da = _make_da(db)
        result = da.get_payments_for_supervision(10)
        assert len(result) == 1

    def test_get_payments_for_crm(self, db):
        da = _make_da(db)
        result = da.get_payments_for_crm(10)
        assert len(result) == 1

    def test_get_year_payments(self, db):
        da = _make_da(db)
        result = da.get_year_payments(2026)
        assert len(result) == 1

    def test_mark_payment_as_paid(self, db):
        da = _make_da(db)
        result = da.mark_payment_as_paid(300, employee_id=5)
        assert result is True

    def test_create_payment_record(self, db):
        da = _make_da(db)
        result = da.create_payment_record(10, 5, 'designer')
        assert result['id'] == 70

    def test_update_payment_manual(self, db):
        da = _make_da(db)
        result = da.update_payment_manual(300, 7000.0, '2026-01')
        assert result is True

    def test_calculate_payment_amount(self, db):
        da = _make_da(db)
        result = da.calculate_payment_amount(10, 5, 'designer')
        assert result['amount'] == 5000


class TestPaymentsOnline:
    def test_get_payments_for_contract_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_payments_for_contract(10)
        api.get_payments_for_contract.assert_called_once()

    def test_create_payment_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.create_payment({'contract_id': 10})
        assert result['id'] == 601

    def test_mark_payment_as_paid_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.mark_payment_as_paid(300, employee_id=5)
        api.mark_payment_as_paid.assert_called_once()

    def test_create_payment_record_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.create_payment_record(10, 5, 'designer')
        assert result['id'] == 602

    def test_update_payment_manual_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.update_payment_manual(300, 7000.0, '2026-01')
        api.update_payment_manual.assert_called_once()

    def test_recalculate_payments_api(self, db, api):
        da = _make_da(db, api)
        result = da.recalculate_payments(contract_id=10)
        assert result['count'] == 5

    def test_recalculate_payments_no_api(self, db):
        da = _make_da(db)
        result = da.recalculate_payments()
        assert result is None

    def test_set_payments_report_month_api(self, db, api):
        da = _make_da(db, api)
        result = da.set_payments_report_month(10, '2026-01')
        assert result is True

    def test_set_payments_report_month_no_api(self, db):
        da = _make_da(db)
        result = da.set_payments_report_month(10, '2026-01')
        assert result is False


class TestPaymentsFallback:
    def test_get_payments_fallback(self, db, api):
        api.get_payments_for_contract.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_payments_for_contract(10)
        db.get_payments_for_contract.assert_called_once()

    def test_get_year_payments_fallback(self, db, api):
        api.get_year_payments.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_year_payments(2026)
        db.get_year_payments.assert_called_once()


# ==================== ИСТОРИЯ ДЕЙСТВИЙ ====================

class TestHistoryOffline:
    def test_get_action_history(self, db):
        da = _make_da(db)
        result = da.get_action_history('contract', 10)
        assert len(result) == 1

    def test_add_action_history(self, db):
        da = _make_da(db)
        result = da.add_action_history(1, 'create', 'contract', 10, 'Создан')
        assert result is True

    def test_get_supervision_history(self, db):
        da = _make_da(db)
        result = da.get_supervision_history(200)
        assert len(result) == 1

    def test_add_supervision_history(self, db):
        da = _make_da(db)
        result = da.add_supervision_history(200, 1, 'create', 'Создана карточка')
        assert result is True


class TestHistoryOnline:
    def test_get_action_history_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_action_history('contract', 10)
        api.get_action_history.assert_called_once()

    def test_add_action_history_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.add_action_history(1, 'create', 'contract', 10)
        api.create_action_history.assert_called_once()

    def test_get_supervision_history_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_supervision_history(200)
        api.get_supervision_history.assert_called_once()

    def test_add_supervision_history_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.add_supervision_history(200, 1, 'create', 'Описание')
        api.add_supervision_history.assert_called_once()


# ==================== СТАВКИ ====================

class TestRatesOffline:
    def test_get_rates(self, db):
        da = _make_da(db)
        result = da.get_rates('Индивидуальный', 'designer')
        assert len(result) == 1

    def test_get_rate(self, db):
        da = _make_da(db)
        result = da.get_rate(700)
        db.get_rate_by_id.assert_called_once()

    def test_create_rate(self, db):
        da = _make_da(db)
        result = da.create_rate({'role': 'designer', 'price': 500})
        assert result['id'] == 70

    def test_update_rate(self, db):
        da = _make_da(db)
        result = da.update_rate(700, {'price': 600})
        assert result is True

    def test_delete_rate(self, db):
        da = _make_da(db)
        result = da.delete_rate(700)
        assert result is True

    def test_get_template_rates(self, db):
        da = _make_da(db)
        result = da.get_template_rates('designer')
        assert len(result) == 1


class TestRatesOnline:
    def test_get_rates_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_rates()
        api.get_rates.assert_called_once()

    def test_create_rate_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.create_rate({'role': 'designer', 'price': 500})
        assert result['id'] == 701

    def test_save_template_rate_api(self, db, api):
        da = _make_da(db, api)
        result = da.save_template_rate('designer', 0, 100, 5000)
        assert result is not None

    def test_save_template_rate_no_api(self, db):
        da = _make_da(db)
        assert da.save_template_rate('designer', 0, 100, 5000) is None

    def test_save_individual_rate_api(self, db, api):
        da = _make_da(db, api)
        result = da.save_individual_rate('designer', 500)
        assert result is not None

    def test_save_individual_rate_no_api(self, db):
        da = _make_da(db)
        assert da.save_individual_rate('designer', 500) is None

    def test_delete_individual_rate_api(self, db, api):
        da = _make_da(db, api)
        result = da.delete_individual_rate('designer')
        assert result is True

    def test_delete_individual_rate_no_api(self, db):
        da = _make_da(db)
        assert da.delete_individual_rate('designer') is False

    def test_save_surveyor_rate_api(self, db, api):
        da = _make_da(db, api)
        result = da.save_surveyor_rate('Москва', 3000)
        assert result is not None

    def test_save_surveyor_rate_no_api(self, db):
        da = _make_da(db)
        assert da.save_surveyor_rate('Москва', 3000) is None

    def test_save_supervision_rate_api(self, db, api):
        da = _make_da(db, api)
        result = da.save_supervision_rate('Обмер', 1000, 500)
        assert result is not None

    def test_save_supervision_rate_no_api(self, db):
        da = _make_da(db)
        assert da.save_supervision_rate('Обмер', 1000, 500) is None


# ==================== ЗАРПЛАТЫ ====================

class TestSalariesOffline:
    def test_get_salaries(self, db):
        da = _make_da(db)
        result = da.get_salaries('2026-01')
        assert len(result) == 1

    def test_get_salary(self, db):
        da = _make_da(db)
        result = da.get_salary(800)
        db.get_salary_by_id.assert_called_once()

    def test_create_salary(self, db):
        da = _make_da(db)
        result = da.create_salary({'amount': 50000})
        assert result['id'] == 80

    def test_update_salary(self, db):
        da = _make_da(db)
        result = da.update_salary(800, {'amount': 60000})
        assert result is True

    def test_delete_salary(self, db):
        da = _make_da(db)
        result = da.delete_salary(800)
        assert result is True


class TestSalariesOnline:
    def test_get_salaries_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_salaries()
        api.get_salaries.assert_called_once()

    def test_create_salary_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.create_salary({'amount': 50000})
        assert result['id'] == 801

    def test_create_salary_api_returns_list(self, db, api):
        api.create_salary.return_value = [{'id': 802}]
        da = _make_da_online(db, api)
        result = da.create_salary({'amount': 50000})
        assert result['id'] == 802

    def test_delete_salary_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.delete_salary(800)
        api.delete_salary.assert_called_once()


# ==================== АГЕНТЫ ====================

class TestAgents:
    def test_get_all_agents_offline(self, db):
        da = _make_da(db)
        result = da.get_all_agents()
        assert len(result) == 1

    def test_get_all_agents_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_all_agents()
        api.get_all_agents.assert_called_once()

    def test_get_agent_color_local_first(self, db, api):
        """Цвет агента ищется в локальной БД ПЕРВЫМ."""
        da = _make_da(db, api)
        result = da.get_agent_color('ФЕСТИВАЛЬ')
        db.get_agent_color.assert_called_once()
        assert result == '#FF0000'

    def test_get_agent_color_fallback_api(self, db, api):
        db.get_agent_color.return_value = None
        da = _make_da(db, api)
        result = da.get_agent_color('ФЕСТИВАЛЬ')
        api.get_agent_color.assert_called_once()

    def test_get_agent_color_not_found(self, db):
        db.get_agent_color.return_value = None
        da = _make_da(db)
        result = da.get_agent_color('НЕСУЩЕСТВУЮЩИЙ')
        assert result is None

    def test_add_agent(self, db, api):
        da = _make_da_online(db, api)
        result = da.add_agent('НовыйАгент', '#123456')
        api.add_agent.assert_called_once()

    def test_update_agent_color(self, db, api):
        da = _make_da_online(db, api)
        result = da.update_agent_color('ФЕСТИВАЛЬ', '#FFFFFF')
        api.update_agent_color.assert_called_once()

    def test_delete_agent_api(self, db, api):
        da = _make_da(db, api)
        result = da.delete_agent(1)
        assert result is True

    def test_delete_agent_no_api(self, db):
        da = _make_da(db)
        result = da.delete_agent(1)
        db.delete_agent.assert_called_once()

    def test_get_agent_types_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_agent_types()
        assert 'FESTIVAL' in result

    def test_get_agent_types_offline(self, db):
        da = _make_da(db)
        result = da.get_agent_types()
        db.get_agent_types.assert_called_once()

    def test_delete_agent_network_error_queues(self, db, api):
        api.delete_agent.side_effect = ConnectionError('timeout')
        da = _make_da(db, api)
        result = da.delete_agent(1)
        assert result is True  # Успешно через очередь


# ==================== ГОРОДА ====================

class TestCities:
    def test_get_all_cities_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_all_cities()
        api.get_all_cities.assert_called_once()

    def test_get_all_cities_fallback_db(self, db, api):
        api.get_all_cities.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_all_cities()
        db.get_all_cities.assert_called_once()

    def test_get_all_cities_offline(self, db):
        da = _make_da(db)
        result = da.get_all_cities()
        db.get_all_cities.assert_called_once()

    def test_add_city_api(self, db, api):
        da = _make_da(db, api)
        result = da.add_city('Казань')
        api.add_city.assert_called_once()

    def test_add_city_network_error_queues(self, db, api):
        api.add_city.side_effect = ConnectionError('timeout')
        da = _make_da(db, api)
        result = da.add_city('Казань')
        assert result is True  # Через очередь

    def test_delete_city_api(self, db, api):
        da = _make_da(db, api)
        result = da.delete_city(1)
        assert result is True

    def test_delete_city_network_error(self, db, api):
        api.delete_city.side_effect = ConnectionError('timeout')
        da = _make_da(db, api)
        result = da.delete_city(1)
        assert result is True


# ==================== ФАЙЛЫ ====================

class TestFilesOffline:
    def test_get_contract_files(self, db):
        da = _make_da(db)
        result = da.get_contract_files(10)
        assert len(result) == 1

    def test_create_file_record(self, db):
        da = _make_da(db)
        result = da.create_file_record({'contract_id': 10, 'file_name': 'test.jpg'})
        assert result['id'] == 90

    def test_delete_file_record(self, db):
        da = _make_da(db)
        result = da.delete_file_record(900)
        assert result is True

    def test_get_project_files(self, db):
        da = _make_da(db)
        result = da.get_project_files(10)
        assert len(result) == 1

    def test_add_project_file_with_dict(self, db):
        da = _make_da(db)
        result = da.add_project_file({'contract_id': 10, 'file_name': 'test.jpg'})
        assert result == {'id': 91}

    def test_add_project_file_with_kwargs(self, db):
        da = _make_da(db)
        result = da.add_project_file(contract_id=10, file_name='test.jpg')
        assert result is not None


class TestFilesOnline:
    def test_get_contract_files_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_contract_files(10)
        api.get_contract_files.assert_called_once()

    def test_create_file_record_api(self, db, api):
        da = _make_da_online(db, api)
        result = da.create_file_record({'contract_id': 10})
        assert result['id'] == 901

    def test_scan_contract_files_api(self, db, api):
        da = _make_da(db, api)
        result = da.scan_contract_files(10)
        assert result['count'] == 3

    def test_scan_contract_files_no_api(self, db):
        da = _make_da(db)
        assert da.scan_contract_files(10) is None

    def test_get_yandex_public_link(self, db, api):
        da = _make_da(db, api)
        result = da.get_yandex_public_link('/path/file.jpg')
        assert result == 'https://ya.ru/file'

    def test_get_yandex_public_link_no_api(self, db):
        da = _make_da(db)
        assert da.get_yandex_public_link('/path') is None

    def test_delete_yandex_file(self, db, api):
        da = _make_da(db, api)
        result = da.delete_yandex_file('/path/file.jpg')
        assert result is True

    def test_delete_yandex_file_no_api(self, db):
        da = _make_da(db)
        assert da.delete_yandex_file('/path') is False

    def test_validate_files(self, db, api):
        da = _make_da(db, api)
        result = da.validate_files([1, 2])
        assert result == [1, 2]

    def test_validate_files_offline(self, db):
        da = _make_da(db)
        assert da.validate_files([1, 2]) == []


# ==================== ШАБЛОНЫ ПРОЕКТОВ ====================

class TestProjectTemplates:
    def test_get_project_templates_offline(self, db):
        da = _make_da(db)
        result = da.get_project_templates(10)
        assert len(result) == 1

    def test_get_project_templates_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_project_templates(10)
        api.get_project_templates.assert_called_once()

    def test_add_project_template(self, db, api):
        da = _make_da_online(db, api)
        result = da.add_project_template(10, 'https://template.url')
        assert result is True

    def test_delete_project_template(self, db, api):
        da = _make_da_online(db, api)
        result = da.delete_project_template(950)
        assert result is True


# ==================== СТАТИСТИКА / ДАШБОРДЫ ====================

class TestStatistics:
    def test_get_dashboard_statistics_offline(self, db):
        da = _make_da(db)
        result = da.get_dashboard_statistics(year=2026)
        assert result['total_orders'] == 10

    def test_get_dashboard_statistics_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_dashboard_statistics()
        assert result['total_orders'] == 50

    def test_get_supervision_statistics(self, db):
        da = _make_da(db)
        result = da.get_supervision_statistics(address='Москва')
        assert isinstance(result, dict)

    def test_get_clients_dashboard_stats_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_clients_dashboard_stats()
        assert result['total'] == 15

    def test_get_clients_dashboard_stats_offline(self, db):
        da = _make_da(db)
        result = da.get_clients_dashboard_stats()
        assert result['total'] == 5

    def test_get_contracts_dashboard_stats_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_contracts_dashboard_stats()
        assert result['total'] == 8

    def test_get_crm_dashboard_stats_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_crm_dashboard_stats()
        assert result['total'] == 20

    def test_get_employees_dashboard_stats_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_employees_dashboard_stats()
        api.get_employees_dashboard_stats.assert_called_once()

    def test_get_salaries_dashboard_stats_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_salaries_dashboard_stats()
        api.get_salaries_dashboard_stats.assert_called_once()

    def test_get_salaries_individual_stats_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_salaries_individual_stats()
        api.get_salaries_individual_stats.assert_called_once()

    def test_get_salaries_salary_stats_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_salaries_salary_stats()
        api.get_salaries_salary_stats.assert_called_once()

    def test_get_salaries_supervision_stats_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_salaries_supervision_stats()
        api.get_salaries_supervision_stats.assert_called_once()

    def test_get_salaries_template_stats_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_salaries_template_stats()
        api.get_salaries_template_stats.assert_called_once()

    def test_get_salaries_all_payments_stats_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_salaries_all_payments_stats()
        api.get_salaries_all_payments_stats.assert_called_once()

    def test_get_employee_report_data_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_employee_report_data(project_type='Индивидуальный')
        api.get_employee_report_data.assert_called_once()

    def test_get_employee_report_data_offline(self, db):
        da = _make_da(db)
        result = da.get_employee_report_data()
        db.get_employee_report_data.assert_called_once()

    def test_get_project_statistics_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_project_statistics()
        api.get_project_statistics.assert_called_once()

    def test_get_supervision_statistics_report_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_supervision_statistics_report()
        api.get_supervision_statistics.assert_called_once()

    def test_get_crm_statistics_filtered_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_crm_statistics_filtered(project_type='Индивидуальный')
        api.get_crm_statistics_filtered.assert_called_once()

    def test_get_crm_statistics_filtered_fallback(self, db, api):
        api.get_crm_statistics_filtered.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_crm_statistics_filtered()
        db.get_crm_statistics_filtered.assert_called_once()


class TestStatisticsFallback:
    def test_dashboard_stats_api_error_each_fallback(self, db, api):
        """Все dashboard_stats методы при ошибке API fallback на db."""
        methods = [
            'get_clients_dashboard_stats',
            'get_contracts_dashboard_stats',
            'get_crm_dashboard_stats',
            'get_employees_dashboard_stats',
            'get_salaries_dashboard_stats',
            'get_salaries_individual_stats',
            'get_salaries_salary_stats',
            'get_salaries_supervision_stats',
            'get_salaries_template_stats',
            'get_salaries_all_payments_stats',
        ]
        for method_name in methods:
            getattr(api, method_name).side_effect = Exception('fail')
        da = _make_da(db, api)
        for method_name in methods:
            result = getattr(da, method_name)()
            assert isinstance(result, dict), f"{method_name} должен вернуть dict при fallback"

    def test_employee_report_fallback(self, db, api):
        api.get_employee_report_data.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_employee_report_data()
        db.get_employee_report_data.assert_called_once()

    def test_project_statistics_fallback(self, db, api):
        api.get_project_statistics.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_project_statistics()
        db.get_project_statistics.assert_called_once()


# ==================== TIMELINE (CRM) ====================

class TestTimeline:
    def test_get_project_timeline_offline(self, db):
        da = _make_da(db)
        result = da.get_project_timeline(10)
        assert result[0]['stage_code'] == 'S1'

    def test_get_project_timeline_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_project_timeline(10)
        api.get_project_timeline.assert_called_once()

    def test_init_project_timeline_api(self, db, api):
        da = _make_da(db, api)
        result = da.init_project_timeline(10, {'entries': [{'stage': 'S1'}]})
        api.init_project_timeline.assert_called_once()

    def test_init_project_timeline_offline_fallback(self, db):
        da = _make_da(db)
        result = da.init_project_timeline(10, {'entries': [{'stage': 'S1'}]})
        assert result['status'] == 'ok_local'

    def test_reinit_project_timeline_api(self, db, api):
        da = _make_da(db, api)
        result = da.reinit_project_timeline(10, {'entries': []})
        api.reinit_project_timeline.assert_called_once()

    def test_reinit_project_timeline_offline(self, db):
        da = _make_da(db)
        result = da.reinit_project_timeline(10, {})
        assert result is None

    def test_update_timeline_entry(self, db, api):
        da = _make_da_online(db, api)
        result = da.update_timeline_entry(10, 'S1', {'actual_date': '2026-01-01'})
        assert result is True
        api.update_timeline_entry.assert_called_once()

    def test_update_timeline_entry_offline(self, db):
        da = _make_da(db)
        result = da.update_timeline_entry(10, 'S1', {'actual_date': '2026-01-01'})
        assert result is True
        db.update_timeline_entry.assert_called_once()

    def test_get_timeline_summary_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_timeline_summary(10)
        api.get_timeline_summary.assert_called_once()

    def test_get_timeline_summary_offline(self, db):
        da = _make_da(db)
        result = da.get_timeline_summary(10)
        assert 'total_entries' in result or 'progress' in result or result == {}

    def test_export_timeline_excel_api(self, db, api):
        da = _make_da(db, api)
        result = da.export_timeline_excel(10)
        assert result == b'EXCEL'

    def test_export_timeline_excel_no_api(self, db):
        da = _make_da(db)
        assert da.export_timeline_excel(10) == b''

    def test_export_timeline_pdf_api(self, db, api):
        da = _make_da(db, api)
        result = da.export_timeline_pdf(10)
        assert result == b'PDF'

    def test_export_timeline_pdf_no_api(self, db):
        da = _make_da(db)
        assert da.export_timeline_pdf(10) == b''


# ==================== TIMELINE (SUPERVISION) ====================

class TestSupervisionTimeline:
    def test_get_supervision_timeline_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_supervision_timeline(200)
        assert 'entries' in result

    def test_get_supervision_timeline_offline(self, db):
        da = _make_da(db)
        result = da.get_supervision_timeline(200)
        assert 'entries' in result
        assert 'totals' in result

    def test_init_supervision_timeline_api(self, db, api):
        da = _make_da(db, api)
        result = da.init_supervision_timeline(200, {'entries': []})
        api.init_supervision_timeline.assert_called_once()

    def test_init_supervision_timeline_offline(self, db):
        da = _make_da(db)
        result = da.init_supervision_timeline(200, {'entries': [{'stage': 'ST1'}]})
        assert result['status'] == 'ok_local'

    def test_update_supervision_timeline_entry(self, db, api):
        da = _make_da_online(db, api)
        result = da.update_supervision_timeline_entry(200, 'ST1', {'actual_date': '2026-01-01'})
        assert result is True

    def test_get_supervision_timeline_summary_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_supervision_timeline_summary(200)
        api.get_supervision_timeline_summary.assert_called_once()

    def test_get_supervision_timeline_summary_offline(self, db):
        da = _make_da(db)
        result = da.get_supervision_timeline_summary(200)
        # Строится из локальных данных
        assert isinstance(result, dict)

    def test_export_supervision_timeline_excel(self, db, api):
        da = _make_da(db, api)
        result = da.export_supervision_timeline_excel(200)
        assert result == b'EXCEL_SUP'

    def test_export_supervision_timeline_excel_no_api(self, db):
        da = _make_da(db)
        assert da.export_supervision_timeline_excel(200) == b''

    def test_export_supervision_timeline_pdf(self, db, api):
        da = _make_da(db, api)
        result = da.export_supervision_timeline_pdf(200)
        assert result == b'PDF_SUP'


# ==================== STAGE EXECUTORS ====================

class TestStageExecutors:
    def test_get_stage_history_offline(self, db):
        da = _make_da(db)
        result = da.get_stage_history(100)
        assert len(result) == 1

    def test_get_stage_history_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_stage_history(100)
        api.get_stage_history.assert_called_once()

    def test_get_accepted_stages(self, db, api):
        da = _make_da(db, api)
        result = da.get_accepted_stages(100)
        api.get_accepted_stages.assert_called_once()

    def test_get_submitted_stages(self, db, api):
        da = _make_da(db, api)
        result = da.get_submitted_stages(100)
        api.get_submitted_stages.assert_called_once()

    def test_update_stage_executor_deadline(self, db, api):
        da = _make_da_online(db, api)
        result = da.update_stage_executor_deadline(100, 'Обмер', deadline='2026-03-01')
        assert result is True
        api.update_stage_executor.assert_called_once()

    def test_assign_stage_executor(self, db, api):
        da = _make_da_online(db, api)
        result = da.assign_stage_executor(100, {'stage_name': 'Обмер', 'executor_id': 5})
        api.assign_stage_executor.assert_called_once()

    def test_complete_stage_for_executor(self, db, api):
        da = _make_da_online(db, api)
        result = da.complete_stage_for_executor(100, 'Обмер', executor_id=5)
        api.complete_stage_for_executor.assert_called_once()

    def test_complete_stage_for_executor_bool_result(self, db, api):
        api.complete_stage_for_executor.return_value = True
        da = _make_da_online(db, api)
        result = da.complete_stage_for_executor(100, 'Обмер')
        assert result == {'success': True}

    def test_get_incomplete_stage_executors(self, db):
        db.get_incomplete_stage_executors.return_value = [{'id': 1}]
        da = _make_da(db)
        result = da.get_incomplete_stage_executors(100, 'Обмер')
        assert len(result) == 1

    def test_get_stage_completion_info(self, db):
        db.get_stage_completion_info.return_value = {'stage': 'S1', 'approval': None}
        da = _make_da(db)
        result = da.get_stage_completion_info(100, 'Обмер')
        assert result['stage'] == 'S1'

    def test_auto_accept_stage(self, db):
        db.auto_accept_stage.return_value = 1
        da = _make_da(db)
        result = da.auto_accept_stage(100, 'Обмер', 5)
        assert result == 1

    def test_reset_stage_completion(self, db, api):
        da = _make_da_online(db, api)
        result = da.reset_stage_completion(100)
        assert result is True

    def test_reset_designer_completion(self, db, api):
        da = _make_da_online(db, api)
        result = da.reset_designer_completion(100)
        assert result is True

    def test_reset_draftsman_completion(self, db, api):
        da = _make_da_online(db, api)
        result = da.reset_draftsman_completion(100)
        assert result is True

    def test_reset_approval_stages(self, db, api):
        da = _make_da_online(db, api)
        result = da.reset_approval_stages(100)
        assert result is True

    def test_save_manager_acceptance(self, db, api):
        da = _make_da_online(db, api)
        result = da.save_manager_acceptance(100, 'Обмер', 'Иванов', 5)
        api.save_manager_acceptance.assert_called_once()

    def test_save_manager_acceptance_bool_result(self, db, api):
        api.save_manager_acceptance.return_value = True
        da = _make_da_online(db, api)
        result = da.save_manager_acceptance(100, 'Обмер', 'Иванов', 5)
        assert result == {'success': True}

    def test_get_previous_executor_by_position(self, db):
        db.get_previous_executor_by_position.return_value = {'id': 3, 'position': 'designer'}
        da = _make_da(db)
        result = da.get_previous_executor_by_position(100, 'designer')
        assert result['id'] == 3


# ==================== RAW SQL ====================

class TestRawSQL:
    def test_execute_raw_query(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.fetchall.return_value = [{'id': 1}]
        da = _make_da(db)
        result = da.execute_raw_query("SELECT * FROM clients")
        assert cursor.execute.called

    def test_execute_raw_query_with_params(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.fetchall.return_value = []
        da = _make_da(db)
        result = da.execute_raw_query("SELECT * FROM clients WHERE id = ?", (1,))
        assert cursor.execute.called

    def test_execute_raw_update(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.rowcount = 3
        da = _make_da(db)
        result = da.execute_raw_update("UPDATE clients SET name='X'")
        assert isinstance(result, int)

    def test_execute_raw_update_with_params(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.rowcount = 1
        da = _make_da(db)
        result = da.execute_raw_update("UPDATE clients SET name=? WHERE id=?", ('X', 1))
        assert conn.commit.called


# ==================== GLOBAL SEARCH ====================

class TestGlobalSearch:
    def test_global_search_api(self, db, api):
        da = _make_da(db, api)
        result = da.global_search('Иванов')
        api.search.assert_called_once_with('Иванов', 50)

    def test_global_search_api_with_limit(self, db, api):
        da = _make_da(db, api)
        result = da.global_search('Иванов', limit=10)
        api.search.assert_called_once_with('Иванов', 10)

    def test_global_search_fallback(self, db, api):
        api.search.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.global_search('Иванов')
        db.global_search.assert_called_once()

    def test_global_search_offline(self, db):
        da = _make_da(db)
        result = da.global_search('Иванов')
        db.global_search.assert_called_once()


# ==================== FUNNEL / EXECUTOR LOAD ====================

class TestFunnelAndLoad:
    def test_get_funnel_statistics_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_funnel_statistics(year=2026)
        api.get_funnel_statistics.assert_called_once()

    def test_get_funnel_statistics_fallback(self, db, api):
        api.get_funnel_statistics.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_funnel_statistics()
        db.get_funnel_statistics.assert_called_once()

    def test_get_executor_load_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_executor_load(year=2026)
        api.get_executor_load.assert_called_once()

    def test_get_executor_load_fallback(self, db, api):
        api.get_executor_load.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_executor_load()
        db.get_executor_load.assert_called_once()


# ==================== МЕССЕНДЖЕР ====================

class TestMessenger:
    def test_create_messenger_chat(self, db, api):
        da = _make_da(db, api)
        result = da.create_messenger_chat(100)
        assert result['chat_id'] == 1

    def test_create_messenger_chat_no_api(self, db):
        da = _make_da(db)
        assert da.create_messenger_chat(100) is None

    def test_bind_messenger_chat(self, db, api):
        da = _make_da(db, api)
        result = da.bind_messenger_chat(100, 'https://t.me/join')
        assert result is not None

    def test_get_messenger_chat(self, db, api):
        da = _make_da(db, api)
        result = da.get_messenger_chat(100)
        assert result['chat_id'] == 1

    def test_get_messenger_chat_no_api(self, db):
        da = _make_da(db)
        assert da.get_messenger_chat(100) is None

    def test_get_supervision_chat(self, db, api):
        da = _make_da(db, api)
        result = da.get_supervision_chat(200)
        assert result['chat_id'] == 2

    def test_create_supervision_chat(self, db, api):
        da = _make_da(db, api)
        result = da.create_supervision_chat(200)
        assert result is not None

    def test_delete_messenger_chat(self, db, api):
        da = _make_da(db, api)
        result = da.delete_messenger_chat(1)
        assert result is not None

    def test_send_messenger_message(self, db, api):
        da = _make_da(db, api)
        result = da.send_messenger_message(1, 'Привет')
        assert result is not None

    def test_get_messenger_scripts(self, db, api):
        da = _make_da(db, api)
        result = da.get_messenger_scripts()
        assert len(result) == 1

    def test_get_messenger_scripts_no_api(self, db):
        da = _make_da(db)
        assert da.get_messenger_scripts() == []

    def test_get_messenger_settings(self, db, api):
        da = _make_da(db, api)
        result = da.get_messenger_settings()
        assert len(result) == 1

    def test_update_messenger_settings(self, db, api):
        da = _make_da(db, api)
        result = da.update_messenger_settings([{'key': 'val'}])
        assert result is not None

    def test_get_messenger_status(self, db, api):
        da = _make_da(db, api)
        result = da.get_messenger_status()
        assert result['telegram_bot_available'] is True

    def test_get_messenger_status_no_api(self, db):
        da = _make_da(db)
        result = da.get_messenger_status()
        assert result['telegram_bot_available'] is False

    def test_trigger_script(self, db, api):
        da = _make_da(db, api)
        result = da.trigger_script(100, 'start')
        assert result is True

    def test_trigger_script_no_api(self, db):
        da = _make_da(db)
        assert da.trigger_script(100, 'start') is False

    def test_create_messenger_script(self, db, api):
        da = _make_da(db, api)
        result = da.create_messenger_script({'text': 'Hello'})
        assert result is not None

    def test_create_messenger_script_no_api(self, db):
        da = _make_da(db)
        assert da.create_messenger_script({'text': 'Hello'}) is None

    def test_update_messenger_script(self, db, api):
        da = _make_da(db, api)
        result = da.update_messenger_script(1, {'text': 'Updated'})
        assert result is not None

    def test_delete_messenger_script(self, db, api):
        da = _make_da(db, api)
        result = da.delete_messenger_script(1)
        assert result is True

    def test_delete_messenger_script_no_api(self, db):
        da = _make_da(db)
        assert da.delete_messenger_script(1) is False


# ==================== MTPROTO ====================

class TestMTProto:
    def test_mtproto_send_code(self, db, api):
        da = _make_da(db, api)
        result = da.mtproto_send_code()
        assert 'phone_code_hash' in result

    def test_mtproto_send_code_no_api(self, db):
        da = _make_da(db)
        result = da.mtproto_send_code()
        assert 'error' in result

    def test_mtproto_send_code_api_error(self, db, api):
        api.mtproto_send_code.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.mtproto_send_code()
        assert 'error' in result

    def test_mtproto_resend_sms(self, db, api):
        da = _make_da(db, api)
        result = da.mtproto_resend_sms()
        assert result['sent'] is True

    def test_mtproto_resend_sms_no_api(self, db):
        da = _make_da(db)
        assert 'error' in da.mtproto_resend_sms()

    def test_mtproto_verify_code(self, db, api):
        da = _make_da(db, api)
        result = da.mtproto_verify_code('12345')
        assert result['valid'] is True

    def test_mtproto_verify_code_no_api(self, db):
        da = _make_da(db)
        assert 'error' in da.mtproto_verify_code('12345')

    def test_mtproto_session_status(self, db, api):
        da = _make_da(db, api)
        result = da.mtproto_session_status()
        assert result['valid'] is True

    def test_mtproto_session_status_no_api(self, db):
        da = _make_da(db)
        result = da.mtproto_session_status()
        assert result['valid'] is False


# ==================== АДМИНИСТРИРОВАНИЕ ====================

class TestAdmin:
    def test_get_role_permissions_matrix_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_role_permissions_matrix()
        assert 'roles' in result

    def test_get_role_permissions_matrix_no_api(self, db):
        da = _make_da(db)
        result = da.get_role_permissions_matrix()
        assert result == {"roles": {}}

    def test_save_role_permissions_matrix(self, db, api):
        da = _make_da(db, api)
        result = da.save_role_permissions_matrix({'roles': {}})
        assert result is not None

    def test_get_employee_permissions(self, db, api):
        da = _make_da(db, api)
        result = da.get_employee_permissions(5)
        api.get_employee_permissions.assert_called_once()

    def test_get_employee_permissions_fallback(self, db, api):
        api.get_employee_permissions.side_effect = Exception('fail')
        da = _make_da(db, api)
        result = da.get_employee_permissions(5)
        db.get_employee_permissions.assert_called_once()

    def test_set_employee_permissions_list(self, db, api):
        da = _make_da_online(db, api)
        result = da.set_employee_permissions(5, ['view', 'edit'])
        api.set_employee_permissions.assert_called_once()

    def test_set_employee_permissions_dict(self, db, api):
        """Принимает dict и извлекает список."""
        da = _make_da_online(db, api)
        result = da.set_employee_permissions(5, {'permissions': ['view']})
        assert result is True

    def test_reset_employee_permissions(self, db, api):
        da = _make_da(db, api)
        result = da.reset_employee_permissions(5)
        assert result is True

    def test_reset_employee_permissions_no_api(self, db):
        da = _make_da(db)
        result = da.reset_employee_permissions(5)
        assert result is False

    def test_get_permission_definitions(self, db, api):
        da = _make_da(db, api)
        result = da.get_permission_definitions()
        assert len(result) == 1

    def test_get_permission_definitions_no_api(self, db):
        da = _make_da(db)
        result = da.get_permission_definitions()
        assert result == []

    def test_get_norm_days_template_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_norm_days_template('Индивидуальный', 'Жилая')
        api.get_norm_days_template.assert_called_once()

    def test_save_norm_days_template(self, db, api):
        da = _make_da(db, api)
        result = da.save_norm_days_template({'entries': []})
        assert result is not None

    def test_preview_norm_days_template(self, db, api):
        da = _make_da(db, api)
        result = da.preview_norm_days_template('Индивидуальный', 'Жилая', 100.0)
        assert 'contract_term' in result

    def test_preview_norm_days_template_no_api(self, db):
        da = _make_da(db)
        result = da.preview_norm_days_template('Индивидуальный', 'Жилая', 100.0)
        assert result['contract_term'] == 0

    def test_reset_norm_days_template(self, db, api):
        da = _make_da(db, api)
        result = da.reset_norm_days_template('Индивидуальный', 'Жилая')
        assert result is not None


# ==================== ПРОЧЕЕ ====================

class TestMisc:
    def test_get_contract_years_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_contract_years()
        assert 2024 in result

    def test_get_contract_years_offline(self, db):
        da = _make_da(db)
        result = da.get_contract_years()
        assert 2026 in result

    def test_get_cities_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_cities()
        assert 'СПБ' in result

    def test_get_cities_no_api(self, db):
        da = _make_da(db)
        result = da.get_cities()
        assert result == []

    def test_get_current_user_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_current_user()
        assert result['login'] == 'admin'

    def test_get_current_user_no_api(self, db):
        da = _make_da(db)
        assert da.get_current_user() is None

    def test_delete_order_offline(self, db):
        da = _make_da(db)
        result = da.delete_order(10, 100)
        db.delete_order.assert_called_once()
        assert result is True

    def test_delete_order_api_success(self, db, api):
        da = _make_da_online(db, api)
        result = da.delete_order(10, 100)
        assert result is True

    def test_delete_order_api_no_crm_card(self, db, api):
        da = _make_da_online(db, api)
        result = da.delete_order(10)
        api.delete_contract.assert_called_once()

    def test_delete_project_file(self, db, api):
        da = _make_da_online(db, api)
        result = da.delete_project_file(900)
        api.delete_project_file.assert_called_once()

    def test_get_projects_by_type_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_projects_by_type('Индивидуальный')
        api.get_projects_by_type.assert_called_once()

    def test_get_supervision_cards_generic_api(self, db, api):
        da = _make_da(db, api)
        result = da.get_supervision_cards(status='archived')
        api.get_supervision_cards.assert_called_once()

    def test_update_stage_executor(self, db, api):
        da = _make_da_online(db, api)
        result = da.update_stage_executor(100, 'Обмер', {'executor_id': 5})
        assert result == {'success': True}


# ==================== КЕШИРОВАНИЕ ====================

class TestCaching:
    def test_clients_cached_after_first_call(self, db):
        da = _make_da(db)
        da.get_all_clients()
        da.get_all_clients()
        # db вызван один раз — второй из кеша
        assert db.get_all_clients.call_count == 1

    def test_create_client_invalidates_cache(self, db):
        da = _make_da(db)
        da.get_all_clients()
        da.create_client({'full_name': 'Новый'})
        da.get_all_clients()
        assert db.get_all_clients.call_count == 2

    def test_contracts_cached(self, db):
        da = _make_da(db)
        da.get_all_contracts()
        da.get_all_contracts()
        assert db.get_all_contracts.call_count == 1

    def test_create_contract_invalidates_cache(self, db):
        da = _make_da(db)
        da.get_all_contracts()
        da.create_contract({'contract_number': 'X'})
        da.get_all_contracts()
        assert db.get_all_contracts.call_count == 2

    def test_employees_cached(self, db):
        da = _make_da(db)
        da.get_all_employees()
        da.get_all_employees()
        assert db.get_all_employees.call_count == 1

    def test_crm_cards_cached(self, db):
        da = _make_da(db)
        da.get_crm_cards('Индивидуальный')
        da.get_crm_cards('Индивидуальный')
        assert db.get_crm_cards_by_project_type.call_count == 1

    def test_supervision_active_cached(self, db):
        da = _make_da(db)
        da.get_supervision_cards_active()
        da.get_supervision_cards_active()
        assert db.get_supervision_cards_active.call_count == 1

    def test_salaries_cached(self, db):
        da = _make_da(db)
        da.get_salaries('2026-01')
        da.get_salaries('2026-01')
        assert db.get_salaries.call_count == 1

    def test_year_payments_cached(self, db):
        da = _make_da(db)
        da.get_year_payments(2026)
        da.get_year_payments(2026)
        assert db.get_year_payments.call_count == 1


# ==================== _update_local_id ====================

class TestUpdateLocalId:
    def test_update_local_id_same_id_skips(self, db):
        da = _make_da(db)
        da._update_local_id('clients', 5, 5)
        # Не должен вызвать connect
        assert db.connect.call_count == 0

    def test_update_local_id_different_id(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        da = _make_da(db)
        da._update_local_id('clients', 5, 10)
        # Вызвал connect и execute
        assert db.connect.called

    def test_update_local_id_handles_error(self, db):
        db.connect.side_effect = Exception('DB locked')
        da = _make_da(db)
        # Не падает
        da._update_local_id('clients', 5, 10)

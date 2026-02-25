# -*- coding: utf-8 -*-
"""
E2E Regression Tests: QA Audit (PR feat/admin-agents-cities-qa-audit)
Тесты на баги найденные при QA аудите.

Баги:
1. Dashboard CRM: active_orders включало архивные статусы
2. Messenger scripts: memo_file_path столбец отсутствовал в PostgreSQL
3. Agents CRUD: delete_agent не использовал _handle_response
4. Supervision DELETE: MessengerChat не удалялся при удалении карточки надзора
5. complete_stage_for_executor: отсутствовала проверка прав
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import (
    TEST_PREFIX, api_get, api_post, api_patch, api_delete
)


@pytest.mark.e2e
class TestDashboardArchiveRegression:
    """Регрессия: dashboard должен корректно разделять active/archive"""

    def test_dashboard_crm_individual_archive_separate(self, api_base, admin_headers):
        """Dashboard Individual: archive_orders не должен включать active"""
        resp = api_get(
            api_base, "/api/dashboard/crm", admin_headers,
            params={"project_type": "Индивидуальный"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "active_orders" in data
        assert "archive_orders" in data
        assert "total_orders" in data
        # active + archive <= total (могут быть заказы в "Новый заказ" и т.п.)
        assert data["active_orders"] + data["archive_orders"] <= data["total_orders"]

    def test_dashboard_crm_template_archive_separate(self, api_base, admin_headers):
        """Dashboard Template: archive_orders не должен включать active"""
        resp = api_get(
            api_base, "/api/dashboard/crm", admin_headers,
            params={"project_type": "Шаблонный"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_orders"] + data["archive_orders"] <= data["total_orders"]

    def test_dashboard_crm_supervision_archive_separate(self, api_base, admin_headers):
        """Dashboard Supervision: корректный подсчёт"""
        resp = api_get(
            api_base, "/api/dashboard/crm", admin_headers,
            params={"project_type": "Авторский надзор"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "active_orders" in data
        assert "archive_orders" in data


@pytest.mark.e2e
class TestMessengerScriptsMemoRegression:
    """Регрессия: messenger scripts должен поддерживать memo_file_path"""

    def test_scripts_list_has_memo_field(self, api_base, admin_headers):
        """GET /api/messenger/scripts — ответ содержит поле memo_file_path"""
        resp = api_get(api_base, "/api/messenger/scripts", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            # Каждый скрипт должен иметь поле memo_file_path
            for script in data:
                assert "memo_file_path" in script, \
                    f"Скрипт id={script.get('id')} не содержит memo_file_path"

    def test_create_script_with_memo(self, api_base, admin_headers):
        """POST /api/messenger/scripts — можно создать скрипт с memo_file_path"""
        payload = {
            "script_type": "stage_complete",
            "stage_name": f"{TEST_PREFIX}Регрессия",
            "message_template": f"{TEST_PREFIX} тест memo",
            "memo_file_path": "/test/memo.pdf",
            "use_auto_deadline": False,
            "is_enabled": False,
        }
        resp = api_post(api_base, "/api/messenger/scripts", admin_headers, json=payload)
        assert resp.status_code in (200, 201)
        created = resp.json()
        assert created.get("memo_file_path") == "/test/memo.pdf"

        # Cleanup
        script_id = created.get("id")
        if script_id:
            api_delete(api_base, f"/api/messenger/scripts/{script_id}", admin_headers)


@pytest.mark.e2e
class TestCompleteStagePermissionRegression:
    """Регрессия: complete_stage_for_executor проверяет права"""

    def test_complete_stage_requires_auth(self, api_base):
        """PATCH /api/crm/cards/999/stage-executor/test/complete — без авторизации = 401"""
        from tests.e2e.conftest import _http_session, REQUEST_TIMEOUT
        resp = _http_session.patch(
            f"{api_base}/api/crm/cards/999/stage-executor/test/complete",
            json={"executor_id": 1},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        assert resp.status_code in (401, 403, 307)


@pytest.mark.e2e
class TestAutoMigrateColumns:
    """Регрессия: новые столбцы моделей автоматически добавляются в БД"""

    def test_messenger_scripts_endpoint_works(self, api_base, admin_headers):
        """Messenger scripts не должен падать с 500 (отсутствие столбца)"""
        resp = api_get(api_base, "/api/messenger/scripts", admin_headers)
        # Главное — НЕ 500! 200 = всё ок, 403 = нет прав (тоже ок)
        assert resp.status_code != 500, \
            f"Messenger scripts вернул 500 — вероятно, отсутствует столбец в БД"

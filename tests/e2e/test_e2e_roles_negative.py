# -*- coding: utf-8 -*-
"""
E2E Tests: Негативные ролевые тесты — авторизация и права доступа
18 тестов — проверка отказов при отсутствии токена, невалидном JWT,
истёкшем токене, пустом Bearer, а также при недостаточных правах роли.

Покрытие:
  1. Запрос без заголовка Authorization -> 401/403
  2. Запрос с невалидным JWT токеном -> 401
  3. Запрос с истёкшим JWT токеном -> 401
  4. Доступ к админ-endpoint (employees.create) с ролью Дизайнер -> 403
  5. Доступ к админ-endpoint (employees.delete) с ролью Дизайнер -> 403
  6. Доступ к agents.create с ролью Замерщик -> 403
  7. Доступ к cities.create с ролью Чертёжник -> 403
  8. Доступ к salaries.create с ролью Дизайнер -> 403
  9. Доступ к clients.delete с ролью Замерщик -> 403
  10. Доступ к rates.create с ролью ДАН -> 403
  11. Доступ к permissions PUT (изменение прав) от НЕ-суперюзера -> 403
  12. Доступ к permissions reset-to-defaults от НЕ-суперюзера -> 403
  13. Запрос с пустым Bearer токеном -> 401/422
  14. Запрос с Bearer 'null' -> 401
  15. Запрос с Bearer 'undefined' -> 401
  16. Множественные protected endpoint-ы без авторизации -> 401/403
  17. Старший менеджер НЕ может менять Руководителя студии (IDOR) -> 403
  18. Старший менеджер НЕ может повышать роль до Руководителя -> 403
"""

import pytest
import sys
import os
import time
import jwt as pyjwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import (
    TEST_PREFIX, api_get, api_post, api_put, api_patch, api_delete,
    REQUEST_TIMEOUT, _http_session, TEST_PASSWORD, ADMIN_LOGIN, ADMIN_PASSWORD,
)


# ==============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==============================================================

def _make_expired_jwt() -> str:
    """
    Создать заведомо истёкший JWT токен.
    Используем HS256 с произвольным секретом — сервер не сможет верифицировать,
    но главное, что токен синтаксически валиден и имеет формат JWT.
    """
    payload = {
        "sub": 999999,
        "exp": int(time.time()) - 3600,  # 1 час назад
        "type": "access",
        "jti": "expired_test_token",
    }
    return pyjwt.encode(payload, "fake_secret_key_for_test", algorithm="HS256")


def _make_invalid_jwt() -> str:
    """Создать невалидный JWT (подпись не совпадает с сервером)."""
    payload = {
        "sub": 1,
        "exp": int(time.time()) + 3600,
        "type": "access",
        "jti": "invalid_test_token",
    }
    return pyjwt.encode(payload, "completely_wrong_secret", algorithm="HS256")


# ==============================================================
# ТЕСТЫ
# ==============================================================

@pytest.mark.e2e
class TestNoAuth:
    """Запросы без авторизации — сервер должен вернуть 401 или 403"""

    def test_clients_no_auth(self, api_base):
        """GET /api/clients без заголовка Authorization -> 401/403"""
        resp = api_get(api_base, "/api/clients", {})
        assert resp.status_code in (401, 403), (
            f"Ожидается 401/403 без авторизации, получено {resp.status_code}"
        )

    def test_employees_no_auth(self, api_base):
        """GET /api/employees без заголовка Authorization -> 401/403"""
        resp = api_get(api_base, "/api/employees", {})
        assert resp.status_code in (401, 403), (
            f"Ожидается 401/403 без авторизации, получено {resp.status_code}"
        )

    def test_contracts_no_auth(self, api_base):
        """GET /api/contracts без заголовка Authorization -> 401/403"""
        resp = api_get(api_base, "/api/contracts", {})
        assert resp.status_code in (401, 403), (
            f"Ожидается 401/403 без авторизации, получено {resp.status_code}"
        )

    def test_agents_no_auth(self, api_base):
        """GET /api/v1/agents без заголовка Authorization -> 401/403"""
        resp = api_get(api_base, "/api/v1/agents", {})
        assert resp.status_code in (401, 403), (
            f"Ожидается 401/403 без авторизации, получено {resp.status_code}"
        )

    def test_rates_no_auth(self, api_base):
        """GET /api/rates без заголовка Authorization -> 401/403"""
        resp = api_get(api_base, "/api/rates", {})
        assert resp.status_code in (401, 403), (
            f"Ожидается 401/403 без авторизации, получено {resp.status_code}"
        )

    def test_cities_no_auth(self, api_base):
        """GET /api/v1/cities без заголовка Authorization -> 401/403"""
        resp = api_get(api_base, "/api/v1/cities", {})
        assert resp.status_code in (401, 403), (
            f"Ожидается 401/403 без авторизации, получено {resp.status_code}"
        )


@pytest.mark.e2e
class TestInvalidTokens:
    """Запросы с невалидными или испорченными JWT токенами"""

    def test_invalid_jwt_token(self, api_base):
        """Запрос с невалидным JWT токеном (неверная подпись) -> 401"""
        headers = {"Authorization": f"Bearer {_make_invalid_jwt()}"}
        resp = api_get(api_base, "/api/clients", headers)
        assert resp.status_code == 401, (
            f"Ожидается 401 для невалидного JWT, получено {resp.status_code}"
        )

    def test_expired_jwt_token(self, api_base):
        """Запрос с истёкшим JWT токеном -> 401"""
        headers = {"Authorization": f"Bearer {_make_expired_jwt()}"}
        resp = api_get(api_base, "/api/employees", headers)
        assert resp.status_code == 401, (
            f"Ожидается 401 для истёкшего JWT, получено {resp.status_code}"
        )

    def test_empty_bearer_token(self, api_base):
        """Запрос с пустым Bearer -> 401/422"""
        headers = {"Authorization": "Bearer "}
        resp = api_get(api_base, "/api/clients", headers)
        assert resp.status_code in (401, 422), (
            f"Ожидается 401/422 для пустого Bearer, получено {resp.status_code}"
        )

    def test_bearer_null_string(self, api_base):
        """Запрос с Bearer 'null' -> 401"""
        headers = {"Authorization": "Bearer null"}
        resp = api_get(api_base, "/api/clients", headers)
        assert resp.status_code == 401, (
            f"Ожидается 401 для Bearer null, получено {resp.status_code}"
        )

    def test_bearer_undefined_string(self, api_base):
        """Запрос с Bearer 'undefined' -> 401"""
        headers = {"Authorization": "Bearer undefined"}
        resp = api_get(api_base, "/api/clients", headers)
        assert resp.status_code == 401, (
            f"Ожидается 401 для Bearer undefined, получено {resp.status_code}"
        )

    def test_garbage_token(self, api_base):
        """Запрос с мусорной строкой вместо JWT -> 401"""
        headers = {"Authorization": "Bearer not-a-real-jwt-token-at-all!!!"}
        resp = api_get(api_base, "/api/employees", headers)
        assert resp.status_code == 401, (
            f"Ожидается 401 для мусорного токена, получено {resp.status_code}"
        )


@pytest.mark.e2e
class TestRolePermissions:
    """
    Проверка ролевых ограничений: роли без соответствующих прав
    получают 403 при попытке доступа к защищённым endpoint-ам.

    Используем тестовых сотрудников из conftest (фикстура test_employees + role_tokens).
    Роли без админ-прав: Дизайнер, Чертёжник, Замерщик, ДАН.
    """

    def test_designer_cannot_create_employee(self, api_base, role_tokens):
        """Дизайнер НЕ может создать сотрудника (employees.create) -> 403"""
        if 'designer' not in role_tokens:
            pytest.skip("Токен дизайнера не создан")
        resp = api_post(
            api_base, "/api/employees", role_tokens['designer'],
            json={
                "full_name": f"{TEST_PREFIX}НеСозданный",
                "login": f"{TEST_PREFIX}no_create",
                "password": "test123456",
                "role": "Дизайнер",
                "position": "Дизайнер",
                "department": "Проектный",
                "phone": "+79990009999",
            }
        )
        assert resp.status_code == 403, (
            f"Дизайнер не должен создавать сотрудников: ожидается 403, получено {resp.status_code}"
        )

    def test_designer_cannot_delete_employee(self, api_base, role_tokens, test_employees):
        """Дизайнер НЕ может удалить сотрудника (employees.delete) -> 403"""
        if 'designer' not in role_tokens:
            pytest.skip("Токен дизайнера не создан")
        # Пробуем удалить любого тестового сотрудника (например, замерщика)
        target = test_employees.get('surveyor')
        if not target:
            pytest.skip("Тестовый сотрудник surveyor не создан")
        resp = api_delete(
            api_base, f"/api/employees/{target['id']}", role_tokens['designer']
        )
        assert resp.status_code == 403, (
            f"Дизайнер не должен удалять сотрудников: ожидается 403, получено {resp.status_code}"
        )

    def test_surveyor_cannot_create_agent(self, api_base, role_tokens):
        """Замерщик НЕ может создать агента (agents.create) -> 403"""
        if 'surveyor' not in role_tokens:
            pytest.skip("Токен замерщика не создан")
        resp = api_post(
            api_base, "/api/v1/agents", role_tokens['surveyor'],
            json={"name": f"{TEST_PREFIX}ЗАПРЕЩЁННЫЙ_АГЕНТ", "color": "#000000"}
        )
        assert resp.status_code == 403, (
            f"Замерщик не должен создавать агентов: ожидается 403, получено {resp.status_code}"
        )

    def test_draftsman_cannot_create_city(self, api_base, role_tokens):
        """Чертёжник НЕ может создать город (cities.create) -> 403"""
        if 'draftsman' not in role_tokens:
            pytest.skip("Токен чертёжника не создан")
        resp = api_post(
            api_base, "/api/v1/cities", role_tokens['draftsman'],
            json={"name": f"{TEST_PREFIX}ЗАПРЕЩЁННЫЙ_ГОРОД"}
        )
        assert resp.status_code == 403, (
            f"Чертёжник не должен создавать города: ожидается 403, получено {resp.status_code}"
        )

    def test_designer_cannot_create_salary(self, api_base, role_tokens, test_employees):
        """Дизайнер НЕ может создать зарплату (salaries.create) -> 403"""
        if 'designer' not in role_tokens:
            pytest.skip("Токен дизайнера не создан")
        target = test_employees.get('designer')
        if not target:
            pytest.skip("Тестовый сотрудник designer не создан")
        resp = api_post(
            api_base, "/api/salaries", role_tokens['designer'],
            json={
                "employee_id": target['id'],
                "payment_type": "Оклад",
                "amount": 50000.0,
                "report_month": "2026-02",
            }
        )
        assert resp.status_code == 403, (
            f"Дизайнер не должен создавать зарплаты: ожидается 403, получено {resp.status_code}"
        )

    def test_surveyor_cannot_delete_client(self, api_base, admin_headers, role_tokens, module_factory):
        """Замерщик НЕ может удалить клиента (clients.delete) -> 403"""
        if 'surveyor' not in role_tokens:
            pytest.skip("Токен замерщика не создан")
        # Создаём клиента от имени admin
        client = module_factory.create_client(
            full_name=f"{TEST_PREFIX}Клиент для проверки удаления",
            phone="+79993330001",
        )
        resp = api_delete(
            api_base, f"/api/clients/{client['id']}", role_tokens['surveyor']
        )
        assert resp.status_code == 403, (
            f"Замерщик не должен удалять клиентов: ожидается 403, получено {resp.status_code}"
        )

    def test_dan_cannot_create_rate(self, api_base, role_tokens):
        """ДАН НЕ может создать тариф (rates.create) -> 403"""
        if 'dan' not in role_tokens:
            pytest.skip("Токен ДАН не создан")
        resp = api_post(
            api_base, "/api/rates", role_tokens['dan'],
            json={
                "project_type": "Индивидуальный",
                "role": "Дизайнер",
                "rate_per_m2": 100.0,
                "stage_name": f"{TEST_PREFIX}запрещённая_ставка",
            }
        )
        assert resp.status_code == 403, (
            f"ДАН не должен создавать тарифы: ожидается 403, получено {resp.status_code}"
        )

    def test_designer_cannot_delete_agent(self, api_base, admin_headers, role_tokens):
        """Дизайнер НЕ может удалить агента (agents.delete) -> 403"""
        if 'designer' not in role_tokens:
            pytest.skip("Токен дизайнера не создан")
        # Создаём агента от имени admin, затем пробуем удалить от дизайнера
        create_resp = api_post(
            api_base, "/api/v1/agents", admin_headers,
            json={"name": f"{TEST_PREFIX}АГЕНТ_ДЛЯ_УДАЛЕНИЯ_РОЛЬ", "color": "#AABBCC"}
        )
        if create_resp.status_code in (200, 201):
            agent_id = create_resp.json()["id"]
        else:
            # Агент уже существует (возможно удалён) — ищем среди всех включая удалённых
            list_resp = api_get(api_base, "/api/v1/agents", admin_headers,
                                params={"include_deleted": "true"})
            agents = list_resp.json()
            agent = next(
                (a for a in agents if a.get("name") == f"{TEST_PREFIX}АГЕНТ_ДЛЯ_УДАЛЕНИЯ_РОЛЬ"),
                None
            )
            if not agent:
                pytest.skip("Не удалось найти тестового агента для удаления")
            agent_id = agent["id"]

        resp = api_delete(api_base, f"/api/v1/agents/{agent_id}", role_tokens['designer'])
        assert resp.status_code == 403, (
            f"Дизайнер не должен удалять агентов: ожидается 403, получено {resp.status_code}"
        )

        # Очистка: удаляем агента от admin
        api_delete(api_base, f"/api/v1/agents/{agent_id}", admin_headers)


@pytest.mark.e2e
class TestPermissionsEndpointAccess:
    """
    Проверка доступа к endpoint-ам управления правами.
    PUT /api/permissions/{id} и POST /api/permissions/{id}/reset-to-defaults
    доступны только суперюзерам (admin / director / Руководитель студии).
    """

    def test_designer_cannot_set_permissions(self, api_base, role_tokens, test_employees):
        """Дизайнер НЕ может менять права другого сотрудника -> 403"""
        if 'designer' not in role_tokens:
            pytest.skip("Токен дизайнера не создан")
        target = test_employees.get('surveyor')
        if not target:
            pytest.skip("Тестовый сотрудник surveyor не создан")
        resp = api_put(
            api_base,
            f"/api/permissions/{target['id']}",
            role_tokens['designer'],
            json={"permissions": ["employees.create", "employees.delete"]}
        )
        assert resp.status_code == 403, (
            f"Дизайнер не должен менять права: ожидается 403, получено {resp.status_code}"
        )

    def test_manager_cannot_reset_permissions(self, api_base, role_tokens, test_employees):
        """Менеджер НЕ может сбросить права до дефолтных -> 403"""
        if 'manager' not in role_tokens:
            pytest.skip("Токен менеджера не создан")
        target = test_employees.get('draftsman')
        if not target:
            pytest.skip("Тестовый сотрудник draftsman не создан")
        resp = api_post(
            api_base,
            f"/api/permissions/{target['id']}/reset-to-defaults",
            role_tokens['manager'],
        )
        assert resp.status_code == 403, (
            f"Менеджер не должен сбрасывать права: ожидается 403, получено {resp.status_code}"
        )


@pytest.mark.e2e
class TestIDORProtection:
    """
    Проверка IDOR-защиты: Старший менеджер проектов НЕ может
    редактировать Руководителя студии и повышать до защищённых ролей.
    """

    def test_senior_manager_cannot_edit_director(self, api_base, role_tokens, admin_headers):
        """Старший менеджер НЕ может изменить данные admin -> 403"""
        if 'senior_manager' not in role_tokens:
            pytest.skip("Токен старшего менеджера не создан")
        # Находим admin пользователя
        resp = api_get(api_base, "/api/employees", admin_headers)
        assert resp.status_code == 200
        employees = resp.json()
        admin_emp = next((e for e in employees if e.get('login') == 'admin'), None)
        if not admin_emp:
            pytest.skip("admin сотрудник не найден в списке")

        # Пробуем изменить admin от имени старшего менеджера
        update_resp = api_put(
            api_base,
            f"/api/employees/{admin_emp['id']}",
            role_tokens['senior_manager'],
            json={"full_name": f"{TEST_PREFIX}Взломанный Админ"}
        )
        assert update_resp.status_code == 403, (
            f"Старший менеджер не должен менять admin: ожидается 403, получено {update_resp.status_code}"
        )

    def test_senior_manager_cannot_promote_to_director(self, api_base, role_tokens, test_employees):
        """Старший менеджер НЕ может назначить роль 'Руководитель студии' -> 403"""
        if 'senior_manager' not in role_tokens:
            pytest.skip("Токен старшего менеджера не создан")
        target = test_employees.get('designer')
        if not target:
            pytest.skip("Тестовый сотрудник designer не создан")

        # Пробуем повысить дизайнера до руководителя
        resp = api_put(
            api_base,
            f"/api/employees/{target['id']}",
            role_tokens['senior_manager'],
            json={"role": "Руководитель студии"}
        )
        assert resp.status_code == 403, (
            f"Старший менеджер не должен повышать до руководителя: ожидается 403, получено {resp.status_code}"
        )

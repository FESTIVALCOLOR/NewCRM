# -*- coding: utf-8 -*-
"""
E2E Tests: Heartbeat
6 тестов — POST endpoint heartbeat с проверкой структуры ответа.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_post, api_get


class TestHeartbeat:
    """Тесты heartbeat"""

    def test_heartbeat_returns_online_users(self, api_base, admin_headers):
        """POST /api/heartbeat — возвращает список онлайн пользователей"""
        resp = api_post(api_base, "/api/heartbeat", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))

    def test_heartbeat_response_structure(self, api_base, admin_headers):
        """POST /api/heartbeat — структура ответа содержит online_users"""
        resp = api_post(api_base, "/api/heartbeat", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        if isinstance(data, dict):
            # Сервер возвращает dict с ключами status, online_users, online_count
            assert "online_users" in data, (
                f"В dict-ответе должен быть ключ 'online_users', получили ключи: {list(data.keys())}"
            )
            assert isinstance(data["online_users"], list), "online_users должен быть list"
            assert "online_count" in data, "В dict-ответе должен быть ключ 'online_count'"
            assert isinstance(data["online_count"], int), "online_count должен быть int"
            # Проверяем структуру элементов online_users
            for user in data["online_users"][:5]:
                assert "id" in user, f"Каждый онлайн-пользователь должен иметь 'id', получили: {user.keys()}"
                assert "full_name" in user, "Каждый онлайн-пользователь должен иметь 'full_name'"
                assert isinstance(user["id"], int), "user id должен быть int"
        elif isinstance(data, list):
            # Если возвращается list — каждый элемент должен иметь employee_id или id
            for item in data[:5]:
                assert isinstance(item, dict), "Элементы списка должны быть dict"
                has_id = "employee_id" in item or "id" in item
                assert has_id, f"Элемент должен содержать 'id' или 'employee_id': {item.keys()}"

    def test_heartbeat_with_employee_id(self, api_base, admin_headers, test_employees):
        """POST /api/heartbeat?employee_id=X — heartbeat с указанием сотрудника"""
        # Безопасное получение первого сотрудника: пропускаем тест если словарь пуст
        if not test_employees:
            pytest.skip("Тестовые сотрудники не созданы — пропускаем тест")
        emp = next(iter(test_employees.values()))
        resp = api_post(
            api_base, "/api/heartbeat", admin_headers,
            params={"employee_id": emp["id"]}
        )
        assert resp.status_code == 200

    def test_heartbeat_double_call(self, api_base, admin_headers):
        """POST /api/heartbeat дважды подряд — оба запроса возвращают 200"""
        resp1 = api_post(api_base, "/api/heartbeat", admin_headers)
        assert resp1.status_code == 200, f"Первый heartbeat вернул {resp1.status_code}"

        resp2 = api_post(api_base, "/api/heartbeat", admin_headers)
        assert resp2.status_code == 200, f"Второй heartbeat вернул {resp2.status_code}"

        data1 = resp1.json()
        data2 = resp2.json()
        # Оба ответа должны иметь одинаковый тип
        assert type(data1) == type(data2), (
            f"Первый и второй heartbeat вернули разные типы: {type(data1)} vs {type(data2)}"
        )

    def test_heartbeat_invalid_employee_id(self, api_base, admin_headers):
        """POST /api/heartbeat?employee_id=999999 — невалидный employee_id"""
        resp = api_post(
            api_base, "/api/heartbeat", admin_headers,
            params={"employee_id": 999999}
        )
        # Сервер должен либо игнорировать невалидный employee_id (200),
        # либо вернуть ошибку (404/422). Не должен падать с 500.
        assert resp.status_code in (200, 404, 422), (
            f"Ожидали 200/404/422 для невалидного employee_id=999999, "
            f"получили {resp.status_code}"
        )

    def test_heartbeat_requires_auth(self, api_base):
        """POST /api/heartbeat без токена — 401"""
        resp = api_post(api_base, "/api/heartbeat", {})
        assert resp.status_code in (401, 403)

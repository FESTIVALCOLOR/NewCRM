# -*- coding: utf-8 -*-
"""
E2E Tests: Блокировки одновременного редактирования
11 тестов -- создание, проверка, продление, снятие блокировок, конфликты и очистка.
"""

import pytest
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import API_BASE_URL
from tests.e2e.conftest import TEST_PREFIX, REQUEST_TIMEOUT, api_get, api_post, api_delete, _http_session


# ==============================================================
# КОНСТАНТЫ ДЛЯ ТЕСТОВ БЛОКИРОВОК
# ==============================================================

LOCK_ENTITY_TYPE = "crm_card"
LOCK_ENTITY_ID = 999999


# ==============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==============================================================

def _release_lock(api_base, entity_type, entity_id, headers):
    """Безопасное снятие блокировки (игнорирует ошибки)"""
    try:
        _http_session.delete(
            f"{api_base}/api/locks/{entity_type}/{entity_id}",
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
    except Exception:
        pass


def _clear_user_locks(api_base, employee_id, headers):
    """Безопасная очистка всех блокировок пользователя (игнорирует ошибки)"""
    try:
        _http_session.delete(
            f"{api_base}/api/locks/user/{employee_id}",
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
    except Exception:
        pass


# ==============================================================
# CRUD БЛОКИРОВОК
# ==============================================================

class TestLockCRUD:
    """Базовые операции с блокировками: создание, проверка, продление, снятие"""

    @pytest.mark.critical
    def test_create_lock(self, api_base, admin_headers, test_employees):
        """Создание блокировки на сущность"""
        admin_emp = test_employees.get('senior_manager')
        if not admin_emp:
            pytest.skip("Нет тестового старшего менеджера")
        employee_id = admin_emp['id']

        try:
            resp = api_post(
                api_base, "/api/locks", admin_headers,
                params={
                    "entity_type": LOCK_ENTITY_TYPE,
                    "entity_id": LOCK_ENTITY_ID,
                    "employee_id": employee_id,
                }
            )
            assert resp.status_code == 200, (
                f"Не удалось создать блокировку: {resp.status_code} {resp.text}"
            )
            data = resp.json()
            assert data["status"] in ("created", "renewed")
            assert data["entity_type"] == LOCK_ENTITY_TYPE
            assert data["entity_id"] == LOCK_ENTITY_ID
        finally:
            _release_lock(api_base, LOCK_ENTITY_TYPE, LOCK_ENTITY_ID, admin_headers)

    def test_check_lock_status(self, api_base, admin_headers, test_employees):
        """Проверка статуса блокировки"""
        admin_emp = test_employees.get('senior_manager')
        if not admin_emp:
            pytest.skip("Нет тестового старшего менеджера")
        employee_id = admin_emp['id']

        try:
            # Создаём блокировку
            resp = api_post(
                api_base, "/api/locks", admin_headers,
                params={
                    "entity_type": LOCK_ENTITY_TYPE,
                    "entity_id": LOCK_ENTITY_ID,
                    "employee_id": employee_id,
                }
            )
            assert resp.status_code == 200

            # Проверяем статус
            resp = api_get(
                api_base,
                f"/api/locks/{LOCK_ENTITY_TYPE}/{LOCK_ENTITY_ID}",
                admin_headers
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_locked"] is True
            assert "locked_by" in data
            assert "locked_at" in data
            assert "expires_at" in data
            assert "is_own_lock" in data
        finally:
            _release_lock(api_base, LOCK_ENTITY_TYPE, LOCK_ENTITY_ID, admin_headers)

    def test_renew_own_lock(self, api_base, admin_headers, test_employees):
        """Продление собственной блокировки"""
        admin_emp = test_employees.get('senior_manager')
        if not admin_emp:
            pytest.skip("Нет тестового старшего менеджера")
        employee_id = admin_emp['id']

        try:
            # Создаём блокировку
            resp = api_post(
                api_base, "/api/locks", admin_headers,
                params={
                    "entity_type": LOCK_ENTITY_TYPE,
                    "entity_id": LOCK_ENTITY_ID,
                    "employee_id": employee_id,
                }
            )
            assert resp.status_code == 200

            # Продлеваем (повторный POST от того же пользователя)
            resp = api_post(
                api_base, "/api/locks", admin_headers,
                params={
                    "entity_type": LOCK_ENTITY_TYPE,
                    "entity_id": LOCK_ENTITY_ID,
                    "employee_id": employee_id,
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "renewed"
        finally:
            _release_lock(api_base, LOCK_ENTITY_TYPE, LOCK_ENTITY_ID, admin_headers)

    def test_release_lock(self, api_base, admin_headers, test_employees):
        """Снятие блокировки владельцем"""
        admin_emp = test_employees.get('senior_manager')
        if not admin_emp:
            pytest.skip("Нет тестового старшего менеджера")
        employee_id = admin_emp['id']

        # Создаём блокировку
        resp = api_post(
            api_base, "/api/locks", admin_headers,
            params={
                "entity_type": LOCK_ENTITY_TYPE,
                "entity_id": LOCK_ENTITY_ID,
                "employee_id": employee_id,
            }
        )
        assert resp.status_code == 200

        # Снимаем блокировку
        resp = api_delete(
            api_base,
            f"/api/locks/{LOCK_ENTITY_TYPE}/{LOCK_ENTITY_ID}",
            admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "released"

    def test_release_nonexistent_lock(self, api_base, admin_headers):
        """Снятие несуществующей блокировки возвращает not_found"""
        # Используем заведомо несуществующий ID
        resp = api_delete(
            api_base,
            f"/api/locks/{LOCK_ENTITY_TYPE}/888888",
            admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_found"

    def test_check_after_release(self, api_base, admin_headers, test_employees):
        """После снятия блокировки is_locked == False"""
        admin_emp = test_employees.get('senior_manager')
        if not admin_emp:
            pytest.skip("Нет тестового старшего менеджера")
        employee_id = admin_emp['id']

        # Создаём и снимаем блокировку
        api_post(
            api_base, "/api/locks", admin_headers,
            params={
                "entity_type": LOCK_ENTITY_TYPE,
                "entity_id": LOCK_ENTITY_ID,
                "employee_id": employee_id,
            }
        )
        api_delete(
            api_base,
            f"/api/locks/{LOCK_ENTITY_TYPE}/{LOCK_ENTITY_ID}",
            admin_headers
        )

        # Проверяем статус -- блокировки нет
        resp = api_get(
            api_base,
            f"/api/locks/{LOCK_ENTITY_TYPE}/{LOCK_ENTITY_ID}",
            admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_locked"] is False


# ==============================================================
# КОНФЛИКТЫ БЛОКИРОВОК
# ==============================================================

class TestLockConflict:
    """Конфликты при попытке заблокировать уже занятую сущность"""

    def test_different_user_gets_409(self, api_base, admin_headers, test_employees, role_tokens):
        """Другой пользователь получает 409 при попытке заблокировать занятую сущность"""
        if 'sdp' not in role_tokens:
            pytest.skip("Нет токена СДП")

        admin_emp = test_employees.get('senior_manager')
        sdp_emp = test_employees.get('sdp')
        if not admin_emp or not sdp_emp:
            pytest.skip("Нет тестовых сотрудников")

        try:
            # Админ создаёт блокировку
            resp = api_post(
                api_base, "/api/locks", admin_headers,
                params={
                    "entity_type": LOCK_ENTITY_TYPE,
                    "entity_id": LOCK_ENTITY_ID,
                    "employee_id": admin_emp['id'],
                }
            )
            assert resp.status_code == 200

            # СДП пытается заблокировать ту же сущность
            resp = api_post(
                api_base, "/api/locks", role_tokens['sdp'],
                params={
                    "entity_type": LOCK_ENTITY_TYPE,
                    "entity_id": LOCK_ENTITY_ID,
                    "employee_id": sdp_emp['id'],
                }
            )
            assert resp.status_code == 409, (
                f"Ожидался 409 Conflict, получен {resp.status_code}: {resp.text}"
            )
            data = resp.json()
            # detail содержит {message, locked_by, locked_at}
            detail = data.get("detail", data)
            assert "locked_by" in detail
            assert "locked_at" in detail
        finally:
            _release_lock(api_base, LOCK_ENTITY_TYPE, LOCK_ENTITY_ID, admin_headers)

    def test_different_user_cannot_release(self, api_base, admin_headers, test_employees, role_tokens):
        """Другой пользователь не может снять чужую блокировку (403)"""
        if 'sdp' not in role_tokens:
            pytest.skip("Нет токена СДП")

        admin_emp = test_employees.get('senior_manager')
        if not admin_emp:
            pytest.skip("Нет тестового старшего менеджера")

        try:
            # Админ создаёт блокировку
            resp = api_post(
                api_base, "/api/locks", admin_headers,
                params={
                    "entity_type": LOCK_ENTITY_TYPE,
                    "entity_id": LOCK_ENTITY_ID,
                    "employee_id": admin_emp['id'],
                }
            )
            assert resp.status_code == 200

            # СДП пытается снять чужую блокировку
            resp = api_delete(
                api_base,
                f"/api/locks/{LOCK_ENTITY_TYPE}/{LOCK_ENTITY_ID}",
                role_tokens['sdp']
            )
            assert resp.status_code == 403, (
                f"Ожидался 403 Forbidden, получен {resp.status_code}: {resp.text}"
            )
        finally:
            _release_lock(api_base, LOCK_ENTITY_TYPE, LOCK_ENTITY_ID, admin_headers)

    def test_admin_can_release_any_lock(self, api_base, admin_headers, test_employees, role_tokens):
        """Администратор может снять любую блокировку"""
        if 'sdp' not in role_tokens:
            pytest.skip("Нет токена СДП")

        sdp_emp = test_employees.get('sdp')
        if not sdp_emp:
            pytest.skip("Нет тестового СДП")

        try:
            # СДП создаёт блокировку
            resp = api_post(
                api_base, "/api/locks", role_tokens['sdp'],
                params={
                    "entity_type": LOCK_ENTITY_TYPE,
                    "entity_id": LOCK_ENTITY_ID,
                    "employee_id": sdp_emp['id'],
                }
            )
            assert resp.status_code == 200

            # Админ снимает чужую блокировку
            resp = api_delete(
                api_base,
                f"/api/locks/{LOCK_ENTITY_TYPE}/{LOCK_ENTITY_ID}",
                admin_headers
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "released"
        finally:
            _release_lock(api_base, LOCK_ENTITY_TYPE, LOCK_ENTITY_ID, admin_headers)


# ==============================================================
# ОЧИСТКА БЛОКИРОВОК ПОЛЬЗОВАТЕЛЯ
# ==============================================================

class TestClearUserLocks:
    """Массовая очистка блокировок пользователя"""

    def test_clear_all_user_locks(self, api_base, admin_headers, test_employees):
        """Очистка всех блокировок пользователя"""
        admin_emp = test_employees.get('senior_manager')
        if not admin_emp:
            pytest.skip("Нет тестового старшего менеджера")
        employee_id = admin_emp['id']

        try:
            # Создаём несколько блокировок
            for entity_id in [999991, 999992, 999993]:
                resp = api_post(
                    api_base, "/api/locks", admin_headers,
                    params={
                        "entity_type": LOCK_ENTITY_TYPE,
                        "entity_id": entity_id,
                        "employee_id": employee_id,
                    }
                )
                assert resp.status_code == 200

            # Очищаем все блокировки пользователя
            resp = api_delete(
                api_base,
                f"/api/locks/user/{employee_id}",
                admin_headers
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "released"
            assert data["count"] >= 3

            # Проверяем что блокировки сняты
            for entity_id in [999991, 999992, 999993]:
                resp = api_get(
                    api_base,
                    f"/api/locks/{LOCK_ENTITY_TYPE}/{entity_id}",
                    admin_headers
                )
                assert resp.status_code == 200
                assert resp.json()["is_locked"] is False
        finally:
            # Страховочная очистка
            _clear_user_locks(api_base, employee_id, admin_headers)
            for entity_id in [999991, 999992, 999993]:
                _release_lock(api_base, LOCK_ENTITY_TYPE, entity_id, admin_headers)

    def test_cannot_clear_other_user_locks(self, api_base, admin_headers, test_employees, role_tokens):
        """Нельзя очистить блокировки другого пользователя (403)"""
        if 'sdp' not in role_tokens:
            pytest.skip("Нет токена СДП")

        admin_emp = test_employees.get('senior_manager')
        if not admin_emp:
            pytest.skip("Нет тестового старшего менеджера")
        employee_id = admin_emp['id']

        try:
            # Админ создаёт блокировку
            resp = api_post(
                api_base, "/api/locks", admin_headers,
                params={
                    "entity_type": LOCK_ENTITY_TYPE,
                    "entity_id": LOCK_ENTITY_ID,
                    "employee_id": employee_id,
                }
            )
            assert resp.status_code == 200

            # СДП пытается очистить блокировки старшего менеджера
            resp = api_delete(
                api_base,
                f"/api/locks/user/{employee_id}",
                role_tokens['sdp']
            )
            assert resp.status_code == 403, (
                f"Ожидался 403 Forbidden, получен {resp.status_code}: {resp.text}"
            )
        finally:
            _release_lock(api_base, LOCK_ENTITY_TYPE, LOCK_ENTITY_ID, admin_headers)
            _clear_user_locks(api_base, employee_id, admin_headers)

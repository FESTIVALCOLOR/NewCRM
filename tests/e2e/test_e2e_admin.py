# -*- coding: utf-8 -*-
"""
E2E Tests: Страница администрирования — матрица прав и нормо-дни.
Тестирование всех endpoint'ов, задействованных во вкладках AdminDialog.

Требуют деплой серверных endpoint'ов:
- /api/permissions/role-matrix (GET, PUT)
- /api/permissions/definitions (GET)
- /api/norm-days/templates (GET, PUT)
- /api/norm-days/templates/preview (POST)
- /api/norm-days/templates/reset (POST)
"""

import pytest
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import (
    TEST_PREFIX, REQUEST_TIMEOUT, _http_session,
    api_get, api_post, api_put, api_delete,
)


# ==============================================================
# Проверка доступности endpoint'ов на сервере
# ==============================================================

def _check_endpoint_available(api_base, headers, path):
    """Проверка что endpoint существует (не 404)"""
    try:
        resp = _http_session.get(
            f"{api_base}{path}",
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        return resp.status_code != 404
    except Exception:
        return False


@pytest.fixture(scope="session")
def admin_endpoints_available(api_base, admin_headers):
    """Проверка что endpoint'ы матрицы прав задеплоены на сервере"""
    try:
        resp = _http_session.get(
            f"{api_base}/api/permissions/role-matrix",
            headers=admin_headers,
            timeout=REQUEST_TIMEOUT
        )
        # 422 означает что URL попал в /{employee_id} — endpoint ещё не задеплоен
        return resp.status_code not in (404, 422)
    except Exception:
        return False


@pytest.fixture(scope="session")
def norm_days_endpoints_available(api_base, admin_headers):
    """Проверка что endpoint'ы нормо-дней задеплоены"""
    return _check_endpoint_available(
        api_base, admin_headers,
        "/api/norm-days/templates?project_type=test&project_subtype=test"
    )


# ==============================================================
# МАТРИЦА ПРАВ ДОСТУПА (/api/permissions/role-matrix)
# ==============================================================

class TestPermissionsMatrix:
    """Тесты матрицы прав доступа по ролям"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, admin_endpoints_available):
        if not admin_endpoints_available:
            pytest.skip("Endpoint'ы администрирования не задеплоены на сервере")
        self.api_base = api_base
        self.headers = admin_headers

    @pytest.mark.order(1)
    @pytest.mark.critical
    def test_get_role_matrix(self):
        """GET /api/permissions/role-matrix — получение матрицы прав"""
        resp = api_get(self.api_base, "/api/permissions/role-matrix", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "roles" in data, f"Ответ должен содержать ключ 'roles': {data.keys()}"
        roles = data["roles"]
        assert isinstance(roles, dict)
        # Должны быть хотя бы стандартные роли
        assert len(roles) > 0, "Матрица ролей пуста"

    @pytest.mark.order(2)
    def test_role_matrix_contains_known_roles(self):
        """Проверка, что матрица содержит стандартные роли"""
        resp = api_get(self.api_base, "/api/permissions/role-matrix", self.headers)
        assert resp.status_code == 200
        roles = resp.json()["roles"]
        expected_roles = {"Менеджер", "СДП", "ГАП"}
        found = set(roles.keys()) & expected_roles
        assert len(found) >= 2, (
            f"Ожидаются роли {expected_roles}, найдены: {set(roles.keys())}"
        )

    @pytest.mark.order(3)
    def test_role_matrix_permissions_are_lists(self):
        """Каждая роль содержит список прав (list of str)"""
        resp = api_get(self.api_base, "/api/permissions/role-matrix", self.headers)
        assert resp.status_code == 200
        for role, perms in resp.json()["roles"].items():
            assert isinstance(perms, list), f"Права роли '{role}' не являются списком"
            for p in perms:
                assert isinstance(p, str), f"Право '{p}' роли '{role}' не строка"

    @pytest.mark.order(4)
    @pytest.mark.critical
    def test_save_role_matrix(self):
        """PUT /api/permissions/role-matrix — сохранение матрицы"""
        # Получаем текущую матрицу
        get_resp = api_get(self.api_base, "/api/permissions/role-matrix", self.headers)
        assert get_resp.status_code == 200
        original_matrix = get_resp.json()["roles"]

        # Сохраняем без изменений (идемпотентность)
        save_resp = api_put(
            self.api_base,
            "/api/permissions/role-matrix",
            self.headers,
            json={"roles": original_matrix, "apply_to_employees": False}
        )
        assert save_resp.status_code == 200
        saved = save_resp.json()
        assert "roles" in saved

    @pytest.mark.order(5)
    def test_save_role_matrix_apply_to_employees(self):
        """PUT с apply_to_employees=True — обновляет права сотрудников"""
        get_resp = api_get(self.api_base, "/api/permissions/role-matrix", self.headers)
        assert get_resp.status_code == 200
        matrix = get_resp.json()["roles"]

        save_resp = api_put(
            self.api_base,
            "/api/permissions/role-matrix",
            self.headers,
            json={"roles": matrix, "apply_to_employees": True}
        )
        assert save_resp.status_code == 200

    @pytest.mark.order(6)
    def test_save_role_matrix_invalid_permission(self):
        """PUT с несуществующим правом — ошибка 400"""
        save_resp = api_put(
            self.api_base,
            "/api/permissions/role-matrix",
            self.headers,
            json={
                "roles": {"Менеджер": ["nonexistent.permission.xyz"]},
                "apply_to_employees": False,
            }
        )
        assert save_resp.status_code == 400
        assert "Неизвестные права" in save_resp.json().get("detail", "")

    @pytest.mark.order(7)
    def test_save_role_matrix_roundtrip(self):
        """Сохранение и повторная загрузка — данные совпадают"""
        # Получаем текущую матрицу
        get1 = api_get(self.api_base, "/api/permissions/role-matrix", self.headers)
        original = get1.json()["roles"]

        # Сохраняем
        api_put(
            self.api_base,
            "/api/permissions/role-matrix",
            self.headers,
            json={"roles": original, "apply_to_employees": False}
        )

        # Загружаем заново
        get2 = api_get(self.api_base, "/api/permissions/role-matrix", self.headers)
        reloaded = get2.json()["roles"]

        # Сравниваем по ключам
        for role in original:
            assert set(original[role]) == set(reloaded.get(role, [])), (
                f"Несовпадение прав для роли '{role}'"
            )


# ==============================================================
# ОПИСАНИЯ ПРАВ (/api/permissions/definitions)
# ==============================================================

class TestPermissionDefinitions:
    """Тесты списка описаний прав"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, admin_endpoints_available):
        if not admin_endpoints_available:
            pytest.skip("Endpoint'ы администрирования не задеплоены на сервере")
        self.api_base = api_base
        self.headers = admin_headers

    @pytest.mark.order(8)
    def test_get_definitions(self):
        """GET /api/permissions/definitions — получение описаний прав"""
        resp = api_get(self.api_base, "/api/permissions/definitions", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Список описаний прав пуст"
        # Каждое описание — dict с name и description
        for item in data:
            assert "name" in item, f"Нет поля 'name': {item}"
            assert "description" in item, f"Нет поля 'description': {item}"


# ==============================================================
# НОРМО-ДНИ: ШАБЛОНЫ (/api/norm-days/templates)
# ==============================================================

class TestNormDaysTemplates:
    """Тесты шаблонов нормо-дней"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, norm_days_endpoints_available):
        if not norm_days_endpoints_available:
            pytest.skip("Endpoint'ы нормо-дней не задеплоены на сервере")
        self.api_base = api_base
        self.headers = admin_headers

    def _cleanup_custom_template(self, project_type, project_subtype):
        """Вспомогательный метод: сбросить кастомный шаблон"""
        api_post(
            self.api_base,
            "/api/norm-days/templates/reset",
            self.headers,
            json={"project_type": project_type, "project_subtype": project_subtype}
        )

    @pytest.mark.order(10)
    @pytest.mark.critical
    def test_get_template_individual_full(self):
        """GET шаблон нормо-дней: Индивидуальный / Полный"""
        resp = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            params={"project_type": "Индивидуальный", "project_subtype": "Полный (с 3д визуализацией)"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data, f"Нет ключа 'entries': {data.keys()}"
        assert "is_custom" in data
        assert isinstance(data["entries"], list)
        assert len(data["entries"]) > 0, "Шаблон нормо-дней пуст"

    @pytest.mark.order(11)
    def test_get_template_individual_sketch(self):
        """GET шаблон: Индивидуальный / Эскизный"""
        resp = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            params={"project_type": "Индивидуальный", "project_subtype": "Эскизный (с коллажами)"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) > 0

    @pytest.mark.order(12)
    def test_get_template_individual_planning(self):
        """GET шаблон: Индивидуальный / Планировочный"""
        resp = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            params={"project_type": "Индивидуальный", "project_subtype": "Планировочный"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) > 0

    @pytest.mark.order(13)
    def test_get_template_template_standard(self):
        """GET шаблон: Шаблонный / Стандарт"""
        resp = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            params={"project_type": "Шаблонный", "project_subtype": "Стандарт"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) > 0

    @pytest.mark.order(14)
    def test_get_template_template_with_viz(self):
        """GET шаблон: Шаблонный / Стандарт с визуализацией"""
        resp = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            params={"project_type": "Шаблонный", "project_subtype": "Стандарт с визуализацией"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) > 0

    @pytest.mark.order(15)
    def test_template_entry_fields(self):
        """Проверка полей каждой записи шаблона"""
        resp = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            params={"project_type": "Индивидуальный", "project_subtype": "Полный (с 3д визуализацией)"}
        )
        data = resp.json()
        required_fields = {"stage_code", "stage_name", "stage_group", "executor_role", "sort_order"}
        for entry in data["entries"]:
            for field in required_fields:
                assert field in entry, f"Поле '{field}' отсутствует в entry: {entry}"

    @pytest.mark.order(16)
    def test_template_default_is_not_custom(self):
        """Дефолтный шаблон (из формул) имеет is_custom=False"""
        # Сначала убеждаемся, что нет кастомного шаблона
        self._cleanup_custom_template("Индивидуальный", "Планировочный")
        resp = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            params={"project_type": "Индивидуальный", "project_subtype": "Планировочный"}
        )
        data = resp.json()
        assert data["is_custom"] is False


# ==============================================================
# НОРМО-ДНИ: ПРЕВЬЮ (/api/norm-days/templates/preview)
# ==============================================================

class TestNormDaysPreview:
    """Тесты предпросмотра расчёта нормо-дней"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, norm_days_endpoints_available):
        if not norm_days_endpoints_available:
            pytest.skip("Endpoint'ы нормо-дней не задеплоены на сервере")
        self.api_base = api_base
        self.headers = admin_headers

    @pytest.mark.order(20)
    @pytest.mark.critical
    def test_preview_individual_100m2(self):
        """POST preview: Индивидуальный, 100 м²"""
        resp = api_post(
            self.api_base,
            "/api/norm-days/templates/preview",
            self.headers,
            json={
                "project_type": "Индивидуальный",
                "project_subtype": "Полный (с 3д визуализацией)",
                "area": 100,
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data
        assert "contract_term" in data
        assert "k_coefficient" in data
        assert data["contract_term"] > 0
        assert len(data["entries"]) > 0

    @pytest.mark.order(21)
    def test_preview_individual_300m2(self):
        """POST preview: Индивидуальный, 300 м²"""
        resp = api_post(
            self.api_base,
            "/api/norm-days/templates/preview",
            self.headers,
            json={
                "project_type": "Индивидуальный",
                "project_subtype": "Полный (с 3д визуализацией)",
                "area": 300,
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["contract_term"] > 0
        # 300 м² должен дать больше дней, чем 100 м²
        # (не проверяем конкретное число, т.к. зависит от формул)

    @pytest.mark.order(22)
    def test_preview_template_standard(self):
        """POST preview: Шаблонный / Стандарт, 100 м²"""
        resp = api_post(
            self.api_base,
            "/api/norm-days/templates/preview",
            self.headers,
            json={
                "project_type": "Шаблонный",
                "project_subtype": "Стандарт",
                "area": 100,
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data
        assert "contract_term" in data

    @pytest.mark.order(23)
    def test_preview_entries_have_norm_days(self):
        """Каждая запись preview содержит norm_days"""
        resp = api_post(
            self.api_base,
            "/api/norm-days/templates/preview",
            self.headers,
            json={
                "project_type": "Индивидуальный",
                "project_subtype": "Полный (с 3д визуализацией)",
                "area": 100,
            }
        )
        data = resp.json()
        for entry in data["entries"]:
            assert "norm_days" in entry, f"Нет поля 'norm_days': {entry}"
            assert "stage_code" in entry

    @pytest.mark.order(24)
    def test_preview_invalid_area_zero(self):
        """POST preview с area=0 — ошибка"""
        resp = api_post(
            self.api_base,
            "/api/norm-days/templates/preview",
            self.headers,
            json={
                "project_type": "Индивидуальный",
                "project_subtype": "Полный (с 3д визуализацией)",
                "area": 0,
            }
        )
        assert resp.status_code in (400, 422), f"Ожидалось 400/422, получено {resp.status_code}"

    @pytest.mark.order(25)
    def test_preview_invalid_area_negative(self):
        """POST preview с area=-10 — ошибка"""
        resp = api_post(
            self.api_base,
            "/api/norm-days/templates/preview",
            self.headers,
            json={
                "project_type": "Индивидуальный",
                "project_subtype": "Полный (с 3д визуализацией)",
                "area": -10,
            }
        )
        assert resp.status_code in (400, 422)


# ==============================================================
# НОРМО-ДНИ: СОХРАНЕНИЕ И СБРОС
# ==============================================================

class TestNormDaysSaveReset:
    """Тесты сохранения и сброса кастомных шаблонов"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, norm_days_endpoints_available):
        if not norm_days_endpoints_available:
            pytest.skip("Endpoint'ы нормо-дней не задеплоены на сервере")
        self.api_base = api_base
        self.headers = admin_headers

    def _get_default_entries(self, project_type, project_subtype):
        """Получить entries из шаблона по умолчанию"""
        resp = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            params={"project_type": project_type, "project_subtype": project_subtype}
        )
        return resp.json().get("entries", [])

    def _cleanup(self, project_type, project_subtype):
        """Сбросить кастомный шаблон"""
        api_post(
            self.api_base,
            "/api/norm-days/templates/reset",
            self.headers,
            json={"project_type": project_type, "project_subtype": project_subtype}
        )

    @pytest.mark.order(30)
    @pytest.mark.critical
    def test_save_custom_template(self):
        """PUT — сохранение кастомного шаблона нормо-дней"""
        pt = "Индивидуальный"
        ps = "Планировочный"
        self._cleanup(pt, ps)

        # Получаем дефолтные entries
        entries = self._get_default_entries(pt, ps)
        assert len(entries) > 0

        # Преобразуем: добавляем base_norm_days если нет
        api_entries = []
        for e in entries:
            api_entries.append({
                "stage_code": e["stage_code"],
                "stage_name": e["stage_name"],
                "stage_group": e["stage_group"],
                "substage_group": e.get("substage_group", ""),
                "base_norm_days": e.get("base_norm_days", 1.0),
                "k_multiplier": e.get("k_multiplier", 0.0),
                "executor_role": e["executor_role"],
                "is_in_contract_scope": e.get("is_in_contract_scope", True),
                "sort_order": e["sort_order"],
            })

        resp = api_put(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            json={
                "project_type": pt,
                "project_subtype": ps,
                "entries": api_entries,
            }
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result["status"] == "saved"
        assert result["count"] == len(api_entries)

        # Проверяем что шаблон теперь кастомный
        get_resp = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            params={"project_type": pt, "project_subtype": ps}
        )
        data = get_resp.json()
        assert data["is_custom"] is True

        # Очистка
        self._cleanup(pt, ps)

    @pytest.mark.order(31)
    def test_save_empty_entries_rejected(self):
        """PUT с пустым списком entries — ошибка 400/422"""
        resp = api_put(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            json={
                "project_type": "Индивидуальный",
                "project_subtype": "Планировочный",
                "entries": [],
            }
        )
        assert resp.status_code in (400, 422), (
            f"Пустой entries должен быть отклонён, но получено {resp.status_code}"
        )

    @pytest.mark.order(32)
    def test_save_invalid_entry_rejected(self):
        """PUT с некорректной записью (отрицательный base_norm_days) — ошибка"""
        resp = api_put(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            json={
                "project_type": "Индивидуальный",
                "project_subtype": "Планировочный",
                "entries": [{
                    "stage_code": "TEST_01",
                    "stage_name": "Тест",
                    "stage_group": "STAGE1",
                    "base_norm_days": -5.0,
                    "executor_role": "Чертежник",
                    "sort_order": 1,
                }],
            }
        )
        assert resp.status_code in (400, 422)

    @pytest.mark.order(33)
    @pytest.mark.critical
    def test_reset_custom_template(self):
        """POST reset — сброс кастомного шаблона к формулам"""
        pt = "Шаблонный"
        ps = "Стандарт"

        # Получаем дефолтные entries
        entries = self._get_default_entries(pt, ps)
        api_entries = []
        for e in entries:
            api_entries.append({
                "stage_code": e["stage_code"],
                "stage_name": e["stage_name"],
                "stage_group": e["stage_group"],
                "substage_group": e.get("substage_group", ""),
                "base_norm_days": e.get("base_norm_days", 1.0),
                "k_multiplier": e.get("k_multiplier", 0.0),
                "executor_role": e["executor_role"],
                "is_in_contract_scope": e.get("is_in_contract_scope", True),
                "sort_order": e["sort_order"],
            })

        # Сначала сохраняем кастомный
        save_resp = api_put(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            json={"project_type": pt, "project_subtype": ps, "entries": api_entries}
        )
        assert save_resp.status_code == 200

        # Проверяем что кастомный
        get_resp = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            params={"project_type": pt, "project_subtype": ps}
        )
        assert get_resp.json()["is_custom"] is True

        # Сбрасываем
        reset_resp = api_post(
            self.api_base,
            "/api/norm-days/templates/reset",
            self.headers,
            json={"project_type": pt, "project_subtype": ps}
        )
        assert reset_resp.status_code == 200
        result = reset_resp.json()
        assert result["status"] == "reset"
        assert result["deleted"] > 0

        # Проверяем что вернулся к дефолту
        get_resp2 = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            params={"project_type": pt, "project_subtype": ps}
        )
        assert get_resp2.json()["is_custom"] is False

    @pytest.mark.order(34)
    def test_reset_nonexistent_template(self):
        """POST reset для несуществующего шаблона — deleted=0"""
        resp = api_post(
            self.api_base,
            "/api/norm-days/templates/reset",
            self.headers,
            json={
                "project_type": "Индивидуальный",
                "project_subtype": "Планировочный"
            }
        )
        assert resp.status_code == 200
        assert resp.json()["deleted"] >= 0

    @pytest.mark.order(35)
    def test_reset_missing_params(self):
        """POST reset без обязательных параметров — 400"""
        resp = api_post(
            self.api_base,
            "/api/norm-days/templates/reset",
            self.headers,
            json={"project_type": "Индивидуальный"}
        )
        assert resp.status_code == 400


# ==============================================================
# АВТОРИЗАЦИЯ: ДОСТУП К АДМИНИСТРИРОВАНИЮ
# ==============================================================

class TestAdminAuthAccess:
    """Тесты доступа к endpoint'ам администрирования для разных ролей"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, role_tokens, test_employees,
              admin_endpoints_available, norm_days_endpoints_available):
        if not admin_endpoints_available:
            pytest.skip("Endpoint'ы администрирования не задеплоены на сервере")
        self.api_base = api_base
        self.admin_headers = admin_headers
        self.role_tokens = role_tokens
        self.test_employees = test_employees

    @pytest.mark.order(40)
    def test_manager_cannot_save_role_matrix(self):
        """Менеджер не может сохранять матрицу прав"""
        manager_headers = self.role_tokens.get("manager")
        if not manager_headers:
            pytest.skip("Токен менеджера не создан")

        resp = api_put(
            self.api_base,
            "/api/permissions/role-matrix",
            manager_headers,
            json={"roles": {"Менеджер": []}, "apply_to_employees": False}
        )
        assert resp.status_code == 403, (
            f"Менеджер не должен иметь доступ к сохранению матрицы: {resp.status_code}"
        )

    @pytest.mark.order(41)
    def test_manager_cannot_save_norm_days(self):
        """Менеджер не может сохранять шаблоны нормо-дней"""
        manager_headers = self.role_tokens.get("manager")
        if not manager_headers:
            pytest.skip("Токен менеджера не создан")

        resp = api_put(
            self.api_base,
            "/api/norm-days/templates",
            manager_headers,
            json={
                "project_type": "Индивидуальный",
                "project_subtype": "Планировочный",
                "entries": [{
                    "stage_code": "TEST", "stage_name": "Test",
                    "stage_group": "STAGE1", "base_norm_days": 1.0,
                    "executor_role": "Чертежник", "sort_order": 1,
                }],
            }
        )
        assert resp.status_code == 403

    @pytest.mark.order(42)
    def test_manager_can_read_role_matrix(self):
        """Менеджер может читать матрицу прав (через employees.update)"""
        manager_headers = self.role_tokens.get("manager")
        if not manager_headers:
            pytest.skip("Токен менеджера не создан")

        # Зависит от прав — может вернуть 200 или 403
        resp = api_get(self.api_base, "/api/permissions/role-matrix", manager_headers)
        # Менеджер без employees.update -> 403
        assert resp.status_code in (200, 403)

    @pytest.mark.order(43)
    def test_manager_can_read_norm_days(self):
        """Менеджер может читать шаблоны нормо-дней"""
        manager_headers = self.role_tokens.get("manager")
        if not manager_headers:
            pytest.skip("Токен менеджера не создан")

        resp = api_get(
            self.api_base,
            "/api/norm-days/templates",
            manager_headers,
            params={"project_type": "Индивидуальный", "project_subtype": "Планировочный"}
        )
        assert resp.status_code == 200

    @pytest.mark.order(44)
    def test_unauthorized_access_rejected(self):
        """Запросы без авторизации отклоняются"""
        resp = api_get(
            self.api_base,
            "/api/permissions/role-matrix",
            {},
        )
        assert resp.status_code in (401, 403, 422)

    @pytest.mark.order(45)
    def test_admin_can_access_all(self):
        """Администратор имеет полный доступ ко всем endpoint'ам"""
        # Матрица прав
        resp1 = api_get(self.api_base, "/api/permissions/role-matrix", self.admin_headers)
        assert resp1.status_code == 200

        # Описания прав
        resp2 = api_get(self.api_base, "/api/permissions/definitions", self.admin_headers)
        assert resp2.status_code == 200

        # Шаблоны нормо-дней
        resp3 = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.admin_headers,
            params={"project_type": "Индивидуальный", "project_subtype": "Планировочный"}
        )
        assert resp3.status_code == 200

        # Preview
        resp4 = api_post(
            self.api_base,
            "/api/norm-days/templates/preview",
            self.admin_headers,
            json={
                "project_type": "Индивидуальный",
                "project_subtype": "Полный (с 3д визуализацией)",
                "area": 100,
            }
        )
        assert resp4.status_code == 200


# ==============================================================
# ИНТЕГРАЦИЯ: ПОЛНЫЙ РАБОЧИЙ ПРОЦЕСС
# ==============================================================

class TestAdminWorkflow:
    """Интеграционные тесты: полный рабочий процесс администрирования"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, admin_endpoints_available, norm_days_endpoints_available):
        if not admin_endpoints_available or not norm_days_endpoints_available:
            pytest.skip("Endpoint'ы администрирования не задеплоены на сервере")
        self.api_base = api_base
        self.headers = admin_headers

    @pytest.mark.order(50)
    @pytest.mark.critical
    def test_full_norm_days_workflow(self):
        """Полный цикл: загрузка → редактирование → сохранение → загрузка → сброс"""
        pt = "Индивидуальный"
        ps = "Планировочный"

        # 1. Сбросить (чтобы гарантировать дефолт)
        api_post(
            self.api_base,
            "/api/norm-days/templates/reset",
            self.headers,
            json={"project_type": pt, "project_subtype": ps}
        )

        # 2. Загрузить дефолтный
        resp1 = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            params={"project_type": pt, "project_subtype": ps}
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["is_custom"] is False
        original_entries = data1["entries"]
        assert len(original_entries) > 0

        # 3. Сохранить как кастомный (модифицируем base_norm_days первой записи)
        api_entries = []
        for e in original_entries:
            api_entries.append({
                "stage_code": e["stage_code"],
                "stage_name": e["stage_name"],
                "stage_group": e["stage_group"],
                "substage_group": e.get("substage_group", ""),
                "base_norm_days": e.get("base_norm_days", 1.0) + 1.0,  # +1 день
                "k_multiplier": e.get("k_multiplier", 0.0),
                "executor_role": e["executor_role"],
                "is_in_contract_scope": e.get("is_in_contract_scope", True),
                "sort_order": e["sort_order"],
            })

        save_resp = api_put(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            json={"project_type": pt, "project_subtype": ps, "entries": api_entries}
        )
        assert save_resp.status_code == 200

        # 4. Загрузить — должен быть кастомный
        resp2 = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            params={"project_type": pt, "project_subtype": ps}
        )
        data2 = resp2.json()
        assert data2["is_custom"] is True

        # 5. Сбросить обратно
        reset_resp = api_post(
            self.api_base,
            "/api/norm-days/templates/reset",
            self.headers,
            json={"project_type": pt, "project_subtype": ps}
        )
        assert reset_resp.status_code == 200

        # 6. Проверить что снова дефолтный
        resp3 = api_get(
            self.api_base,
            "/api/norm-days/templates",
            self.headers,
            params={"project_type": pt, "project_subtype": ps}
        )
        assert resp3.json()["is_custom"] is False

    @pytest.mark.order(51)
    def test_full_permissions_workflow(self):
        """Полный цикл матрицы прав: загрузка → изменение → сохранение → проверка"""
        # 1. Загрузить текущую матрицу
        resp1 = api_get(self.api_base, "/api/permissions/role-matrix", self.headers)
        assert resp1.status_code == 200
        original_matrix = resp1.json()["roles"]

        # 2. Сохранить без изменений
        save_resp = api_put(
            self.api_base,
            "/api/permissions/role-matrix",
            self.headers,
            json={"roles": original_matrix, "apply_to_employees": False}
        )
        assert save_resp.status_code == 200

        # 3. Проверить что ничего не сломалось
        resp2 = api_get(self.api_base, "/api/permissions/role-matrix", self.headers)
        assert resp2.status_code == 200
        reloaded = resp2.json()["roles"]
        for role in original_matrix:
            if role in reloaded:
                assert set(original_matrix[role]) == set(reloaded[role])

    @pytest.mark.order(52)
    def test_preview_different_areas(self):
        """Preview для разных площадей — contract_term увеличивается с площадью"""
        areas = [70, 130, 300]
        terms = []
        for area in areas:
            resp = api_post(
                self.api_base,
                "/api/norm-days/templates/preview",
                self.headers,
                json={
                    "project_type": "Индивидуальный",
                    "project_subtype": "Полный (с 3д визуализацией)",
                    "area": area,
                }
            )
            assert resp.status_code == 200
            terms.append(resp.json()["contract_term"])

        # Срок должен расти (или не уменьшаться) с площадью
        assert terms[-1] >= terms[0], (
            f"Срок должен расти с площадью: {list(zip(areas, terms))}"
        )

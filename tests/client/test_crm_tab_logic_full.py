# -*- coding: utf-8 -*-
"""
Покрытие ui/crm_tab.py — чистые функции бизнес-логики.
_emp_has_pos, _emp_only_pos, _load_user_permissions, _has_perm.
~25 тестов.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture(autouse=True)
def _clear_permissions_cache():
    """Очищать кэш permissions перед каждым тестом."""
    from ui.crm_tab import _user_permissions_cache
    _user_permissions_cache.clear()
    yield
    _user_permissions_cache.clear()


# ==================== _emp_has_pos ====================

class TestEmpHasPos:
    def test_primary_position_matches(self):
        from ui.crm_tab import _emp_has_pos
        emp = {'position': 'Менеджер', 'secondary_position': ''}
        assert _emp_has_pos(emp, 'Менеджер') is True

    def test_secondary_position_matches(self):
        from ui.crm_tab import _emp_has_pos
        emp = {'position': 'Дизайнер', 'secondary_position': 'ГАП'}
        assert _emp_has_pos(emp, 'ГАП') is True

    def test_no_match(self):
        from ui.crm_tab import _emp_has_pos
        emp = {'position': 'Дизайнер', 'secondary_position': ''}
        assert _emp_has_pos(emp, 'Менеджер') is False

    def test_multiple_positions_any_match(self):
        from ui.crm_tab import _emp_has_pos
        emp = {'position': 'Замерщик', 'secondary_position': ''}
        assert _emp_has_pos(emp, 'Менеджер', 'Замерщик', 'ГАП') is True

    def test_none_employee(self):
        from ui.crm_tab import _emp_has_pos
        assert _emp_has_pos(None, 'Менеджер') is False

    def test_empty_employee(self):
        from ui.crm_tab import _emp_has_pos
        assert _emp_has_pos({}, 'Менеджер') is False


# ==================== _emp_only_pos ====================

class TestEmpOnlyPos:
    def test_single_position_matches(self):
        from ui.crm_tab import _emp_only_pos
        emp = {'position': 'Дизайнер', 'secondary_position': ''}
        assert _emp_only_pos(emp, 'Дизайнер') is True

    def test_both_positions_in_set(self):
        from ui.crm_tab import _emp_only_pos
        emp = {'position': 'Дизайнер', 'secondary_position': 'Чертёжник'}
        assert _emp_only_pos(emp, 'Дизайнер', 'Чертёжник') is True

    def test_secondary_outside_set(self):
        from ui.crm_tab import _emp_only_pos
        emp = {'position': 'Дизайнер', 'secondary_position': 'ГАП'}
        assert _emp_only_pos(emp, 'Дизайнер') is False

    def test_primary_not_in_set(self):
        from ui.crm_tab import _emp_only_pos
        emp = {'position': 'Менеджер', 'secondary_position': ''}
        assert _emp_only_pos(emp, 'Дизайнер') is False

    def test_none_employee(self):
        from ui.crm_tab import _emp_only_pos
        assert _emp_only_pos(None, 'Менеджер') is False

    def test_no_secondary_empty_string(self):
        from ui.crm_tab import _emp_only_pos
        emp = {'position': 'Менеджер', 'secondary_position': ''}
        # empty string is falsy, so sec check is skipped
        assert _emp_only_pos(emp, 'Менеджер') is True


# ==================== _load_user_permissions ====================

class TestLoadUserPermissions:
    def test_none_employee_returns_empty_set(self):
        from ui.crm_tab import _load_user_permissions
        result = _load_user_permissions(None, None)
        assert result == set()

    def test_admin_returns_none(self):
        from ui.crm_tab import _load_user_permissions
        emp = {'id': 1, 'role': 'admin'}
        result = _load_user_permissions(emp, None)
        assert result is None  # None = все права

    def test_director_returns_none(self):
        from ui.crm_tab import _load_user_permissions
        emp = {'id': 2, 'role': 'director'}
        result = _load_user_permissions(emp, None)
        assert result is None

    def test_regular_user_with_api(self):
        from ui.crm_tab import _load_user_permissions
        emp = {'id': 3, 'role': 'user'}
        mock_api = MagicMock()
        mock_api.get_employee_permissions.return_value = {'permissions': ['view_crm', 'edit_crm']}
        result = _load_user_permissions(emp, mock_api)
        assert 'view_crm' in result
        assert 'edit_crm' in result

    def test_regular_user_without_api(self):
        from ui.crm_tab import _load_user_permissions
        emp = {'id': 4, 'role': 'user'}
        result = _load_user_permissions(emp, None)
        assert result == set()

    def test_caches_result(self):
        from ui.crm_tab import _load_user_permissions, _user_permissions_cache
        emp = {'id': 5, 'role': 'admin'}
        _load_user_permissions(emp, None)
        assert 5 in _user_permissions_cache
        # Проверяем формат кортежа (perms, timestamp)
        cached = _user_permissions_cache[5]
        assert isinstance(cached, tuple) and len(cached) == 2

    def test_returns_cached_value(self):
        import time
        from ui.crm_tab import _load_user_permissions, _user_permissions_cache
        _user_permissions_cache[6] = ({'custom_perm'}, time.time())
        emp = {'id': 6, 'role': 'user'}
        result = _load_user_permissions(emp, None)
        assert result == {'custom_perm'}

    def test_api_error_returns_empty(self):
        from ui.crm_tab import _load_user_permissions
        emp = {'id': 7, 'role': 'user'}
        mock_api = MagicMock()
        mock_api.get_employee_permissions.side_effect = Exception('network')
        result = _load_user_permissions(emp, mock_api)
        assert result == set()


# ==================== _has_perm ====================

class TestHasPerm:
    def test_superuser_has_all_perms(self):
        from ui.crm_tab import _has_perm
        emp = {'id': 10, 'role': 'admin'}
        assert _has_perm(emp, None, 'anything') is True

    def test_user_with_perm(self):
        import time
        from ui.crm_tab import _has_perm, _user_permissions_cache
        _user_permissions_cache[11] = ({'view_crm', 'edit_crm'}, time.time())
        emp = {'id': 11, 'role': 'user'}
        assert _has_perm(emp, None, 'view_crm') is True

    def test_user_without_perm(self):
        import time
        from ui.crm_tab import _has_perm, _user_permissions_cache
        _user_permissions_cache[12] = ({'view_crm'}, time.time())
        emp = {'id': 12, 'role': 'user'}
        assert _has_perm(emp, None, 'delete_crm') is False

    def test_user_with_no_perms(self):
        import time
        from ui.crm_tab import _has_perm, _user_permissions_cache
        _user_permissions_cache[13] = (set(), time.time())
        emp = {'id': 13, 'role': 'user'}
        assert _has_perm(emp, None, 'view_crm') is False

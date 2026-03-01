# -*- coding: utf-8 -*-
"""Unit-тесты для utils/permissions.py — центрального модуля проверки прав.

Покрывает:
- _emp_has_pos / _emp_only_pos — проверка должностей
- _load_user_permissions — загрузка, кэш, superuser, fallback
- _has_perm / has_any_perm — проверка конкретных прав
- invalidate_cache — сброс кэша
- get_allowed_tabs — маппинг access.* → вкладки + fallback на config.py
- _get_default_permissions_for_position — дефолты по должности
"""

import pytest
from unittest.mock import MagicMock, patch

from utils.permissions import (
    _emp_has_pos,
    _emp_only_pos,
    _load_user_permissions,
    _get_default_permissions_for_position,
    _has_perm,
    has_any_perm,
    invalidate_cache,
    get_allowed_tabs,
    ACCESS_TAB_MAP,
    _user_permissions_cache,
)


# ============================================================================
# Фикстуры
# ============================================================================

def _make_employee(position, secondary_position='', role='user', emp_id=1):
    """Фабрика тестовых сотрудников."""
    return {
        'id': emp_id,
        'full_name': 'Тест',
        'position': position,
        'secondary_position': secondary_position,
        'role': role,
    }


def _make_api_client(permissions=None, raise_error=False):
    """Фабрика mock API клиента."""
    api = MagicMock()
    if raise_error:
        api.get_employee_permissions.side_effect = Exception("Connection refused")
    elif permissions is not None:
        api.get_employee_permissions.return_value = {'permissions': list(permissions)}
    else:
        api.get_employee_permissions.return_value = {'permissions': []}
    return api


@pytest.fixture(autouse=True)
def clear_cache():
    """Очистка кэша перед каждым тестом."""
    _user_permissions_cache.clear()
    yield
    _user_permissions_cache.clear()


# ============================================================================
# _emp_has_pos — проверка наличия должности
# ============================================================================

class TestEmpHasPos:
    """Тесты _emp_has_pos: True если хотя бы одна должность совпадает."""

    def test_none_employee_returns_false(self):
        assert _emp_has_pos(None, 'Дизайнер') is False

    def test_empty_dict_returns_false(self):
        assert _emp_has_pos({}, 'Дизайнер') is False

    def test_primary_position_match(self):
        emp = _make_employee('Дизайнер')
        assert _emp_has_pos(emp, 'Дизайнер') is True

    def test_secondary_position_match(self):
        emp = _make_employee('Дизайнер', secondary_position='Чертёжник')
        assert _emp_has_pos(emp, 'Чертёжник') is True

    def test_no_match(self):
        emp = _make_employee('Дизайнер')
        assert _emp_has_pos(emp, 'Менеджер', 'ГАП') is False

    def test_multiple_positions_one_matches(self):
        emp = _make_employee('Менеджер')
        assert _emp_has_pos(emp, 'Дизайнер', 'Менеджер', 'ГАП') is True

    def test_empty_position_no_match(self):
        emp = _make_employee('')
        assert _emp_has_pos(emp, 'Дизайнер') is False

    def test_secondary_empty_no_false_match(self):
        """secondary_position == '' не должен матчить пустую строку в аргументах."""
        emp = _make_employee('Дизайнер', secondary_position='')
        assert _emp_has_pos(emp, 'Дизайнер') is True
        assert _emp_has_pos(emp, 'Чертёжник') is False


# ============================================================================
# _emp_only_pos — проверка что ВСЕ должности в наборе
# ============================================================================

class TestEmpOnlyPos:
    """Тесты _emp_only_pos: True если сотрудник — чистый исполнитель."""

    def test_none_employee_returns_false(self):
        assert _emp_only_pos(None, 'Дизайнер') is False

    def test_primary_in_set_no_secondary(self):
        emp = _make_employee('Дизайнер')
        assert _emp_only_pos(emp, 'Дизайнер', 'Чертёжник') is True

    def test_both_positions_in_set(self):
        emp = _make_employee('Дизайнер', secondary_position='Чертёжник')
        assert _emp_only_pos(emp, 'Дизайнер', 'Чертёжник') is True

    def test_primary_in_set_secondary_not(self):
        """Дизайнер + Менеджер — не чистый исполнитель."""
        emp = _make_employee('Дизайнер', secondary_position='Менеджер')
        assert _emp_only_pos(emp, 'Дизайнер', 'Чертёжник') is False

    def test_primary_not_in_set(self):
        emp = _make_employee('Менеджер')
        assert _emp_only_pos(emp, 'Дизайнер', 'Чертёжник') is False

    def test_single_position_match(self):
        emp = _make_employee('Замерщик')
        assert _emp_only_pos(emp, 'Замерщик') is True

    def test_single_position_no_match(self):
        emp = _make_employee('Замерщик')
        assert _emp_only_pos(emp, 'Дизайнер') is False


# ============================================================================
# _load_user_permissions — загрузка, кэш, superuser, fallback
# ============================================================================

class TestLoadUserPermissions:
    """Тесты _load_user_permissions: API → кэш → fallback."""

    def test_none_employee_returns_empty_set(self):
        result = _load_user_permissions(None, MagicMock())
        assert result == set()

    # --- Суперюзеры ---

    def test_admin_role_is_superuser(self):
        emp = _make_employee('Менеджер', role='admin')
        result = _load_user_permissions(emp, MagicMock())
        assert result is None  # None = все права

    def test_director_role_is_superuser(self):
        emp = _make_employee('Менеджер', role='director')
        result = _load_user_permissions(emp, MagicMock())
        assert result is None

    def test_rukovoditel_position_is_superuser(self):
        """Руководитель студии — суперюзер по должности, даже без роли admin."""
        emp = _make_employee('Руководитель студии', role='user')
        result = _load_user_permissions(emp, MagicMock())
        assert result is None

    def test_regular_user_is_not_superuser(self):
        emp = _make_employee('Дизайнер')
        api = _make_api_client(permissions={'access.crm', 'crm_cards.files_upload'})
        result = _load_user_permissions(emp, api)
        assert result is not None
        assert isinstance(result, set)

    # --- API ---

    def test_api_returns_permissions(self):
        emp = _make_employee('Менеджер', emp_id=10)
        perms = {'access.crm', 'crm_cards.move', 'crm_cards.update'}
        api = _make_api_client(permissions=perms)
        result = _load_user_permissions(emp, api)
        assert result == perms
        api.get_employee_permissions.assert_called_once_with(10)

    def test_api_error_falls_back_to_defaults(self):
        emp = _make_employee('Дизайнер', emp_id=20)
        api = _make_api_client(raise_error=True)
        result = _load_user_permissions(emp, api)
        # Должен вернуть дефолтные для Дизайнера
        assert 'access.crm' in result
        assert 'crm_cards.files_upload' in result

    def test_api_returns_empty_falls_back_to_defaults(self):
        emp = _make_employee('ДАН', emp_id=30)
        api = _make_api_client(permissions=set())  # пустой набор
        result = _load_user_permissions(emp, api)
        # Должен fallback на дефолтные ДАН
        assert 'access.supervision' in result

    def test_no_api_client_falls_back_to_defaults(self):
        emp = _make_employee('Менеджер', emp_id=40)
        result = _load_user_permissions(emp, None)
        # Дефолтные менеджера
        assert 'access.crm' in result
        assert 'access.supervision' in result

    # --- Кэширование ---

    def test_cache_hit_skips_api_call(self):
        emp = _make_employee('Менеджер', emp_id=50)
        api = _make_api_client(permissions={'access.crm'})

        # Первый вызов — загрузка через API
        result1 = _load_user_permissions(emp, api)
        # Второй вызов — из кэша
        result2 = _load_user_permissions(emp, api)

        assert result1 == result2
        # API вызван ровно 1 раз (второй из кэша)
        assert api.get_employee_permissions.call_count == 1

    def test_cache_stores_none_for_superuser(self):
        emp = _make_employee('Менеджер', role='admin', emp_id=60)
        _load_user_permissions(emp, MagicMock())
        assert _user_permissions_cache[60] is None

    def test_different_employees_cached_separately(self):
        emp1 = _make_employee('Дизайнер', emp_id=70)
        emp2 = _make_employee('Менеджер', emp_id=71)

        api1 = _make_api_client(permissions={'access.crm'})
        api2 = _make_api_client(permissions={'access.crm', 'access.supervision'})

        r1 = _load_user_permissions(emp1, api1)
        r2 = _load_user_permissions(emp2, api2)

        assert r1 != r2
        assert 'access.supervision' not in r1
        assert 'access.supervision' in r2

    # --- Дефолтные + secondary_position ---

    def test_fallback_merges_secondary_position(self):
        """Дизайнер + ДАН (secondary) → объединение дефолтов обеих должностей."""
        emp = _make_employee('Дизайнер', secondary_position='ДАН', emp_id=80)
        result = _load_user_permissions(emp, None)
        # От Дизайнера
        assert 'access.crm' in result
        assert 'crm_cards.files_upload' in result
        # От ДАН
        assert 'access.supervision' in result
        assert 'supervision.complete_stage' in result


# ============================================================================
# _get_default_permissions_for_position
# ============================================================================

class TestGetDefaultPermissions:
    """Тесты _get_default_permissions_for_position."""

    def test_known_position(self):
        emp = _make_employee('Дизайнер')
        perms = _get_default_permissions_for_position(emp)
        assert 'access.crm' in perms
        assert 'crm_cards.files_upload' in perms

    def test_unknown_position_returns_empty(self):
        emp = _make_employee('Несуществующая должность')
        perms = _get_default_permissions_for_position(emp)
        assert perms == set()

    def test_none_employee_returns_empty(self):
        perms = _get_default_permissions_for_position(None)
        assert perms == set()

    def test_secondary_position_merged(self):
        emp = _make_employee('Дизайнер', secondary_position='Менеджер')
        perms = _get_default_permissions_for_position(emp)
        # Дизайнер
        assert 'crm_cards.files_upload' in perms
        # Менеджер
        assert 'access.supervision' in perms
        assert 'crm_cards.reset_designer' in perms

    def test_all_nine_roles_have_defaults(self):
        """Все 9 ролей должны иметь непустые дефолты."""
        from ui.permissions_matrix_widget import DEFAULT_ROLE_PERMISSIONS, ROLES
        for role in ROLES:
            assert role in DEFAULT_ROLE_PERMISSIONS, f"Роль '{role}' отсутствует в DEFAULT_ROLE_PERMISSIONS"
            assert len(DEFAULT_ROLE_PERMISSIONS[role]) > 0, f"Роль '{role}' имеет пустые дефолтные права"

    def test_rukovoditel_has_all_access(self):
        """Руководитель студии должен иметь все access.* права."""
        from ui.permissions_matrix_widget import DEFAULT_ROLE_PERMISSIONS
        perms = DEFAULT_ROLE_PERMISSIONS['Руководитель студии']
        for access_perm in ACCESS_TAB_MAP:
            assert access_perm in perms, f"Руководитель не имеет {access_perm}"
        # + admin
        assert 'access.admin' in perms


# ============================================================================
# _has_perm — проверка конкретного права
# ============================================================================

class TestHasPerm:
    """Тесты _has_perm."""

    def test_superuser_has_any_perm(self):
        emp = _make_employee('Менеджер', role='admin', emp_id=100)
        assert _has_perm(emp, MagicMock(), 'nonexistent.perm') is True

    def test_user_has_granted_perm(self):
        emp = _make_employee('Менеджер', emp_id=101)
        api = _make_api_client(permissions={'access.crm', 'crm_cards.move'})
        assert _has_perm(emp, api, 'crm_cards.move') is True

    def test_user_lacks_perm(self):
        emp = _make_employee('Менеджер', emp_id=102)
        api = _make_api_client(permissions={'access.crm'})
        assert _has_perm(emp, api, 'employees.delete') is False

    def test_none_employee_lacks_perm(self):
        assert _has_perm(None, MagicMock(), 'access.crm') is False


# ============================================================================
# has_any_perm — проверка хотя бы одного из набора
# ============================================================================

class TestHasAnyPerm:
    """Тесты has_any_perm."""

    def test_superuser_always_true(self):
        emp = _make_employee('Менеджер', role='admin', emp_id=110)
        assert has_any_perm(emp, MagicMock(), 'a.b', 'c.d') is True

    def test_has_one_of_perms(self):
        emp = _make_employee('Менеджер', emp_id=111)
        api = _make_api_client(permissions={'access.crm', 'access.reports'})
        assert has_any_perm(emp, api, 'access.crm', 'access.admin') is True

    def test_has_none_of_perms(self):
        emp = _make_employee('Менеджер', emp_id=112)
        api = _make_api_client(permissions={'access.crm'})
        assert has_any_perm(emp, api, 'employees.delete', 'access.admin') is False

    def test_none_employee_returns_false(self):
        assert has_any_perm(None, MagicMock(), 'access.crm') is False


# ============================================================================
# invalidate_cache — сброс кэша
# ============================================================================

class TestInvalidateCache:
    """Тесты invalidate_cache."""

    def test_clear_all(self):
        _user_permissions_cache[1] = {'access.crm'}
        _user_permissions_cache[2] = None
        invalidate_cache()
        assert len(_user_permissions_cache) == 0

    def test_clear_single_employee(self):
        _user_permissions_cache[1] = {'access.crm'}
        _user_permissions_cache[2] = {'access.reports'}
        invalidate_cache(employee_id=1)
        assert 1 not in _user_permissions_cache
        assert 2 in _user_permissions_cache

    def test_clear_nonexistent_no_error(self):
        invalidate_cache(employee_id=999)  # не должно упасть

    def test_cache_cleared_reloads_from_api(self):
        """После сброса кэша следующий вызов должен обратиться к API."""
        emp = _make_employee('Менеджер', emp_id=130)
        api = _make_api_client(permissions={'access.crm'})

        _load_user_permissions(emp, api)
        assert api.get_employee_permissions.call_count == 1

        invalidate_cache(employee_id=130)

        _load_user_permissions(emp, api)
        assert api.get_employee_permissions.call_count == 2


# ============================================================================
# get_allowed_tabs — маппинг access.* → вкладки
# ============================================================================

class TestGetAllowedTabs:
    """Тесты get_allowed_tabs."""

    def test_superuser_gets_all_tabs(self):
        emp = _make_employee('Менеджер', role='admin', emp_id=200)
        tabs = get_allowed_tabs(emp, MagicMock())
        assert tabs == set(ACCESS_TAB_MAP.values())

    def test_rukovoditel_gets_all_tabs(self):
        emp = _make_employee('Руководитель студии', emp_id=201)
        tabs = get_allowed_tabs(emp, MagicMock())
        assert tabs == set(ACCESS_TAB_MAP.values())

    def test_single_access_perm(self):
        emp = _make_employee('Менеджер', emp_id=202)
        api = _make_api_client(permissions={'access.crm'})
        tabs = get_allowed_tabs(emp, api)
        assert tabs == {'СРМ'}

    def test_multiple_access_perms(self):
        emp = _make_employee('Менеджер', emp_id=203)
        api = _make_api_client(permissions={
            'access.crm', 'access.supervision', 'access.reports',
            'crm_cards.move',  # не access.* — не влияет на вкладки
        })
        tabs = get_allowed_tabs(emp, api)
        assert tabs == {'СРМ', 'СРМ надзора', 'Отчеты и Статистика'}

    def test_no_access_perms_fallback_to_config(self):
        """Если нет access.* прав — fallback на config.py ROLES."""
        emp = _make_employee('Дизайнер', emp_id=204)
        # API возвращает права без access.*
        api = _make_api_client(permissions={'crm_cards.files_upload'})
        tabs = get_allowed_tabs(emp, api)
        # Fallback на config.py ROLES['Дизайнер']['tabs']
        assert 'СРМ' in tabs

    def test_fallback_secondary_position(self):
        """Fallback на config.py объединяет вкладки primary + secondary."""
        emp = _make_employee('Дизайнер', secondary_position='ДАН', emp_id=205)
        # Без access.* прав и без API
        api = _make_api_client(permissions=set())
        tabs = get_allowed_tabs(emp, api)
        # Дизайнер → СРМ, ДАН → СРМ надзора
        assert 'СРМ' in tabs
        assert 'СРМ надзора' in tabs

    def test_none_employee_returns_empty(self):
        tabs = get_allowed_tabs(None, MagicMock())
        # None → _load returns empty set → no access.* → fallback config.py → empty
        assert isinstance(tabs, set)

    def test_all_access_tab_map_values_unique(self):
        """Имена вкладок должны быть уникальными."""
        values = list(ACCESS_TAB_MAP.values())
        assert len(values) == len(set(values))


# ============================================================================
# Интеграционные: полный цикл permissions
# ============================================================================

class TestPermissionsIntegration:
    """Интеграционные тесты: полный цикл от загрузки до проверки."""

    def test_designer_limited_access(self):
        """Дизайнер: видит CRM, может загружать файлы, не может двигать карточки."""
        emp = _make_employee('Дизайнер', emp_id=300)
        # Без API — fallback на дефолты
        assert _has_perm(emp, None, 'access.crm') is True
        assert _has_perm(emp, None, 'crm_cards.files_upload') is True
        assert _has_perm(emp, None, 'crm_cards.move') is False
        assert _has_perm(emp, None, 'crm_cards.assign_executor') is False
        assert _has_perm(emp, None, 'access.supervision') is False

    def test_manager_moderate_access(self):
        """Менеджер: CRM, надзор, отчёты, сотрудники, сброс стадий."""
        emp = _make_employee('Менеджер', emp_id=301)
        assert _has_perm(emp, None, 'access.crm') is True
        assert _has_perm(emp, None, 'access.supervision') is True
        assert _has_perm(emp, None, 'access.reports') is True
        assert _has_perm(emp, None, 'crm_cards.reset_designer') is True
        # Но не admin
        assert _has_perm(emp, None, 'access.admin') is False
        assert _has_perm(emp, None, 'employees.delete') is False

    def test_dan_supervision_only(self):
        """ДАН: видит надзор, завершает стадии, загружает файлы."""
        emp = _make_employee('ДАН', emp_id=302)
        assert _has_perm(emp, None, 'access.supervision') is True
        assert _has_perm(emp, None, 'supervision.complete_stage') is True
        assert _has_perm(emp, None, 'supervision.files_upload') is True
        # Но не CRM и не перемещение
        assert _has_perm(emp, None, 'access.crm') is False
        assert _has_perm(emp, None, 'supervision.move') is False

    def test_api_overrides_defaults(self):
        """API-права перекрывают дефолтные: если API дал права — используем их."""
        emp = _make_employee('Дизайнер', emp_id=303)
        # API дал расширенные права (дизайнеру дали move через админку)
        api = _make_api_client(permissions={
            'access.crm', 'crm_cards.files_upload', 'crm_cards.move',
        })
        assert _has_perm(emp, api, 'crm_cards.move') is True  # API дал
        assert _has_perm(emp, api, 'employees.delete') is False  # API не давал

    def test_cache_invalidation_picks_up_new_api_perms(self):
        """После invalidate_cache и обновления прав в API — новые права подхватываются."""
        emp = _make_employee('Дизайнер', emp_id=304)

        # Первая загрузка — ограниченные права
        api1 = _make_api_client(permissions={'access.crm'})
        assert _has_perm(emp, api1, 'crm_cards.move') is False

        # Админ добавил право через UI → сброс кэша
        invalidate_cache(employee_id=304)

        # Вторая загрузка — расширенные права
        api2 = _make_api_client(permissions={'access.crm', 'crm_cards.move'})
        assert _has_perm(emp, api2, 'crm_cards.move') is True

    def test_zamerschik_minimal_access(self):
        """Замерщик: минимальные права — только доступ к CRM."""
        emp = _make_employee('Замерщик', emp_id=305)
        assert _has_perm(emp, None, 'access.crm') is True
        assert _has_perm(emp, None, 'crm_cards.files_upload') is False
        assert _has_perm(emp, None, 'crm_cards.move') is False

    def test_senior_manager_full_access(self):
        """Старший менеджер: почти все права, но без admin."""
        emp = _make_employee('Старший менеджер проектов', emp_id=306)
        assert _has_perm(emp, None, 'access.crm') is True
        assert _has_perm(emp, None, 'access.supervision') is True
        assert _has_perm(emp, None, 'access.clients') is True
        assert _has_perm(emp, None, 'crm_cards.move') is True
        assert _has_perm(emp, None, 'crm_cards.assign_executor') is True
        assert _has_perm(emp, None, 'employees.update') is True
        # Но не admin и не delete сотрудников
        assert _has_perm(emp, None, 'access.admin') is False
        assert _has_perm(emp, None, 'employees.delete') is False


# ============================================================================
# Консистентность: server/permissions.py ↔ ui/permissions_matrix_widget.py
# ============================================================================

class TestPermissionsConsistency:
    """Проверка согласованности определений прав между модулями."""

    def test_access_tab_map_covers_all_access_perms(self):
        """Все access.* права из матрицы (кроме access.admin) должны быть в ACCESS_TAB_MAP."""
        from ui.permissions_matrix_widget import PERMISSION_GROUPS
        access_perms = set(PERMISSION_GROUPS.get('Доступ к страницам', []))
        # access.admin не маппится на вкладку
        access_perms.discard('access.admin')
        map_perms = set(ACCESS_TAB_MAP.keys())
        assert access_perms == map_perms, (
            f"Расхождение: в матрице={access_perms - map_perms}, в маппинге={map_perms - access_perms}"
        )

    def test_all_permission_groups_non_empty(self):
        """Все группы прав в матрице непустые."""
        from ui.permissions_matrix_widget import PERMISSION_GROUPS
        for group, perms in PERMISSION_GROUPS.items():
            assert len(perms) > 0, f"Группа '{group}' пустая"

    def test_no_duplicate_permissions_across_groups(self):
        """Одно право не должно быть в нескольких группах."""
        from ui.permissions_matrix_widget import PERMISSION_GROUPS
        all_perms = []
        for perms in PERMISSION_GROUPS.values():
            all_perms.extend(perms)
        duplicates = [p for p in all_perms if all_perms.count(p) > 1]
        assert len(duplicates) == 0, f"Дубликаты прав: {set(duplicates)}"

    def test_default_perms_only_contain_defined_permissions(self):
        """DEFAULT_ROLE_PERMISSIONS не должен содержать прав, не определённых в PERMISSION_GROUPS."""
        from ui.permissions_matrix_widget import PERMISSION_GROUPS, DEFAULT_ROLE_PERMISSIONS
        all_defined = set()
        for perms in PERMISSION_GROUPS.values():
            all_defined.update(perms)
        for role, perms in DEFAULT_ROLE_PERMISSIONS.items():
            undefined = perms - all_defined
            assert len(undefined) == 0, f"Роль '{role}' имеет неопределённые права: {undefined}"

    def test_roles_count_is_nine(self):
        """Должно быть ровно 9 ролей."""
        from ui.permissions_matrix_widget import ROLES
        assert len(ROLES) == 9

    def test_all_descriptions_exist(self):
        """Каждое право из PERMISSION_GROUPS должно иметь описание."""
        from ui.permissions_matrix_widget import PERMISSION_GROUPS, PERMISSION_DESCRIPTIONS
        for group, perms in PERMISSION_GROUPS.items():
            for perm in perms:
                assert perm in PERMISSION_DESCRIPTIONS, (
                    f"Право '{perm}' из группы '{group}' не имеет описания"
                )

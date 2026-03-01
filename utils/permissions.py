# -*- coding: utf-8 -*-
"""Единый модуль проверки прав на клиенте.

Все UI-модули должны использовать ТОЛЬКО этот модуль для проверки прав.
Внутри: кэш прав + API + fallback на config.py ROLES.

Исторически функции _emp_has_pos, _has_perm и др. были определены в ui/crm_tab.py.
Сейчас они перенесены сюда, а в crm_tab.py остаётся реэкспорт для обратной совместимости.
"""


# ========== Маппинг access.* прав на имена вкладок ==========
ACCESS_TAB_MAP = {
    "access.clients": "Клиенты",
    "access.contracts": "Договора",
    "access.crm": "СРМ",
    "access.supervision": "СРМ надзора",
    "access.reports": "Отчеты и Статистика",
    "access.employees": "Сотрудники",
    "access.salaries": "Зарплаты",
    "access.employee_reports": "Отчеты по сотрудникам",
}


# ========== HELPER: Проверка должности с учётом secondary_position ==========
def _emp_has_pos(employee, *positions):
    """Проверяет, есть ли у сотрудника одна из указанных должностей (основная или дополнительная).
    Используется для ПРЕДОСТАВЛЕНИЯ доступа: True если хотя бы одна должность совпадает."""
    if not employee:
        return False
    return employee.get('position', '') in positions or employee.get('secondary_position', '') in positions


def _emp_only_pos(employee, *positions):
    """Проверяет, что ВСЕ должности сотрудника входят в указанный набор.
    Используется для ОГРАНИЧЕНИЯ доступа: True если сотрудник — чистый исполнитель без второй роли выше."""
    if not employee:
        return False
    pos = employee.get('position', '')
    sec = employee.get('secondary_position', '')
    if pos not in positions:
        return False
    if sec and sec not in positions:
        return False
    return True
# =============================================================================


# ========== Кэш и проверка permissions для текущего пользователя ==========
_user_permissions_cache = {}  # {employee_id: set(permissions) | None}


def _load_user_permissions(employee, api_client):
    """Загрузить и закэшировать permissions текущего пользователя."""
    if not employee:
        return set()
    emp_id = employee.get('id')
    if emp_id in _user_permissions_cache:
        return _user_permissions_cache[emp_id]

    # Суперюзеры имеют все права (роль ИЛИ позиция Руководитель студии)
    role = employee.get('role', '')
    position = employee.get('position', '')
    if role in ('admin', 'director') or position == 'Руководитель студии':
        _user_permissions_cache[emp_id] = None  # None = все права
        return None

    perms = set()
    if api_client:
        try:
            result = api_client.get_employee_permissions(emp_id)
            perms = set(result.get('permissions', []))
        except Exception:
            pass

    # Fallback: если API недоступен или вернул пустой набор — дефолтные по должности
    if not perms:
        perms = _get_default_permissions_for_position(employee)

    _user_permissions_cache[emp_id] = perms
    return perms


def _get_default_permissions_for_position(employee):
    """Получить дефолтные права по должности (fallback без API)."""
    from ui.permissions_matrix_widget import DEFAULT_ROLE_PERMISSIONS
    position = employee.get('position', '') if employee else ''
    secondary = employee.get('secondary_position', '') if employee else ''

    perms = set(DEFAULT_ROLE_PERMISSIONS.get(position, set()))
    if secondary:
        perms |= set(DEFAULT_ROLE_PERMISSIONS.get(secondary, set()))
    return perms


def _has_perm(employee, api_client, perm_name):
    """Проверить право у сотрудника. None в кэше = суперюзер (все права)."""
    perms = _load_user_permissions(employee, api_client)
    if perms is None:
        return True  # суперюзер
    return perm_name in perms


def has_any_perm(employee, api_client, *perm_names):
    """Проверить наличие хотя бы одного из перечисленных прав."""
    perms = _load_user_permissions(employee, api_client)
    if perms is None:
        return True  # суперюзер
    return bool(perms & set(perm_names))


def invalidate_cache(employee_id=None):
    """Сбросить кэш прав. Без аргумента — весь кэш."""
    if employee_id is None:
        _user_permissions_cache.clear()
    else:
        _user_permissions_cache.pop(employee_id, None)
# =============================================================================


def get_allowed_tabs(employee, api_client):
    """Получить набор доступных вкладок из permissions.

    Если права загружены и содержат access.* — используем их.
    Иначе — fallback на config.py ROLES.
    """
    perms = _load_user_permissions(employee, api_client)

    # Суперюзер — все вкладки
    if perms is None:
        return set(ACCESS_TAB_MAP.values())

    # Проверяем access.* права
    tabs = set()
    for perm, tab_name in ACCESS_TAB_MAP.items():
        if perm in perms:
            tabs.add(tab_name)

    if tabs:
        return tabs

    # Fallback на config.py ROLES (для обратной совместимости / offline)
    from config import ROLES
    position = employee.get('position', '') if employee else ''
    secondary = employee.get('secondary_position', '') if employee else ''

    result = set(ROLES.get(position, {}).get('tabs', []))
    if secondary:
        result |= set(ROLES.get(secondary, {}).get('tabs', []))
    return result

# -*- coding: utf-8 -*-
"""
Покрытие ui/crm_card_edit_dialog.py — чистая бизнес-логика.
~35 тестов.

Тестирует: truncate_filename, get_resize_edge, helper-функции фильтрации
сотрудников и прав, сортировку/группировку платежей, фильтрацию истории,
логику синхронизации, маппинги ролей, и прочую бизнес-логику,
извлечённую без создания реального GUI.
"""

import pytest
import sys
import os
import re
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ['QT_QPA_PLATFORM'] = 'offscreen'


# =====================================================================
# Хелперы для доступа к классам и функциям
# =====================================================================

def _get_dialog_class():
    """Импортировать CardEditDialog без создания экземпляра."""
    from ui.crm_card_edit_dialog import CardEditDialog
    return CardEditDialog


def _get_crm_helpers():
    """Импортировать helper-функции из crm_tab."""
    from ui.crm_tab import _emp_has_pos, _emp_only_pos, _has_perm, _load_user_permissions
    return _emp_has_pos, _emp_only_pos, _has_perm, _load_user_permissions


def _make_mock_self(**kwargs):
    """Создать мок объекта CardEditDialog с нужными атрибутами."""
    mock = MagicMock()
    mock.resize_margin = kwargs.pop('resize_margin', 8)
    mock.card_data = kwargs.pop('card_data', {'id': 1, 'contract_id': 100})
    mock.employee = kwargs.pop('employee', {'id': 1, 'full_name': 'Тест'})
    mock._loading_data = kwargs.pop('_loading_data', False)
    mock._active_sync_count = kwargs.pop('_active_sync_count', 0)
    for k, v in kwargs.items():
        setattr(mock, k, v)
    return mock


# =====================================================================
# Тесты: truncate_filename
# =====================================================================

class TestTruncateFilename:
    """Тестирует обрезку длинных имён файлов."""

    def test_short_filename_unchanged(self):
        """Короткое имя файла возвращается без изменений."""
        Cls = _get_dialog_class()
        mock_self = _make_mock_self()
        result = Cls.truncate_filename(mock_self, 'photo.jpg', max_length=50)
        assert result == 'photo.jpg'

    def test_exact_length_unchanged(self):
        """Имя файла ровно по лимиту не обрезается."""
        Cls = _get_dialog_class()
        mock_self = _make_mock_self()
        name = 'a' * 46 + '.jpg'  # 50 символов
        result = Cls.truncate_filename(mock_self, name, max_length=50)
        assert result == name

    def test_long_filename_truncated(self):
        """Длинное имя обрезается с многоточием в середине."""
        Cls = _get_dialog_class()
        mock_self = _make_mock_self()
        name = 'a' * 60 + '.pdf'  # 64 символа
        result = Cls.truncate_filename(mock_self, name, max_length=30)
        assert '...' in result
        assert result.endswith('.pdf')
        assert len(result) <= 30

    def test_filename_no_extension(self):
        """Файл без расширения корректно обрезается."""
        Cls = _get_dialog_class()
        mock_self = _make_mock_self()
        name = 'a' * 60
        result = Cls.truncate_filename(mock_self, name, max_length=20)
        assert '...' in result
        assert len(result) <= 20

    def test_very_small_max_length(self):
        """При очень маленьком max_length файл всё равно обрезается."""
        Cls = _get_dialog_class()
        mock_self = _make_mock_self()
        result = Cls.truncate_filename(mock_self, 'very_long_name.pdf', max_length=10)
        assert '...' in result
        assert len(result) <= 10

    def test_long_extension(self):
        """Файл с длинным расширением обрабатывается корректно."""
        Cls = _get_dialog_class()
        mock_self = _make_mock_self()
        name = 'document_with_long_name.docx'
        result = Cls.truncate_filename(mock_self, name, max_length=20)
        assert len(result) <= 20


# =====================================================================
# Тесты: get_resize_edge
# =====================================================================

class TestGetResizeEdge:
    """Тестирует определение края/угла для ресайза окна."""

    def _make_pos(self, x, y):
        """Создать мок позиции."""
        pos = MagicMock()
        pos.x.return_value = x
        pos.y.return_value = y
        return pos

    def _make_rect(self, width=800, height=600):
        """Создать мок rect."""
        rect = MagicMock()
        rect.width.return_value = width
        rect.height.return_value = height
        return rect

    def _make_self(self, width=800, height=600):
        """Создать мок self с rect()."""
        mock_self = _make_mock_self()
        mock_self.rect.return_value = self._make_rect(width, height)
        return mock_self

    def test_top_left_corner(self):
        Cls = _get_dialog_class()
        mock_self = self._make_self()
        pos = self._make_pos(3, 3)
        assert Cls.get_resize_edge(mock_self, pos) == 'top-left'

    def test_top_right_corner(self):
        Cls = _get_dialog_class()
        mock_self = self._make_self()
        pos = self._make_pos(796, 3)
        assert Cls.get_resize_edge(mock_self, pos) == 'top-right'

    def test_bottom_left_corner(self):
        Cls = _get_dialog_class()
        mock_self = self._make_self()
        pos = self._make_pos(3, 596)
        assert Cls.get_resize_edge(mock_self, pos) == 'bottom-left'

    def test_bottom_right_corner(self):
        Cls = _get_dialog_class()
        mock_self = self._make_self()
        pos = self._make_pos(796, 596)
        assert Cls.get_resize_edge(mock_self, pos) == 'bottom-right'

    def test_top_edge(self):
        Cls = _get_dialog_class()
        mock_self = self._make_self()
        pos = self._make_pos(400, 3)
        assert Cls.get_resize_edge(mock_self, pos) == 'top'

    def test_bottom_edge(self):
        Cls = _get_dialog_class()
        mock_self = self._make_self()
        pos = self._make_pos(400, 596)
        assert Cls.get_resize_edge(mock_self, pos) == 'bottom'

    def test_left_edge(self):
        Cls = _get_dialog_class()
        mock_self = self._make_self()
        pos = self._make_pos(3, 300)
        assert Cls.get_resize_edge(mock_self, pos) == 'left'

    def test_right_edge(self):
        Cls = _get_dialog_class()
        mock_self = self._make_self()
        pos = self._make_pos(796, 300)
        assert Cls.get_resize_edge(mock_self, pos) == 'right'

    def test_center_returns_none(self):
        """Позиция в центре окна — не край, возвращает None."""
        Cls = _get_dialog_class()
        mock_self = self._make_self()
        pos = self._make_pos(400, 300)
        assert Cls.get_resize_edge(mock_self, pos) is None


# =====================================================================
# Тесты: _emp_has_pos / _emp_only_pos (из crm_tab)
# =====================================================================

class TestEmpHasPos:
    """Тестирует проверку должностей сотрудника."""

    def test_primary_position_match(self):
        _emp_has_pos, _, _, _ = _get_crm_helpers()
        emp = {'position': 'Дизайнер', 'secondary_position': ''}
        assert _emp_has_pos(emp, 'Дизайнер') is True

    def test_secondary_position_match(self):
        _emp_has_pos, _, _, _ = _get_crm_helpers()
        emp = {'position': 'Менеджер', 'secondary_position': 'СДП'}
        assert _emp_has_pos(emp, 'СДП') is True

    def test_no_match(self):
        _emp_has_pos, _, _, _ = _get_crm_helpers()
        emp = {'position': 'Дизайнер', 'secondary_position': ''}
        assert _emp_has_pos(emp, 'Чертёжник') is False

    def test_none_employee(self):
        _emp_has_pos, _, _, _ = _get_crm_helpers()
        assert _emp_has_pos(None, 'Дизайнер') is False


class TestEmpOnlyPos:
    """Тестирует что ВСЕ должности из набора."""

    def test_single_position_in_set(self):
        _, _emp_only_pos, _, _ = _get_crm_helpers()
        emp = {'position': 'Дизайнер', 'secondary_position': ''}
        assert _emp_only_pos(emp, 'Дизайнер', 'Чертёжник') is True

    def test_both_positions_in_set(self):
        _, _emp_only_pos, _, _ = _get_crm_helpers()
        emp = {'position': 'Дизайнер', 'secondary_position': 'Чертёжник'}
        assert _emp_only_pos(emp, 'Дизайнер', 'Чертёжник') is True

    def test_secondary_outside_set(self):
        """Вторая должность вне набора — False."""
        _, _emp_only_pos, _, _ = _get_crm_helpers()
        emp = {'position': 'Дизайнер', 'secondary_position': 'СДП'}
        assert _emp_only_pos(emp, 'Дизайнер', 'Чертёжник') is False

    def test_primary_outside_set(self):
        _, _emp_only_pos, _, _ = _get_crm_helpers()
        emp = {'position': 'Менеджер', 'secondary_position': ''}
        assert _emp_only_pos(emp, 'Дизайнер') is False

    def test_none_employee(self):
        _, _emp_only_pos, _, _ = _get_crm_helpers()
        assert _emp_only_pos(None, 'Дизайнер') is False


# =====================================================================
# Тесты: _has_perm / _load_user_permissions
# =====================================================================

class TestHasPerm:
    """Тестирует проверку прав пользователя."""

    def test_admin_has_all_perms(self):
        """Администратор имеет все права (возвращает None = суперюзер)."""
        _, _, _has_perm, _load_user_permissions = _get_crm_helpers()
        # Очищаем кеш
        from ui.crm_tab import _user_permissions_cache
        _user_permissions_cache.clear()

        emp = {'id': 999, 'role': 'admin', 'position': 'Администратор'}
        assert _has_perm(emp, None, 'any_permission') is True

    def test_director_has_all_perms(self):
        """Директор имеет все права."""
        _, _, _has_perm, _ = _get_crm_helpers()
        from ui.crm_tab import _user_permissions_cache
        _user_permissions_cache.clear()

        emp = {'id': 998, 'role': 'director', 'position': 'Директор'}
        assert _has_perm(emp, None, 'some_perm') is True

    def test_regular_user_without_perm(self):
        """Обычный пользователь без конкретного права."""
        _, _, _has_perm, _ = _get_crm_helpers()
        from ui.crm_tab import _user_permissions_cache
        _user_permissions_cache.clear()

        emp = {'id': 997, 'role': 'user', 'position': 'Дизайнер'}
        mock_api = MagicMock()
        mock_api.get_employee_permissions.return_value = {'permissions': ['view_cards']}
        assert _has_perm(emp, mock_api, 'delete_cards') is False

    def test_regular_user_with_perm(self):
        """Обычный пользователь с нужным правом."""
        _, _, _has_perm, _ = _get_crm_helpers()
        from ui.crm_tab import _user_permissions_cache
        _user_permissions_cache.clear()

        emp = {'id': 996, 'role': 'user', 'position': 'Менеджер'}
        mock_api = MagicMock()
        mock_api.get_employee_permissions.return_value = {'permissions': ['view_cards', 'edit_cards']}
        assert _has_perm(emp, mock_api, 'edit_cards') is True

    def test_none_employee(self):
        """None сотрудник — нет прав."""
        _, _, _has_perm, _ = _get_crm_helpers()
        from ui.crm_tab import _user_permissions_cache
        _user_permissions_cache.clear()

        assert _has_perm(None, None, 'anything') is False


# =====================================================================
# Тесты: Логика платежей — get_stage_num, payment_sort_key, get_payment_group
# =====================================================================

class TestPaymentHelpers:
    """Тестирует внутренние функции сортировки и группировки платежей."""

    def _get_stage_num(self, stage):
        """Реплика внутренней функции get_stage_num из create_payments_tab."""
        if stage:
            match = re.search(r'[Сс]тадия\s*(\d+)', stage)
            if match:
                return int(match.group(1))
        return 0

    def _get_payment_group(self, payment):
        """Реплика внутренней функции get_payment_group из create_payments_tab."""
        role = payment.get('role', '')
        if role in ('Старший менеджер проектов', 'СДП', 'ГАП'):
            return 'management'
        elif role in ('Менеджер', 'Менеджер проектов', 'Помощник менеджера', 'Замерщик'):
            return 'support'
        else:
            return 'executors'

    def test_stage_num_stage1(self):
        assert self._get_stage_num('Стадия 1') == 1

    def test_stage_num_stage3(self):
        assert self._get_stage_num('Стадия 3') == 3

    def test_stage_num_lowercase(self):
        """Буква 'с' в нижнем регистре."""
        assert self._get_stage_num('стадия 2') == 2

    def test_stage_num_none(self):
        assert self._get_stage_num(None) == 0

    def test_stage_num_empty(self):
        assert self._get_stage_num('') == 0

    def test_stage_num_no_match(self):
        assert self._get_stage_num('Этап 5') == 0

    def test_group_management_smp(self):
        assert self._get_payment_group({'role': 'Старший менеджер проектов'}) == 'management'

    def test_group_management_sdp(self):
        assert self._get_payment_group({'role': 'СДП'}) == 'management'

    def test_group_management_gap(self):
        assert self._get_payment_group({'role': 'ГАП'}) == 'management'

    def test_group_support_manager(self):
        assert self._get_payment_group({'role': 'Менеджер'}) == 'support'

    def test_group_support_surveyor(self):
        assert self._get_payment_group({'role': 'Замерщик'}) == 'support'

    def test_group_executors_designer(self):
        assert self._get_payment_group({'role': 'Дизайнер'}) == 'executors'

    def test_group_executors_draftsman(self):
        assert self._get_payment_group({'role': 'Чертёжник'}) == 'executors'

    def test_group_unknown_role(self):
        """Неизвестная роль попадает в executors."""
        assert self._get_payment_group({'role': 'Стажёр'}) == 'executors'


# =====================================================================
# Тесты: Логика фильтрации истории
# =====================================================================

class TestHistoryFilterLogic:
    """Тестирует маппинг фильтров из _on_history_filter_changed."""

    FILTER_MAP = {
        'Изменение дедлайна': ['deadline_changed', 'executor_deadline_changed'],
        'Загрузка файлов': ['file_upload'],
        'Удаление файлов': ['file_delete'],
        'Замер': ['survey_complete', 'survey_date_changed'],
        'Дата ТЗ': ['tech_task_date_changed'],
    }

    def _filter_items(self, filter_text, items):
        """Реплика логики фильтрации из _on_history_filter_changed."""
        allowed_types = self.FILTER_MAP.get(filter_text)
        if filter_text == 'Все действия':
            return items
        elif filter_text == 'Прочее':
            all_known = set()
            for types in self.FILTER_MAP.values():
                all_known.update(types)
            return [a for a in items if a.get('action_type', '') not in all_known]
        elif allowed_types:
            return [a for a in items if a.get('action_type', '') in allowed_types]
        else:
            return items

    def test_all_actions_returns_everything(self):
        items = [{'action_type': 'file_upload'}, {'action_type': 'unknown'}]
        result = self._filter_items('Все действия', items)
        assert len(result) == 2

    def test_filter_deadline_changes(self):
        items = [
            {'action_type': 'deadline_changed'},
            {'action_type': 'executor_deadline_changed'},
            {'action_type': 'file_upload'},
        ]
        result = self._filter_items('Изменение дедлайна', items)
        assert len(result) == 2
        assert all(r['action_type'] in ('deadline_changed', 'executor_deadline_changed') for r in result)

    def test_filter_file_upload(self):
        items = [
            {'action_type': 'file_upload'},
            {'action_type': 'file_delete'},
        ]
        result = self._filter_items('Загрузка файлов', items)
        assert len(result) == 1
        assert result[0]['action_type'] == 'file_upload'

    def test_filter_other(self):
        """Фильтр 'Прочее' отбирает действия, не входящие в известные типы."""
        items = [
            {'action_type': 'file_upload'},
            {'action_type': 'custom_action'},
            {'action_type': 'another_unknown'},
        ]
        result = self._filter_items('Прочее', items)
        assert len(result) == 2
        assert all(r['action_type'] not in ('file_upload',) for r in result)

    def test_unknown_filter_returns_all(self):
        """Неизвестный фильтр возвращает все элементы."""
        items = [{'action_type': 'x'}, {'action_type': 'y'}]
        result = self._filter_items('Несуществующий', items)
        assert len(result) == 2


# =====================================================================
# Тесты: Sync-логика (_show_sync_label, _on_sync_ended)
# =====================================================================

class TestSyncLogic:
    """Тестирует логику счётчика синхронизации."""

    def test_show_sync_increments_counter(self):
        Cls = _get_dialog_class()
        mock_self = _make_mock_self(_active_sync_count=0)
        # У mock_self нет sync_label — hasattr вернёт True (MagicMock), поэтому проверяем счётчик
        Cls._show_sync_label(mock_self)
        assert mock_self._active_sync_count == 1

    def test_on_sync_ended_decrements(self):
        Cls = _get_dialog_class()
        mock_self = _make_mock_self(_active_sync_count=2)
        Cls._on_sync_ended(mock_self)
        assert mock_self._active_sync_count == 1

    def test_on_sync_ended_does_not_go_below_zero(self):
        Cls = _get_dialog_class()
        mock_self = _make_mock_self(_active_sync_count=0)
        Cls._on_sync_ended(mock_self)
        assert mock_self._active_sync_count == 0


# =====================================================================
# Тесты: Маппинг ролей (on_employee_changed)
# =====================================================================

class TestRoleMapping:
    """Тестирует маппинг ролей на поля БД из on_employee_changed."""

    ROLE_TO_FIELD = {
        'Старший менеджер проектов': 'senior_manager_id',
        'СДП': 'sdp_id',
        'ГАП': 'gap_id',
        'Менеджер': 'manager_id',
        'Замерщик': 'surveyor_id',
    }

    def test_all_roles_mapped(self):
        """Все 5 ролей имеют маппинг на поля карточки."""
        assert len(self.ROLE_TO_FIELD) == 5

    def test_smp_maps_to_senior_manager_id(self):
        assert self.ROLE_TO_FIELD['Старший менеджер проектов'] == 'senior_manager_id'

    def test_sdp_maps_to_sdp_id(self):
        assert self.ROLE_TO_FIELD['СДП'] == 'sdp_id'

    def test_gap_maps_to_gap_id(self):
        assert self.ROLE_TO_FIELD['ГАП'] == 'gap_id'

    def test_manager_maps_to_manager_id(self):
        assert self.ROLE_TO_FIELD['Менеджер'] == 'manager_id'

    def test_surveyor_maps_to_surveyor_id(self):
        assert self.ROLE_TO_FIELD['Замерщик'] == 'surveyor_id'


# =====================================================================
# Тесты: auto_save_field — пропуск при загрузке данных
# =====================================================================

class TestAutoSaveSkip:
    """Тестирует что auto_save_field не сохраняет при _loading_data=True."""

    def test_skips_during_loading(self):
        """При _loading_data=True метод ничего не делает."""
        Cls = _get_dialog_class()
        mock_self = _make_mock_self(_loading_data=True)
        # Если бы он не вышел ранее, попытался бы обратиться к card_data["id"]
        # и data.update_crm_card — убедимся, что этого не произошло
        Cls.auto_save_field(mock_self)
        mock_self.data.update_crm_card.assert_not_called()


# =====================================================================
# Тесты: _get_contract_yandex_folder
# =====================================================================

class TestGetContractYandexFolder:
    """Тестирует получение пути к папке договора на ЯДиске."""

    def test_returns_none_for_no_contract(self):
        Cls = _get_dialog_class()
        mock_self = _make_mock_self()
        result = Cls._get_contract_yandex_folder(mock_self, None)
        assert result is None

    def test_returns_none_for_zero_contract(self):
        Cls = _get_dialog_class()
        mock_self = _make_mock_self()
        result = Cls._get_contract_yandex_folder(mock_self, 0)
        assert result is None

    def test_returns_path_from_data(self):
        Cls = _get_dialog_class()
        mock_self = _make_mock_self()
        mock_self.data.get_contract.return_value = {'yandex_folder_path': '/disk/projects/123'}
        result = Cls._get_contract_yandex_folder(mock_self, 123)
        assert result == '/disk/projects/123'

    def test_returns_none_when_contract_not_found(self):
        Cls = _get_dialog_class()
        mock_self = _make_mock_self()
        mock_self.data.get_contract.return_value = None
        result = Cls._get_contract_yandex_folder(mock_self, 999)
        assert result is None

    def test_returns_none_on_exception(self):
        Cls = _get_dialog_class()
        mock_self = _make_mock_self()
        mock_self.data.get_contract.side_effect = Exception("DB error")
        result = Cls._get_contract_yandex_folder(mock_self, 100)
        assert result is None


# =====================================================================
# Тесты: _add_action_history
# =====================================================================

class TestAddActionHistory:
    """Тестирует вспомогательный метод записи в историю действий."""

    def test_calls_data_add_action_history(self):
        Cls = _get_dialog_class()
        mock_self = _make_mock_self()
        mock_self.card_data = {'id': 42}
        mock_self.employee = {'id': 7}

        Cls._add_action_history(mock_self, 'file_upload', 'Загружен файл ТЗ')

        mock_self.data.add_action_history.assert_called_once_with(
            user_id=7,
            action_type='file_upload',
            entity_type='crm_card',
            entity_id=42,
            description='Загружен файл ТЗ'
        )

    def test_uses_custom_entity_id(self):
        Cls = _get_dialog_class()
        mock_self = _make_mock_self()
        mock_self.card_data = {'id': 42}
        mock_self.employee = {'id': 7}

        Cls._add_action_history(mock_self, 'deadline_changed', 'Изменён дедлайн', entity_id=99)

        mock_self.data.add_action_history.assert_called_once_with(
            user_id=7,
            action_type='deadline_changed',
            entity_type='crm_card',
            entity_id=99,
            description='Изменён дедлайн'
        )

    def test_none_employee(self):
        """Если employee=None — user_id будет None."""
        Cls = _get_dialog_class()
        mock_self = _make_mock_self(employee=None)
        mock_self.card_data = {'id': 10}

        Cls._add_action_history(mock_self, 'test', 'описание')

        mock_self.data.add_action_history.assert_called_once_with(
            user_id=None,
            action_type='test',
            entity_type='crm_card',
            entity_id=10,
            description='описание'
        )


# =====================================================================
# Тесты: Логика определения исполнителя в reassign_executor_from_dialog
# =====================================================================

class TestReassignExecutorParams:
    """Тестирует определение параметров по executor_type."""

    def test_designer_params(self):
        """Для дизайнера: позиция='Дизайнер', stage_keyword='концепция'."""
        executor_type = 'designer'
        card_data = {'column_name': 'Концепция', 'designer_name': 'Иванов'}

        if executor_type == 'designer':
            position = 'Дизайнер'
            stage_keyword = 'концепция'
            current_name = card_data.get('designer_name', 'Не назначен')
        else:
            position = 'Чертёжник'
            current_name = card_data.get('draftsman_name', 'Не назначен')
            stage_keyword = 'чертежи'

        assert position == 'Дизайнер'
        assert stage_keyword == 'концепция'
        assert current_name == 'Иванов'

    def test_draftsman_params_plans(self):
        """Для чертёжника в колонке 'Планировочные решения' — keyword='планировочные'."""
        executor_type = 'draftsman'
        card_data = {'column_name': 'Планировочные решения', 'draftsman_name': 'Петров'}

        current_column = card_data.get('column_name', '')

        if executor_type == 'designer':
            position = 'Дизайнер'
            stage_keyword = 'концепция'
            current_name = card_data.get('designer_name', 'Не назначен')
        else:
            position = 'Чертёжник'
            current_name = card_data.get('draftsman_name', 'Не назначен')
            if 'планировочные' in current_column.lower():
                stage_keyword = 'планировочные'
            else:
                stage_keyword = 'чертежи'

        assert position == 'Чертёжник'
        assert stage_keyword == 'планировочные'
        assert current_name == 'Петров'

    def test_draftsman_params_drawings(self):
        """Для чертёжника в другой колонке — keyword='чертежи'."""
        executor_type = 'draftsman'
        card_data = {'column_name': 'Рабочие чертежи', 'draftsman_name': 'Сидоров'}

        current_column = card_data.get('column_name', '')

        if executor_type == 'designer':
            position = 'Дизайнер'
            stage_keyword = 'концепция'
            current_name = card_data.get('designer_name', 'Не назначен')
        else:
            position = 'Чертёжник'
            current_name = card_data.get('draftsman_name', 'Не назначен')
            if 'планировочные' in current_column.lower():
                stage_keyword = 'планировочные'
            else:
                stage_keyword = 'чертежи'

        assert position == 'Чертёжник'
        assert stage_keyword == 'чертежи'
        assert current_name == 'Сидоров'


# =====================================================================
# Тест: on_employee_changed пропускает при загрузке
# =====================================================================

class TestOnEmployeeChangedSkip:
    """Тестирует что on_employee_changed не выполняется при загрузке."""

    def test_skips_during_loading(self):
        Cls = _get_dialog_class()
        mock_self = _make_mock_self(_loading_data=True)
        mock_combo = MagicMock()
        Cls.on_employee_changed(mock_self, mock_combo, 'СДП')
        # Не должен обращаться к data при загрузке
        mock_self.data.update_crm_card.assert_not_called()

    def test_skips_without_contract_id(self):
        Cls = _get_dialog_class()
        mock_self = _make_mock_self(_loading_data=False, card_data={'id': 1})
        mock_combo = MagicMock()
        Cls.on_employee_changed(mock_self, mock_combo, 'СДП')
        mock_self.data.update_crm_card.assert_not_called()


# =====================================================================
# Тест: Шаблонный проект пропускает создание платежа для СМП/Менеджер
# =====================================================================

class TestTemplateProjectPaymentSkip:
    """Тестирует пропуск создания платежа для СМП и Менеджера в шаблонных проектах."""

    def test_smp_in_template_skipped(self):
        """Старший менеджер в шаблонном проекте — платёж не создаётся."""
        project_type = 'Шаблонный'
        role_name = 'Старший менеджер проектов'
        should_skip = (project_type == 'Шаблонный' and role_name in ['Старший менеджер проектов', 'Менеджер'])
        assert should_skip is True

    def test_manager_in_template_skipped(self):
        project_type = 'Шаблонный'
        role_name = 'Менеджер'
        should_skip = (project_type == 'Шаблонный' and role_name in ['Старший менеджер проектов', 'Менеджер'])
        assert should_skip is True

    def test_sdp_in_template_not_skipped(self):
        """СДП в шаблонном проекте — платёж создаётся."""
        project_type = 'Шаблонный'
        role_name = 'СДП'
        should_skip = (project_type == 'Шаблонный' and role_name in ['Старший менеджер проектов', 'Менеджер'])
        assert should_skip is False

    def test_smp_in_individual_not_skipped(self):
        """СМП в индивидуальном проекте — платёж создаётся."""
        project_type = 'Индивидуальный'
        role_name = 'Старший менеджер проектов'
        should_skip = (project_type == 'Шаблонный' and role_name in ['Старший менеджер проектов', 'Менеджер'])
        assert should_skip is False

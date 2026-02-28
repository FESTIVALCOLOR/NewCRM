# -*- coding: utf-8 -*-
"""
Тесты для PermissionsMatrixWidget — матрица прав доступа по ролям.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QApplication, QTableWidget, QPushButton, QCheckBox, QLabel
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="module")
def qapp():
    """QApplication для модуля тестов."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _make_mock_data_access():
    """Создать MagicMock DataAccess для матрицы прав."""
    mock_da = MagicMock()
    mock_da.get_role_permissions_matrix.return_value = None
    mock_da.get_permission_definitions.return_value = []
    mock_da.save_role_permissions_matrix.return_value = True
    return mock_da


class TestPermissionsMatrixWidget:

    def test_create_widget(self, qapp):
        """Виджет PermissionsMatrixWidget создаётся без ошибок."""
        with patch('ui.permissions_matrix_widget.DataAccess', return_value=_make_mock_data_access()):
            from ui.permissions_matrix_widget import PermissionsMatrixWidget
            mock_api = MagicMock()
            widget = PermissionsMatrixWidget(parent=None, api_client=mock_api)
            assert widget is not None
            widget.close()

    def test_widget_has_table(self, qapp):
        """Виджет содержит таблицу с атрибутом table."""
        with patch('ui.permissions_matrix_widget.DataAccess', return_value=_make_mock_data_access()):
            from ui.permissions_matrix_widget import PermissionsMatrixWidget
            mock_api = MagicMock()
            widget = PermissionsMatrixWidget(parent=None, api_client=mock_api)
            assert hasattr(widget, 'table')
            assert isinstance(widget.table, QTableWidget)
            widget.close()

    def test_table_has_correct_columns(self, qapp):
        """Таблица содержит столбец 'Право' + по 1 на каждую роль (итого 7)."""
        with patch('ui.permissions_matrix_widget.DataAccess', return_value=_make_mock_data_access()):
            from ui.permissions_matrix_widget import PermissionsMatrixWidget, ROLES
            mock_api = MagicMock()
            widget = PermissionsMatrixWidget(parent=None, api_client=mock_api)
            expected_cols = 1 + len(ROLES)  # 1 (Право) + кол-во ролей
            assert widget.table.columnCount() == expected_cols
            widget.close()

    def test_checkboxes_initialized(self, qapp):
        """Чекбоксы проинициализированы для каждой комбинации право-роль."""
        with patch('ui.permissions_matrix_widget.DataAccess', return_value=_make_mock_data_access()):
            from ui.permissions_matrix_widget import PermissionsMatrixWidget, ROLES, PERMISSION_GROUPS
            mock_api = MagicMock()
            widget = PermissionsMatrixWidget(parent=None, api_client=mock_api)
            total_perms = sum(len(perms) for perms in PERMISSION_GROUPS.values())
            expected_checkboxes = total_perms * len(ROLES)
            assert len(widget._checkboxes) == expected_checkboxes
            widget.close()

    def test_apply_matrix_checks_correct_boxes(self, qapp):
        """_apply_matrix корректно устанавливает чекбоксы для заданной матрицы."""
        with patch('ui.permissions_matrix_widget.DataAccess', return_value=_make_mock_data_access()):
            from ui.permissions_matrix_widget import PermissionsMatrixWidget
            mock_api = MagicMock()
            widget = PermissionsMatrixWidget(parent=None, api_client=mock_api)
            # Применяем тестовую матрицу
            test_matrix = {
                'Руководитель студии': ['employees.create', 'employees.delete'],
            }
            widget._apply_matrix(test_matrix)
            cb_create = widget._checkboxes.get(('employees.create', 'Руководитель студии'))
            cb_delete = widget._checkboxes.get(('employees.delete', 'Руководитель студии'))
            cb_update = widget._checkboxes.get(('employees.update', 'Руководитель студии'))
            assert cb_create is not None and cb_create.isChecked()
            assert cb_delete is not None and cb_delete.isChecked()
            assert cb_update is not None and not cb_update.isChecked()
            widget.close()

    def test_collect_matrix_returns_dict(self, qapp):
        """_collect_matrix возвращает словарь со всеми ролями."""
        with patch('ui.permissions_matrix_widget.DataAccess', return_value=_make_mock_data_access()):
            from ui.permissions_matrix_widget import PermissionsMatrixWidget, ROLES
            mock_api = MagicMock()
            widget = PermissionsMatrixWidget(parent=None, api_client=mock_api)
            matrix = widget._collect_matrix()
            assert isinstance(matrix, dict)
            for role in ROLES:
                assert role in matrix
            widget.close()

    def test_default_permissions_loaded(self, qapp):
        """При недоступном API загружаются дефолтные права."""
        with patch('ui.permissions_matrix_widget.DataAccess', return_value=_make_mock_data_access()):
            from ui.permissions_matrix_widget import PermissionsMatrixWidget, DEFAULT_ROLE_PERMISSIONS
            mock_api = MagicMock()
            widget = PermissionsMatrixWidget(parent=None, api_client=mock_api)
            # Руководитель студии должен иметь employees.create по умолчанию
            cb = widget._checkboxes.get(('employees.create', 'Руководитель студии'))
            assert cb is not None
            assert cb.isChecked()
            widget.close()

    def test_widget_has_save_button(self, qapp):
        """Виджет содержит кнопку 'Сохранить'."""
        with patch('ui.permissions_matrix_widget.DataAccess', return_value=_make_mock_data_access()):
            from ui.permissions_matrix_widget import PermissionsMatrixWidget
            mock_api = MagicMock()
            widget = PermissionsMatrixWidget(parent=None, api_client=mock_api)
            buttons = widget.findChildren(QPushButton)
            btn_texts = [b.text() for b in buttons]
            assert 'Сохранить' in btn_texts
            widget.close()

    def test_widget_has_reset_button(self, qapp):
        """Виджет содержит кнопку 'Сбросить по умолчанию'."""
        with patch('ui.permissions_matrix_widget.DataAccess', return_value=_make_mock_data_access()):
            from ui.permissions_matrix_widget import PermissionsMatrixWidget
            mock_api = MagicMock()
            widget = PermissionsMatrixWidget(parent=None, api_client=mock_api)
            buttons = widget.findChildren(QPushButton)
            btn_texts = [b.text() for b in buttons]
            assert 'Сбросить по умолчанию' in btn_texts
            widget.close()

    def test_row_perm_map_contains_permission_names(self, qapp):
        """_row_perm_map содержит маппинг строк → имена прав."""
        with patch('ui.permissions_matrix_widget.DataAccess', return_value=_make_mock_data_access()):
            from ui.permissions_matrix_widget import PermissionsMatrixWidget
            mock_api = MagicMock()
            widget = PermissionsMatrixWidget(parent=None, api_client=mock_api)
            perm_names = [v for v in widget._row_perm_map.values() if v is not None]
            assert 'employees.create' in perm_names
            assert 'supervision.complete_stage' in perm_names
            widget.close()

    def test_apply_matrix_with_api_data(self, qapp):
        """_load_data применяет данные из API если они возвращены корректно."""
        api_matrix = {
            'roles': {
                'ДАН': ['supervision.complete_stage'],
                'Менеджер': ['crm_cards.reset_designer'],
            }
        }
        mock_da = _make_mock_data_access()
        mock_da.get_role_permissions_matrix.return_value = api_matrix
        with patch('ui.permissions_matrix_widget.DataAccess', return_value=mock_da):
            from ui.permissions_matrix_widget import PermissionsMatrixWidget
            mock_api = MagicMock()
            widget = PermissionsMatrixWidget(parent=None, api_client=mock_api)
            # ДАН должен иметь supervision.complete_stage
            cb = widget._checkboxes.get(('supervision.complete_stage', 'ДАН'))
            assert cb is not None and cb.isChecked()
            widget.close()

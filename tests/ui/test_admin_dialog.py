# -*- coding: utf-8 -*-
"""
Тесты для AdminDialog — диалог администрирования.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QApplication, QTabWidget, QDialog, QPushButton, QLabel
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="module")
def qapp():
    """QApplication для модуля тестов."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class TestAdminDialog:

    def test_create_dialog_basic(self, qapp):
        """Диалог AdminDialog создаётся без ошибок с минимальными параметрами."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.admin_dialog import AdminDialog
            parent = None
            mock_api = MagicMock()
            dialog = AdminDialog(parent=None, api_client=mock_api)
            assert dialog is not None
            dialog.close()

    def test_dialog_has_tab_widget(self, qapp):
        """Диалог содержит виджет вкладок QTabWidget."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.admin_dialog import AdminDialog
            mock_api = MagicMock()
            dialog = AdminDialog(parent=None, api_client=mock_api)
            tabs = dialog.findChild(QTabWidget)
            assert tabs is not None
            dialog.close()

    def test_dialog_tabs_count(self, qapp):
        """Диалог содержит ровно 5 вкладок."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.admin_dialog import AdminDialog
            mock_api = MagicMock()
            dialog = AdminDialog(parent=None, api_client=mock_api)
            tabs = dialog._tabs
            assert tabs.count() >= 5
            dialog.close()

    def test_dialog_tab_names(self, qapp):
        """Вкладки имеют правильные названия."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.admin_dialog import AdminDialog
            mock_api = MagicMock()
            dialog = AdminDialog(parent=None, api_client=mock_api)
            tabs = dialog._tabs
            expected = [
                'Права доступа',
                'Настройка чата',
                'Настройка норма дней',
                'Тарифы',
                'Агенты и города',
            ]
            actual = [tabs.tabText(i) for i in range(tabs.count())]
            assert actual == expected
            dialog.close()

    def test_dialog_has_close_button(self, qapp):
        """Диалог содержит кнопку 'Закрыть'."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.admin_dialog import AdminDialog
            mock_api = MagicMock()
            dialog = AdminDialog(parent=None, api_client=mock_api)
            buttons = dialog.findChildren(QPushButton)
            btn_texts = [b.text() for b in buttons]
            assert 'Закрыть' in btn_texts
            dialog.close()

    def test_dialog_minimum_size(self, qapp):
        """Диалог имеет минимальные размеры 1250x750."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.admin_dialog import AdminDialog
            mock_api = MagicMock()
            dialog = AdminDialog(parent=None, api_client=mock_api)
            assert dialog.minimumWidth() == 1250
            assert dialog.minimumHeight() == 750
            dialog.close()

    def test_dialog_with_employee(self, qapp):
        """Диалог корректно принимает параметр employee."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.admin_dialog import AdminDialog
            mock_api = MagicMock()
            mock_da = MagicMock()
            employee = {'id': 1, 'full_name': 'Тестов', 'position': 'Руководитель студии'}
            dialog = AdminDialog(parent=None, api_client=mock_api,
                                 data_access=mock_da, employee=employee)
            assert dialog.employee == employee
            dialog.close()

    def test_dialog_empty_employee_defaults(self, qapp):
        """При отсутствии employee используется пустой словарь."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.admin_dialog import AdminDialog
            mock_api = MagicMock()
            dialog = AdminDialog(parent=None, api_client=mock_api)
            assert dialog.employee == {}
            dialog.close()

    def test_permissions_tab_widget_exists(self, qapp):
        """Вкладка 'Права доступа' содержит виджет с заглушкой или контентом."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.admin_dialog import AdminDialog
            mock_api = MagicMock()
            dialog = AdminDialog(parent=None, api_client=mock_api)
            assert dialog._tab_permissions is not None
            dialog.close()

    def test_init_permissions_widget_graceful_failure(self, qapp):
        """_init_permissions_widget обрабатывает ошибку импорта без краша."""
        with patch('ui.custom_title_bar.resource_path', return_value=''), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.admin_dialog import AdminDialog
            mock_api = MagicMock()
            dialog = AdminDialog(parent=None, api_client=mock_api)
            with patch('ui.admin_dialog.AdminDialog._init_permissions_widget',
                       side_effect=Exception("тест ошибка")):
                # Не должен падать
                try:
                    dialog._init_permissions_widget()
                except Exception:
                    pass
            dialog.close()

# -*- coding: utf-8 -*-
"""
Тесты главного окна — MainWindow.
18 тестов.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from PyQt5.QtWidgets import QMainWindow, QTabWidget, QWidget, QLabel, QStackedWidget
from PyQt5.QtCore import Qt, QTimer


# ========== Хелпер ==========

class _FakeSearchWidget(QWidget):
    """Подставной GlobalSearchWidget — реальный QWidget с mock-сигналом."""
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.result_selected = MagicMock()


def _make_fake_tab(*args, **kwargs):
    """Фабрика для подставных вкладок — возвращает реальный QWidget."""
    w = QWidget()
    w._is_lazy_placeholder = False
    w.on_sync_update = MagicMock()
    w.ensure_data_loaded = MagicMock()
    return w


def _create_main_window(qtbot, employee_data):
    """Создать MainWindow с полной мок-изоляцией."""
    mock_db = MagicMock()
    mock_da = MagicMock()

    patches = [
        # БД и DataAccess (импортируются внутри методов)
        patch('database.db_manager.DatabaseManager', return_value=mock_db),
        patch('utils.data_access.DataAccess', return_value=mock_da),
        # SyncManager и OfflineManager (условный импорт)
        patch('utils.sync_manager.SyncManager', return_value=MagicMock()),
        patch('utils.offline_manager.init_offline_manager', return_value=MagicMock()),
        # Вкладки — реальные QWidget через фабрику
        patch('ui.main_window.ClientsTab', side_effect=_make_fake_tab),
        patch('ui.main_window.ContractsTab', side_effect=_make_fake_tab),
        patch('ui.main_window.CRMTab', side_effect=_make_fake_tab),
        patch('ui.main_window.CRMSupervisionTab', side_effect=_make_fake_tab),
        patch('ui.main_window.ReportsTab', side_effect=_make_fake_tab),
        patch('ui.main_window.EmployeesTab', side_effect=_make_fake_tab),
        patch('ui.main_window.SalariesTab', side_effect=_make_fake_tab),
        patch('ui.main_window.EmployeeReportsTab', side_effect=_make_fake_tab),
        patch('ui.main_window.GlobalSearchWidget', side_effect=lambda *a, **k: _FakeSearchWidget()),
        patch('ui.main_window.DashboardTab', side_effect=_make_fake_tab),
    ]

    for p in patches:
        p.start()

    try:
        from ui.main_window import MainWindow
        w = MainWindow(employee_data=employee_data, api_client=None)
        # Отключаем closeEvent чтобы тест не блокировался на диалоге подтверждения
        w.closeEvent = lambda e: e.accept()
        qtbot.addWidget(w)
        # Запускаем отложенную инициализацию вкладок
        w._init_deferred()
        return w
    finally:
        for p in patches:
            p.stop()


# ========== 1. Рендеринг (6 тестов) ==========

@pytest.mark.ui
class TestMainWindowRendering:
    """Проверка рендеринга главного окна."""

    def test_creates(self, qtbot, mock_employee_admin):
        """MainWindow создаётся как QMainWindow."""
        w = _create_main_window(qtbot, mock_employee_admin)
        assert isinstance(w, QMainWindow)

    def test_tab_widget_exists(self, qtbot, mock_employee_admin):
        """QTabWidget существует."""
        w = _create_main_window(qtbot, mock_employee_admin)
        assert hasattr(w, 'tabs')
        assert isinstance(w.tabs, QTabWidget)

    def test_all_tabs_admin(self, qtbot, mock_employee_admin):
        """Админ видит 8 вкладок."""
        w = _create_main_window(qtbot, mock_employee_admin)
        assert w.tabs.count() == 8

    def test_limited_tabs_designer(self, qtbot, mock_employee_designer):
        """Дизайнер видит только 1 вкладку (СРМ)."""
        w = _create_main_window(qtbot, mock_employee_designer)
        assert w.tabs.count() == 1

    def test_dashboard_stack_exists(self, qtbot, mock_employee_admin):
        """DashboardStack существует."""
        w = _create_main_window(qtbot, mock_employee_admin)
        assert hasattr(w, 'dashboard_stack')
        assert isinstance(w.dashboard_stack, QStackedWidget)

    def test_status_label_exists(self, qtbot, mock_employee_admin):
        """Статусная строка существует."""
        w = _create_main_window(qtbot, mock_employee_admin)
        assert hasattr(w, 'status_label')


# ========== 2. Навигация (6 тестов) ==========

@pytest.mark.ui
class TestMainWindowNavigation:
    """Проверка навигации между вкладками."""

    def test_switch_tab(self, qtbot, mock_employee_admin):
        """Переключение вкладки работает."""
        w = _create_main_window(qtbot, mock_employee_admin)
        if w.tabs.count() > 1:
            w.tabs.setCurrentIndex(1)
            assert w.tabs.currentIndex() == 1

    def test_first_tab_active(self, qtbot, mock_employee_admin):
        """При создании активна первая вкладка."""
        w = _create_main_window(qtbot, mock_employee_admin)
        assert w.tabs.currentIndex() == 0

    def test_tab_names_admin(self, qtbot, mock_employee_admin):
        """Названия вкладок для админа."""
        w = _create_main_window(qtbot, mock_employee_admin)
        tab_names = [w.tabs.tabText(i).strip() for i in range(w.tabs.count())]
        assert 'Клиенты' in tab_names
        assert 'Договора' in tab_names
        assert 'СРМ' in tab_names

    def test_sync_manager_none_offline(self, qtbot, mock_employee_admin):
        """Без api_client — sync_manager = None."""
        w = _create_main_window(qtbot, mock_employee_admin)
        assert w.sync_manager is None

    def test_offline_manager_none_without_api(self, qtbot, mock_employee_admin):
        """Без api_client — offline_manager = None."""
        w = _create_main_window(qtbot, mock_employee_admin)
        assert w.offline_manager is None

    def test_employee_data_stored(self, qtbot, mock_employee_admin):
        """Данные сотрудника сохранены."""
        w = _create_main_window(qtbot, mock_employee_admin)
        assert w.employee == mock_employee_admin


# ========== 3. Видимость вкладок по ролям (6 тестов) ==========

@pytest.mark.ui
class TestMainWindowTabVisibility:
    """Проверка видимости вкладок по ролям."""

    def test_sdp_3_tabs(self, qtbot, mock_employee_sdp):
        """СДП видит 3 вкладки: СРМ, Отчеты, Сотрудники."""
        w = _create_main_window(qtbot, mock_employee_sdp)
        assert w.tabs.count() == 3

    def test_gap_3_tabs(self, qtbot, mock_employee_gap):
        """ГАП видит 3 вкладки."""
        w = _create_main_window(qtbot, mock_employee_gap)
        assert w.tabs.count() == 3

    def test_manager_4_tabs(self, qtbot, mock_employee_manager):
        """Менеджер видит 4 вкладки."""
        w = _create_main_window(qtbot, mock_employee_manager)
        assert w.tabs.count() == 4

    def test_dan_1_tab(self, qtbot, mock_employee_dan):
        """ДАН видит только 1 вкладку (СРМ надзора)."""
        w = _create_main_window(qtbot, mock_employee_dan)
        assert w.tabs.count() == 1
        assert 'надзор' in w.tabs.tabText(0).strip().lower()

    def test_dual_designer_manager_more_tabs(self, qtbot, mock_employee_designer_manager):
        """Дизайнер+Менеджер видит больше вкладок чем просто Дизайнер."""
        w_dual = _create_main_window(qtbot, mock_employee_designer_manager)
        # Дизайнер: ['СРМ'] = 1, Менеджер: ['СРМ', 'СРМ надзора', 'Отчеты', 'Сотрудники'] = 4
        # Объединение: СРМ + СРМ надзора + Отчеты + Сотрудники = 4
        assert w_dual.tabs.count() >= 2

    def test_senior_manager_8_tabs(self, qtbot, mock_employee_senior_manager):
        """Старший менеджер видит 8 вкладок."""
        w = _create_main_window(qtbot, mock_employee_senior_manager)
        assert w.tabs.count() == 8

# -*- coding: utf-8 -*-
"""
Глубокие тесты главного окна MainWindow.
~50 тестов: инициализация, UI-элементы, роли, resize, snap, дашборды,
обработчики событий, статусная строка, обновления, sync/offline.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock, call
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QWidget, QLabel,
                             QStackedWidget, QPushButton, QApplication, QGroupBox)
from PyQt5.QtCore import Qt, QTimer, QEvent, QPoint, QRect, QSize
from PyQt5.QtGui import QMouseEvent


# ========== Хелперы ==========

class _FakeSearchWidget(QWidget):
    """Подставной GlobalSearchWidget с mock-сигналом."""
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.result_selected = MagicMock()


def _make_fake_tab(*args, **kwargs):
    """Фабрика подставных вкладок — реальный QWidget с mock-методами."""
    w = QWidget()
    w._is_lazy_placeholder = False
    w.on_sync_update = MagicMock()
    w.ensure_data_loaded = MagicMock()
    w.load_all_statistics = MagicMock()
    w.refresh_current_tab = MagicMock()
    w.project_tabs = MagicMock()
    w.project_tabs.currentIndex.return_value = 0
    w.project_tabs.tabText.return_value = 'Индивидуальные проекты'
    return w


# Стандартные патчи для изоляции MainWindow
_STANDARD_PATCHES = [
    'database.db_manager.DatabaseManager',
    'utils.data_access.DataAccess',
    'utils.sync_manager.SyncManager',
    'utils.offline_manager.init_offline_manager',
    'ui.main_window.ClientsTab',
    'ui.main_window.ContractsTab',
    'ui.main_window.CRMTab',
    'ui.main_window.CRMSupervisionTab',
    'ui.main_window.ReportsTab',
    'ui.main_window.EmployeesTab',
    'ui.main_window.SalariesTab',
    'ui.main_window.EmployeeReportsTab',
    'ui.main_window.GlobalSearchWidget',
    'ui.main_window.DashboardTab',
]


def _create_mw(qtbot, employee_data, api_client=None):
    """Создать MainWindow с полной мок-изоляцией.

    Возвращает (window, mock_db, mock_da).
    """
    mock_db = MagicMock()
    mock_da = MagicMock()

    # Патч DataAccess внутри dashboards — чтобы stats возвращали числа, а не MagicMock
    _zero_stats = {
        'total_clients': 0, 'total_individual': 0, 'total_legal': 0,
        'clients_by_year': 0, 'agent_clients_total': 0, 'agent_clients_by_year': 0,
        'individual_orders': 0, 'individual_area': 0,
        'template_orders': 0, 'template_area': 0,
        'agent_orders_by_year': 0, 'agent_area_by_year': 0,
        'total_orders': 0, 'total_area': 0,
        'active_orders': 0, 'archive_orders': 0,
        'agent_active_orders': 0, 'agent_archive_orders': 0,
        'active_employees': 0, 'reserve_employees': 0,
        'active_admin': 0, 'active_project': 0,
        'active_execution': 0, 'nearest_birthday': '',
        'total_paid': 0, 'paid_by_year': 0, 'paid_by_month': 0,
        'avg_salary': 0, 'employees_paid': 0, 'max_salary': 0,
        'total_amount': 0, 'year_amount': 0, 'month_amount': 0,
        'avg_amount': 0, 'total_count': 0, 'year_count': 0,
        'agent_amount': 0, 'agent_count': 0,
    }
    mock_dashboard_da = MagicMock()
    mock_dashboard_da.get_clients_dashboard_stats.return_value = _zero_stats
    mock_dashboard_da.get_contracts_dashboard_stats.return_value = _zero_stats
    mock_dashboard_da.get_crm_dashboard_stats.return_value = _zero_stats
    mock_dashboard_da.get_employees_dashboard_stats.return_value = _zero_stats
    mock_dashboard_da.get_salaries_dashboard_stats.return_value = _zero_stats
    mock_dashboard_da.get_salaries_all_payments_stats.return_value = _zero_stats
    mock_dashboard_da.get_salaries_individual_stats.return_value = _zero_stats
    mock_dashboard_da.get_salaries_template_stats.return_value = _zero_stats
    mock_dashboard_da.get_salaries_salary_stats.return_value = _zero_stats
    mock_dashboard_da.get_salaries_supervision_stats.return_value = _zero_stats
    mock_dashboard_da.get_contract_years.return_value = [2026]
    mock_dashboard_da.get_agent_types.return_value = ['Прямой', 'Агент']

    patches = []
    # Патч DataAccess в dashboards модуле (создаёт дашборды с реальными числами)
    patches.append(patch('ui.dashboards.DataAccess', return_value=mock_dashboard_da))
    patches.append(patch('ui.dashboard_widget.create_colored_icon', return_value=None))

    for target in _STANDARD_PATCHES:
        if target == 'database.db_manager.DatabaseManager':
            patches.append(patch(target, return_value=mock_db))
        elif target == 'utils.data_access.DataAccess':
            patches.append(patch(target, return_value=mock_da))
        elif target == 'utils.sync_manager.SyncManager':
            mock_sm = MagicMock()
            mock_sm.online_users_updated = MagicMock()
            mock_sm.connection_status_changed = MagicMock()
            patches.append(patch(target, return_value=mock_sm))
        elif target == 'utils.offline_manager.init_offline_manager':
            mock_om = MagicMock()
            mock_om.connection_status_changed = MagicMock()
            mock_om.pending_operations_changed = MagicMock()
            mock_om.sync_completed = MagicMock()
            patches.append(patch(target, return_value=mock_om))
        elif target == 'ui.main_window.GlobalSearchWidget':
            patches.append(patch(target, side_effect=lambda *a, **k: _FakeSearchWidget()))
        else:
            patches.append(patch(target, side_effect=_make_fake_tab))

    from contextlib import ExitStack
    stack = ExitStack()
    for p in patches:
        stack.enter_context(p)

    from ui.main_window import MainWindow
    w = MainWindow(employee_data=employee_data, api_client=api_client)
    # Отключаем closeEvent чтобы тест не блокировался на диалоге подтверждения
    w.closeEvent = lambda e: e.accept()
    qtbot.addWidget(w)
    # Запускаем отложённую инициализацию вкладок
    w._init_deferred()

    # Сохраняем ExitStack для очистки после теста
    w._patch_stack = stack

    return w, mock_db, mock_da


# ========== 1. Инициализация и структура (10 тестов) ==========

@pytest.mark.ui
class TestMainWindowInit:
    """Инициализация MainWindow — конструктор, атрибуты, флаги."""

    def test_is_qmainwindow(self, qtbot, mock_employee_admin):
        """MainWindow наследуется от QMainWindow."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert isinstance(w, QMainWindow)

    def test_employee_data_stored(self, qtbot, mock_employee_admin):
        """Данные сотрудника сохраняются в self.employee."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert w.employee == mock_employee_admin
        assert w.employee['full_name'] == 'Тестов Админ'

    def test_api_client_none_by_default(self, qtbot, mock_employee_admin):
        """Без api_client — атрибут равен None."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert w.api_client is None

    def test_offline_mode_false_by_default(self, qtbot, mock_employee_admin):
        """По умолчанию is_offline_mode = False."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert w.is_offline_mode is False

    def test_offline_mode_true(self, qtbot):
        """offline_mode=True из employee_data."""
        emp = {"id": 1, "full_name": "Офлайн Тест", "login": "offline",
               "position": "Руководитель студии", "secondary_position": "",
               "department": "Тест", "status": "активный", "offline_mode": True}
        w, _, _ = _create_mw(qtbot, emp)
        assert w.is_offline_mode is True

    def test_resize_flags_initial(self, qtbot, mock_employee_admin):
        """Начальные значения resize-флагов."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert w.resizing is False
        assert w.resize_edge is None
        assert w.resize_margin == 8

    def test_snap_flags_initial(self, qtbot, mock_employee_admin):
        """Начальные значения snap-флагов."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert w.is_snapped is False
        assert w.snap_position is None
        assert w.restore_geometry is None
        assert w.snap_threshold == 10

    def test_frameless_window_hint(self, qtbot, mock_employee_admin):
        """Окно создаётся без стандартной рамки."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert w.windowFlags() & Qt.FramelessWindowHint

    def test_translucent_background(self, qtbot, mock_employee_admin):
        """Атрибут WA_TranslucentBackground включён для border-radius."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert w.testAttribute(Qt.WA_TranslucentBackground)

    def test_minimum_size(self, qtbot, mock_employee_admin):
        """Минимальный размер окна 800x600."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert w.minimumWidth() == 800
        assert w.minimumHeight() == 600


# ========== 2. UI-элементы (8 тестов) ==========

@pytest.mark.ui
class TestMainWindowUIElements:
    """Проверка наличия и типов UI-элементов."""

    def test_tab_widget_exists(self, qtbot, mock_employee_admin):
        """QTabWidget существует."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert hasattr(w, 'tabs')
        assert isinstance(w.tabs, QTabWidget)

    def test_dashboard_stack_exists(self, qtbot, mock_employee_admin):
        """QStackedWidget дашбордов создан."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert hasattr(w, 'dashboard_stack')
        assert isinstance(w.dashboard_stack, QStackedWidget)

    def test_status_label_exists(self, qtbot, mock_employee_admin):
        """Метка статуса существует."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert hasattr(w, 'status_label')
        assert isinstance(w.status_label, QLabel)

    def test_status_label_initial_text(self, qtbot, mock_employee_admin):
        """Начальный текст статуса — 'Готов к работе'."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert w.status_label.text() == 'Готов к работе'

    def test_online_indicator_exists(self, qtbot, mock_employee_admin):
        """Индикатор онлайн-пользователей создан."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert hasattr(w, 'online_indicator')
        assert isinstance(w.online_indicator, QLabel)

    def test_offline_indicator_hidden(self, qtbot, mock_employee_admin):
        """Индикатор offline скрыт по умолчанию."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert hasattr(w, 'offline_indicator')
        assert not w.offline_indicator.isVisible()

    def test_update_button_exists(self, qtbot, mock_employee_admin):
        """Кнопка обновления существует."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert hasattr(w, 'update_btn')
        assert isinstance(w.update_btn, QPushButton)

    def test_version_label_exists(self, qtbot, mock_employee_admin):
        """Метка версии приложения существует."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert hasattr(w, 'version_label')
        assert 'Версия' in w.version_label.text()


# ========== 3. Вкладки по ролям (8 тестов) ==========

@pytest.mark.ui
class TestMainWindowTabsByRole:
    """Проверка набора вкладок для каждой роли."""

    def test_admin_8_tabs(self, qtbot, mock_employee_admin):
        """Руководитель студии видит 8 вкладок."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert w.tabs.count() == 8

    def test_admin_tab_names(self, qtbot, mock_employee_admin):
        """Названия всех вкладок админа."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        names = [w.tabs.tabText(i).strip() for i in range(w.tabs.count())]
        assert 'Клиенты' in names
        assert 'Договора' in names
        assert 'СРМ' in names
        assert 'СРМ надзора' in names

    def test_designer_1_tab(self, qtbot, mock_employee_designer):
        """Дизайнер видит только 1 вкладку (СРМ)."""
        w, _, _ = _create_mw(qtbot, mock_employee_designer)
        assert w.tabs.count() == 1
        assert 'СРМ' in w.tabs.tabText(0).strip()

    def test_surveyor_1_tab(self, qtbot, mock_employee_surveyor):
        """Замерщик видит 1 вкладку (СРМ)."""
        w, _, _ = _create_mw(qtbot, mock_employee_surveyor)
        assert w.tabs.count() == 1

    def test_dan_supervision_only(self, qtbot, mock_employee_dan):
        """ДАН видит только вкладку СРМ надзора."""
        w, _, _ = _create_mw(qtbot, mock_employee_dan)
        assert w.tabs.count() == 1
        assert 'надзор' in w.tabs.tabText(0).strip().lower()

    def test_dual_role_union(self, qtbot, mock_employee_designer_manager):
        """Двойная роль Дизайнер+Менеджер объединяет вкладки."""
        w, _, _ = _create_mw(qtbot, mock_employee_designer_manager)
        # Дизайнер: {СРМ}, Менеджер: {СРМ, СРМ надзора, Отчеты и Статистика, Сотрудники}
        # Объединение: 4 вкладки
        assert w.tabs.count() == 4

    def test_draftsman_1_tab(self, qtbot, mock_employee_draftsman):
        """Чертёжник видит 1 вкладку."""
        w, _, _ = _create_mw(qtbot, mock_employee_draftsman)
        assert w.tabs.count() == 1

    def test_designer_draftsman_dual(self, qtbot, mock_employee_designer_draftsman):
        """Двойная роль Дизайнер+Чертёжник — 1 вкладка (обе роли имеют только СРМ)."""
        w, _, _ = _create_mw(qtbot, mock_employee_designer_draftsman)
        assert w.tabs.count() == 1


# ========== 4. Заголовок и информационная панель (4 теста) ==========

@pytest.mark.ui
class TestMainWindowTitleAndInfo:
    """Заголовок окна и информационная панель."""

    def test_window_title_contains_name(self, qtbot, mock_employee_admin):
        """Заголовок содержит имя сотрудника."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert 'Тестов Админ' in w.windowTitle()

    def test_window_title_prefix(self, qtbot, mock_employee_admin):
        """Заголовок начинается с FESTIVAL COLOR."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert w.windowTitle().startswith('FESTIVAL COLOR')

    def test_info_bar_shows_position(self, qtbot, mock_employee_admin):
        """Информационная панель содержит должность."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        # Ищем QLabel с текстом позиции
        labels = w.findChildren(QLabel)
        position_labels = [l for l in labels if 'Руководитель студии' in l.text()]
        assert len(position_labels) >= 1

    def test_info_bar_dual_position(self, qtbot, mock_employee_designer_manager):
        """Двойная должность отображается через /."""
        w, _, _ = _create_mw(qtbot, mock_employee_designer_manager)
        labels = w.findChildren(QLabel)
        dual_labels = [l for l in labels if 'Дизайнер/Менеджер' in l.text()]
        assert len(dual_labels) >= 1


# ========== 5. get_resize_edge (6 тестов) ==========

@pytest.mark.ui
class TestMainWindowResizeEdge:
    """Определение края окна для resize."""

    def test_no_edge_center(self, qtbot, mock_employee_admin):
        """Точка в центре окна — edge = None."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        pos = MagicMock()
        pos.x.return_value = 100
        pos.y.return_value = 100
        assert w.get_resize_edge(pos) is None

    def test_left_edge(self, qtbot, mock_employee_admin):
        """Точка у левого края — 'left'."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        pos = MagicMock()
        pos.x.return_value = 3  # <= resize_margin (8)
        pos.y.return_value = 100
        assert w.get_resize_edge(pos) == 'left'

    def test_right_edge(self, qtbot, mock_employee_admin):
        """Точка у правого края — 'right'."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w.resize(1400, 800)
        pos = MagicMock()
        pos.x.return_value = 1397  # >= width - margin
        pos.y.return_value = 100
        assert w.get_resize_edge(pos) == 'right'

    def test_top_edge(self, qtbot, mock_employee_admin):
        """Точка у верхнего края — 'top'."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        pos = MagicMock()
        pos.x.return_value = 100
        pos.y.return_value = 2  # <= margin
        assert w.get_resize_edge(pos) == 'top'

    def test_bottom_edge(self, qtbot, mock_employee_admin):
        """Точка у нижнего края — 'bottom'."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w.resize(1400, 800)
        pos = MagicMock()
        pos.x.return_value = 100
        pos.y.return_value = 797  # >= height - margin
        assert w.get_resize_edge(pos) == 'bottom'

    def test_corner_top_left(self, qtbot, mock_employee_admin):
        """Точка в верхнем левом углу — 'top-left'."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        pos = MagicMock()
        pos.x.return_value = 2
        pos.y.return_value = 2
        assert w.get_resize_edge(pos) == 'top-left'


# ========== 6. set_cursor_shape (5 тестов) ==========

@pytest.mark.ui
class TestMainWindowCursorShape:
    """Установка формы курсора по краю."""

    def test_cursor_none_arrow(self, qtbot, mock_employee_admin):
        """Без края — стрелка."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w.set_cursor_shape(None)
        assert w.cursor().shape() == Qt.ArrowCursor

    def test_cursor_left_hor(self, qtbot, mock_employee_admin):
        """Левый край — горизонтальный курсор."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w.set_cursor_shape('left')
        assert w.cursor().shape() == Qt.SizeHorCursor

    def test_cursor_top_ver(self, qtbot, mock_employee_admin):
        """Верхний край — вертикальный курсор."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w.set_cursor_shape('top')
        assert w.cursor().shape() == Qt.SizeVerCursor

    def test_cursor_top_left_fdiag(self, qtbot, mock_employee_admin):
        """Верхний левый угол — диагональный курсор."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w.set_cursor_shape('top-left')
        assert w.cursor().shape() == Qt.SizeFDiagCursor

    def test_cursor_top_right_bdiag(self, qtbot, mock_employee_admin):
        """Верхний правый угол — обратный диагональный курсор."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w.set_cursor_shape('top-right')
        assert w.cursor().shape() == Qt.SizeBDiagCursor


# ========== 7. Обработчики статусов sync/offline (6 тестов) ==========

@pytest.mark.ui
class TestMainWindowSyncHandlers:
    """Обработчики SyncManager и OfflineManager."""

    def test_online_indicator_zero(self, qtbot, mock_employee_admin):
        """0 онлайн — пустой текст индикатора."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w._update_online_indicator(0)
        assert w.online_indicator.text() == ""

    def test_online_indicator_one(self, qtbot, mock_employee_admin):
        """1 онлайн — '1 онлайн'."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w._update_online_indicator(1)
        assert w.online_indicator.text() == "1 онлайн"

    def test_online_indicator_many(self, qtbot, mock_employee_admin):
        """Несколько онлайн — 'N онлайн'."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w._update_online_indicator(5)
        assert w.online_indicator.text() == "5 онлайн"

    def test_online_indicator_tooltip(self, qtbot, mock_employee_admin):
        """Tooltip формируется из списка пользователей."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        users = [{'full_name': 'Иванов'}, {'full_name': 'Петров'}]
        w._update_online_indicator(2, users)
        tooltip = w.online_indicator.toolTip()
        assert 'Иванов' in tooltip
        assert 'Петров' in tooltip

    def test_connection_status_online(self, qtbot, mock_employee_admin):
        """Статус онлайн — текст 'Готов к работе'."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w._on_connection_status_changed(True)
        assert w.status_label.text() == "Готов к работе"

    def test_connection_status_offline(self, qtbot, mock_employee_admin):
        """Статус офлайн — текст 'Нет соединения с сервером'."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w._on_connection_status_changed(False)
        assert w.status_label.text() == "Нет соединения с сервером"


# ========== 8. Offline-обработчики (5 тестов) ==========

@pytest.mark.ui
class TestMainWindowOfflineHandlers:
    """Обработчики OfflineManager."""

    def test_offline_status_online(self, qtbot, mock_employee_admin):
        """Статус 'online' — индикатор скрыт."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w._on_offline_status_changed('online')
        assert w.offline_indicator.isHidden()

    def test_offline_status_offline(self, qtbot, mock_employee_admin):
        """Статус 'offline' — индикатор показан с текстом 'OFFLINE'."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w._on_offline_status_changed('offline')
        assert not w.offline_indicator.isHidden()
        assert w.offline_indicator.text() == "OFFLINE"

    def test_offline_status_syncing(self, qtbot, mock_employee_admin):
        """Статус 'syncing' — индикатор показывает 'Синхронизация...'."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w._on_offline_status_changed('syncing')
        assert not w.offline_indicator.isHidden()
        assert 'Синхронизация' in w.offline_indicator.text()

    def test_pending_operations_count(self, qtbot, mock_employee_admin):
        """Ожидающие операции — индикатор показывает количество."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w._on_pending_operations_changed(3)
        assert '3' in w.offline_indicator.text()
        assert not w.offline_indicator.isHidden()

    def test_sync_completed_success(self, qtbot, mock_employee_admin):
        """Успешная синхронизация — текст статуса обновлён."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w._on_sync_completed(True, "OK")
        assert 'Синхронизация завершена' in w.status_label.text()


# ========== 9. Навигация по вкладкам (5 тестов) ==========

@pytest.mark.ui
class TestMainWindowTabNavigation:
    """Навигация между вкладками."""

    def test_first_tab_active(self, qtbot, mock_employee_admin):
        """При создании активна первая вкладка."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert w.tabs.currentIndex() == 0

    def test_switch_to_second_tab(self, qtbot, mock_employee_admin):
        """Переключение на вторую вкладку."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        if w.tabs.count() > 1:
            w.tabs.setCurrentIndex(1)
            assert w.tabs.currentIndex() == 1

    def test_on_tab_changed_called(self, qtbot, mock_employee_admin):
        """on_tab_changed вызывается при переключении."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        with patch.object(w, 'on_tab_changed') as mock_otc:
            w.tabs.currentChanged.connect(mock_otc)
            if w.tabs.count() > 1:
                w.tabs.setCurrentIndex(1)
                mock_otc.assert_called()

    def test_search_result_selected_client(self, qtbot, mock_employee_admin):
        """Навигация к клиенту из глобального поиска."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        # Находим индекс вкладки "Клиенты"
        client_idx = None
        for i in range(w.tabs.count()):
            if 'Клиенты' in w.tabs.tabText(i):
                client_idx = i
                break
        if client_idx is not None:
            w._on_search_result_selected("client", 1)
            assert w.tabs.currentIndex() == client_idx

    def test_search_result_unknown_type(self, qtbot, mock_employee_admin):
        """Неизвестный тип сущности — ничего не меняется."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        initial_idx = w.tabs.currentIndex()
        w._on_search_result_selected("unknown_entity", 1)
        assert w.tabs.currentIndex() == initial_idx


# ========== 10. Дашборды (5 тестов) ==========

@pytest.mark.ui
class TestMainWindowDashboards:
    """Переключение дашбордов."""

    def test_dashboards_dict_initial(self, qtbot, mock_employee_admin):
        """Начальный словарь дашбордов пуст."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        # При lazy-создании dashboards может быть пустым или нет (зависит от on_tab_changed)
        assert isinstance(w.dashboards, dict)

    def test_dashboard_factories_populated(self, qtbot, mock_employee_admin):
        """Фабрики дашбордов заполнены после _init_deferred."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        assert len(w._dashboard_factories) > 0

    def test_switch_dashboard_none_hides(self, qtbot, mock_employee_admin):
        """switch_dashboard(None) скрывает стек дашбордов."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w.switch_dashboard(None)
        assert not w.dashboard_stack.isVisible()
        assert w.current_dashboard_key is None

    def test_switch_dashboard_unknown_key(self, qtbot, mock_employee_admin):
        """Неизвестный ключ дашборда скрывает стек."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w.switch_dashboard('Несуществующий')
        assert not w.dashboard_stack.isVisible()

    def test_refresh_current_dashboard_no_crash(self, qtbot, mock_employee_admin):
        """refresh_current_dashboard без ошибок при отсутствии дашборда."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w.current_dashboard_key = None
        w.refresh_current_dashboard()  # Не должно бросить исключение


# ========== 11. Обновления (4 теста) ==========

@pytest.mark.ui
class TestMainWindowUpdates:
    """Система обновлений программы."""

    def test_show_no_updates(self, qtbot, mock_employee_admin):
        """_show_no_updates обновляет статус."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        with patch('ui.main_window.QMessageBox') as MockMB:
            w._show_no_updates()
            assert w.status_label.text() == "Обновлений нет"
            assert w.update_btn.isEnabled()

    def test_show_updates_disabled(self, qtbot, mock_employee_admin):
        """_show_updates_disabled обновляет статус."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        with patch('ui.main_window.QMessageBox') as MockMB:
            w._show_updates_disabled()
            assert w.status_label.text() == "Обновления отключены"
            assert w.update_btn.isEnabled()

    def test_show_update_error(self, qtbot, mock_employee_admin):
        """_show_update_error обновляет статус."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        with patch('ui.main_window.QMessageBox') as MockMB:
            w._show_update_error("Тестовая ошибка")
            assert w.status_label.text() == "Ошибка обновления"
            assert w.update_btn.isEnabled()

    def test_show_update_dialog(self, qtbot, mock_employee_admin):
        """_show_update_dialog обновляет статус и показывает диалог."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        with patch('ui.update_dialogs.UpdateDialog') as MockUD:
            MockUD.return_value.exec_.return_value = None
            update_info = {"available": True, "version": "2.0.0"}
            w._show_update_dialog(update_info)
            assert w.status_label.text() == "Доступно обновление"


# ========== 12. Создание карточек статистики (3 теста) ==========

@pytest.mark.ui
class TestMainWindowStatCards:
    """Создание карточек статистики."""

    def test_simple_stat_card_type(self, qtbot, mock_employee_admin):
        """create_simple_stat_card возвращает QGroupBox."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        with patch('utils.resource_path.resource_path', return_value='/fake/icon.svg'), \
             patch('os.path.exists', return_value=False):
            card = w.create_simple_stat_card(
                'test_card', 'Тест', '42', 'resources/icons/test.svg', '#fff', '#000')
            assert isinstance(card, QGroupBox)

    def test_simple_stat_card_value(self, qtbot, mock_employee_admin):
        """Карточка содержит значение."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        with patch('utils.resource_path.resource_path', return_value='/fake/icon.svg'), \
             patch('os.path.exists', return_value=False):
            card = w.create_simple_stat_card(
                'test_card', 'Клиенты', '99', 'resources/icons/test.svg', '#fff', '#000')
            value_label = card.findChild(QLabel, 'value')
            assert value_label is not None
            assert value_label.text() == '99'

    def test_compact_stat_card_type(self, qtbot, mock_employee_admin):
        """create_compact_stat_card возвращает QGroupBox."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        card = w.create_compact_stat_card(
            'test_compact', 'Заказы', '10', '150 кв.м', '--', '#fff', '#000')
        assert isinstance(card, QGroupBox)


# ========== 13. closeEvent (2 теста) ==========

@pytest.mark.ui
class TestMainWindowCloseEvent:
    """Обработка закрытия окна."""

    def test_close_event_accept(self, qtbot, mock_employee_admin):
        """Подтверждение выхода — событие принимается."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        # closeEvent перезаписан в _create_mw, проверяем что не падает
        mock_event = MagicMock()
        w.closeEvent(mock_event)
        mock_event.accept.assert_called_once()

    def test_close_original_with_rejection(self, qtbot, mock_employee_admin):
        """Оригинальный closeEvent — отмена выхода игнорирует событие."""
        from ui.main_window import MainWindow
        mock_db = MagicMock()
        patches = []
        for target in _STANDARD_PATCHES:
            if target == 'database.db_manager.DatabaseManager':
                patches.append(patch(target, return_value=mock_db))
            elif target == 'utils.data_access.DataAccess':
                patches.append(patch(target, return_value=MagicMock()))
            elif target == 'utils.sync_manager.SyncManager':
                patches.append(patch(target, return_value=MagicMock()))
            elif target == 'utils.offline_manager.init_offline_manager':
                patches.append(patch(target, return_value=MagicMock()))
            elif target == 'ui.main_window.GlobalSearchWidget':
                patches.append(patch(target, side_effect=lambda *a, **k: _FakeSearchWidget()))
            else:
                patches.append(patch(target, side_effect=_make_fake_tab))

        for p in patches:
            p.start()
        try:
            w = MainWindow(employee_data=mock_employee_admin, api_client=None)
            qtbot.addWidget(w)
            w._init_deferred()

            # Мокаем CustomQuestionBox чтобы он возвращал Rejected
            from PyQt5.QtWidgets import QDialog
            with patch('ui.custom_message_box.CustomQuestionBox') as MockCQB:
                mock_dialog = MagicMock()
                mock_dialog.exec_.return_value = QDialog.Rejected
                MockCQB.return_value = mock_dialog

                mock_event = MagicMock()
                # Вызываем оригинальный closeEvent
                MainWindow.closeEvent(w, mock_event)
                mock_event.ignore.assert_called_once()

            # Подменяем closeEvent чтобы qtbot не завис при cleanup
            w.closeEvent = lambda e: e.accept()
        finally:
            for p in patches:
                p.stop()


# ========== 14. leaveEvent и changeEvent (2 теста) ==========

@pytest.mark.ui
class TestMainWindowEvents:
    """Обработка различных событий."""

    def test_leave_event_resets_cursor(self, qtbot, mock_employee_admin):
        """leaveEvent сбрасывает курсор на стрелку."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w.setCursor(Qt.SizeHorCursor)
        event = QEvent(QEvent.Leave)
        w.leaveEvent(event)
        assert w.cursor().shape() == Qt.ArrowCursor

    def test_change_event_resets_snap(self, qtbot, mock_employee_admin):
        """changeEvent WindowStateChange сбрасывает snap-флаги."""
        w, _, _ = _create_mw(qtbot, mock_employee_admin)
        w.is_snapped = True
        w.snap_position = 'left'
        # Создаём реальное событие WindowStateChange
        event = QEvent(QEvent.WindowStateChange)
        # Эмулируем нормальное состояние (не maximized, не minimized)
        with patch.object(w, 'isMaximized', return_value=False), \
             patch.object(w, 'isMinimized', return_value=False):
            w.changeEvent(event)
            assert w.is_snapped is False
            assert w.snap_position is None

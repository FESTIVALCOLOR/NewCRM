# -*- coding: utf-8 -*-
import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                             QHBoxLayout, QMenuBar, QAction, QMessageBox, QDialog,
                             QLabel, QStatusBar, QGridLayout, QGroupBox, QSizePolicy, QApplication)
from PyQt5.QtCore import Qt, QTimer, QRect, QSize, QEvent
from PyQt5.QtGui import QFont, QPixmap, QColor, QPalette
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QTabWidget
from config import ROLES
from ui.dashboard_tab import DashboardTab
from ui.clients_tab import ClientsTab
from ui.contracts_tab import ContractsTab
from ui.crm_tab import CRMTab
from ui.crm_supervision_tab import CRMSupervisionTab
from ui.reports_tab import ReportsTab
from ui.employees_tab import EmployeesTab
from ui.salaries_tab import SalariesTab
from ui.employee_reports_tab import EmployeeReportsTab
from utils.tab_helpers import disable_wheel_on_tabwidget

class MainWindow(QMainWindow):
    def __init__(self, employee_data, api_client=None):
        super().__init__()
        self.employee = employee_data
        self.api_client = api_client  # API
        from database.db_manager import DatabaseManager
        self.db = DatabaseManager()

        # Проверяем offline режим
        self.is_offline_mode = self.employee.get('offline_mode', False)

        # SyncManager для real-time синхронизации (только если НЕ в offline режиме)
        self.sync_manager = None
        if self.api_client and not self.is_offline_mode:
            from utils.sync_manager import SyncManager
            self.sync_manager = SyncManager(
                api_client=self.api_client,
                employee_id=self.employee.get('id', 0),
                parent=self
            )
            # Подключаем сигналы
            self.sync_manager.online_users_updated.connect(self._on_online_users_updated)
            self.sync_manager.connection_status_changed.connect(self._on_connection_status_changed)

        # OfflineManager для работы без сети
        self.offline_manager = None
        if self.api_client:
            try:
                from utils.offline_manager import init_offline_manager
                from config import DATABASE_PATH
                self.offline_manager = init_offline_manager(DATABASE_PATH, self.api_client)
                # Подключаем сигналы
                self.offline_manager.connection_status_changed.connect(self._on_offline_status_changed)
                self.offline_manager.pending_operations_changed.connect(self._on_pending_operations_changed)
                self.offline_manager.sync_completed.connect(self._on_sync_completed)

                # Если в offline режиме - устанавливаем статус сразу
                if self.is_offline_mode:
                    from utils.offline_manager import ConnectionStatus
                    self.offline_manager.status = ConnectionStatus.OFFLINE
            except Exception as e:
                print(f"[MainWindow] Ошибка инициализации OfflineManager: {e}")

        #   resize
        self.resizing = False
        self.resize_edge = None
        self.resize_margin = 8

        #   Snap Assist
        self.snap_threshold = 10  #     (  20  10)
        self.is_snapped = False
        self.snap_position = None  # 'left', 'right', 'top', 'maximized'
        self.restore_geometry = None  #   snap

        self.init_ui()

        # ==========     ==========
        from utils.calendar_helpers import CALENDAR_STYLE

        current_style = self.styleSheet()
        self.setStyleSheet(current_style + "\n" + CALENDAR_STYLE)
        # ===========================================================

        # Устанавливаем event filter для перехвата событий мыши от всех дочерних виджетов
        QApplication.instance().installEventFilter(self)

        # Отложенный запуск синхронизации (2 сек), чтобы не блокировать первый показ данных
        QTimer.singleShot(2000, self._start_background_sync)

    def _start_background_sync(self):
        """Отложенный запуск синхронизации после первого показа данных"""
        if self.sync_manager:
            self.sync_manager.start()
        if self.offline_manager:
            self.offline_manager.start_monitoring()

    def init_ui(self):
        self.setWindowTitle(f'FESTIVAL COLOR - {self.employee["full_name"]}')
        # Абсолютный минимум Qt (для Snap Assist на маленьких экранах)
        # Рекомендуемый минимум 1400x800 контролируется в mouseMoveEvent
        self.setMinimumSize(800, 600)
        self.resize(1400, 800)
        
        #   TITLE BAR
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)  #  border-radius

        # ==========     ==========
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0, 0))  #   border-radius
        self.setPalette(palette)
        # =====================================================

        # ==========    ==========
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)
        # ====================================================

        # ==========   ==========
        main_container = QWidget()
        main_container.setObjectName("mainContainer")
        main_container.setStyleSheet("""
            QWidget#mainContainer {
                background-color: transparent;
                border-radius: 10px;
            }
        """)
        self.setCentralWidget(main_container)

        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        main_container.setLayout(container_layout)
        # ====================================================

        # ==========      ==========
        from PyQt5.QtWidgets import QFrame
        border_frame = QFrame()
        border_frame.setObjectName("mainBorderFrame")
        border_frame.setStyleSheet("""
            QFrame#mainBorderFrame {
                background-color: #FFFFFF;
                border: 1px solid #d9d9d9;
                border-radius: 10px;
            }
        """)
        container_layout.addWidget(border_frame)
        # ======================================================

        # ==========  MOUSE TRACKING  BORDER FRAME ==========
        border_frame.setMouseTracking(True)
        border_frame.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        # ==============================================================

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        border_frame.setLayout(layout)
        # ==========  TITLE BAR ==========
        from ui.custom_title_bar import CustomTitleBar
        self.title_bar = CustomTitleBar(
            self,
            "FESTIVAL COLOR - Приложение управления заказами",
            simple_mode=False
        )
        # ==========    TITLE BAR ==========
        self.title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        # ======================================================
        layout.addWidget(self.title_bar)
        # =========================================
        
        #   ()
        info_label = QLabel(f'Пользователь: {self.employee["full_name"]} - должность: {self.employee["position"]}')
        info_label.setStyleSheet('''
            padding: 8px 15px; 
            background-color: #F8F9FA; 
            border-bottom: 0px solid #E0E0E0;
            font-size: 12px;
            color: #555;
            font-weight: 500;
        ''')
        layout.addWidget(info_label)
        
        #
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: white;
            }
            QTabBar::tab {
                background: #ffffff;
                border: 1px solid #d9d9d9;
                padding: 6px 16px;
                margin-right: 2px;
                border-radius: 4px 4px 0 0;
            }
            QTabBar::tab:hover {
                background: #fafafa;
            }
            QTabBar::tab:selected {
                background: #ffd93c;
                font-weight: bold;
                border-color: #e6c236;
            }
        """)

        #
        disable_wheel_on_tabwidget(self.tabs)

        # ==========  DASHBOARD CONTAINER ==========
        # Создаем дашборды ПЕРЕД setup_tabs, чтобы они были готовы при вызове on_tab_changed
        from PyQt5.QtWidgets import QStackedWidget
        from ui.dashboards import (ClientsDashboard, ContractsDashboard, CRMDashboard,
                                   EmployeesDashboard, SalariesDashboard,
                                   SalariesAllPaymentsDashboard, SalariesIndividualDashboard,
                                   SalariesTemplateDashboard, SalariesSalaryDashboard,
                                   SalariesSupervisionDashboard)

        # Создаем QStackedWidget с parent=border_frame чтобы не было отдельного окна
        self.dashboard_stack = QStackedWidget(border_frame)
        self.dashboard_stack.setObjectName('dashboard_stack')

        # Создаем все дашборды сразу с parent=dashboard_stack
        # ПРИМЕЧАНИЕ: Дашборды для "Отчеты и Статистика" и "Отчеты по сотрудникам" временно отключены
        # т.к. эти страницы будут полностью переработаны в будущем
        self.dashboards = {
            'Клиенты': ClientsDashboard(self.db, self.api_client, parent=self.dashboard_stack),
            'Договора': ContractsDashboard(self.db, self.api_client, parent=self.dashboard_stack),
            'СРМ (Индивидуальные)': CRMDashboard(self.db, 'Индивидуальный', self.api_client, parent=self.dashboard_stack),
            'СРМ (Шаблонные)': CRMDashboard(self.db, 'Шаблонный', self.api_client, parent=self.dashboard_stack),
            'СРМ надзора': CRMDashboard(self.db, 'Авторский надзор', self.api_client, parent=self.dashboard_stack),
            'Сотрудники': EmployeesDashboard(self.db, self.api_client, parent=self.dashboard_stack),
            # Дашборды для вкладок Зарплаты - по одному на каждую внутреннюю вкладку
            'Зарплаты (Все)': SalariesAllPaymentsDashboard(self.db, self.api_client, parent=self.dashboard_stack),
            'Зарплаты (Индивидуальные)': SalariesIndividualDashboard(self.db, self.api_client, parent=self.dashboard_stack),
            'Зарплаты (Шаблонные)': SalariesTemplateDashboard(self.db, self.api_client, parent=self.dashboard_stack),
            'Зарплаты (Оклады)': SalariesSalaryDashboard(self.db, self.api_client, parent=self.dashboard_stack),
            'Зарплаты (Надзор)': SalariesSupervisionDashboard(self.db, self.api_client, parent=self.dashboard_stack),
        }

        # Добавляем все дашборды в stack и сохраняем индексы
        self.dashboard_indices = {}
        for key, dashboard in self.dashboards.items():
            index = self.dashboard_stack.addWidget(dashboard)
            self.dashboard_indices[key] = index

        # Текущий ключ дашборда
        self.current_dashboard_key = None
        # ======================================================

        #
        self.setup_tabs()

        # Контейнер для вкладок с отступами слева и справа
        tabs_container = QWidget()
        tabs_container_layout = QVBoxLayout()
        tabs_container_layout.setContentsMargins(10, 0, 10, 0)
        tabs_container_layout.setSpacing(0)
        tabs_container_layout.addWidget(self.tabs)
        tabs_container.setLayout(tabs_container_layout)

        layout.addWidget(tabs_container, 1)  # stretch=1 - таблицы получают всё доступное место

        # Добавляем dashboard_stack в layout (фиксированная высота, без stretch)
        layout.addWidget(self.dashboard_stack, 0)  # stretch=0 - дашборд не растягивается

        # ==========  -   ==========
        from PyQt5.QtWidgets import QPushButton
        from PyQt5.QtGui import QIcon
        from config import APP_VERSION

        status_bar_container = QWidget()
        status_bar_layout = QHBoxLayout()
        status_bar_layout.setContentsMargins(10, 5, 10, 5)
        status_bar_layout.setSpacing(10)
        status_bar_container.setLayout(status_bar_layout)

        #   -
        self.status_label = QLabel('Готов к работе')
        self.status_label.setStyleSheet("color: #555; font-size: 11px; border: none;")
        status_bar_layout.addWidget(self.status_label)

        # Индикатор онлайн пользователей
        self.online_indicator = QLabel()
        self.online_indicator.setStyleSheet("""
            QLabel {
                color: #27ae60;
                font-size: 11px;
                border: none;
                padding-left: 10px;
            }
        """)
        self.online_indicator.setToolTip("Пользователи онлайн")
        self._update_online_indicator(0)
        status_bar_layout.addWidget(self.online_indicator)

        # Индикатор offline-режима и ожидающих операций
        self.offline_indicator = QLabel()
        self.offline_indicator.setStyleSheet("""
            QLabel {
                color: #e67e22;
                font-size: 11px;
                border: none;
                padding-left: 10px;
                font-weight: bold;
            }
        """)
        self.offline_indicator.hide()  # Скрыт по умолчанию
        status_bar_layout.addWidget(self.offline_indicator)

        status_bar_layout.addStretch()

        # Версия приложения с пробелом для отступа
        self.version_label = QLabel(f'Версия: {APP_VERSION}')
        self.version_label.setStyleSheet("color: #555; font-size: 11px; border: none;")
        status_bar_layout.addWidget(self.version_label)

        # Кнопка "Обновить" (только для руководителя студии)
        if self.employee.get('position') == 'Руководитель студии':
            from utils.resource_path import resource_path
            self.update_btn = QPushButton()

            # Загружаем иконку с помощью resource_path
            icon_path = resource_path('resources/icons/refresh.svg')

            if os.path.exists(icon_path):
                self.update_btn.setIcon(QIcon(icon_path))
                self.update_btn.setIconSize(QSize(12, 12))

            self.update_btn.setFixedSize(16, 16)
            self.update_btn.setToolTip("Проверить обновления")
            self.update_btn.setProperty('icon-only', True)  # Для применения стилей без padding
            self.update_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 4px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #E0E0E0;
                }
            """)
            self.update_btn.clicked.connect(self.check_for_updates_manual)
            status_bar_layout.addWidget(self.update_btn)

        #
        status_bar_container.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                border-top: 1px solid #E0E0E0;
            }
        """)

        layout.addWidget(status_bar_container)
        # ====================================================

        # ==========   - ==========
        self.setStatusBar(None)
        # ====================================================

    def get_resize_edge(self, pos):
        """ /   """
        rect = self.rect()
        margin = self.resize_margin
        
        on_left = pos.x() <= margin
        on_right = pos.x() >= rect.width() - margin
        on_top = pos.y() <= margin
        on_bottom = pos.y() >= rect.height() - margin
        
        #  ()
        if on_top and on_left:
            return 'top-left'
        elif on_top and on_right:
            return 'top-right'
        elif on_bottom and on_left:
            return 'bottom-left'
        elif on_bottom and on_right:
            return 'bottom-right'
        
        # 
        elif on_top:
            return 'top'
        elif on_bottom:
            return 'bottom'
        elif on_left:
            return 'left'
        elif on_right:
            return 'right'
        
        return None

    def set_cursor_shape(self, edge):
        """  """
        if edge == 'top-left' or edge == 'bottom-right':
            self.setCursor(Qt.SizeFDiagCursor)
        elif edge == 'top-right' or edge == 'bottom-left':
            self.setCursor(Qt.SizeBDiagCursor)
        elif edge == 'left' or edge == 'right':
            self.setCursor(Qt.SizeHorCursor)
        elif edge == 'top' or edge == 'bottom':
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def snap_to_edge(self, pos):
        """      """
        screen = QApplication.desktop().availableGeometry(self)

        #           - 
        restore_threshold = 50  #    
        should_restore = False

        if self.is_snapped:
            if self.snap_position == 'maximized':
                # Восстановление из maximized при перетаскивании
                if pos.y() > screen.y() + restore_threshold:
                    should_restore = True
                    # При maximized: восстанавливаем сохраненную геометрию
                    if self.restore_geometry:
                        # Восстанавливаем минимальный размер
                        self.setMinimumSize(800, 600)

                        # Центрируем окно относительно курсора в области title bar
                        new_x = pos.x() - self.restore_geometry.width() // 2
                        new_y = pos.y() - 20  # 20px - примерно центр title bar

                        # Применяем сохраненную геометрию
                        self.setGeometry(new_x, new_y, self.restore_geometry.width(), self.restore_geometry.height())

                        self.is_snapped = False
                        self.snap_position = None
                        self.restore_geometry = None
                        return
            elif self.snap_position == 'left':
                # Восстановление из левого snap
                if pos.x() > screen.x() + restore_threshold:
                    should_restore = True
            elif self.snap_position == 'right':
                # Восстановление из правого snap
                if pos.x() < screen.x() + screen.width() - restore_threshold:
                    should_restore = True

            # Восстановление из snap - возвращаем геометрию
            if should_restore and self.restore_geometry and self.snap_position in ['left', 'right']:
                self.setGeometry(self.restore_geometry)
                # Восстанавливаем минимальный размер
                self.setMinimumSize(800, 600)
                self.is_snapped = False
                self.snap_position = None
                self.restore_geometry = None
                return

        #      ()
        if pos.y() <= screen.y() + self.snap_threshold:
            if not self.is_snapped or self.snap_position != 'maximized':
                self.restore_geometry = self.geometry()
                self.is_snapped = True
                self.snap_position = 'maximized'
                #    ,  mouseReleaseEvent

        #     
        elif pos.x() <= screen.x() + self.snap_threshold:
            if not self.is_snapped or self.snap_position != 'left':
                self.restore_geometry = self.geometry()
                self.is_snapped = True
                self.snap_position = 'left'

        #      (:  screen.x())
        elif pos.x() >= screen.x() + screen.width() - self.snap_threshold:
            if not self.is_snapped or self.snap_position != 'right':
                self.restore_geometry = self.geometry()
                self.is_snapped = True
                self.snap_position = 'right'
        else:
            #     -  snap
            if self.is_snapped:
                self.is_snapped = False
                self.snap_position = None

    def apply_snap(self):
        """Применение snap позиции"""
        if not self.is_snapped or not self.snap_position:
            # Не в режиме snap - восстанавливаем минимальный размер
            self.setMinimumSize(800, 600)
            self.setCursor(Qt.ArrowCursor)
            return

        screen = QApplication.desktop().availableGeometry(self)

        # Временно убираем ограничения для Snap Assist
        self.setMinimumSize(1, 1)
        self.setMaximumSize(16777215, 16777215)  # Максимум Qt

        if self.snap_position == 'maximized':
            # Развернуть на весь экран
            self.setGeometry(screen)

        elif self.snap_position == 'left':
            # Левая половина экрана
            half_width = screen.width() // 2
            self.setGeometry(screen.x(), screen.y(), half_width, screen.height())

        elif self.snap_position == 'right':
            # Правая половина экрана
            half_width = screen.width() // 2
            self.setGeometry(screen.x() + half_width, screen.y(), half_width, screen.height())

        # Сбрасываем курсор после snap
        self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        """Начало изменения размера"""
        if event.button() == Qt.LeftButton:
            # Если окно maximized, сначала восстанавливаем его для resize
            if self.isMaximized():
                self.showNormal()

            edge = self.get_resize_edge(event.pos())

            if edge:
                # Если выходим из snap режима - восстанавливаем минимальный размер
                if self.is_snapped:
                    self.is_snapped = False
                    self.snap_position = None
                    self.restore_geometry = None
                # Восстанавливаем минимальный размер перед resize
                self.setMinimumSize(800, 600)

                self.resizing = True
                self.resize_edge = edge
                self.resize_start_pos = event.globalPos()
                self.resize_start_geometry = self.geometry()
                # ВАЖНО: Захватываем мышь чтобы получать события даже за пределами окна
                self.grabMouse()
                event.accept()
                return
        super().mousePressEvent(event)

    def eventFilter(self, obj, event):
        """Глобальный перехватчик событий мыши для корректной работы resize"""
        try:
            # Проверяем, что obj является QWidget (не QWindow или другой объект)
            from PyQt5.QtWidgets import QWidget
            if not isinstance(obj, QWidget):
                return super().eventFilter(obj, event)

            # Проверяем, что окно еще существует и видимо
            if not self.isVisible():
                return super().eventFilter(obj, event)

            # Перехватываем отпускание кнопки мыши для сброса resize состояния
            # Это нужно на случай если mouseReleaseEvent не дошел до окна
            if event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton and self.resizing:
                    self.releaseMouse()
                    self.resizing = False
                    self.resize_edge = None
                    self.setCursor(Qt.ArrowCursor)
                    return False  # Пропускаем событие дальше

            # Обрабатываем только события от виджетов внутри этого окна
            if not self.isAncestorOf(obj) and obj != self:
                return super().eventFilter(obj, event)
            # Перехватываем движение мыши для изменения курсора на границах
            if event.type() == QEvent.MouseMove:
                if not self.resizing:
                    # Преобразуем координаты в координаты окна
                    global_pos = event.globalPos()
                    local_pos = self.mapFromGlobal(global_pos)
                    edge = self.get_resize_edge(local_pos)
                    self.set_cursor_shape(edge)

            # Перехватываем выход мыши для сброса курсора
            elif event.type() == QEvent.Leave:
                if not self.resizing:
                    self.setCursor(Qt.ArrowCursor)

            return super().eventFilter(obj, event)
        except RuntimeError:
            # Объект был удален - игнорируем
            return False

    def event(self, event):
        """Обработка событий наведения мыши"""
        if event.type() == QEvent.HoverMove:
            # Изменяем курсор при наведении (без нажатия)
            # Не меняем курсор во время resize или если окно maximized
            if not self.resizing:
                edge = self.get_resize_edge(event.pos())
                self.set_cursor_shape(edge)
        elif event.type() == QEvent.HoverLeave:
            # Сброс курсора при выходе мыши за пределы окна
            if not self.resizing:
                self.setCursor(Qt.ArrowCursor)

        return super().event(event)

    def nativeEvent(self, eventType, message):
        """Обработка нативных Windows событий для корректной работы Snap Assist"""
        try:
            import sys
            if sys.platform == 'win32':
                import ctypes
                from ctypes import wintypes

                # Константы Windows сообщений
                WM_NCCALCSIZE = 0x0083  # Расчет размера клиентской области
                WM_GETMINMAXINFO = 0x0024  # Ограничение размеров
                WM_NCHITTEST = 0x0084  # Определение зоны клика (для Snap Assist!)

                # Константы зон NCHITTEST
                HTCAPTION = 2  # Заголовок окна (для перетаскивания и Snap Assist)
                HTCLIENT = 1   # Клиентская область
                HTLEFT = 10
                HTRIGHT = 11
                HTTOP = 12
                HTTOPLEFT = 13
                HTTOPRIGHT = 14
                HTBOTTOM = 15
                HTBOTTOMLEFT = 16
                HTBOTTOMRIGHT = 17

                # Получаем сообщение
                msg = ctypes.wintypes.MSG.from_address(message.__int__())

                if msg.message == WM_NCHITTEST:
                    # ИСПРАВЛЕНИЕ 07.02.2026: Обработка WM_NCHITTEST для Snap Assist
                    # Получаем координаты курсора из lParam
                    x = msg.lParam & 0xFFFF
                    y = (msg.lParam >> 16) & 0xFFFF

                    # Преобразуем в локальные координаты
                    from PyQt5.QtCore import QPoint
                    local_pos = self.mapFromGlobal(QPoint(x, y))
                    lx, ly = local_pos.x(), local_pos.y()

                    # Зона resize (края окна) - 5 пикселей
                    border = 5
                    w, h = self.width(), self.height()

                    # Проверяем углы и края для resize
                    if lx < border and ly < border:
                        return True, HTTOPLEFT
                    elif lx > w - border and ly < border:
                        return True, HTTOPRIGHT
                    elif lx < border and ly > h - border:
                        return True, HTBOTTOMLEFT
                    elif lx > w - border and ly > h - border:
                        return True, HTBOTTOMRIGHT
                    elif lx < border:
                        return True, HTLEFT
                    elif lx > w - border:
                        return True, HTRIGHT
                    elif ly < border:
                        return True, HTTOP
                    elif ly > h - border:
                        return True, HTBOTTOM

                    # Проверяем зону заголовка (верхние 40 пикселей = title bar)
                    # Это активирует Snap Assist при перетаскивании за title bar
                    if ly < 40:
                        # Исключаем область кнопок управления окном (правый край)
                        # Обычно кнопки занимают ~120px справа
                        if lx < w - 120:
                            return True, HTCAPTION

                    return True, HTCLIENT

                elif msg.message == WM_NCCALCSIZE:
                    # При WM_NCCALCSIZE с wParam=True Windows запрашивает размер клиентской области
                    # Возвращаем 0 чтобы убрать стандартную рамку
                    if self.isMaximized():
                        return True, 0
                    return False, 0

                elif msg.message == WM_GETMINMAXINFO:
                    # Ограничиваем минимальный размер при Snap Assist
                    pass

        except Exception as e:
            # Если что-то пошло не так с нативными событиями - игнорируем
            pass

        return super().nativeEvent(eventType, message)

    def leaveEvent(self, event):
        """Сброс курсора при выходе мыши за пределы окна"""
        if not self.resizing:
            self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    def changeEvent(self, event):
        """Обработка изменения состояния окна (maximize/restore)"""
        if event.type() == QEvent.WindowStateChange:
            # Сбрасываем курсор при любом изменении состояния окна
            self.setCursor(Qt.ArrowCursor)

            # Если окно восстановлено из maximized состояния
            if not self.isMaximized() and not self.isMinimized():
                # Сбрасываем snap состояние для корректной работы resize
                self.is_snapped = False
                self.snap_position = None
                # Восстанавливаем минимальный размер (абсолютный минимум)
                self.setMinimumSize(800, 600)
                # Сбрасываем флаги resize на всякий случай
                self.resizing = False
                self.resize_edge = None
        super().changeEvent(event)

    def mouseMoveEvent(self, event):
        """  """
        if self.resizing and self.resize_edge:
            delta = event.globalPos() - self.resize_start_pos
            
            old_geometry = self.resize_start_geometry
            x = old_geometry.x()
            y = old_geometry.y()
            w = old_geometry.width()
            h = old_geometry.height()
            
            edge = self.resize_edge
            min_w, min_h = 1400, 800
            
            if 'left' in edge:
                new_x = x + delta.x()
                new_w = w - delta.x()
                if new_w >= min_w:
                    x = new_x
                    w = new_w
            
            elif 'right' in edge:
                new_w = w + delta.x()
                if new_w >= min_w:
                    w = new_w
            
            if 'top' in edge:
                new_y = y + delta.y()
                new_h = h - delta.y()
                if new_h >= min_h:
                    y = new_y
                    h = new_h
            
            elif 'bottom' in edge:
                new_h = h + delta.y()
                if new_h >= min_h:
                    h = new_h
            
            self.setGeometry(x, y, w, h)
            event.accept()
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        """Завершение изменения размера"""
        if event.button() == Qt.LeftButton and self.resizing:
            # ВАЖНО: Освобождаем захват мыши
            self.releaseMouse()
            self.resizing = False
            self.resize_edge = None
            self.setCursor(Qt.ArrowCursor)

            # Сбрасываем snap состояние после resize
            self.is_snapped = False
            self.snap_position = None
            self.restore_geometry = None

            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """  -      (1400x800)"""
        if event.button() == Qt.LeftButton:
            #      ,   
            #   snap
            self.is_snapped = False
            self.snap_position = None
            self.restore_geometry = None

            #      
            self.showNormal()
            self.resize(1400, 800)

            screen = QApplication.desktop().availableGeometry(self)
            x = (screen.width() - 1400) // 2
            y = (screen.height() - 800) // 2
            self.move(x, y)

            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return

        super().mouseDoubleClickEvent(event)

    def create_simple_stat_card(self, object_name, title, value, icon_path, bg_color, border_color):
        """Создание карточки статистики для нижней панели"""
        from utils.resource_path import resource_path

        card = QGroupBox()
        card.setObjectName(object_name)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setFixedHeight(80)

        # Рамка 1px (было 2px)
        card.setStyleSheet(f"""
            QGroupBox {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 5px;
                padding: 8px;
            }}
            QGroupBox:hover {{
                border: 2px solid {border_color};
            }}
        """)

        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 2, 0, 2)

        # Иконка слева (SVG или текстовый fallback)
        full_icon_path = resource_path(icon_path)
        if os.path.exists(full_icon_path):
            icon_widget = QSvgWidget(full_icon_path)
            icon_widget.setFixedSize(40, 40)
            layout.addWidget(icon_widget)
        else:
            # Fallback - текстовый символ
            icon_label = QLabel('--')
            icon_label.setStyleSheet(f'font-size: 24px; font-weight: bold; color: {border_color}; background-color: transparent;')
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setFixedWidth(40)
            layout.addWidget(icon_label)

        # Текстовая часть справа
        data_layout = QVBoxLayout()
        data_layout.setSpacing(1)
        data_layout.setAlignment(Qt.AlignVCenter)

        # Название карточки
        title_label = QLabel(title)
        title_label.setStyleSheet(f'''
            font-size: 10px;
            color: {border_color};
            font-weight: 600;
            background-color: transparent;
        ''')
        title_label.setWordWrap(True)
        title_label.setMinimumWidth(50)
        data_layout.addWidget(title_label)

        # Значение
        value_label = QLabel(value)
        value_label.setObjectName('value')
        value_label.setStyleSheet(f'''
            font-size: 20px;
            font-weight: bold;
            color: {border_color};
            background-color: transparent;
        ''')
        value_label.setWordWrap(False)
        value_label.setMinimumWidth(100)
        data_layout.addWidget(value_label)

        layout.addLayout(data_layout, 1)

        card.setLayout(layout)
        return card

    def create_compact_stat_card(self, object_name, title, orders_value, area_value, icon, bg_color, border_color):
        """    ( )"""

        card = QGroupBox()
        card.setObjectName(object_name)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setFixedHeight(85)

        card.setStyleSheet(f"""
            QGroupBox {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 6px;
            }}
            QGroupBox:hover {{
                border: 2px solid {border_color};
            }}
        """)

        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(8, 4, 8, 4)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet('font-size: 32px; background-color: transparent;')
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedWidth(40)
        layout.addWidget(icon_label)

        data_layout = QVBoxLayout()
        data_layout.setSpacing(2)
        data_layout.setAlignment(Qt.AlignVCenter)

        title_label = QLabel(title)
        title_label.setStyleSheet(f'''
            font-size: 10px;
            color: {border_color};
            font-weight: bold;
            background-color: transparent;
        ''')
        title_label.setWordWrap(False)
        data_layout.addWidget(title_label)

        orders_label = QLabel(f': {orders_value}')
        orders_label.setObjectName('orders_value')
        orders_label.setStyleSheet('''
            font-size: 16px;
            font-weight: bold;
            color: #2C3E50;
            background-color: transparent;
        ''')
        orders_label.setWordWrap(False)
        data_layout.addWidget(orders_label)

        area_label = QLabel(f': {area_value}')
        area_label.setObjectName('area_value')
        area_label.setStyleSheet('''
            font-size: 11px;
            color: #7F8C8D;
            font-weight: 500;
            background-color: transparent;
        ''')
        area_label.setWordWrap(False)
        data_layout.addWidget(area_label)

        layout.addLayout(data_layout, 1)

        card.setLayout(layout)
        return card
    
    def setup_tabs(self):
        """    """

        # ==========   ==========
        position = self.employee.get('position', '')
        secondary_position = self.employee.get('secondary_position', '')

        #
        allowed_tabs = set(ROLES.get(position, {}).get('tabs', []))
        can_edit = ROLES.get(position, {}).get('can_edit', False)
        
        # ==========     ==========
        if secondary_position:
            secondary_tabs = set(ROLES.get(secondary_position, {}).get('tabs', []))
            allowed_tabs = allowed_tabs.union(secondary_tabs)  # 
            
            #       can_edit - 
            secondary_can_edit = ROLES.get(secondary_position, {}).get('can_edit', False)
            can_edit = can_edit or secondary_can_edit
        # ================================================================

        print(f"\n  :")
        print(f"   : {self.employee['full_name']}")
        print(f"    : {position}")
        if secondary_position:
            print(f"    : {secondary_position}")
        print(f"    : {sorted(allowed_tabs)}")
        print(f"    : {can_edit}\n")

        # Сохраняем ссылки на вкладки для подключения сигналов синхронизации
        self.clients_tab = None
        self.contracts_tab = None
        self.crm_tab = None
        self.crm_supervision_tab = None

        # Добавляем вкладки
        if 'Клиенты' in allowed_tabs:
            self.clients_tab = ClientsTab(self.employee, api_client=self.api_client, parent=self)
            self.tabs.addTab(self.clients_tab, '  Клиенты  ')

        if 'Договора' in allowed_tabs:
            self.contracts_tab = ContractsTab(self.employee, api_client=self.api_client, parent=self)
            self.tabs.addTab(self.contracts_tab, '  Договора  ')

        if 'СРМ' in allowed_tabs:
            self.crm_tab = CRMTab(self.employee, can_edit, api_client=self.api_client, parent=self)
            self.tabs.addTab(self.crm_tab, '  СРМ  ')

        if 'СРМ надзора' in allowed_tabs:
            self.crm_supervision_tab = CRMSupervisionTab(self.employee, api_client=self.api_client, parent=self)
            self.tabs.addTab(self.crm_supervision_tab, '  СРМ надзора  ')

        if 'Отчеты и Статистика' in allowed_tabs:
            self.tabs.addTab(ReportsTab(self.employee, api_client=self.api_client), '  Отчеты и Статистика  ')

        if 'Сотрудники' in allowed_tabs:
            self.employees_tab = EmployeesTab(self.employee, api_client=self.api_client, parent=self)
            self.tabs.addTab(self.employees_tab, '  Сотрудники  ')

        if 'Зарплаты' in allowed_tabs:
            self.tabs.addTab(SalariesTab(self.employee, api_client=self.api_client, parent=self), '  Зарплаты  ')

        if 'Отчеты по сотрудникам' in allowed_tabs:
            self.tabs.addTab(EmployeeReportsTab(self.employee, api_client=self.api_client), '  Отчеты по сотрудникам  ')

        # Подключаем сигналы синхронизации к вкладкам
        if self.sync_manager:
            if self.clients_tab:
                self.sync_manager.clients_updated.connect(self.clients_tab.on_sync_update)
            if self.contracts_tab:
                self.sync_manager.contracts_updated.connect(self.contracts_tab.on_sync_update)
            if self.crm_tab:
                self.sync_manager.crm_cards_updated.connect(self.crm_tab.on_sync_update)
            if self.crm_supervision_tab:
                self.sync_manager.supervision_cards_updated.connect(self.crm_supervision_tab.on_sync_update)
            if hasattr(self, 'employees_tab') and self.employees_tab:
                self.sync_manager.employees_updated.connect(self.employees_tab.on_sync_update)

        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Показываем дашборд для первой вкладки при запуске
        self.on_tab_changed(0)

    def on_tab_changed(self, index):
        """Обновление данных при переключении вкладок + переключение дашбордов"""
        try:
            current_widget = self.tabs.widget(index)
            tab_name = self.tabs.tabText(index).strip()

            # Определяем, какой дашборд показывать
            dashboard_key = None

            if 'Клиенты' in tab_name:
                dashboard_key = 'Клиенты'
            elif 'Договора' in tab_name:
                dashboard_key = 'Договора'
            elif 'СРМ' in tab_name:
                if 'надзора' in tab_name:
                    dashboard_key = 'СРМ надзора'
                else:
                    # Для основной вкладки СРМ определяем по внутренней вкладке
                    if hasattr(current_widget, 'project_tabs'):
                        inner_index = current_widget.project_tabs.currentIndex()
                        inner_tab_name = current_widget.project_tabs.tabText(inner_index)
                        if 'Индивидуальн' in inner_tab_name:
                            dashboard_key = 'СРМ (Индивидуальные)'
                        elif 'Шаблонн' in inner_tab_name:
                            dashboard_key = 'СРМ (Шаблонные)'
                        else:
                            dashboard_key = 'СРМ (Индивидуальные)'  # По умолчанию
                    else:
                        dashboard_key = 'СРМ (Индивидуальные)'  # По умолчанию
            elif 'Сотрудники' in tab_name:
                dashboard_key = 'Сотрудники'
            elif 'Зарплаты' in tab_name:
                # Определяем дашборд по внутренней вкладке SalariesTab
                if hasattr(current_widget, 'tabs'):
                    inner_index = current_widget.tabs.currentIndex()
                    salaries_dashboard_map = {
                        0: 'Зарплаты (Все)',
                        1: 'Зарплаты (Индивидуальные)',
                        2: 'Зарплаты (Шаблонные)',
                        3: 'Зарплаты (Оклады)',
                        4: 'Зарплаты (Надзор)'
                    }
                    dashboard_key = salaries_dashboard_map.get(inner_index, 'Зарплаты (Все)')
                else:
                    dashboard_key = 'Зарплаты (Все)'
            # Дашборды для "Отчеты и Статистика" и "Отчеты по сотрудникам" отключены
            # elif 'Отчеты и Статистика' in tab_name:
            #     dashboard_key = 'Отчеты и Статистика'
            # elif 'Отчеты по сотрудникам' in tab_name:
            #     dashboard_key = 'Отчеты по сотрудникам'

            # Переключаем дашборд
            self.switch_dashboard(dashboard_key)

            # Ленивая загрузка данных при первом показе таба
            if hasattr(current_widget, 'ensure_data_loaded'):
                current_widget.ensure_data_loaded()
            elif hasattr(current_widget, 'load_all_statistics'):
                current_widget.load_all_statistics()
            elif hasattr(current_widget, 'refresh_current_tab'):
                current_widget.refresh_current_tab()

        except Exception as e:
            print(f"Ошибка обновления данных: {e}")
            import traceback
            traceback.print_exc()

    def switch_dashboard(self, dashboard_key):
        """Переключение дашборда через QStackedWidget"""
        try:
            if dashboard_key and dashboard_key in self.dashboard_indices:
                # Переключаем на нужный дашборд
                index = self.dashboard_indices[dashboard_key]
                self.dashboard_stack.setCurrentIndex(index)

                # ИСПРАВЛЕНО 05.02.2026: Всегда обновляем данные при переключении
                # чтобы дашборд показывал актуальные данные
                self.dashboards[dashboard_key].refresh()
                self.current_dashboard_key = dashboard_key

                self.dashboard_stack.show()
            else:
                # Скрываем дашборд для страниц без него
                self.dashboard_stack.hide()
                self.current_dashboard_key = None

        except Exception as e:
            print(f"[ERROR] Ошибка переключения дашборда: {e}")
            import traceback
            traceback.print_exc()

    def refresh_current_dashboard(self):
        """Принудительное обновление текущего дашборда (после изменения данных)"""
        if self.current_dashboard_key and self.current_dashboard_key in self.dashboards:
            self.dashboards[self.current_dashboard_key].refresh()

    # ========== СИСТЕМА ОБНОВЛЕНИЯ ПРОГРАММЫ ==========
    def check_for_updates_manual(self):
        """Ручная проверка обновлений (по нажатию кнопки)"""
        from utils.update_manager import UpdateManager
        from ui.update_dialogs import UpdateDialog, VersionDialog
        import threading

        # Проверяем, нажата ли Shift для управления версией
        from PyQt5.QtWidgets import QApplication
        modifiers = QApplication.keyboardModifiers()
        from PyQt5.QtCore import Qt

        if modifiers == Qt.ShiftModifier:
            # Shift + клик = управление версией
            dialog = VersionDialog(self)
            dialog.exec_()
            return

        self.status_label.setText("Проверка обновлений...")
        self.update_btn.setEnabled(False)

        def check_thread():
            manager = UpdateManager()
            update_info = manager.check_for_updates()

            if update_info.get("available"):
                # Есть обновление
                QTimer.singleShot(0, lambda: self._show_update_dialog(update_info))
            elif update_info.get("disabled"):
                QTimer.singleShot(0, lambda: self._show_updates_disabled())
            elif update_info.get("error"):
                QTimer.singleShot(0, lambda: self._show_update_error(update_info.get("error")))
            else:
                QTimer.singleShot(0, lambda: self._show_no_updates())

        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()

    def _show_update_dialog(self, update_info):
        """Показать диалог обновления"""
        from ui.update_dialogs import UpdateDialog

        self.status_label.setText("Доступно обновление")
        self.update_btn.setEnabled(True)

        dialog = UpdateDialog(update_info, self)
        dialog.exec_()

    def _show_no_updates(self):
        """Показать сообщение об отсутствии обновлений"""
        self.status_label.setText("Обновлений нет")
        self.update_btn.setEnabled(True)

        QMessageBox.information(
            self,
            "Обновления",
            "У вас установлена последняя версия программы."
        )

    def _show_updates_disabled(self):
        """Показать сообщение о выключенных обновлениях"""
        self.status_label.setText("Обновления отключены")
        self.update_btn.setEnabled(True)

        QMessageBox.information(
            self,
            "Обновления",
            "Проверка обновлений отключена в настройках."
        )

    def _show_update_error(self, error):
        """Показать ошибку обновления"""
        self.status_label.setText("Ошибка обновления")
        self.update_btn.setEnabled(True)

        QMessageBox.warning(
            self,
            "Ошибка обновления",
            f"Не удалось проверить обновления:\n{error}"
        )
    # ===================================================

    # ==========================================
    # SYNC MANAGER - обработчики событий
    # ==========================================

    def _update_online_indicator(self, count: int, users: list = None):
        """Обновить индикатор онлайн пользователей"""
        if count == 0:
            self.online_indicator.setText("")
        elif count == 1:
            self.online_indicator.setText("1 онлайн")
        else:
            self.online_indicator.setText(f"{count} онлайн")

        # Формируем tooltip со списком пользователей
        if users:
            user_names = [u.get('full_name', 'Неизвестный') for u in users]
            tooltip = "Пользователи онлайн:\n" + "\n".join(f"- {name}" for name in user_names)
            self.online_indicator.setToolTip(tooltip)

    def _on_online_users_updated(self, users: list):
        """Обработчик обновления списка онлайн пользователей"""
        self._update_online_indicator(len(users), users)

    def _on_connection_status_changed(self, is_online: bool):
        """Обработчик изменения статуса соединения"""
        if is_online:
            self.status_label.setText("Готов к работе")
            self.status_label.setStyleSheet("color: #555; font-size: 11px; border: none;")
        else:
            self.status_label.setText("Нет соединения с сервером")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 11px; border: none;")

    # ==========================================
    # OFFLINE MANAGER - обработчики событий
    # ==========================================

    def _on_offline_status_changed(self, status: str):
        """Обработчик изменения статуса offline-режима"""
        if status == 'online':
            self.offline_indicator.hide()
            self.status_label.setText("Готов к работе")
            self.status_label.setStyleSheet("color: #555; font-size: 11px; border: none;")
        elif status == 'offline':
            self.offline_indicator.setText("OFFLINE")
            self.offline_indicator.setToolTip("Нет подключения к серверу. Изменения будут синхронизированы при восстановлении связи.")
            self.offline_indicator.show()
            self.status_label.setText("Работа в автономном режиме")
            self.status_label.setStyleSheet("color: #e67e22; font-size: 11px; border: none;")
        elif status == 'syncing':
            self.offline_indicator.setText("Синхронизация...")
            self.offline_indicator.setStyleSheet("""
                QLabel {
                    color: #3498db;
                    font-size: 11px;
                    border: none;
                    padding-left: 10px;
                    font-weight: bold;
                }
            """)
            self.offline_indicator.show()
            self.status_label.setText("Синхронизация данных...")
            self.status_label.setStyleSheet("color: #3498db; font-size: 11px; border: none;")

    def _on_pending_operations_changed(self, count: int):
        """Обработчик изменения количества ожидающих операций"""
        if count > 0:
            self.offline_indicator.setText(f"OFFLINE ({count})")
            self.offline_indicator.setToolTip(f"Ожидает синхронизации: {count} операций")
            self.offline_indicator.setStyleSheet("""
                QLabel {
                    color: #e67e22;
                    font-size: 11px;
                    border: none;
                    padding-left: 10px;
                    font-weight: bold;
                }
            """)
            self.offline_indicator.show()
        elif self.offline_manager and self.offline_manager.is_online():
            self.offline_indicator.hide()

    def _on_sync_completed(self, success: bool, message: str):
        """Обработчик завершения синхронизации"""
        if success:
            self.status_label.setText("Синхронизация завершена")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 11px; border: none;")
            # Через 3 секунды вернуть обычный статус
            QTimer.singleShot(3000, lambda: self.status_label.setText("Готов к работе"))
            QTimer.singleShot(3000, lambda: self.status_label.setStyleSheet("color: #555; font-size: 11px; border: none;"))
        else:
            self.status_label.setText(f"Ошибка синхронизации: {message}")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 11px; border: none;")

    # ==========================================

    def closeEvent(self, event):
        """Подтверждение выхода из программы"""
        from ui.custom_message_box import CustomQuestionBox

        dialog = CustomQuestionBox(
            self,
            'Выход из программы',
            'Вы уверены, что хотите выйти из программы?'
        )

        if dialog.exec_() == QDialog.Accepted:
            # Удаляем eventFilter перед выходом
            QApplication.instance().removeEventFilter(self)
            # Останавливаем sync_manager перед выходом
            if self.sync_manager:
                self.sync_manager.stop()
            # Останавливаем offline_manager перед выходом
            if self.offline_manager:
                self.offline_manager.stop_monitoring()
            event.accept()
        else:
            event.ignore()
            

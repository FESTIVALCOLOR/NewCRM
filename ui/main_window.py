# -*- coding: utf-8 -*-
import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                             QHBoxLayout, QMenuBar, QAction, QMessageBox, QDialog,
                             QLabel, QStatusBar, QGridLayout, QGroupBox, QSizePolicy, QApplication)
from PyQt5.QtCore import Qt, QTimer, QRect, QSize
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
    def __init__(self, employee_data):
        super().__init__()
        self.employee = employee_data
        from database.db_manager import DatabaseManager
        self.db = DatabaseManager()
        
        # Переменные для resize
        self.resizing = False
        self.resize_edge = None
        self.resize_margin = 8

        # Переменные для Snap Assist
        self.snap_threshold = 10  # Порог прилипания в пикселях (уменьшен с 20 до 10)
        self.is_snapped = False
        self.snap_position = None  # 'left', 'right', 'top', 'maximized'
        self.restore_geometry = None  # Геометрия до snap
        
        self.init_ui()

        # ========== ПРИМЕНЯЕМ ГЛОБАЛЬНЫЙ СТИЛЬ КАЛЕНДАРЯ ==========
        from utils.calendar_styles import CALENDAR_STYLE

        # Получаем текущий стиль окна и добавляем стиль календаря
        current_style = self.styleSheet()
        self.setStyleSheet(current_style + "\n" + CALENDAR_STYLE)
        # ===========================================================
        
    def init_ui(self):
        self.setWindowTitle(f'FESTIVAL COLOR - {self.employee["full_name"]}')
        self.setMinimumSize(1400, 800)
        self.resize(1400, 800)
        
        # УБИРАЕМ СТАНДАРТНЫЙ TITLE BAR
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)  # Для border-radius

        # ========== УСТАНАВЛИВАЕМ ФОН ГЛАВНОГО ОКНА ==========
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0, 0))  # Прозрачный для border-radius
        self.setPalette(palette)
        # =====================================================

        # ========== ВКЛЮЧАЕМ ОТСЛЕЖИВАНИЕ НАВЕДЕНИЯ ==========
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)
        # ====================================================

        # ========== ГЛАВНЫЙ КОНТЕЙНЕР ==========
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

        # ========== КОНТЕЙНЕР С РАМКОЙ И СКРУГЛЕНИЕМ ==========
        from PyQt5.QtWidgets import QFrame
        border_frame = QFrame()
        border_frame.setObjectName("mainBorderFrame")
        border_frame.setStyleSheet("""
            QFrame#mainBorderFrame {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        container_layout.addWidget(border_frame)
        # ======================================================

        # ========== ВКЛЮЧАЕМ MOUSE TRACKING ДЛЯ BORDER FRAME ==========
        border_frame.setMouseTracking(True)
        border_frame.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        # ==============================================================

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        border_frame.setLayout(layout)
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        from ui.custom_title_bar import CustomTitleBar
        self.title_bar = CustomTitleBar(
            self,
            "FESTIVAL COLOR - Система управления заказами",
            simple_mode=False
        )
        # ========== СКРУГЛЯЕМ ВЕРХНИЕ УГЛЫ TITLE BAR ==========
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
        
        # Информационная панель (компактная)
        info_label = QLabel(f'{self.employee["full_name"]} · {self.employee["position"]}')
        info_label.setStyleSheet('''
            padding: 8px 15px; 
            background-color: #F8F9FA; 
            border-bottom: 0px solid #E0E0E0;
            font-size: 12px;
            color: #555;
            font-weight: 500;
        ''')
        layout.addWidget(info_label)
        
        # Вкладки
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #CCCCCC;
                background: white;
            }
            QTabBar::tab {
                background: #F5F5F5;
                border: 1px solid #CCCCCC;
                padding: 8px 28px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #E8F4F8;
                font-weight: bold;
            }
        """)

        # Блокируем переключение вкладок колесом мыши
        disable_wheel_on_tabwidget(self.tabs)

        # Добавление вкладок в соответствии с ролью
        self.setup_tabs()
        
        layout.addWidget(self.tabs)
        
        # ========== БЛОК СТАТИСТИКИ (6 КАРТОЧЕК В 1 РЯД) ==========
        stats_container = QWidget()
        stats_container.setObjectName('stats_container')
        stats_container.setStyleSheet('background-color: #FFFFFF; padding: 5px; border-bottom: 1px ')

        # СОЗДАЕМ GRIDLAYOUT
        stats_layout = QGridLayout()
        stats_layout.setSpacing(10)
        stats_layout.setContentsMargins(10, 0, 10, 10)

        # ВСЕ 6 КАРТОЧЕК В ОДИН РЯД (row=0)
        individual_orders_card = self.create_simple_stat_card(
            'individual_orders',
            'Всего заказов индивидуальных',
            '0',
            'resources/icons/clipboard1.svg',
            '#ffffff',
            '#F57C00'
        )
        stats_layout.addWidget(individual_orders_card, 0, 0)

        template_orders_card = self.create_simple_stat_card(
            'individual_area',
            'Всего площадь индивидуальных',
            '0 м²',
            'resources/icons/codepen1.svg',
            '#ffffff',
            '#F57C00'
        )
        stats_layout.addWidget(template_orders_card, 0, 1)

        supervision_orders_card = self.create_simple_stat_card(
            'template_orders',
            'Всего заказов шаблонных',
            '0',
            'resources/icons/clipboard2.svg',
            '#ffffff',
            '#C62828'

        )
        stats_layout.addWidget(supervision_orders_card, 0, 2)

        individual_area_card = self.create_simple_stat_card(
            'template_area',
            'Всего площадь шаблонных',
            '0 м²',
            'resources/icons/codepen2.svg',
            '#ffffff',
            '#C62828'
        )
        stats_layout.addWidget(individual_area_card, 0, 3)

        template_area_card = self.create_simple_stat_card(
            'supervision_orders',
            'Всего заказов авторского надзора',
            '0',
            'resources/icons/clipboard3.svg',
            '#ffffff',
            '#388E3C'
        )
        stats_layout.addWidget(template_area_card, 0, 4)

        supervision_area_card = self.create_simple_stat_card(
            'supervision_area',
            'Всего площадь авторского надзора',
            '0 м²',
            'resources/icons/codepen3.svg',
            '#ffffff',
            '#388E3C'
        )
        stats_layout.addWidget(supervision_area_card, 0, 5)

        # Растягиваем колонки
        for col in range(6):
            stats_layout.setColumnStretch(col, 1)

        stats_container.setLayout(stats_layout)
        layout.addWidget(stats_container)
        # ======================================================

        # ========== КАСТОМНЫЙ СТАТУС-БАР С ВЕРСИЕЙ ==========
        from PyQt5.QtWidgets import QPushButton
        from PyQt5.QtGui import QIcon
        from config import APP_VERSION

        status_bar_container = QWidget()
        status_bar_layout = QHBoxLayout()
        status_bar_layout.setContentsMargins(10, 5, 10, 5)
        status_bar_layout.setSpacing(10)
        status_bar_container.setLayout(status_bar_layout)

        # Левая часть - статус
        self.status_label = QLabel('Готово к работе')
        self.status_label.setStyleSheet("color: #555; font-size: 11px;")
        status_bar_layout.addWidget(self.status_label)

        status_bar_layout.addStretch()

        # Правая часть - версия и кнопка обновления
        self.version_label = QLabel(f'Версия: {APP_VERSION}')
        self.version_label.setStyleSheet("color: #555; font-size: 11px;")
        status_bar_layout.addWidget(self.version_label)

        # Кнопка "обновить" (видна только руководителю студии)
        if self.employee.get('position') == 'Руководитель студии':
            from utils.resource_path import resource_path
            self.update_btn = QPushButton()

            # Получаем путь к иконке через resource_path
            icon_path = resource_path('resources/icons/refresh.svg')

            if os.path.exists(icon_path):
                self.update_btn.setIcon(QIcon(icon_path))

            self.update_btn.setFixedSize(24, 24)
            self.update_btn.setToolTip("Проверить обновления")
            self.update_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #E0E0E0;
                }
            """)
            self.update_btn.clicked.connect(self.check_for_updates_manual)
            status_bar_layout.addWidget(self.update_btn)

        # Применяем стиль к контейнеру
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

        # ========== УБИРАЕМ СТАНДАРТНЫЙ СТАТУС-БАР ==========
        self.setStatusBar(None)
        # ====================================================

        # ========== ЗАГРУЗКА СТАТИСТИКИ ==========
        QTimer.singleShot(100, self.load_dashboard_statistics)
        # =========================================
        
    def get_resize_edge(self, pos):
        """Определение края/угла для изменения размера"""
        rect = self.rect()
        margin = self.resize_margin
        
        on_left = pos.x() <= margin
        on_right = pos.x() >= rect.width() - margin
        on_top = pos.y() <= margin
        on_bottom = pos.y() >= rect.height() - margin
        
        # Углы (приоритет)
        if on_top and on_left:
            return 'top-left'
        elif on_top and on_right:
            return 'top-right'
        elif on_bottom and on_left:
            return 'bottom-left'
        elif on_bottom and on_right:
            return 'bottom-right'
        
        # Края
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
        """Установка формы курсора"""
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
        """Прилипание окна к краю экрана при перетаскивании"""
        screen = QApplication.desktop().availableGeometry(self)

        # Если окно уже прилипло и двигается достаточно далеко от края - восстанавливаем
        restore_threshold = 50  # Больший порог для восстановления
        should_restore = False

        if self.is_snapped:
            if self.snap_position == 'maximized':
                # Если двигаем вниз от верхнего края
                if pos.y() > screen.y() + restore_threshold:
                    should_restore = True
                    # Для maximized: центрируем окно под курсором при восстановлении
                    if self.restore_geometry:
                        # Восстанавливаем минимальный размер ПЕРЕД изменением геометрии
                        self.setMinimumSize(1400, 800)

                        # Вычисляем новую позицию так, чтобы курсор был в центре title bar
                        new_x = pos.x() - self.restore_geometry.width() // 2
                        new_y = pos.y() - 20  # 20px - примерно середина title bar

                        # ВАЖНО: Используем setGeometry для одновременной установки размера и позиции
                        self.setGeometry(new_x, new_y, self.restore_geometry.width(), self.restore_geometry.height())

                        self.is_snapped = False
                        self.snap_position = None
                        self.restore_geometry = None
                        return
            elif self.snap_position == 'left':
                # Если двигаем вправо от левого края
                if pos.x() > screen.x() + restore_threshold:
                    should_restore = True
            elif self.snap_position == 'right':
                # Если двигаем влево от правого края
                if pos.x() < screen.x() + screen.width() - restore_threshold:
                    should_restore = True

            # Для боковых snap - просто восстанавливаем геометрию
            if should_restore and self.restore_geometry and self.snap_position in ['left', 'right']:
                self.setGeometry(self.restore_geometry)
                # Восстанавливаем минимальный размер
                self.setMinimumSize(1400, 800)
                self.is_snapped = False
                self.snap_position = None
                self.restore_geometry = None
                return

        # Проверяем прилипание к верхнему краю (максимизация)
        if pos.y() <= screen.y() + self.snap_threshold:
            if not self.is_snapped or self.snap_position != 'maximized':
                self.restore_geometry = self.geometry()
                self.is_snapped = True
                self.snap_position = 'maximized'
                # Не применяем геометрию сразу, ждем mouseReleaseEvent

        # Проверяем прилипание к левому краю
        elif pos.x() <= screen.x() + self.snap_threshold:
            if not self.is_snapped or self.snap_position != 'left':
                self.restore_geometry = self.geometry()
                self.is_snapped = True
                self.snap_position = 'left'

        # Проверяем прилипание к правому краю (ИСПРАВЛЕНО: учитываем screen.x())
        elif pos.x() >= screen.x() + screen.width() - self.snap_threshold:
            if not self.is_snapped or self.snap_position != 'right':
                self.restore_geometry = self.geometry()
                self.is_snapped = True
                self.snap_position = 'right'
        else:
            # Если не у края - сбрасываем snap
            if self.is_snapped:
                self.is_snapped = False
                self.snap_position = None

    def apply_snap(self):
        """Применение прилипания после отпускания мыши"""
        if not self.is_snapped or not self.snap_position:
            # Восстанавливаем обычный курсор
            self.setCursor(Qt.ArrowCursor)
            return

        screen = QApplication.desktop().availableGeometry(self)

        # КРИТИЧНО: Полностью снимаем ограничения размера для Snap Assist
        self.setMinimumSize(1, 1)
        self.setMaximumSize(16777215, 16777215)  # Максимум Qt

        if self.snap_position == 'maximized':
            # Развернуть на весь экран
            self.setGeometry(screen)

        elif self.snap_position == 'left':
            # Половина экрана слева
            half_width = screen.width() // 2
            self.setGeometry(screen.x(), screen.y(), half_width, screen.height())

        elif self.snap_position == 'right':
            # Половина экрана справа
            half_width = screen.width() // 2
            self.setGeometry(screen.x() + half_width, screen.y(), half_width, screen.height())

        # Восстанавливаем обычный курсор после применения snap
        self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        """Начало изменения размера"""
        if event.button() == Qt.LeftButton:
            # ВАЖНО: Если окно maximized, выходим из этого режима при попытке resize
            if self.isMaximized():
                self.showNormal()

            edge = self.get_resize_edge(event.pos())

            if edge:
                self.resizing = True
                self.resize_edge = edge
                self.resize_start_pos = event.globalPos()
                self.resize_start_geometry = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)

    def event(self, event):
        """Обработка событий наведения мыши"""
        if event.type() == event.HoverMove:
            # Изменяем курсор при наведении (без нажатия)
            # Показываем курсор resize даже если окно maximized (чтобы пользователь видел возможность изменить размер)
            if not self.resizing:
                edge = self.get_resize_edge(event.pos())
                self.set_cursor_shape(edge)

        return super().event(event)

    def mouseMoveEvent(self, event):
        """Процесс изменения размера"""
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
            self.resizing = False
            self.resize_edge = None
            self.setCursor(Qt.ArrowCursor)

            # ВАЖНО: Сбрасываем snap состояние при ручном resize
            # Это позволяет уменьшать окно после Snap Assist
            self.is_snapped = False
            self.snap_position = None
            self.restore_geometry = None

            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Двойной клик - возврат к размеру по умолчанию (1400x800)"""
        if event.button() == Qt.LeftButton:
            # ВСЕГДА возвращаем к размеру по умолчанию, центрируем на экране
            # Сбрасываем состояние snap
            self.is_snapped = False
            self.snap_position = None
            self.restore_geometry = None

            # Центрируем окно с размером по умолчанию
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
        """Создание простой карточки статистики с иконкой из файла"""
        from utils.resource_path import resource_path

        card = QGroupBox()
        card.setObjectName(object_name)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setFixedHeight(110)

        # РАМКА 1px (вместо 2px)
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
        layout.setSpacing(12)
        layout.setContentsMargins(0, 2, 0, 2)

        # Иконка слева (SVG из файла или fallback на эмодзи)
        full_icon_path = resource_path(icon_path)
        if os.path.exists(full_icon_path):
            icon_widget = QSvgWidget(full_icon_path)
            icon_widget.setFixedSize(60, 60)
            layout.addWidget(icon_widget)
        else:
            # Fallback на эмодзи
            fallback_icons = {
                'clipboard1.svg': '📐',
                'clipboard2.svg': '📋',
                'clipboard3.svg': '🏗️',
                'codepen1.svg': '📏',
                'codepen2.svg': '📐',
                'codepen3.svg': '🏢'
            }
            icon_name = os.path.basename(icon_path)
            emoji = fallback_icons.get(icon_name, '📊')
            
            icon_label = QLabel(emoji)
            icon_label.setStyleSheet('font-size: 40px; background-color: transparent;')
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setFixedWidth(50)
            layout.addWidget(icon_label)
        
        # Данные справа (РАСШИРЕННЫЕ ПОЛЯ)
        data_layout = QVBoxLayout()
        data_layout.setSpacing(2)
        data_layout.setAlignment(Qt.AlignVCenter)
        
        # Название (с переносом строк)
        title_label = QLabel(title)
        title_label.setStyleSheet(f'''
            font-size: 11px; 
            color: {border_color}; 
            font-weight: 600; 
            background-color: transparent;
        ''')
        title_label.setWordWrap(True)  # ← Включаем перенос
        title_label.setMinimumWidth(50)  # ← Расширяем поле
        data_layout.addWidget(title_label)
        
        # Значение (КРУПНО)
        value_label = QLabel(value)
        value_label.setObjectName('value')
        value_label.setStyleSheet('''
            font-size: 28px; 
            font-weight: bold; 
            color: #2C3E50; 
            background-color: transparent;
        ''')
        value_label.setWordWrap(False)
        value_label.setMinimumWidth(150)  # ← Расширяем поле
        data_layout.addWidget(value_label)
        
        layout.addLayout(data_layout, 1)
        
        card.setLayout(layout)
        return card

    def create_compact_stat_card(self, object_name, title, orders_value, area_value, icon, bg_color, border_color):
        """Создание компактной карточки статистики (старый метод)"""
        
        card = QGroupBox()
        card.setObjectName(object_name)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setFixedHeight(120)
        
        card.setStyleSheet(f"""
            QGroupBox {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 12px;
            }}
            QGroupBox:hover {{
                border: 2px solid {border_color};
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(12, 10, 12, 10)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet('font-size: 48px; background-color: transparent;')
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedWidth(60)
        layout.addWidget(icon_label)
        
        data_layout = QVBoxLayout()
        data_layout.setSpacing(5)
        data_layout.setAlignment(Qt.AlignVCenter)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f'''
            font-size: 12px; 
            color: {border_color}; 
            font-weight: bold; 
            background-color: transparent;
        ''')
        title_label.setWordWrap(False)
        data_layout.addWidget(title_label)
        
        orders_label = QLabel(f'Заказов: {orders_value}')
        orders_label.setObjectName('orders_value')
        orders_label.setStyleSheet('''
            font-size: 20px; 
            font-weight: bold; 
            color: #2C3E50; 
            background-color: transparent;
        ''')
        orders_label.setWordWrap(False)
        data_layout.addWidget(orders_label)
        
        area_label = QLabel(f'Площадь: {area_value}')
        area_label.setObjectName('area_value')
        area_label.setStyleSheet('''
            font-size: 13px; 
            color: #7F8C8D; 
            font-weight: 500; 
            background-color: transparent;
        ''')
        area_label.setWordWrap(False)
        data_layout.addWidget(area_label)
        
        layout.addLayout(data_layout, 1)
        
        card.setLayout(layout)
        return card
    
    def load_dashboard_statistics(self):
        """Загрузка статистики для dashboard"""
        try:
            stats = self.db.get_dashboard_statistics()
            
            # ========== ОБНОВЛЯЕМ ЗАКАЗЫ ==========
            individual_orders = self.findChild(QGroupBox, 'individual_orders')
            if individual_orders:
                individual_orders.findChild(QLabel, 'value').setText(str(stats['individual_orders']))
            
            template_orders = self.findChild(QGroupBox, 'template_orders')
            if template_orders:
                template_orders.findChild(QLabel, 'value').setText(str(stats['template_orders']))
            
            supervision_orders = self.findChild(QGroupBox, 'supervision_orders')
            if supervision_orders:
                supervision_orders.findChild(QLabel, 'value').setText(str(stats['supervision_orders']))
            
            individual_area = self.findChild(QGroupBox, 'individual_area')
            if individual_area:
                individual_area.findChild(QLabel, 'value').setText(f"{stats['individual_area']:,.0f} м²")
            
            template_area = self.findChild(QGroupBox, 'template_area')
            if template_area:
                template_area.findChild(QLabel, 'value').setText(f"{stats['template_area']:,.0f} м²")
            
            supervision_area = self.findChild(QGroupBox, 'supervision_area')
            if supervision_area:
                supervision_area.findChild(QLabel, 'value').setText(f"{stats['supervision_area']:,.0f} м²")
            
            print("✓ Статистика dashboard обновлена")
            print(f"  Индивидуальные: {stats['individual_orders']} ({stats['individual_area']:.0f} м²)")
            print(f"  Шаблонные: {stats['template_orders']} ({stats['template_area']:.0f} м²)")
            print(f"  Надзор: {stats['supervision_orders']} ({stats['supervision_area']:.0f} м²)")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки статистики: {e}")
            import traceback
            traceback.print_exc()
            
    def setup_tabs(self):
        """Настройка вкладок с подключением обновлений"""
        
        # ========== ПОЛУЧАЕМ ОБЯЗАННОСТИ ==========
        position = self.employee.get('position', 'Дизайнер')
        secondary_position = self.employee.get('secondary_position', '')
        
        # Получаем права основной должности
        allowed_tabs = set(ROLES.get(position, {}).get('tabs', []))
        can_edit = ROLES.get(position, {}).get('can_edit', False)
        
        # ========== ОБЪЕДИНЯЕМ ПРАВА ДОПОЛНИТЕЛЬНОЙ ДОЛЖНОСТИ ==========
        if secondary_position:
            secondary_tabs = set(ROLES.get(secondary_position, {}).get('tabs', []))
            allowed_tabs = allowed_tabs.union(secondary_tabs)  # Объединяем
            
            # Если хотя бы одна должность дает can_edit - предоставляем
            secondary_can_edit = ROLES.get(secondary_position, {}).get('can_edit', False)
            can_edit = can_edit or secondary_can_edit
        # ================================================================
        
        print(f"\n🔐 ПРОВЕРКА ДОСТУПА:")
        print(f"   Сотрудник: {self.employee['full_name']}")
        print(f"   Основная должность: {position}")
        if secondary_position:
            print(f"   Дополнительная должность: {secondary_position}")
        print(f"   Разрешенные вкладки: {sorted(allowed_tabs)}")
        print(f"   Права редактирования: {can_edit}\n")
        
        # Добавляем вкладки
        if 'Клиенты' in allowed_tabs:
            self.tabs.addTab(ClientsTab(self.employee), '  Клиенты  ')
        
        if 'Договора' in allowed_tabs:
            self.tabs.addTab(ContractsTab(self.employee), '  Договора  ')
        
        if 'СРМ' in allowed_tabs:
            self.tabs.addTab(CRMTab(self.employee, can_edit), '  СРМ  ')
        
        if 'СРМ надзора' in allowed_tabs:
            self.tabs.addTab(CRMSupervisionTab(self.employee), '  СРМ надзора  ')
        
        if 'Отчеты и Статистика' in allowed_tabs:
            self.tabs.addTab(ReportsTab(self.employee), '  Отчеты и Статистика  ')
        
        if 'Сотрудники' in allowed_tabs:
            self.tabs.addTab(EmployeesTab(self.employee), '  Сотрудники  ')
        
        if 'Зарплаты' in allowed_tabs:
            self.tabs.addTab(SalariesTab(self.employee), '  Зарплаты  ')
        
        if 'Отчеты по сотрудникам' in allowed_tabs:
            self.tabs.addTab(EmployeeReportsTab(self.employee), '  Отчеты по сотрудникам  ')
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
    def on_tab_changed(self, index):
        """Обновление данных + скрытие/показ dashboard"""
        try:
            current_widget = self.tabs.widget(index)
            tab_name = self.tabs.tabText(index).strip()
            
            # ========== СКРЫВАЕМ DASHBOARD НА ВКЛАДКЕ "ОТЧЕТЫ" ==========
            stats_container = self.findChild(QWidget, 'stats_container')  # Нужно добавить objectName
            if stats_container:
                if 'Отчеты и Статистика' in tab_name:
                    stats_container.hide()
                    print("📊 Dashboard скрыт (вкладка Reports)")
                else:
                    stats_container.show()
                    print("📊 Dashboard показан")
            # =============================================================
            
            # Обновляем данные
            self.load_dashboard_statistics()
            
            if hasattr(current_widget, 'load_all_statistics'):
                current_widget.load_all_statistics()
            elif hasattr(current_widget, 'refresh_current_tab'):
                current_widget.refresh_current_tab()
            
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")

    # ========== МЕТОДЫ ДЛЯ СИСТЕМЫ ОБНОВЛЕНИЙ ==========
    def check_for_updates_manual(self):
        """Ручная проверка обновлений (кнопка в статус-баре)"""
        from utils.update_manager import UpdateManager
        from ui.update_dialogs import UpdateDialog, VersionDialog
        import threading

        # Проверяем, нажата ли клавиша Shift для диалога изменения версии
        from PyQt5.QtWidgets import QApplication
        modifiers = QApplication.keyboardModifiers()
        from PyQt5.QtCore import Qt

        if modifiers == Qt.ShiftModifier:
            # Shift + клик = диалог изменения версии
            dialog = VersionDialog(self)
            dialog.exec_()
            return

        self.status_label.setText("Проверка обновлений...")
        self.update_btn.setEnabled(False)

        def check_thread():
            manager = UpdateManager()
            update_info = manager.check_for_updates()

            if update_info.get("available"):
                # Показать диалог обновления
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

        self.status_label.setText("Готово к работе")
        self.update_btn.setEnabled(True)

        dialog = UpdateDialog(update_info, self)
        dialog.exec_()

    def _show_no_updates(self):
        """Показать сообщение об отсутствии обновлений"""
        self.status_label.setText("Готово к работе")
        self.update_btn.setEnabled(True)

        QMessageBox.information(
            self,
            "Обновления",
            "У вас установлена последняя версия программы."
        )

    def _show_updates_disabled(self):
        """Показать сообщение о отключенных обновлениях"""
        self.status_label.setText("Готово к работе")
        self.update_btn.setEnabled(True)

        QMessageBox.information(
            self,
            "Обновления",
            "Проверка обновлений отключена в настройках."
        )

    def _show_update_error(self, error):
        """Показать ошибку проверки обновлений"""
        self.status_label.setText("Готово к работе")
        self.update_btn.setEnabled(True)

        QMessageBox.warning(
            self,
            "Ошибка проверки обновлений",
            f"Не удалось проверить наличие обновлений:\n{error}"
        )
    # ===================================================

    def closeEvent(self, event):
        """ИСПРАВЛЕНИЕ: Обработка закрытия окна с кастомным диалогом"""
        from ui.custom_message_box import CustomQuestionBox

        dialog = CustomQuestionBox(
            self,
            'Выход',
            'Вы уверены, что хотите выйти из программы?'
        )

        if dialog.exec_() == QDialog.Accepted:
            event.accept()
        else:
            event.ignore()
            

# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel

from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtGui import QPixmap, QIcon
from utils.resource_path import resource_path
import os

class CustomTitleBar(QWidget):
    """Кастомный title bar с двумя режимами"""
    
    def __init__(self, parent, title="", simple_mode=False):
        """
        Args:
            parent: родительское окно
            title: заголовок окна
            simple_mode: True - только кнопка закрытия (для login_window)
                        False - полный функционал (для main_window)
        """
        super().__init__(parent)
        self.parent_window = parent
        self.title_text = title
        self.simple_mode = simple_mode
        self.start_pos = None
        self.resize_margin = 8  # ← ДОБАВЛЕНО: отступ для зоны resize
        self.init_ui()
        
    def init_ui(self):
        self.setFixedHeight(45)
        self.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 6, 6, 0)
        layout.setSpacing(10)
        
        # ========== РЕЖИМ 1: ПОЛНЫЙ (для main_window) ==========
        if not self.simple_mode:
            # ЛОГОТИП (мини)
            logo_label = QLabel()
            logo_pixmap = QPixmap(resource_path('resources/logo.png'))
            if not logo_pixmap.isNull():
                scaled_logo = logo_pixmap.scaledToHeight(24, Qt.SmoothTransformation)
                logo_label.setPixmap(scaled_logo)
            else:
                logo_label.setText('FC')
                logo_label.setStyleSheet('''
                    font-size: 12px; 
                    font-weight: bold; 
                    color: #FF9800;
                    background-color: transparent;
                ''')
            layout.addWidget(logo_label)
            
            # НАЗВАНИЕ ОКНА
            title_label = QLabel(self.title_text)
            title_label.setStyleSheet("""
                font-size: 12px;
                color: #333333;
                font-weight: 500;
                background-color: transparent;
            """)
            layout.addWidget(title_label)
        
        layout.addStretch()
        
        # ========== РЕЖИМ 2: ПРОСТОЙ (для login_window) ==========
        if self.simple_mode:
            # ТОЛЬКО КНОПКА ЗАКРЫТИЯ
            self.close_btn = QPushButton()
            self.close_btn.setIcon(self.load_svg_icon('close.svg'))
            self.close_btn.setIconSize(QSize(16, 16))
            self.close_btn.setFixedSize(40, 40)
            self.close_btn.setStyleSheet(self.close_button_style())
            self.close_btn.clicked.connect(self.parent_window.close)
            self.close_btn.setToolTip('Закрыть')
            layout.addWidget(self.close_btn)
        # ========== РЕЖИМ 1: ПОЛНЫЙ (три кнопки) ==========
        else:
            # Кнопка "Свернуть"
            self.minimize_btn = QPushButton()
            self.minimize_btn.setIcon(self.load_svg_icon('minimize.svg'))
            self.minimize_btn.setIconSize(QSize(16, 16))
            self.minimize_btn.setFixedSize(40, 40)
            self.minimize_btn.setStyleSheet(self.button_style())
            self.minimize_btn.clicked.connect(self.parent_window.showMinimized)
            self.minimize_btn.setToolTip('Свернуть')
            layout.addWidget(self.minimize_btn)
            
            # Кнопка "Развернуть/Восстановить"
            self.maximize_btn = QPushButton()
            self.maximize_btn.setIcon(self.load_svg_icon('maximize.svg'))
            self.maximize_btn.setIconSize(QSize(16, 16))
            self.maximize_btn.setFixedSize(40, 40)
            self.maximize_btn.setStyleSheet(self.button_style())
            self.maximize_btn.clicked.connect(self.toggle_maximize)
            self.maximize_btn.setToolTip('Развернуть/Восстановить')
            layout.addWidget(self.maximize_btn)
            
            # Кнопка "Закрыть"
            self.close_btn = QPushButton()
            self.close_btn.setIcon(self.load_svg_icon('close.svg'))
            self.close_btn.setIconSize(QSize(16, 16))
            self.close_btn.setFixedSize(40, 40)
            self.close_btn.setStyleSheet(self.close_button_style())
            self.close_btn.clicked.connect(self.parent_window.close)
            self.close_btn.setToolTip('Закрыть')
            layout.addWidget(self.close_btn)
        
        self.setLayout(layout)
    
    def load_svg_icon(self, icon_name):
        """Загрузка SVG иконки"""
        icon_path = resource_path(f'resources/icons/{icon_name}')
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        else:
            print(f"[WARN] SVG не найден: {icon_path}")
            return QIcon()
    
    def button_style(self):
        """Стиль для кнопок минимизации/максимизации"""
        return """
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
                border-radius: 4px;
            }
        """
    
    def close_button_style(self):
        """Стиль для кнопки закрытия"""
        return """
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #E74C3C;
                border-radius: 4px;
            }
        """
    
    def toggle_maximize(self):
        """Переключение развернуть/восстановить (только в полном режиме)"""
        if not self.simple_mode:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
            else:
                self.parent_window.showMaximized()
    
    # ========== ДОБАВЛЕНА ПРОВЕРКА ЗОНЫ RESIZE ==========
    def is_in_resize_zone(self, pos):
        """Проверка, находится ли курсор в зоне изменения размера"""
        # Конвертируем локальные координаты title bar в координаты главного окна
        global_pos = self.mapToGlobal(pos)
        window_pos = self.parent_window.mapFromGlobal(global_pos)
        
        rect = self.parent_window.rect()
        margin = self.resize_margin
        
        # Проверяем ТОЛЬКО верхние углы и верхний край
        on_left = window_pos.x() <= margin
        on_right = window_pos.x() >= rect.width() - margin
        on_top = window_pos.y() <= margin
        
        if on_top or (on_top and on_left) or (on_top and on_right):
            return True
        
        return False
    # ====================================================
    
    def mousePressEvent(self, event):
        """Захват позиции для перетаскивания окна"""
        if event.button() == Qt.LeftButton:
            # ========== ДОБАВЛЕНА ПРОВЕРКА ==========
            if self.is_in_resize_zone(event.pos()):
                event.ignore()  # Пропускаем событие в main_window
                return
            # ========================================

            self.start_pos = event.globalPos() - self.parent_window.frameGeometry().topLeft()
            # ВАЖНО: Захватываем мышь чтобы получать события даже если курсор уходит за границы виджета
            self.grabMouse()
            event.accept()

    def mouseMoveEvent(self, event):
        """Перетаскивание окна"""
        # ВАЖНО: НЕ проверяем is_in_resize_zone здесь, потому что при быстром движении
        # курсор может выйти за пределы title bar, но перетаскивание должно продолжаться
        # Проверка нужна только в mousePressEvent для начала перетаскивания

        if event.buttons() == Qt.LeftButton and self.start_pos:
            # Нельзя перетаскивать развернутое окно (только в полном режиме)
            if not self.simple_mode and self.parent_window.isMaximized():
                return

            # Перемещаем окно
            self.parent_window.move(event.globalPos() - self.start_pos)

            # Вызываем Snap Assist только если это MainWindow (у него есть метод snap_to_edge)
            if hasattr(self.parent_window, 'snap_to_edge'):
                self.parent_window.snap_to_edge(event.globalPos())

            event.accept()

    def mouseReleaseEvent(self, event):
        """Отпускание кнопки мыши - применяем snap"""
        if event.button() == Qt.LeftButton and self.start_pos:
            # ВАЖНО: Освобождаем захват мыши
            self.releaseMouse()
            # Применяем прилипание если оно было активировано (только для MainWindow)
            if hasattr(self.parent_window, 'apply_snap'):
                self.parent_window.apply_snap()
            self.start_pos = None
            event.accept()
    
    def mouseDoubleClickEvent(self, event):
        """Двойной клик - развернуть/восстановить (только в полном режиме)"""
        if event.button() == Qt.LeftButton and not self.simple_mode:
            # ========== ДОБАВЛЕНА ПРОВЕРКА ==========
            if self.is_in_resize_zone(event.pos()):
                event.ignore()
                return
            # ========================================
            
            self.toggle_maximize()
            event.accept()

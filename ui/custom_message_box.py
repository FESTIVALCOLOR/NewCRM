# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QFrame

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class CustomMessageBox(QDialog):
    """Кастомное окно сообщения в стиле приложения"""
    
    def __init__(self, parent, title, message, icon_type='warning'):
        """
        Args:
            parent: родительское окно
            title: заголовок диалога
            message: текст сообщения
            icon_type: 'warning', 'error', 'success', 'info'
        """
        super().__init__(parent)
        
        # Без стандартной рамки
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.init_ui(title, message, icon_type)
    
    def init_ui(self, title, message, icon_type):
        # ========== ГЛАВНЫЙ LAYOUT ==========
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== КОНТЕЙНЕР С РАМКОЙ  ==========
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        from ui.custom_title_bar import CustomTitleBar
        title_bar = CustomTitleBar(self, title, simple_mode=True)
        
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        
        border_layout.addWidget(title_bar)
        
        # ========== КОНТЕЙНЕР ДЛЯ КОНТЕНТА ==========
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        
        # ИСПРАВЛЕНИЕ: Уменьшены размеры на 30%
        content_layout = QVBoxLayout()
        content_layout.setSpacing(14)  # было 20
        content_layout.setContentsMargins(28, 14, 28, 28)  # было 40, 20, 40, 40

        # ===== ИКОНКА =====
        icon_label = QLabel()

        if icon_type == 'warning':
            icon_text = 'ВНИМАНИЕ'
            bg_color = '#FFF3CD'
        elif icon_type == 'error':
            icon_text = 'ОШИБКА'
            bg_color = '#FADBD8'
        elif icon_type == 'success':
            icon_text = 'УСПЕХ'
            bg_color = '#D5F4E6'
        else:  # info
            icon_text = 'ИНФО'
            bg_color = '#E8F4F8'

        icon_label.setText(icon_text)
        icon_label.setStyleSheet('font-size: 14px; font-weight: bold; background-color: transparent; padding: 5px;')
        icon_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(icon_label)

        # ========== СООБЩЕНИЕ ==========
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setStyleSheet(f'''
            font-size: 11px;
            color: #333;
            line-height: 1.6;
            padding: 10px;
            background-color: {bg_color};
            border-radius: 6px;
        ''')
        content_layout.addWidget(message_label)

        content_layout.addSpacing(7)  # было 10

        # ========== КНОПКА OK ==========
        ok_btn = QPushButton('OK')
        ok_btn.setFixedHeight(35)  # было 50
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #333333;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #F8F9FA;
                border-color: #999999;
            }
            QPushButton:pressed {
                background-color: #E8E9EA;
                border-color: #666666;
            }
        """)
        ok_btn.clicked.connect(self.accept)
        ok_btn.setCursor(Qt.PointingHandCursor)
        content_layout.addWidget(ok_btn)

        content_widget.setLayout(content_layout)

        border_layout.addWidget(content_widget)
        border_frame.setLayout(border_layout)

        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        self.setMinimumWidth(280)  # было 400
    
    def showEvent(self, event):
        """Центрирование при первом показе окна"""
        super().showEvent(event)

        if not hasattr(self, '_centered'):
            self._centered = True
            from utils.dialog_helpers import center_dialog_on_parent
            center_dialog_on_parent(self)


# ========== КЛАСС ДЛЯ ВОПРОСОВ (YES/NO) ==========
class CustomQuestionBox(QDialog):
    """Кастомное окно вопроса с кнопками Да/Нет"""
    
    def __init__(self, parent, title, message):
        super().__init__(parent)
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.init_ui(title, message)
    
    def init_ui(self, title, message):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        from ui.custom_title_bar import CustomTitleBar
        title_bar = CustomTitleBar(self, title, simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)
        
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        
        # ИСПРАВЛЕНИЕ: Убрана иконка вопроса, уменьшены размеры на 30%
        content_layout = QVBoxLayout()
        content_layout.setSpacing(14)  # было 20
        content_layout.setContentsMargins(28, 20, 28, 28)  # было 40, 20, 40, 40

        # ИСПРАВЛЕНИЕ: Убрана иконка вопроса (❓)

        # Сообщение
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setStyleSheet('''
            font-size: 11px;
            color: #333;
            line-height: 1.6;
            padding: 10px;
            background-color: #E8F4F8;
            border-radius: 6px;
        ''')
        content_layout.addWidget(message_label)

        content_layout.addSpacing(7)  # было 10

        # Кнопки ДА/НЕТ
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(7)  # было 10

        yes_btn = QPushButton('Да')
        yes_btn.setFixedHeight(35)  # было 50
        yes_btn.setMinimumWidth(84)  # было 120
        yes_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1E8449;
            }
        """)
        yes_btn.clicked.connect(self.accept)
        yes_btn.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(yes_btn)

        no_btn = QPushButton('Нет')
        no_btn.setFixedHeight(35)  # было 50
        no_btn.setMinimumWidth(84)  # было 120
        no_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #7F8C8D;
            }
            QPushButton:pressed {
                background-color: #626D71;
            }
        """)
        no_btn.clicked.connect(self.reject)
        no_btn.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(no_btn)

        content_layout.addLayout(buttons_layout)

        content_widget.setLayout(content_layout)
        border_layout.addWidget(content_widget)

        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        self.setMinimumWidth(315)  # было 450
    
    def showEvent(self, event):
        """Центрирование при первом показе окна"""
        super().showEvent(event)

        if not hasattr(self, '_centered'):
            self._centered = True
            from utils.dialog_helpers import center_dialog_on_parent
            center_dialog_on_parent(self)

# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QDialog, QFrame,
                             QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QColor
from PyQt5.QtWidgets import QTabWidget
from database.db_manager import DatabaseManager
from ui.main_window import MainWindow
from ui.custom_message_box import CustomMessageBox
from utils.resource_path import resource_path

# ========== ЛОГИРОВАНИЕ ==========
from utils.logger import log_auth_attempt, app_logger
# =================================

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.main_window = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('Festival Color - Вход')
        self.setFixedSize(400, 580)
        
        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)  # Для border-radius
        # ===============================================
        
        # ========== ГЛАВНЫЙ LAYOUT ==========
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        # ====================================
        
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
        
        # ================================================
        
        # Layout для контейнера
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        from ui.custom_title_bar import CustomTitleBar
        title_bar = CustomTitleBar(self, "", simple_mode=True)
        
        # ========== СКРУГЛЯЕМ ВЕРХНИЕ УГЛЫ TITLE BAR ==========
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        # ======================================================
        
        border_layout.addWidget(title_bar)
        # =========================================
        
        # ========== КОНТЕЙНЕР ДЛЯ КОНТЕНТА ==========
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(40, 20, 40, 40)
        # ===========================================
        
        # ===== ЛОГОТИП =====
        logo_label = QLabel()
        logo_pixmap = QPixmap(resource_path('resources/logo.png'))
        
        if not logo_pixmap.isNull():
            scaled_logo = logo_pixmap.scaled(
                100, 100,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            logo_label.setPixmap(scaled_logo)
            logo_label.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(logo_label)
            content_layout.addSpacing(10)
        else:
            emoji_label = QLabel('FC')
            emoji_label.setAlignment(Qt.AlignCenter)
            emoji_label.setStyleSheet('font-size: 36px; font-weight: bold; color: #FF9800; background-color: transparent;')
            content_layout.addWidget(emoji_label)
            content_layout.addSpacing(10)
            print("⚠️ Логотип не найден: resources/logo.png")
        
        # Заголовок
        title = QLabel('Вход в систему')
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont('Arial', 20, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet('color: #333333; font-size: 20px; margin-bottom: 0px; background-color: transparent;')
        content_layout.addWidget(title)
        
        content_layout.addSpacing(20)
        
        # Поле логина
        login_label = QLabel('Логин:')
        login_label.setStyleSheet('font-size: 14px; color: #333333; font-weight: bold; background-color: transparent;')
        content_layout.addWidget(login_label)
        
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText('Введите логин')
        self.login_input.setFixedHeight(45)
        content_layout.addWidget(self.login_input)
        
        content_layout.addSpacing(10)
        
        # Поле пароля
        password_label = QLabel('Пароль:')
        password_label.setStyleSheet('font-size: 14px; color: #333333; font-weight: bold; background-color: transparent;')
        content_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Введите пароль')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(45)
        self.password_input.returnPressed.connect(self.login)
        content_layout.addWidget(self.password_input)
        
        content_layout.addSpacing(15)
        
        # Кнопка входа
        login_btn = QPushButton('ВОЙТИ')
        login_btn.setFixedHeight(50)
        login_btn.clicked.connect(self.login)
        login_btn.setCursor(Qt.PointingHandCursor)
        content_layout.addWidget(login_btn)
        
        content_layout.addStretch()
        
        content_widget.setLayout(content_layout)
        
        # ========== СБОРКА ==========
        border_layout.addWidget(content_widget)
        border_frame.setLayout(border_layout)
        
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        # ============================
        
        self.center_on_screen()
    
    def center_on_screen(self):
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )
    
    def login(self):
        login = self.login_input.text().strip()
        password = self.password_input.text().strip()

        if not login or not password:
            CustomMessageBox(
                self,
                'Ошибка',
                'Введите логин и пароль!',
                'warning'
            ).exec_()
            app_logger.warning("Попытка входа с пустыми полями")
            return

        # Проверка в БД
        app_logger.info(f"Попытка входа: логин='{login}'")
        employee = self.db.get_employee_by_login(login, password)

        if employee:
            # Успешный вход
            employee_name = employee.get('full_name', login)
            role = employee.get('role', 'Unknown')

            log_auth_attempt(login, success=True)
            app_logger.info(f"Успешный вход: {employee_name} (роль: {role})")

            self.hide()
            self.main_window = MainWindow(employee)
            self.main_window.show()
        else:
            # Неудачный вход
            log_auth_attempt(login, success=False)
            app_logger.warning(f"Неудачная попытка входа: логин='{login}'")

            CustomMessageBox(
                self,
                'Ошибка входа',
                'Неверный логин или пароль!',
                'error'
            ).exec_()

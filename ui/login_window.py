# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QDialog, QFrame,
                             QGraphicsDropShadowEffect, QProgressBar,
                             QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap, QColor
from PyQt5.QtWidgets import QTabWidget
from database.db_manager import DatabaseManager
from ui.main_window import MainWindow
from ui.custom_message_box import CustomMessageBox
from utils.resource_path import resource_path
from config import MULTI_USER_MODE, API_BASE_URL
from utils.password_utils import verify_password

# ========== ЛОГИРОВАНИЕ ==========
from utils.logger import log_auth_attempt, app_logger
# =================================

# ========== API CLIENT ==========
if MULTI_USER_MODE:
    from utils.api_client import APIClient, APIConnectionError, APITimeoutError
    from utils.db_sync import sync_on_login
# ================================


class SyncProgressDialog(QDialog):
    """Кастомный диалог прогресса синхронизации"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Без стандартной рамки
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)

        self.init_ui()

    def init_ui(self):
        # ========== ГЛАВНЫЙ LAYOUT ==========
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== КОНТЕЙНЕР С РАМКОЙ ==========
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
        title_bar = CustomTitleBar(self, "Синхронизация", simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        # Скрываем кнопку закрытия
        if hasattr(title_bar, 'close_btn'):
            title_bar.close_btn.hide()

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

        content_layout = QVBoxLayout()
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(30, 20, 30, 30)

        # Иконка/заголовок
        icon_label = QLabel("ЗАГРУЗКА ДАННЫХ")
        icon_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #333333;
            background-color: transparent;
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(icon_label)

        # Сообщение о текущем действии
        self.message_label = QLabel("Подготовка...")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("""
            font-size: 12px;
            color: #666666;
            background-color: #F5F5F5;
            padding: 10px;
            border-radius: 6px;
        """)
        content_layout.addWidget(self.message_label)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(7)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                background-color: #F5F5F5;
                height: 20px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)
        content_layout.addWidget(self.progress_bar)

        content_widget.setLayout(content_layout)
        border_layout.addWidget(content_widget)
        border_frame.setLayout(border_layout)

        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        self.setFixedWidth(350)

    def set_progress(self, current, total, message):
        """Обновить прогресс"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.message_label.setText(message)
        QApplication.processEvents()

    def showEvent(self, event):
        """Центрирование при показе"""
        super().showEvent(event)
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)


class SyncWorker(QThread):
    """Поток для синхронизации данных в фоне"""
    progress = pyqtSignal(int, int, str)  # current, total, message
    finished_sync = pyqtSignal(dict)  # result

    def __init__(self, db_manager, api_client):
        super().__init__()
        self.db_manager = db_manager
        self.api_client = api_client

    def run(self):
        """Выполнение синхронизации в отдельном потоке"""
        def progress_callback(current, total, message):
            self.progress.emit(current, total, message)

        result = sync_on_login(self.db_manager, self.api_client, progress_callback)
        self.finished_sync.emit(result)

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.main_window = None
        self.api_client = None
        self.current_employee = None
        self.sync_worker = None
        self.progress_dialog = None

        # Инициализация API клиента если включен многопользовательский режим
        if MULTI_USER_MODE:
            try:
                self.api_client = APIClient(API_BASE_URL)
                app_logger.info(f"API клиент инициализирован: {API_BASE_URL}")
            except Exception as e:
                app_logger.error(f"Ошибка инициализации API клиента: {e}")

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
                border: 1px solid #d9d9d9;
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
            print("[WARN] Логотип не найден: resources/logo.png")
        
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
        self.login_input.returnPressed.connect(self.focus_password)
        self.login_input.setStyleSheet("""
            QLineEdit {
                max-height: 28px;
                min-height: 28px;
                padding: 6px 8px;
            }
        """)
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
        self.password_input.setStyleSheet("""
            QLineEdit {
                max-height: 28px;
                min-height: 28px;
                padding: 6px 8px;
            }
        """)
        content_layout.addWidget(self.password_input)
        
        content_layout.addSpacing(10)
        
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

        # Многопользовательский режим - аутентификация через API
        if MULTI_USER_MODE and self.api_client:
            try:
                app_logger.info(f"API аутентификация: логин='{login}'")

                # Вход через API
                result = self.api_client.login(login, password)

                # Формируем данные пользователя
                self.current_employee = {
                    'id': result['employee_id'],
                    'full_name': result['full_name'],
                    'role': result['role'],
                    'position': result.get('position', result['role']),
                    'department': result.get('department', ''),
                    'login': login,
                    'api_mode': True,  # Флаг что работаем через API
                    'offline_mode': False  # Онлайн режим
                }

                log_auth_attempt(login, success=True)
                app_logger.info(f"Успешный API вход: {result['full_name']} (роль: {result['role']})")

                # Кешируем пароль для offline-входа
                self._cache_password_for_offline(result['employee_id'], password)

                # Запускаем синхронизацию данных
                self._start_sync()
                return

            except (APIConnectionError, APITimeoutError) as e:
                # Ошибка соединения - пробуем offline-вход
                app_logger.warning(f"Ошибка соединения с сервером: {e}")
                app_logger.info(f"Попытка offline-аутентификации для: {login}")

                offline_result = self._try_offline_login(login, password)
                if offline_result:
                    return  # Успешный offline-вход
                else:
                    # Offline-вход не удался
                    CustomMessageBox(
                        self,
                        'Ошибка входа',
                        f'Нет подключения к серверу.\n\n'
                        f'Offline-вход невозможен: пользователь "{login}" '
                        f'не найден в локальной базе данных или пароль не был закеширован.\n\n'
                        f'Для первого входа требуется подключение к серверу.',
                        'error'
                    ).exec_()
                    return

            except Exception as e:
                log_auth_attempt(login, success=False)
                app_logger.error(f"Ошибка API входа: {e}")

                error_msg = str(e)
                if "Не удалось войти" in error_msg or "401" in error_msg:
                    error_msg = "Неверный логин или пароль!"
                elif "ConnectionError" in error_msg or "Timeout" in error_msg:
                    # Дополнительная проверка на ошибки соединения
                    app_logger.info(f"Попытка offline-аутентификации после ошибки: {login}")
                    offline_result = self._try_offline_login(login, password)
                    if offline_result:
                        return
                    error_msg = f"Ошибка подключения к серверу.\nOffline-вход недоступен для этого пользователя."

                CustomMessageBox(
                    self,
                    'Ошибка входа',
                    error_msg,
                    'error'
                ).exec_()
            return

        # Локальный режим - аутентификация через SQLite БД
        app_logger.info(f"Локальная аутентификация: логин='{login}'")
        employee = self.db.get_employee_by_login(login, password)

        if employee:
            # Успешный вход
            employee_name = employee.get('full_name', login)
            role = employee.get('role', 'Unknown')

            log_auth_attempt(login, success=True)
            app_logger.info(f"Успешный локальный вход: {employee_name} (роль: {role})")

            self.hide()
            self.main_window = MainWindow(employee)
            self.main_window.show()
        else:
            # Неудачный вход
            log_auth_attempt(login, success=False)
            app_logger.warning(f"Неудачная попытка локального входа: логин='{login}'")

            CustomMessageBox(
                self,
                'Ошибка входа',
                'Неверный логин или пароль!',
                'error'
            ).exec_()

    def _cache_password_for_offline(self, employee_id: int, password: str):
        """Кеширование пароля для offline-аутентификации"""
        try:
            self.db.cache_employee_password(employee_id, password)
            app_logger.info(f"Пароль закеширован для offline-входа (employee_id={employee_id})")
        except Exception as e:
            app_logger.warning(f"Не удалось закешировать пароль: {e}")

    def _try_offline_login(self, login: str, password: str) -> bool:
        """
        Попытка offline-аутентификации через локальную БД.

        Args:
            login: Логин пользователя
            password: Пароль

        Returns:
            True если вход успешен, False иначе
        """
        try:
            # Получаем сотрудника с закешированным паролем
            employee = self.db.get_employee_for_offline_login(login)

            if not employee:
                app_logger.warning(f"Offline-вход: пользователь '{login}' не найден или пароль не закеширован")
                return False

            # Проверяем пароль
            stored_password = employee.get('password')
            if not stored_password or not verify_password(password, stored_password):
                app_logger.warning(f"Offline-вход: неверный пароль для '{login}'")
                return False

            # Успешный offline-вход
            self.current_employee = {
                'id': employee['id'],
                'full_name': employee.get('full_name', login),
                'role': employee.get('role', 'user'),
                'position': employee.get('position', ''),
                'department': employee.get('department', ''),
                'login': login,
                'api_mode': True,  # Всё ещё в многопользовательском режиме
                'offline_mode': True  # Но работаем offline
            }

            log_auth_attempt(login, success=True)
            app_logger.info(f"Успешный OFFLINE вход: {employee.get('full_name')} (роль: {employee.get('role')})")

            # Показываем предупреждение об offline-режиме
            CustomMessageBox(
                self,
                'Offline-режим',
                f'Вход выполнен в offline-режиме.\n\n'
                f'Нет подключения к серверу. Вы работаете с локальными данными.\n'
                f'Изменения будут синхронизированы при восстановлении связи.',
                'warning'
            ).exec_()

            # Открываем главное окно без синхронизации
            self.hide()
            self.main_window = MainWindow(self.current_employee, api_client=self.api_client)
            self.main_window.show()

            return True

        except Exception as e:
            app_logger.error(f"Ошибка offline-аутентификации: {e}")
            return False

    def _start_sync(self):
        """Запуск синхронизации данных после успешного входа"""
        # Создаем кастомный диалог прогресса
        self.progress_dialog = SyncProgressDialog(self)
        self.progress_dialog.show()

        # Запускаем синхронизацию в отдельном потоке
        self.sync_worker = SyncWorker(self.db, self.api_client)
        self.sync_worker.progress.connect(self._on_sync_progress)
        self.sync_worker.finished_sync.connect(self._on_sync_finished)
        self.sync_worker.start()

    @pyqtSlot(int, int, str)
    def _on_sync_progress(self, current, total, message):
        """Обновление прогресса синхронизации"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.set_progress(current, total, message)

    @pyqtSlot(dict)
    def _on_sync_finished(self, result):
        """Завершение синхронизации"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()

        if result['success']:
            synced = result['synced']
            app_logger.info(
                f"Синхронизация завершена: "
                f"сотрудники={synced['employees']}, "
                f"клиенты={synced['clients']}, "
                f"договоры={synced['contracts']}, "
                f"CRM={synced['crm_cards']}"
            )
        else:
            app_logger.warning(f"Синхронизация завершена с ошибками: {result['errors']}")

        # Открываем главное окно
        self.hide()
        self.main_window = MainWindow(self.current_employee, api_client=self.api_client)
        self.main_window.show()

    def focus_password(self):
        """Переход к полю пароля при нажатии Enter в поле логина"""
        self.password_input.setFocus()

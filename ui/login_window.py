# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QPixmap
from PyQt5.QtWidgets import QApplication, QCheckBox, QDialog, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton, QTabWidget, QVBoxLayout, QWidget

from config import API_BASE_URL, API_VERIFY_SSL, MULTI_USER_MODE
from database.db_manager import DatabaseManager
from ui.custom_message_box import CustomMessageBox
from ui.main_window import MainWindow

# ========== ЛОГИРОВАНИЕ ==========
from utils.logger import app_logger, log_auth_attempt
from utils.password_utils import verify_password
from utils.resource_path import resource_path

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
        if hasattr(title_bar, "close_btn"):
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
                self.api_client = APIClient(API_BASE_URL, verify_ssl=API_VERIFY_SSL)
                app_logger.info(f"API клиент инициализирован: {API_BASE_URL}")
            except Exception as e:
                app_logger.error(f"Ошибка инициализации API клиента: {e}")

        self.init_ui()

        # Попытка автологина из сохранённой сессии
        self._auto_login_attempted = False

    def try_auto_login(self):
        """Попытка автологина из сохранённой сессии (вызывается после show)."""
        if self._auto_login_attempted:
            return
        self._auto_login_attempted = True

        if not MULTI_USER_MODE or not self.api_client:
            return

        from utils.session_storage import clear_session, load_session

        session = load_session()
        if not session:
            return

        refresh_token = session.get("refresh_token")
        if not refresh_token:
            return

        app_logger.info(f"Автологин: пробуем восстановить сессию для {session.get('login', '?')}")

        try:
            # Устанавливаем refresh_token и пробуем обновить access_token
            self.api_client.refresh_token = refresh_token

            # Пробуем refresh — если 403 (уволен/резерв), покажем сообщение
            try:
                resp = self.api_client._request(
                    "POST",
                    f"{self.api_client.base_url}/api/v1/auth/refresh",
                    json={"refresh_token": refresh_token},
                    mark_offline=False,
                )
            except Exception:
                app_logger.info("Автологин: сервер недоступен")
                clear_session()
                return

            if resp.status_code == 403:
                # Уволен / в резерве — показываем сообщение
                detail = ""
                try:
                    detail = resp.json().get("detail", "")
                except Exception:
                    pass
                app_logger.info(f"Автологин запрещён: {detail}")
                clear_session()
                from ui.custom_message_box import CustomMessageBox

                CustomMessageBox(
                    self,
                    "Сессия завершена",
                    detail or "Ваша учётная запись деактивирована. Обратитесь к руководителю.",
                    "warning",
                ).exec_()
                return

            if resp.status_code != 200:
                app_logger.info("Автологин: refresh_token истёк или отозван")
                clear_session()
                return

            # Refresh удался — сохраняем токены
            data = resp.json()
            new_refresh = data.get("refresh_token", refresh_token)
            self.api_client.set_token(data["access_token"], new_refresh)
            self.api_client.employee_id = data.get("employee_id", self.api_client.employee_id)

            # Получаем данные пользователя
            try:
                me = self.api_client._request("GET", f"{self.api_client.base_url}/api/v1/auth/me")
                if me.status_code != 200:
                    clear_session()
                    return
                user_data = me.json()
            except Exception:
                clear_session()
                return

            position = user_data.get("position", "") or user_data.get("role", "")
            self.current_employee = {
                "id": user_data["id"],
                "full_name": user_data.get("full_name", ""),
                "role": user_data.get("role", ""),
                "position": position,
                "secondary_position": user_data.get("secondary_position", ""),
                "department": user_data.get("department", ""),
                "login": session.get("login", ""),
                "api_mode": True,
                "offline_mode": False,
            }

            # Устанавливаем auto-relogin callback
            _login = session.get("login", "")
            _api = self.api_client

            def _auto_relogin():
                try:
                    _api.refresh_token = refresh_token
                    return _api.refresh_access_token()
                except Exception:
                    return False

            self.api_client.set_relogin_callback(_auto_relogin)

            log_auth_attempt(session.get("login", "?"), success=True)
            app_logger.info(f"Автологин успешен: {user_data.get('full_name', '?')}")

            # Обновляем refresh_token в файле (мог быть ротирован)
            from utils.session_storage import save_session

            save_session(
                refresh_token=self.api_client.refresh_token,
                employee_id=user_data["id"],
                full_name=user_data.get("full_name", ""),
                login=session.get("login", ""),
            )

            # Запускаем синхронизацию
            self._start_sync()

        except Exception as e:
            app_logger.warning(f"Автологин не удался: {e}")
            clear_session()

    def init_ui(self):
        self.setWindowTitle("Festival Color - Вход")
        self.setFixedSize(400, 580)

        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        # Qt.Window обязателен — без него окно не появляется в панели задач
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        # ===============================================

        import sys

        if sys.platform == "win32":
            # Windows: DWM для прозрачности (как в main_window), НЕ WA_TranslucentBackground
            self._setup_windows_taskbar()
        else:
            self.setAttribute(Qt.WA_TranslucentBackground, True)  # macOS/Linux: CSS border-radius

        # Иконка через Qt (fallback для не-Windows)
        if QApplication.instance():
            self.setWindowIcon(QApplication.instance().windowIcon())

        # ========== ГЛАВНЫЙ LAYOUT ==========
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        # ====================================

        # ========== КОНТЕЙНЕР С РАМКОЙ  ==========
        import sys as _sys

        _radius = "10px" if _sys.platform != "win32" else "0px"
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet(f"""
            QFrame#borderFrame {{
                background-color: #FFFFFF;
                border: 1px solid #d9d9d9;
                border-radius: {_radius};
            }}
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
        title_bar.setStyleSheet(f"""
            CustomTitleBar {{
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: {_radius};
                border-top-right-radius: {_radius};
            }}
        """)
        # ======================================================

        border_layout.addWidget(title_bar)
        # =========================================

        # ========== КОНТЕЙНЕР ДЛЯ КОНТЕНТА ==========
        content_widget = QWidget()
        content_widget.setStyleSheet(f"""
            QWidget {{
                background-color: #FFFFFF;
                border-bottom-left-radius: {_radius};
                border-bottom-right-radius: {_radius};
            }}
        """)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(14)
        content_layout.setContentsMargins(40, 12, 40, 30)
        # ===========================================

        # ===== ЛОГОТИП =====
        logo_label = QLabel()
        logo_pixmap = QPixmap(resource_path("resources/logo.png"))

        if not logo_pixmap.isNull():
            scaled_logo = logo_pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_logo)
            logo_label.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(logo_label)
            content_layout.addSpacing(4)
        else:
            emoji_label = QLabel("FC")
            emoji_label.setAlignment(Qt.AlignCenter)
            emoji_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #FF9800; background-color: transparent;")
            content_layout.addWidget(emoji_label)
            content_layout.addSpacing(4)
            print("[WARN] Логотип не найден: resources/logo.png")

        # Заголовок
        title = QLabel("Вход в систему")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont("Manrope", 20, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #333333; font-size: 20px; margin-bottom: 0px; background-color: transparent;")
        content_layout.addWidget(title)

        content_layout.addSpacing(12)

        # Поле логина
        login_label = QLabel("Логин:")
        login_label.setStyleSheet("font-size: 14px; color: #333333; font-weight: bold; background-color: transparent;")
        content_layout.addWidget(login_label)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Введите логин")
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

        content_layout.addSpacing(6)

        # Поле пароля
        password_label = QLabel("Пароль:")
        password_label.setStyleSheet("font-size: 14px; color: #333333; font-weight: bold; background-color: transparent;")
        content_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Введите пароль")
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

        # Чекбокс "Запомнить меня"
        self.remember_me = QCheckBox("Запомнить меня")
        self.remember_me.setStyleSheet("""
            QCheckBox {
                color: #666666;
                font-size: 12px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #d9d9d9;
                border-radius: 3px;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background-color: #F57C00;
                border-color: #F57C00;
            }
        """)
        content_layout.addWidget(self.remember_me)

        content_layout.addSpacing(5)

        # Кнопка входа
        login_btn = QPushButton("ВОЙТИ")
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

    def _setup_windows_taskbar(self):
        """Windows: WS_CAPTION для taskbar + DWM прозрачность + Win32 иконка."""
        try:
            import ctypes
            from ctypes import wintypes
            import os

            hwnd = int(self.winId())

            # Добавляем WS_CAPTION — окно появится в панели задач
            GWL_STYLE = -16
            WS_CAPTION = 0x00C00000
            style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_STYLE)
            style |= WS_CAPTION
            ctypes.windll.user32.SetWindowLongPtrW(hwnd, GWL_STYLE, style)

            # DWM: расширяем фрейм — даёт прозрачность без WA_TranslucentBackground
            class MARGINS(ctypes.Structure):
                _fields_ = [
                    ("cxLeftWidth", ctypes.c_int),
                    ("cxRightWidth", ctypes.c_int),
                    ("cyTopHeight", ctypes.c_int),
                    ("cyBottomHeight", ctypes.c_int),
                ]

            margins = MARGINS(0, 0, 1, 0)
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

            # Win32 иконка (WM_SETICON + SetClassLongPtrW)
            WM_SETICON = 0x0080
            ICON_BIG = 1
            ICON_SMALL = 0
            GCL_HICON = -14
            GCL_HICONSM = -34
            LR_LOADFROMFILE = 0x00000010
            LR_SHARED = 0x00008000
            IMAGE_ICON = 1

            from utils.resource_path import resource_path

            ico_path = resource_path("resources/icon256.ico")
            if not os.path.exists(ico_path):
                ico_path = resource_path("resources/icon.ico")
            ico_small_path = resource_path("resources/icon32.ico")
            if not os.path.exists(ico_small_path):
                ico_small_path = ico_path

            hicon_big = ctypes.windll.user32.LoadImageW(0, ico_path, IMAGE_ICON, 256, 256, LR_LOADFROMFILE | LR_SHARED)
            hicon_small = ctypes.windll.user32.LoadImageW(0, ico_small_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE | LR_SHARED)
            if hicon_big:
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
                ctypes.windll.user32.SetClassLongPtrW(hwnd, GCL_HICON, hicon_big)
            if hicon_small:
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
                ctypes.windll.user32.SetClassLongPtrW(hwnd, GCL_HICONSM, hicon_small)
        except Exception as e:
            app_logger.warning(f"Win32 taskbar icon setup failed: {e}")

    def nativeEvent(self, eventType, message):
        """Убираем стандартный заголовок Windows, который добавляет WS_CAPTION."""
        try:
            import sys

            if sys.platform == "win32":
                import ctypes
                from ctypes import wintypes

                msg = wintypes.MSG.from_address(message.__int__())
                WM_NCCALCSIZE = 0x0083
                if msg.message == WM_NCCALCSIZE:
                    # Клиентская область = всё окно (убираем рамку от WS_CAPTION)
                    return True, 0
        except Exception:
            pass
        return super().nativeEvent(eventType, message)

    def center_on_screen(self):
        from PyQt5.QtWidgets import QDesktopWidget

        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)

    def login(self):
        # Защита от повторного нажатия во время авторизации/синхронизации
        if getattr(self, "_login_in_progress", False):
            return
        self._login_in_progress = True

        login = self.login_input.text().strip()
        password = self.password_input.text().strip()

        if not login or not password:
            CustomMessageBox(self, "Ошибка", "Введите логин и пароль!", "warning").exec_()
            app_logger.warning("Попытка входа с пустыми полями")
            self._login_in_progress = False
            return

        # Многопользовательский режим - аутентификация через API
        if MULTI_USER_MODE and self.api_client:
            try:
                app_logger.info(f"API аутентификация: логин='{login}'")

                # Вход через API
                result = self.api_client.login(login, password)

                # Auto-relogin: сохраняем credentials для автоматического перелогинивания
                _login, _password, _api = login, password, self.api_client

                def _auto_relogin():
                    try:
                        _api.login(_login, _password)
                        return True
                    except Exception:
                        return False

                self.api_client.set_relogin_callback(_auto_relogin)

                # Формируем данные пользователя
                position = result.get("position", "") or result.get("role", "")
                self.current_employee = {
                    "id": result["employee_id"],
                    "full_name": result["full_name"],
                    "role": result.get("role", ""),
                    "position": position,
                    "secondary_position": result.get("secondary_position", ""),
                    "department": result.get("department", ""),
                    "login": login,
                    "api_mode": True,  # Флаг что работаем через API
                    "offline_mode": False,  # Онлайн режим
                }

                log_auth_attempt(login, success=True)
                app_logger.info(f"Успешный API вход: {result['full_name']} (роль: {result['role']})")

                # Кешируем пароль для offline-входа
                self._cache_password_for_offline(result["employee_id"], password)

                # Сохраняем сессию для автологина ("Запомнить меня")
                if self.remember_me.isChecked() and self.api_client.refresh_token:
                    from utils.session_storage import save_session

                    save_session(
                        refresh_token=self.api_client.refresh_token,
                        employee_id=result["employee_id"],
                        full_name=result["full_name"],
                        login=login,
                    )

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
                        "Ошибка входа",
                        f"Нет подключения к серверу.\n\n"
                        f'Offline-вход невозможен: пользователь "{login}" '
                        f"не найден в локальной базе данных или пароль не был закеширован.\n\n"
                        f"Для первого входа требуется подключение к серверу.",
                        "error",
                    ).exec_()
                    self._login_in_progress = False
                    return

            except Exception as e:
                log_auth_attempt(login, success=False)
                # Логируем только тип ошибки, НЕ полный traceback (безопасность)
                app_logger.error(f"Ошибка API входа для '{login}': {type(e).__name__}")

                error_str = str(e)
                if "429" in error_str or "Слишком много попыток" in error_str:
                    error_msg = "Слишком много попыток входа.\nПовторите через 15 минут."
                elif "401" in error_str or "Требуется авторизация" in error_str:
                    error_msg = "Неверный логин или пароль!"
                elif "Вход запрещён" in error_str or "Статус сотрудника" in error_str:
                    error_msg = error_str
                elif "ConnectionError" in error_str or "Timeout" in error_str or "Offline" in error_str:
                    app_logger.info(f"Попытка offline-аутентификации после ошибки: {login}")
                    offline_result = self._try_offline_login(login, password)
                    if offline_result:
                        return
                    error_msg = "Ошибка подключения к серверу.\nOffline-вход недоступен для этого пользователя."
                else:
                    # Обобщённое сообщение — НЕ раскрываем внутренние детали
                    error_msg = "Ошибка входа. Попробуйте позже."

                error_title = "Отказано в доступе" if "Вход запрещён" in error_msg else "Ошибка входа"
                CustomMessageBox(self, error_title, error_msg, "error").exec_()
            self._login_in_progress = False
            return

        # Локальный режим - аутентификация через SQLite БД
        app_logger.info(f"Локальная аутентификация: логин='{login}'")
        employee = self.db.get_employee_by_login(login, password)

        if employee:
            # Успешный вход
            employee_name = employee.get("full_name", login)
            role = employee.get("role", "Unknown")

            log_auth_attempt(login, success=True)
            app_logger.info(f"Успешный локальный вход: {employee_name} (роль: {role})")

            self.hide()
            self.main_window = MainWindow(employee)
            self.main_window.show()
        else:
            # Неудачный вход
            log_auth_attempt(login, success=False)
            app_logger.warning(f"Неудачная попытка локального входа: логин='{login}'")

            CustomMessageBox(self, "Ошибка входа", "Неверный логин или пароль!", "error").exec_()
            self._login_in_progress = False

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
            stored_password = employee.get("password")
            if not stored_password or not verify_password(password, stored_password):
                app_logger.warning(f"Offline-вход: неверный пароль для '{login}'")
                return False

            # Успешный offline-вход
            self.current_employee = {
                "id": employee["id"],
                "full_name": employee.get("full_name", login),
                "role": employee.get("role", "user"),
                "position": employee.get("position", ""),
                "secondary_position": employee.get("secondary_position", ""),
                "department": employee.get("department", ""),
                "login": login,
                "api_mode": True,  # Всё ещё в многопользовательском режиме
                "offline_mode": True,  # Но работаем offline
            }

            log_auth_attempt(login, success=True)
            app_logger.info(f"Успешный OFFLINE вход: {employee.get('full_name')} (роль: {employee.get('role')})")

            # ИСПРАВЛЕНИЕ: Устанавливаем offline режим в api_client
            # чтобы предотвратить ненужные API запросы при загрузке UI
            if self.api_client:
                self.api_client.set_offline_mode(True)

            # Показываем предупреждение об offline-режиме
            CustomMessageBox(
                self,
                "Offline-режим",
                f"Вход выполнен в offline-режиме.\n\nНет подключения к серверу. Вы работаете с локальными данными.\nИзменения будут синхронизированы при восстановлении связи.",
                "warning",
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
        if hasattr(self, "progress_dialog") and self.progress_dialog:
            self.progress_dialog.set_progress(current, total, message)

    @pyqtSlot(dict)
    def _on_sync_finished(self, result):
        """Завершение синхронизации"""
        if hasattr(self, "progress_dialog") and self.progress_dialog:
            self.progress_dialog.close()

        if result["success"]:
            synced = result["synced"]
            app_logger.info(f"Синхронизация завершена: сотрудники={synced['employees']}, клиенты={synced['clients']}, договоры={synced['contracts']}, CRM={synced['crm_cards']}")
        else:
            app_logger.warning(f"Синхронизация завершена с ошибками: {result['errors']}")

        # Открываем главное окно
        self.hide()
        self.main_window = MainWindow(self.current_employee, api_client=self.api_client)
        self.main_window.show()

        # Предупреждение о заполненности диска — только для администраторов
        _admin_pos = ["Руководитель студии", "Старший менеджер проектов", "СДП", "ГАП"]
        _pos = (self.current_employee or {}).get("position", "")
        _role = (self.current_employee or {}).get("role", "")
        if (_pos in _admin_pos or _role in {"admin", "director"}) and self.api_client:
            import threading

            def _check_disk():
                try:
                    status = self.api_client.get_server_disk_status()
                    if status and status.get("disk_warning"):
                        disk = status["disk_percent"]
                        free = status["disk_free_gb"]
                        total = status["disk_total_gb"]
                        level = "critical" if status.get("disk_critical") else "warning"
                        from PyQt5.QtCore import QTimer

                        QTimer.singleShot(
                            500,
                            lambda: CustomMessageBox(
                                self.main_window,
                                "Внимание: диск сервера заполнен",
                                f"Диск сервера заполнен на {disk}%.\nСвободно: {free} ГБ из {total} ГБ.\n\nОчистите логи или Docker-кэш на сервере,\nиначе сервер прекратит работу.",
                                level,
                            ).exec_(),
                        )
                except Exception:
                    pass

            threading.Thread(target=_check_disk, daemon=True).start()

    def focus_password(self):
        """Переход к полю пароля при нажатии Enter в поле логина"""
        self.password_input.setFocus()

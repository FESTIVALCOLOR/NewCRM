# -*- coding: utf-8 -*-
"""
Run with Auto Login - Запуск приложения с автоматическим входом

Использование:
    python tests/visual/run_with_autologin.py --login admin --password admin123
"""

import sys
import os
import argparse
from pathlib import Path

# Добавляем корень проекта
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Парсим аргументы ДО импорта PyQt5
parser = argparse.ArgumentParser(description="Run app with auto login")
parser.add_argument('--login', required=True, help='Login username')
parser.add_argument('--password', required=True, help='Login password')
parser.add_argument('--delay', type=int, default=2000, help='Delay before auto login (ms)')
parser.add_argument('--screenshot', action='store_true', help='Take screenshots')
args = parser.parse_args()

# Теперь импортируем PyQt5 и приложение
from PyQt5.QtWidgets import QApplication, QLineEdit, QPushButton
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtTest import QTest
from datetime import datetime


class AutoLoginInjector:
    """Инжектор автологина"""

    def __init__(self, login: str, password: str, screenshot: bool = False):
        self.login = login
        self.password = password
        self.screenshot = screenshot
        self.screenshot_dir = PROJECT_ROOT / "tests" / "visual" / "auto_captures"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def capture(self, name: str):
        """Сделать скриншот"""
        if not self.screenshot:
            return

        try:
            import pyautogui
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = self.screenshot_dir / filename
            img = pyautogui.screenshot()
            img.save(str(filepath))
            print(f"[SCREENSHOT] {filepath}")
        except Exception as e:
            print(f"[ERROR] Screenshot failed: {e}")

    def find_login_window(self):
        """Найти окно входа"""
        for widget in QApplication.topLevelWidgets():
            if widget.isVisible():
                class_name = widget.__class__.__name__
                title = widget.windowTitle() if hasattr(widget, 'windowTitle') else ''
                print(f"[WIDGET] {class_name}: '{title}'")

                if 'LoginWindow' in class_name or 'Login' in class_name:
                    return widget
                if 'Вход' in title or 'Festival' in title:
                    return widget

        return None

    def do_login(self):
        """Выполнить автологин"""
        print("\n[AUTO-LOGIN] Starting...")
        self.capture("01_before_login")

        login_window = self.find_login_window()
        if not login_window:
            print("[ERROR] Login window not found!")
            # Попробуем ещё раз через 1 секунду
            QTimer.singleShot(1000, self.do_login)
            return

        print(f"[OK] Found login window: {login_window.__class__.__name__}")

        # Находим все QLineEdit
        line_edits = login_window.findChildren(QLineEdit)
        buttons = login_window.findChildren(QPushButton)

        print(f"[INFO] Found {len(line_edits)} input fields, {len(buttons)} buttons")

        if len(line_edits) < 2:
            print("[ERROR] Need at least 2 input fields!")
            return

        # Определяем поля по placeholder или echoMode
        login_field = None
        password_field = None

        for edit in line_edits:
            placeholder = edit.placeholderText().lower()
            echo_mode = edit.echoMode()

            print(f"  Field: placeholder='{edit.placeholderText()}', echoMode={echo_mode}")

            if echo_mode == QLineEdit.Password:
                password_field = edit
            elif 'логин' in placeholder or 'login' in placeholder or 'имя' in placeholder:
                login_field = edit
            elif 'пароль' in placeholder or 'password' in placeholder:
                password_field = edit

        # Если не нашли по placeholder, берём по порядку
        if not login_field:
            login_field = line_edits[0]
        if not password_field:
            password_field = line_edits[1] if len(line_edits) > 1 else line_edits[0]

        print(f"[INFO] Login field: {login_field.placeholderText()}")
        print(f"[INFO] Password field: {password_field.placeholderText()}")

        # Вводим логин
        print(f"[INPUT] Typing login: {self.login}")
        login_field.setFocus()
        login_field.clear()
        login_field.setText(self.login)  # Прямая установка текста!

        # Вводим пароль
        print(f"[INPUT] Typing password: {'*' * len(self.password)}")
        password_field.setFocus()
        password_field.clear()
        password_field.setText(self.password)  # Прямая установка текста!

        self.capture("02_after_input")

        # Находим кнопку входа
        login_button = None
        for btn in buttons:
            text = btn.text().lower()
            print(f"  Button: '{btn.text()}'")
            if 'войти' in text or 'вход' in text or 'login' in text:
                login_button = btn
                break

        if not login_button and buttons:
            # Берём первую видимую кнопку
            for btn in buttons:
                if btn.isVisible() and btn.isEnabled():
                    login_button = btn
                    break

        if login_button:
            print(f"[CLICK] Clicking button: '{login_button.text()}'")
            login_button.click()  # Прямой вызов click()!
        else:
            print("[WARN] No login button found, trying Enter key")
            QTest.keyClick(password_field, Qt.Key_Return)

        # Скриншот после входа
        QTimer.singleShot(3000, lambda: self.capture("03_after_login"))

        print("[AUTO-LOGIN] Completed!")


def main():
    """Запуск приложения с автологином"""
    print(f"[START] Running with auto-login: {args.login}")

    # ========== ПОЛНОЕ КОПИРОВАНИЕ НАСТРОЕК ИЗ main.py ==========

    # High DPI атрибуты (ДО создания QApplication!)
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    # Поддержка композитинга для tooltip поверх полупрозрачных окон
    if hasattr(Qt, 'AA_UseDesktopOpenGL'):
        QApplication.setAttribute(Qt.AA_UseDesktopOpenGL, True)

    # Создаём QApplication
    app = QApplication(sys.argv)

    # Устанавливаем стиль Fusion (как в main.py)
    app.setStyle('Fusion')

    # Устанавливаем иконку приложения
    from utils.resource_path import resource_path
    from PyQt5.QtGui import QIcon, QPalette, QColor
    from PyQt5.QtWidgets import QComboBox
    from PyQt5.QtCore import QObject, QEvent
    app_icon = QIcon(resource_path('resources/icon.ico'))
    app.setWindowIcon(app_icon)

    # ========== ComboBox Event Filter (как в main.py) ==========
    # Отключает изменение значения при прокрутке колесиком, если ComboBox не в фокусе
    class ComboBoxEventFilter(QObject):
        def eventFilter(self, obj, event):
            if isinstance(obj, QComboBox) and event.type() == QEvent.Wheel:
                if not obj.hasFocus():
                    event.ignore()
                    return True
            return super().eventFilter(obj, event)

    combo_filter = ComboBoxEventFilter(app)
    app.installEventFilter(combo_filter)
    print("[FILTER] ComboBox scroll filter installed")
    # ===========================================================

    # Устанавливаем палитру для tooltip
    palette = app.palette()
    palette.setColor(QPalette.ToolTipBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ToolTipText, QColor(51, 51, 51))
    app.setPalette(palette)

    # КРИТИЧНО: Применяем единые стили!
    from utils.unified_styles import get_unified_stylesheet
    tooltip_override = """
    QToolTip {
        background-color: rgb(245, 245, 245);
        color: rgb(51, 51, 51);
        border: 1px solid rgb(204, 204, 204);
        border-radius: 4px;
        padding: 5px;
        font-size: 12px;
    }
    """
    combined_styles = get_unified_stylesheet() + "\n" + tooltip_override
    app.setStyleSheet(combined_styles)
    print("[STYLES] Unified styles applied!")

    # ========== Инициализация базы данных (как в main.py) ==========
    from database.db_manager import DatabaseManager
    db = DatabaseManager()
    db.initialize_database()
    print("[DATABASE] Database initialized")
    # ================================================================

    # ================================================================

    # Импортируем LoginWindow
    from ui.login_window import LoginWindow

    # Создаём окно входа
    login_window = LoginWindow()
    login_window.show()

    # Настраиваем автологин
    injector = AutoLoginInjector(args.login, args.password, args.screenshot)

    # Запускаем автологин через таймер
    QTimer.singleShot(args.delay, injector.do_login)

    # Запускаем event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

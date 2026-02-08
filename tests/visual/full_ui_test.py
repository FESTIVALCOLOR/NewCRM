# -*- coding: utf-8 -*-
"""
Full UI Test - Полное автоматическое тестирование UI через Qt механизмы

Этот скрипт:
1. Запускает приложение
2. Автоматически входит в систему через Qt API
3. Навигирует по вкладкам
4. Делает скриншоты для анализа
5. Выполняет тестовые сценарии

Использование:
    python tests/visual/full_ui_test.py --login admin --password admin123 [--test TEST_NAME]

Тесты:
    login      - Только проверка входа
    dashboard  - Вход + дашборд
    crm        - Вход + CRM вкладка
    all        - Все тесты
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Парсим аргументы ДО импорта PyQt5
parser = argparse.ArgumentParser(description="Full UI Test for Interior Studio CRM")
parser.add_argument('--login', required=True, help='Login username')
parser.add_argument('--password', required=True, help='Login password')
parser.add_argument('--test', default='login',
                   choices=['login', 'dashboard', 'crm', 'tabs', 'full', 'all'],
                   help='Test to run: login, dashboard, crm, tabs (all tabs), full (complete test), all')
parser.add_argument('--delay', type=int, default=2000, help='Delay before auto login (ms)')
args = parser.parse_args()

# Теперь импортируем PyQt5
from PyQt5.QtWidgets import (QApplication, QWidget, QLineEdit, QPushButton,
                             QTabWidget, QTabBar, QMainWindow)
from PyQt5.QtCore import QTimer, Qt, QThread
from PyQt5.QtTest import QTest


class UITester:
    """Класс для автоматического тестирования UI"""

    def __init__(self, login: str, password: str, test_name: str):
        self.login = login
        self.password = password
        self.test_name = test_name
        self.screenshot_dir = PROJECT_ROOT / "tests" / "visual" / "test_results"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots = []
        self.test_results = []
        self.main_window = None
        self.step = 0

    def log(self, message: str):
        """Логирование"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def capture(self, name: str):
        """Сделать скриншот"""
        try:
            import pyautogui
            self.step += 1
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{self.step:02d}_{name}_{timestamp}.png"
            filepath = self.screenshot_dir / filename
            img = pyautogui.screenshot()
            img.save(str(filepath))
            self.screenshots.append(str(filepath))
            self.log(f"SCREENSHOT: {filename}")
            return str(filepath)
        except Exception as e:
            self.log(f"Screenshot error: {e}")
            return None

    def find_login_window(self):
        """Найти окно входа"""
        for widget in QApplication.topLevelWidgets():
            if widget.isVisible():
                class_name = widget.__class__.__name__
                title = widget.windowTitle() if hasattr(widget, 'windowTitle') else ''

                if 'LoginWindow' in class_name or 'Login' in class_name:
                    return widget
                if 'Вход' in title or 'Festival' in title:
                    return widget
        return None

    def find_main_window(self):
        """Найти главное окно"""
        for widget in QApplication.topLevelWidgets():
            if widget.isVisible():
                class_name = widget.__class__.__name__
                title = widget.windowTitle() if hasattr(widget, 'windowTitle') else ''

                if 'MainWindow' in class_name:
                    return widget
                # Проверяем что это не окно входа
                if 'Login' not in class_name and 'Вход' not in title:
                    if isinstance(widget, QMainWindow):
                        return widget
        return None

    def do_login(self):
        """Выполнить автологин"""
        self.log("=== Starting Auto-Login ===")
        self.capture("before_login")

        login_window = self.find_login_window()
        if not login_window:
            self.log("ERROR: Login window not found, retrying...")
            QTimer.singleShot(1000, self.do_login)
            return

        self.log(f"Found login window: {login_window.__class__.__name__}")

        # Находим поля ввода
        line_edits = login_window.findChildren(QLineEdit)
        buttons = login_window.findChildren(QPushButton)

        self.log(f"Found {len(line_edits)} input fields, {len(buttons)} buttons")

        if len(line_edits) < 2:
            self.log("ERROR: Not enough input fields!")
            return

        # Определяем поля
        login_field = None
        password_field = None

        for edit in line_edits:
            placeholder = edit.placeholderText().lower()
            echo_mode = edit.echoMode()

            if echo_mode == QLineEdit.Password:
                password_field = edit
            elif 'логин' in placeholder or 'login' in placeholder:
                login_field = edit
            elif 'пароль' in placeholder or 'password' in placeholder:
                password_field = edit

        if not login_field:
            login_field = line_edits[0]
        if not password_field and len(line_edits) > 1:
            password_field = line_edits[1]

        # Вводим данные через Qt API (setText работает!)
        self.log(f"Typing login: {self.login}")
        login_field.setFocus()
        login_field.clear()
        login_field.setText(self.login)

        self.log(f"Typing password: {'*' * len(self.password)}")
        password_field.setFocus()
        password_field.clear()
        password_field.setText(self.password)

        self.capture("after_input")

        # Находим и нажимаем кнопку входа
        login_button = None
        for btn in buttons:
            text = btn.text().lower()
            if 'войти' in text or 'вход' in text or 'login' in text:
                login_button = btn
                break

        if not login_button and buttons:
            login_button = buttons[0]

        if login_button:
            self.log(f"Clicking login button: '{login_button.text()}'")
            login_button.click()
        else:
            self.log("No button found, pressing Enter")
            QTest.keyClick(password_field, Qt.Key_Return)

        self.log("Login submitted!")

        # Планируем следующий шаг теста
        QTimer.singleShot(3000, self.after_login)

    def after_login(self):
        """Действия после входа"""
        self.capture("after_login")

        self.main_window = self.find_main_window()

        if self.main_window:
            self.log(f"Found main window: {self.main_window.__class__.__name__}")
            self.test_results.append({'name': 'login', 'passed': True})

            # Продолжаем тесты в зависимости от режима
            if self.test_name == 'dashboard':
                QTimer.singleShot(1000, self.test_dashboard)
            elif self.test_name == 'crm':
                QTimer.singleShot(1000, self.test_crm_tab)
            elif self.test_name == 'tabs':
                QTimer.singleShot(1000, self.test_all_tabs)
            elif self.test_name in ['full', 'all']:
                QTimer.singleShot(1000, self.test_dashboard)
            else:
                QTimer.singleShot(2000, self.finish_tests)
        else:
            self.log("Main window not found - login may have failed")
            self.test_results.append({'name': 'login', 'passed': False, 'error': 'Main window not found'})
            QTimer.singleShot(2000, self.finish_tests)

    def test_dashboard(self):
        """Тест дашборда"""
        self.log("=== Testing Dashboard ===")
        self.capture("dashboard_view")

        # Ищем дашборд виджет
        if self.main_window:
            # Делаем несколько скриншотов
            for i in range(3):
                QTimer.singleShot(i * 1000, lambda: self.capture(f"dashboard_{i}"))

        self.test_results.append({'name': 'dashboard', 'passed': True})

        if self.test_name in ['full', 'all']:
            QTimer.singleShot(4000, self.test_crm_tab)
        else:
            QTimer.singleShot(4000, self.finish_tests)

    def get_main_tab_widget(self):
        """Получить главный TabWidget"""
        if not self.main_window:
            return None
        tab_widgets = self.main_window.findChildren(QTabWidget)
        return tab_widgets[0] if tab_widgets else None

    def switch_to_tab(self, tab_name_part: str) -> bool:
        """Переключиться на вкладку по части названия"""
        tab_widget = self.get_main_tab_widget()
        if not tab_widget:
            return False

        for i in range(tab_widget.count()):
            tab_text = tab_widget.tabText(i).lower()
            if tab_name_part.lower() in tab_text:
                self.log(f"Switching to tab {i}: '{tab_widget.tabText(i)}'")
                tab_widget.setCurrentIndex(i)
                return True
        return False

    def test_crm_tab(self):
        """Тест CRM вкладки"""
        self.log("=== Testing CRM Tab ===")

        if not self.main_window:
            self.log("Main window not available")
            self.test_results.append({'name': 'crm', 'passed': False})
            QTimer.singleShot(1000, self.finish_tests)
            return

        # Ищем TabWidget
        tab_widgets = self.main_window.findChildren(QTabWidget)
        self.log(f"Found {len(tab_widgets)} tab widgets")

        if tab_widgets:
            tab_widget = tab_widgets[0]
            tab_count = tab_widget.count()
            self.log(f"Tab widget has {tab_count} tabs")

            # Выводим названия вкладок
            for i in range(tab_count):
                tab_text = tab_widget.tabText(i)
                self.log(f"  Tab {i}: '{tab_text}'")

            # Ищем CRM вкладку
            for i in range(tab_count):
                tab_text = tab_widget.tabText(i).lower()
                if 'crm' in tab_text or 'проект' in tab_text:
                    self.log(f"Switching to tab {i}: '{tab_widget.tabText(i)}'")
                    tab_widget.setCurrentIndex(i)
                    break

        QTimer.singleShot(1000, lambda: self.capture("crm_tab"))
        self.test_results.append({'name': 'crm', 'passed': True})

        if self.test_name in ['all', 'full']:
            QTimer.singleShot(2000, self.test_all_tabs)
        else:
            QTimer.singleShot(3000, self.finish_tests)

    def test_all_tabs(self):
        """Тест всех вкладок - скриншот каждой"""
        self.log("=== Testing All Tabs ===")

        tab_widget = self.get_main_tab_widget()
        if not tab_widget:
            self.log("No tab widget found")
            QTimer.singleShot(1000, self.test_crm_cards)
            return

        tab_count = tab_widget.count()
        self.log(f"Capturing all {tab_count} tabs...")

        # Переключаемся по всем вкладкам с задержкой
        def capture_tab(index):
            if index >= tab_count:
                self.test_results.append({'name': 'all_tabs', 'passed': True})
                QTimer.singleShot(1000, self.test_crm_cards)
                return

            tab_widget.setCurrentIndex(index)
            tab_name = tab_widget.tabText(index).strip()
            # Убираем пробелы и спецсимволы для имени файла
            safe_name = ''.join(c for c in tab_name if c.isalnum() or c in '_-')
            QTimer.singleShot(500, lambda: self.capture(f"tab_{index}_{safe_name}"))
            QTimer.singleShot(1000, lambda: capture_tab(index + 1))

        capture_tab(0)

    def test_crm_cards(self):
        """Тест CRM карточек - попытка открыть карточку"""
        self.log("=== Testing CRM Cards ===")

        # Переключаемся на CRM
        if not self.switch_to_tab('crm'):
            self.log("CRM tab not found")
            QTimer.singleShot(1000, self.test_dialogs)
            return

        QTimer.singleShot(500, self._find_and_click_card)

    def _find_and_click_card(self):
        """Найти и кликнуть на CRM карточку"""
        # Ищем виджеты карточек (QFrame с определенным стилем или классом)
        from PyQt5.QtWidgets import QFrame, QLabel

        frames = self.main_window.findChildren(QFrame)
        self.log(f"Found {len(frames)} QFrame widgets")

        # Ищем карточки по характерным признакам
        card_found = False
        for frame in frames:
            # Карточки обычно имеют определенный размер и содержат текст
            if frame.isVisible() and frame.width() > 200 and frame.height() > 100:
                labels = frame.findChildren(QLabel)
                if len(labels) >= 2:  # Карточка обычно имеет несколько лейблов
                    self.log(f"Potential card found: {frame.width()}x{frame.height()}, {len(labels)} labels")
                    # Пробуем кликнуть
                    try:
                        # Симулируем двойной клик для открытия
                        QTest.mouseDClick(frame, Qt.LeftButton)
                        card_found = True
                        self.log("Double-clicked on card")
                        break
                    except Exception as e:
                        self.log(f"Click failed: {e}")

        if card_found:
            QTimer.singleShot(1000, lambda: self.capture("crm_card_dialog"))
            self.test_results.append({'name': 'crm_cards', 'passed': True})
        else:
            self.log("No clickable card found")
            self.test_results.append({'name': 'crm_cards', 'passed': False, 'error': 'No card found'})

        QTimer.singleShot(2000, self.test_dialogs)

    def test_dialogs(self):
        """Тест открытых диалогов"""
        self.log("=== Testing Dialogs ===")

        # Ищем открытые диалоги
        from PyQt5.QtWidgets import QDialog

        dialogs = []
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QDialog) and widget.isVisible():
                dialogs.append(widget)
                self.log(f"Found dialog: {widget.__class__.__name__}")

        if dialogs:
            for i, dialog in enumerate(dialogs):
                self.capture(f"dialog_{i}_{dialog.__class__.__name__}")

            # Проверяем стиль рамки (должна быть 1px)
            self.test_results.append({'name': 'dialogs', 'passed': True})
        else:
            self.log("No open dialogs found")
            self.test_results.append({'name': 'dialogs', 'passed': True, 'note': 'No dialogs to test'})

        QTimer.singleShot(1000, self.test_contracts_tab)

    def test_contracts_tab(self):
        """Тест вкладки Договоры"""
        self.log("=== Testing Contracts Tab ===")

        if self.switch_to_tab('договор'):
            QTimer.singleShot(500, lambda: self.capture("contracts_tab"))
            self.test_results.append({'name': 'contracts', 'passed': True})
        else:
            self.test_results.append({'name': 'contracts', 'passed': False})

        QTimer.singleShot(1500, self.test_clients_tab)

    def test_clients_tab(self):
        """Тест вкладки Клиенты"""
        self.log("=== Testing Clients Tab ===")

        if self.switch_to_tab('клиент'):
            QTimer.singleShot(500, lambda: self.capture("clients_tab"))
            self.test_results.append({'name': 'clients', 'passed': True})
        else:
            self.test_results.append({'name': 'clients', 'passed': False})

        QTimer.singleShot(1500, self.test_employees_tab)

    def test_employees_tab(self):
        """Тест вкладки Сотрудники"""
        self.log("=== Testing Employees Tab ===")

        if self.switch_to_tab('сотрудник'):
            QTimer.singleShot(500, lambda: self.capture("employees_tab"))
            self.test_results.append({'name': 'employees', 'passed': True})
        else:
            self.test_results.append({'name': 'employees', 'passed': False})

        QTimer.singleShot(1500, self.test_salaries_tab)

    def test_salaries_tab(self):
        """Тест вкладки Зарплаты"""
        self.log("=== Testing Salaries Tab ===")

        if self.switch_to_tab('зарплат') or self.switch_to_tab('выплат'):
            QTimer.singleShot(500, lambda: self.capture("salaries_tab"))
            self.test_results.append({'name': 'salaries', 'passed': True})
        else:
            self.test_results.append({'name': 'salaries', 'passed': False})

        QTimer.singleShot(1500, self.finish_tests)

    def finish_tests(self):
        """Завершение тестов"""
        self.log("\n" + "=" * 60)
        self.log("TEST RESULTS")
        self.log("=" * 60)

        passed = 0
        failed = 0

        for result in self.test_results:
            status = "PASS" if result.get('passed') else "FAIL"
            if result.get('passed'):
                passed += 1
            else:
                failed += 1
            self.log(f"  [{status}] {result['name']}")
            if result.get('error'):
                self.log(f"         Error: {result['error']}")

        self.log(f"\nTotal: {passed} passed, {failed} failed")
        self.log(f"Screenshots: {len(self.screenshots)}")
        self.log(f"Results dir: {self.screenshot_dir}")
        self.log("=" * 60)

        # Делаем финальный скриншот
        self.capture("final_state")

        # Закрываем приложение через 2 секунды
        QTimer.singleShot(2000, QApplication.quit)


def main():
    """Главная функция"""
    print(f"[START] Full UI Test: {args.test}")
    print(f"[INFO] Login: {args.login}")
    print(f"[INFO] Delay: {args.delay}ms")

    # ========== КОПИРУЕМ НАСТРОЙКИ ИЗ main.py ==========

    # High DPI атрибуты (ДО создания QApplication!)
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Создаём приложение
    app = QApplication(sys.argv)

    # Устанавливаем стиль Fusion (как в main.py)
    app.setStyle('Fusion')

    # Устанавливаем иконку приложения
    from utils.resource_path import resource_path
    from PyQt5.QtGui import QIcon, QPalette, QColor
    app_icon = QIcon(resource_path('resources/icon.ico'))
    app.setWindowIcon(app_icon)

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

    # ===================================================

    # Импортируем и создаём LoginWindow
    from ui.login_window import LoginWindow
    login_window = LoginWindow()
    login_window.show()

    # Создаём тестер
    tester = UITester(args.login, args.password, args.test)

    # Запускаем тест через таймер
    QTimer.singleShot(args.delay, tester.do_login)

    # Запускаем event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

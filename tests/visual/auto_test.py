# -*- coding: utf-8 -*-
"""
Auto Test - Полностью автоматическое тестирование UI с анализом скриншотов

Этот скрипт:
1. Запускает приложение
2. Автоматически входит в систему
3. Навигирует по вкладкам
4. Делает скриншоты для анализа
5. Выполняет действия (открытие диалогов и т.д.)

Использование:
    python tests/visual/auto_test.py --login ЛОГИН --password ПАРОЛЬ [--test TEST_NAME]

Примеры:
    python tests/visual/auto_test.py --login admin --password 123456
    python tests/visual/auto_test.py --login admin --password 123456 --test dashboard
"""

import sys
import os
import time
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pyautogui
import pyperclip
from PIL import Image
import keyboard  # Более надежная библиотека для ввода текста
import ctypes

# Устанавливаем DPI awareness для корректных координат
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.2


class AutoTester:
    """Автоматический тестер UI"""

    def __init__(self, login: str = None, password: str = None):
        self.login = login
        self.password = password
        self.project_root = PROJECT_ROOT
        self.screenshot_dir = self.project_root / "tests" / "visual" / "auto_captures"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.process = None
        self.screenshots = []
        self.test_results = []

        # Координаты элементов окна входа (примерные, нужно уточнить)
        # Определяются относительно центра экрана
        self.screen_width, self.screen_height = pyautogui.size()
        self.center_x = self.screen_width // 2
        self.center_y = self.screen_height // 2

    def log(self, message: str):
        """Логирование"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def capture(self, name: str) -> str:
        """Сделать скриншот"""
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = self.screenshot_dir / filename

        try:
            img = pyautogui.screenshot()
            img.save(str(filepath))
            self.screenshots.append(str(filepath))
            self.log(f"CAPTURE: {filename}")
            return str(filepath)
        except Exception as e:
            self.log(f"ERROR capturing: {e}")
            return None

    def start_app(self, wait: float = 4.0) -> bool:
        """Запустить приложение"""
        app_path = self.project_root / "main.py"
        self.log(f"Starting app: {app_path}")

        try:
            self.process = subprocess.Popen(
                [sys.executable, str(app_path)],
                cwd=str(self.project_root)
            )
            self.log(f"Waiting {wait}s for app to load...")
            time.sleep(wait)

            if self.process.poll() is not None:
                self.log(f"ERROR: App exited with code {self.process.returncode}")
                return False

            self.log("App is running")
            return True
        except Exception as e:
            self.log(f"ERROR starting app: {e}")
            return False

    def stop_app(self):
        """Остановить приложение"""
        if self.process:
            self.log("Stopping app...")
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except:
                self.process.kill()
            self.process = None

    def wait(self, seconds: float):
        """Ожидание"""
        time.sleep(seconds)

    def click(self, x: int, y: int, clicks: int = 1):
        """Клик по координатам"""
        pyautogui.click(x, y, clicks=clicks)
        self.log(f"CLICK: ({x}, {y})")

    def type_text_ru(self, text: str):
        """Ввод текста (включая кириллицу) через буфер обмена"""
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        self.log(f"TYPE: {text}")

    def type_text_en(self, text: str, interval: float = 0.05):
        """Ввод латинского текста напрямую"""
        pyautogui.typewrite(text, interval=interval)
        self.log(f"TYPE: {text}")

    def press(self, key: str):
        """Нажать клавишу"""
        pyautogui.press(key)
        self.log(f"PRESS: {key}")

    def hotkey(self, *keys):
        """Комбинация клавиш"""
        pyautogui.hotkey(*keys)
        self.log(f"HOTKEY: {'+'.join(keys)}")

    def find_window(self, title_contains: str):
        """Найти окно по части заголовка"""
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title_contains)
            if windows:
                return windows[0]
        except Exception as e:
            self.log(f"Window search error: {e}")
        return None

    def focus_app_window(self):
        """Сфокусировать окно приложения"""
        window = self.find_window("Interior Studio") or self.find_window("CRM") or self.find_window("Вход")
        if window:
            try:
                window.activate()
                self.log(f"Focused window: {window.title}")
                self.wait(0.5)
                return True
            except:
                pass
        return False

    def do_login(self) -> bool:
        """
        Выполнить вход в систему

        Логика:
        1. Найти и активировать окно входа
        2. Использовать Win32 API для надежной активации
        3. Ввести логин и пароль
        4. Нажать Enter
        """
        if not self.login or not self.password:
            self.log("Login/password not provided, skipping auto-login")
            return False

        self.log("Attempting auto-login...")

        # Используем Win32 API для принудительной активации окна
        try:
            import win32gui
            import win32con
            import win32api
            import win32process

            # Ищем окно по заголовку
            def find_window_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if any(x in title for x in ['Festival', 'Вход', 'Interior', 'CRM']):
                        windows.append((hwnd, title))
                return True

            windows = []
            win32gui.EnumWindows(find_window_callback, windows)

            if windows:
                hwnd, title = windows[0]
                self.log(f"Found window via Win32: '{title}' (hwnd={hwnd})")

                # МЕТОД ПРИНУДИТЕЛЬНОЙ АКТИВАЦИИ:
                # 1. Получаем thread IDs
                current_thread = win32api.GetCurrentThreadId()
                target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)

                # 2. Присоединяем input threads
                win32process.AttachThreadInput(current_thread, target_thread, True)

                try:
                    # 3. Показываем окно
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                    # 4. Поднимаем окно на передний план
                    win32gui.BringWindowToTop(hwnd)
                    # 5. Активируем окно
                    win32gui.SetForegroundWindow(hwnd)
                    # 6. Устанавливаем фокус
                    win32gui.SetFocus(hwnd)
                finally:
                    # 7. Отсоединяем threads
                    win32process.AttachThreadInput(current_thread, target_thread, False)

                self.wait(0.5)
                self.log(f"Forcefully activated window")

                # Получаем позицию и размер окна
                rect = win32gui.GetWindowRect(hwnd)
                left, top, right, bottom = rect
                width = right - left
                height = bottom - top
                self.log(f"Window rect: ({left}, {top}, {right}, {bottom}), size=({width}x{height})")

                # Вычисляем координаты полей относительно окна
                # На основе анализа скриншотов:
                # - Поле логина примерно на 35% высоты окна
                # - Поле пароля примерно на 45% высоты окна
                center_x = left + width // 2
                login_y = top + int(height * 0.35)
                password_y = top + int(height * 0.45)
                button_y = top + int(height * 0.55)

                self.log(f"Calculated coords: center_x={center_x}, login_y={login_y}, password_y={password_y}")

            else:
                self.log("Window not found via Win32, using pygetwindow...")
                window = self.find_window("Festival") or self.find_window("Вход") or self.find_window("Interior")
                if window:
                    window.activate()
                    self.wait(0.5)
                    center_x = window.left + window.width // 2
                    login_y = window.top + int(window.height * 0.35)
                    password_y = window.top + int(window.height * 0.45)
                    button_y = window.top + int(window.height * 0.55)
                    hwnd = None
                else:
                    self.log("No window found!")
                    return False

        except ImportError:
            self.log("Win32 not available, falling back to pygetwindow")
            window = self.find_window("Festival") or self.find_window("Вход") or self.find_window("Interior")
            if window:
                window.activate()
                self.wait(0.5)
                center_x = window.left + window.width // 2
                login_y = window.top + int(window.height * 0.35)
                password_y = window.top + int(window.height * 0.45)
                button_y = window.top + int(window.height * 0.55)
                hwnd = None
            else:
                return False

        # Делаем скриншот для анализа позиции
        self.capture("before_login")

        try:
            self.log(f"Final coords: center_x={center_x}, login_y={login_y}, password_y={password_y}")

            # Используем АЛЬТЕРНАТИВНЫЙ МЕТОД: SendMessage для отправки текста
            # Это работает даже когда окно не в фокусе!

            # Ищем дочерние окна (QLineEdit)
            def find_edit_controls(parent_hwnd):
                """Найти все Edit контролы в окне"""
                edits = []

                def enum_child_callback(child_hwnd, _):
                    class_name = win32gui.GetClassName(child_hwnd)
                    # Qt использует класс "QWidget" или "Qt..." для своих контролов
                    if 'Edit' in class_name or 'QWidget' in class_name or 'Qt' in class_name:
                        rect = win32gui.GetWindowRect(child_hwnd)
                        edits.append((child_hwnd, class_name, rect))
                    return True

                win32gui.EnumChildWindows(parent_hwnd, enum_child_callback, None)
                return edits

            if 'hwnd' in dir() and hwnd:
                edits = find_edit_controls(hwnd)
                self.log(f"Found {len(edits)} child controls")
                for e in edits[:10]:
                    self.log(f"  Child: hwnd={e[0]}, class={e[1]}, rect={e[2]}")

            # МЕТОД: Минимизируем все окна и разворачиваем только наше
            self.log("Minimizing all windows and maximizing target...")

            try:
                import pygetwindow as gw

                # Минимизируем ВСЕ видимые окна кроме нашего
                all_windows = gw.getAllWindows()
                for w in all_windows:
                    if w.title and 'Festival' not in w.title and 'Вход' not in w.title:
                        try:
                            if w.isMaximized or w.isActive:
                                w.minimize()
                        except:
                            pass
                self.wait(0.5)

                # Ищем наше окно
                windows = gw.getWindowsWithTitle('Festival') + gw.getWindowsWithTitle('Вход')
                if windows:
                    win = windows[0]
                    self.log(f"Found window: {win.title}")

                    # Восстанавливаем окно если оно минимизировано
                    if win.isMinimized:
                        win.restore()
                        self.wait(0.3)

                    # МАКСИМИЗИРУЕМ окно чтобы оно было на переднем плане
                    win.maximize()
                    self.wait(0.5)

                    # Активируем окно
                    win.activate()
                    self.wait(0.5)

                    # После максимизации координаты изменятся
                    # Окно теперь на весь экран (3440x1440)
                    screen_width, screen_height = pyautogui.size()
                    center_x = screen_width // 2  # 1720

                    # На основе точного анализа скриншота (3440x1440):
                    # Поле логина работает на Y=250
                    # Поле пароля: нужно ниже, ~250 + 100 = 350
                    # Кнопка: ~250 + 180 = 430
                    actual_login_y = 250
                    actual_password_y = 350  # Увеличено для попадания в поле
                    actual_button_y = 430   # Увеличено

                    self.log(f"Window MAXIMIZED. Screen: {screen_width}x{screen_height}")
                    self.log(f"Coords: center_x={center_x}, login_y={actual_login_y}, password_y={actual_password_y}, button_y={actual_button_y}")
                else:
                    self.log("Window not found via pygetwindow")
                    win = None

            except Exception as e:
                self.log(f"pygetwindow activation failed: {e}")
                win = None
                # Fallback координаты если pygetwindow не сработал
                screen_width, screen_height = pyautogui.size()
                center_x = screen_width // 2
                actual_login_y = 250
                actual_password_y = 350
                actual_button_y = 430

            self.log(f"Using coords: login_y={actual_login_y}, password_y={actual_password_y}, button_y={actual_button_y}")

            # Используем Win32 PostMessage для отправки клавиш
            # PostMessage работает асинхронно и лучше подходит для Qt
            try:
                WM_CHAR = 0x0102
                WM_KEYDOWN = 0x0100
                WM_KEYUP = 0x0101
                VK_RETURN = 0x0D
                VK_TAB = 0x09

                # ===== МЕТОД: Win32 SendInput - самый низкоуровневый ввод =====
                # Используем ctypes для прямой отправки виртуальных клавиш

                import ctypes
                from ctypes import wintypes

                # Определяем структуры для SendInput
                INPUT_KEYBOARD = 1
                KEYEVENTF_UNICODE = 0x0004
                KEYEVENTF_KEYUP = 0x0002

                class KEYBDINPUT(ctypes.Structure):
                    _fields_ = [
                        ("wVk", wintypes.WORD),
                        ("wScan", wintypes.WORD),
                        ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD),
                        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
                    ]

                class INPUT(ctypes.Structure):
                    class _INPUT(ctypes.Union):
                        _fields_ = [("ki", KEYBDINPUT)]
                    _fields_ = [
                        ("type", wintypes.DWORD),
                        ("_input", _INPUT)
                    ]

                def send_unicode_char(char):
                    """Отправить один Unicode символ через SendInput"""
                    user32 = ctypes.windll.user32

                    # Key down
                    inp = INPUT()
                    inp.type = INPUT_KEYBOARD
                    inp.ki = KEYBDINPUT()
                    inp.ki.wVk = 0
                    inp.ki.wScan = ord(char)
                    inp.ki.dwFlags = KEYEVENTF_UNICODE
                    inp.ki.time = 0
                    inp.ki.dwExtraInfo = None
                    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

                    # Key up
                    inp.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
                    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

                def type_string_sendinput(text, delay=0.05):
                    """Ввести строку через SendInput"""
                    for char in text:
                        send_unicode_char(char)
                        time.sleep(delay)

                # Сначала убедимся что окно активно
                if win:
                    win.activate()
                    self.wait(1.0)

                self.log("=== STARTING LOGIN INPUT (SendInput method) ===")

                # ===== ВВОД ЛОГИНА =====
                # Кликаем в поле логина
                pyautogui.click(center_x, actual_login_y)
                self.wait(0.5)
                self.log(f"Clicked login field at ({center_x}, {actual_login_y})")

                # Ещё раз активируем окно после клика
                if win:
                    win.activate()
                    self.wait(0.3)

                # Вводим логин через SendInput
                type_string_sendinput(self.login, delay=0.08)
                self.log(f"SendInput typed login: {self.login}")
                self.wait(0.8)

                self.capture("debug_01_after_login_sendinput")

                # ===== ВВОД ПАРОЛЯ =====
                # Кликаем в поле пароля
                pyautogui.click(center_x, actual_password_y)
                self.wait(0.5)
                self.log(f"Clicked password field at ({center_x}, {actual_password_y})")

                # Ещё раз активируем окно после клика
                if win:
                    win.activate()
                    self.wait(0.3)

                # Вводим пароль через SendInput
                type_string_sendinput(self.password, delay=0.08)
                self.log(f"SendInput typed password")
                self.wait(0.8)

                self.capture("debug_02_after_password_sendinput")

                # ===== НАЖАТИЕ КНОПКИ =====
                # Нажимаем Enter через SendInput
                VK_RETURN = 0x0D
                user32 = ctypes.windll.user32
                inp = INPUT()
                inp.type = INPUT_KEYBOARD
                inp.ki = KEYBDINPUT()
                inp.ki.wVk = VK_RETURN
                inp.ki.wScan = 0
                inp.ki.dwFlags = 0
                inp.ki.time = 0
                inp.ki.dwExtraInfo = None
                user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
                inp.ki.dwFlags = KEYEVENTF_KEYUP
                user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
                self.log("SendInput pressed Enter")
                self.wait(1.0)

                # Также кликаем на кнопку для надежности
                pyautogui.click(center_x, actual_button_y)
                self.log(f"Clicked login button at ({center_x}, {actual_button_y})")

            except Exception as e:
                self.log(f"PostMessage failed: {e}, falling back to click method")
                # Fallback: клик на кнопку
                pyautogui.click(center_x, actual_button_y)

            self.wait(5)  # Ждем загрузки главного окна

            self.capture("after_login")
            self.log("Login attempt completed")
            return True

        except Exception as e:
            self.log(f"Login error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def navigate_to_tab(self, tab_index: int):
        """
        Навигация по вкладкам главного окна

        Args:
            tab_index: Индекс вкладки (0 = первая)
        """
        # Вкладки обычно находятся в левой части окна
        # Примерные координаты
        tab_x = 100  # Левая часть экрана
        tab_y_start = 200  # Начало списка вкладок
        tab_height = 40  # Высота одной вкладки

        y = tab_y_start + (tab_index * tab_height)
        self.click(tab_x, y)
        self.wait(1)

    def test_login_window(self):
        """Тест окна входа"""
        self.log("=== TEST: Login Window ===")

        if not self.start_app(wait=3):
            return False

        self.capture("login_window_initial")
        self.wait(1)
        self.capture("login_window_1sec")

        self.stop_app()
        return True

    def test_main_window(self):
        """Тест главного окна после входа"""
        self.log("=== TEST: Main Window ===")

        if not self.start_app(wait=4):
            return False

        self.capture("01_app_started")

        # Пробуем войти
        if self.do_login():
            self.wait(2)
            self.capture("02_after_login")

            # Делаем несколько скриншотов разных состояний
            for i in range(3):
                self.wait(1)
                self.capture(f"03_main_window_{i}")

        self.stop_app()
        return True

    def test_dashboard_buttons(self):
        """Тест кнопок фильтров на дашборде"""
        self.log("=== TEST: Dashboard Buttons ===")

        if not self.start_app(wait=4):
            return False

        self.capture("dashboard_01_start")

        if self.do_login():
            self.wait(2)
            self.capture("dashboard_02_logged_in")

            # Ищем дашборд (обычно вверху)
            self.wait(1)
            self.capture("dashboard_03_view")

        self.stop_app()
        return True

    def test_crm_tab(self):
        """Тест CRM вкладки"""
        self.log("=== TEST: CRM Tab ===")

        if not self.start_app(wait=4):
            return False

        if self.do_login():
            self.wait(2)

            # Пробуем кликнуть на CRM вкладку (обычно одна из первых)
            self.navigate_to_tab(1)  # Примерно
            self.wait(2)
            self.capture("crm_tab_01")

            # Делаем еще скриншоты
            self.wait(1)
            self.capture("crm_tab_02")

        self.stop_app()
        return True

    def test_dialog_styles(self):
        """Тест стилей диалогов"""
        self.log("=== TEST: Dialog Styles ===")

        if not self.start_app(wait=4):
            return False

        if self.do_login():
            self.wait(2)
            self.capture("dialog_01_main")

            # Здесь можно добавить открытие конкретных диалогов
            # например, клик на карточку CRM для открытия диалога редактирования

        self.stop_app()
        return True

    def run_all_tests(self):
        """Запустить все тесты"""
        tests = [
            ('login_window', self.test_login_window),
            ('main_window', self.test_main_window),
            ('dashboard_buttons', self.test_dashboard_buttons),
            ('crm_tab', self.test_crm_tab),
        ]

        for test_name, test_func in tests:
            self.log(f"\n{'='*50}")
            self.log(f"Running: {test_name}")
            self.log(f"{'='*50}")

            try:
                result = test_func()
                self.test_results.append({
                    'name': test_name,
                    'passed': result,
                    'error': None
                })
            except Exception as e:
                self.log(f"Test failed with error: {e}")
                self.test_results.append({
                    'name': test_name,
                    'passed': False,
                    'error': str(e)
                })
                self.stop_app()  # Убеждаемся что приложение остановлено

            self.wait(2)  # Пауза между тестами

    def print_summary(self):
        """Вывести итоги тестирования"""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Screenshots directory: {self.screenshot_dir}")
        print(f"Total screenshots: {len(self.screenshots)}")
        print(f"\nTest Results:")

        passed = 0
        failed = 0
        for result in self.test_results:
            status = "PASS" if result['passed'] else "FAIL"
            if result['passed']:
                passed += 1
            else:
                failed += 1
            print(f"  [{status}] {result['name']}")
            if result['error']:
                print(f"         Error: {result['error']}")

        print(f"\nTotal: {passed} passed, {failed} failed")
        print(f"{'='*60}")

        # Список скриншотов
        print("\nScreenshots captured:")
        for s in self.screenshots:
            print(f"  - {Path(s).name}")


def main():
    parser = argparse.ArgumentParser(description="Auto Test for Interior Studio CRM")
    parser.add_argument('--login', help='Login username')
    parser.add_argument('--password', help='Login password')
    parser.add_argument('--test', default='all',
                       choices=['all', 'login', 'main', 'dashboard', 'crm', 'dialogs'],
                       help='Test to run')

    args = parser.parse_args()

    tester = AutoTester(login=args.login, password=args.password)

    test_map = {
        'login': tester.test_login_window,
        'main': tester.test_main_window,
        'dashboard': tester.test_dashboard_buttons,
        'crm': tester.test_crm_tab,
        'dialogs': tester.test_dialog_styles,
        'all': tester.run_all_tests,
    }

    try:
        test_func = test_map.get(args.test, tester.run_all_tests)
        test_func()
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Stopping...")
    finally:
        tester.stop_app()
        tester.print_summary()


if __name__ == "__main__":
    main()

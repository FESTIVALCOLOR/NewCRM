# -*- coding: utf-8 -*-
"""
Visual Tester - Автоматическое визуальное тестирование PyQt5 приложения
Использует PyAutoGUI для управления и скриншоты для анализа

Использование:
    python tests/visual/visual_tester.py [--test TEST_NAME] [--screenshot-dir DIR]

Примеры:
    python tests/visual/visual_tester.py --test login
    python tests/visual/visual_tester.py --test all
    python tests/visual/visual_tester.py --screenshot-dir ./screenshots
"""

import sys
import os
import time
import subprocess
import argparse
import json
from datetime import datetime
from pathlib import Path

# Добавляем корень проекта в path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("[WARN] PyAutoGUI not installed. Run: pip install pyautogui")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[WARN] Pillow not installed. Run: pip install Pillow")


class VisualTester:
    """
    Визуальный тестер для PyQt5 приложения Interior Studio CRM
    """

    def __init__(self, screenshot_dir: str = None, app_path: str = None):
        """
        Args:
            screenshot_dir: Директория для сохранения скриншотов
            app_path: Путь к main.py приложения
        """
        self.project_root = PROJECT_ROOT
        self.app_path = app_path or str(self.project_root / "main.py")
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else self.project_root / "tests" / "visual" / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        self.app_process = None
        self.test_results = []
        self.current_test = None

        # Настройки PyAutoGUI
        if PYAUTOGUI_AVAILABLE:
            pyautogui.FAILSAFE = True  # Перемещение в угол останавливает
            pyautogui.PAUSE = 0.5  # Пауза между действиями

    def start_app(self, wait_time: float = 5.0) -> bool:
        """
        Запустить приложение

        Args:
            wait_time: Время ожидания загрузки (секунды)

        Returns:
            True если приложение запущено успешно
        """
        print(f"[TEST] Запуск приложения: {self.app_path}")

        try:
            # Запускаем приложение в фоне
            self.app_process = subprocess.Popen(
                [sys.executable, self.app_path],
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Ждем загрузки
            print(f"[TEST] Ожидание загрузки {wait_time} сек...")
            time.sleep(wait_time)

            # Проверяем что процесс жив
            if self.app_process.poll() is not None:
                stdout, stderr = self.app_process.communicate()
                print(f"[ERROR] Приложение завершилось с кодом {self.app_process.returncode}")
                print(f"STDOUT: {stdout.decode('utf-8', errors='ignore')[:500]}")
                print(f"STDERR: {stderr.decode('utf-8', errors='ignore')[:500]}")
                return False

            print("[TEST] Приложение запущено успешно")
            return True

        except Exception as e:
            print(f"[ERROR] Ошибка запуска приложения: {e}")
            return False

    def stop_app(self):
        """Остановить приложение"""
        if self.app_process:
            print("[TEST] Остановка приложения...")
            self.app_process.terminate()
            try:
                self.app_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.app_process.kill()
            self.app_process = None
            print("[TEST] Приложение остановлено")

    def take_screenshot(self, name: str = None) -> str:
        """
        Сделать скриншот

        Args:
            name: Имя скриншота (без расширения)

        Returns:
            Путь к сохраненному скриншоту
        """
        if not PYAUTOGUI_AVAILABLE:
            print("[ERROR] PyAutoGUI не установлен")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if name:
            filename = f"{name}_{timestamp}.png"
        else:
            filename = f"screenshot_{timestamp}.png"

        filepath = self.screenshot_dir / filename

        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(str(filepath))
            print(f"[SCREENSHOT] Сохранен: {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"[ERROR] Ошибка скриншота: {e}")
            return None

    def take_window_screenshot(self, window_title: str = None, name: str = None) -> str:
        """
        Сделать скриншот конкретного окна

        Args:
            window_title: Заголовок окна (частичное совпадение)
            name: Имя скриншота

        Returns:
            Путь к скриншоту
        """
        if not PYAUTOGUI_AVAILABLE:
            return None

        # Пока делаем полный скриншот
        # TODO: Добавить поиск окна по заголовку через win32gui на Windows
        return self.take_screenshot(name)

    def click(self, x: int, y: int, clicks: int = 1):
        """Клик по координатам"""
        if PYAUTOGUI_AVAILABLE:
            pyautogui.click(x, y, clicks=clicks)
            print(f"[ACTION] Click ({x}, {y})")

    def type_text(self, text: str, interval: float = 0.05):
        """Ввод текста"""
        if PYAUTOGUI_AVAILABLE:
            pyautogui.typewrite(text, interval=interval)
            print(f"[ACTION] Type: {text[:20]}...")

    def press_key(self, key: str):
        """Нажатие клавиши"""
        if PYAUTOGUI_AVAILABLE:
            pyautogui.press(key)
            print(f"[ACTION] Press: {key}")

    def hotkey(self, *keys):
        """Комбинация клавиш"""
        if PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey(*keys)
            print(f"[ACTION] Hotkey: {'+'.join(keys)}")

    def wait(self, seconds: float):
        """Ожидание"""
        print(f"[WAIT] {seconds} сек...")
        time.sleep(seconds)

    def find_on_screen(self, image_path: str, confidence: float = 0.9):
        """
        Найти изображение на экране

        Args:
            image_path: Путь к эталонному изображению
            confidence: Порог совпадения (0.0 - 1.0)

        Returns:
            (x, y) координаты центра или None
        """
        if not PYAUTOGUI_AVAILABLE:
            return None

        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                print(f"[FOUND] {image_path} at ({center.x}, {center.y})")
                return (center.x, center.y)
            else:
                print(f"[NOT FOUND] {image_path}")
                return None
        except Exception as e:
            print(f"[ERROR] Поиск изображения: {e}")
            return None

    def start_test(self, test_name: str):
        """Начать тест"""
        self.current_test = {
            'name': test_name,
            'start_time': datetime.now().isoformat(),
            'screenshots': [],
            'steps': [],
            'passed': None,
            'error': None
        }
        print(f"\n{'='*60}")
        print(f"[TEST START] {test_name}")
        print(f"{'='*60}")

    def log_step(self, step: str, passed: bool = True):
        """Залогировать шаг теста"""
        if self.current_test:
            self.current_test['steps'].append({
                'step': step,
                'passed': passed,
                'time': datetime.now().isoformat()
            })
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {step}")

    def end_test(self, passed: bool, error: str = None):
        """Завершить тест"""
        if self.current_test:
            self.current_test['passed'] = passed
            self.current_test['error'] = error
            self.current_test['end_time'] = datetime.now().isoformat()
            self.test_results.append(self.current_test)

        status = "PASSED" if passed else "FAILED"
        print(f"{'='*60}")
        print(f"[TEST END] {self.current_test['name']}: {status}")
        if error:
            print(f"[ERROR] {error}")
        print(f"{'='*60}\n")

        self.current_test = None

    def save_report(self, filename: str = None) -> str:
        """
        Сохранить отчет о тестировании

        Returns:
            Путь к отчету
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.json"

        report_path = self.screenshot_dir / filename

        report = {
            'generated_at': datetime.now().isoformat(),
            'total_tests': len(self.test_results),
            'passed': sum(1 for t in self.test_results if t['passed']),
            'failed': sum(1 for t in self.test_results if not t['passed']),
            'tests': self.test_results
        }

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n[REPORT] Сохранен: {report_path}")
        print(f"[SUMMARY] Всего: {report['total_tests']}, Passed: {report['passed']}, Failed: {report['failed']}")

        return str(report_path)


# ===========================================
# КОНКРЕТНЫЕ ТЕСТЫ
# ===========================================

class CRMVisualTests:
    """Визуальные тесты для CRM"""

    def __init__(self, tester: VisualTester):
        self.tester = tester

    def test_login_window(self):
        """Тест окна входа"""
        self.tester.start_test("Login Window")

        try:
            # Запускаем приложение
            if not self.tester.start_app(wait_time=3):
                self.tester.end_test(False, "Не удалось запустить приложение")
                return False

            # Скриншот окна входа
            screenshot = self.tester.take_screenshot("login_window")
            if screenshot:
                self.tester.current_test['screenshots'].append(screenshot)
                self.tester.log_step("Скриншот окна входа сделан", True)

            # Здесь можно добавить проверки элементов через image matching
            # или OCR для проверки текста

            self.tester.end_test(True)
            return True

        except Exception as e:
            self.tester.end_test(False, str(e))
            return False
        finally:
            self.tester.stop_app()

    def test_main_window_after_login(self, username: str = None, password: str = None):
        """Тест главного окна после входа"""
        self.tester.start_test("Main Window After Login")

        try:
            if not self.tester.start_app(wait_time=3):
                self.tester.end_test(False, "Не удалось запустить приложение")
                return False

            # Скриншот до логина
            self.tester.take_screenshot("before_login")

            # Если есть credentials - пробуем войти
            # TODO: Реализовать автоматический вход

            self.tester.wait(2)
            self.tester.take_screenshot("after_wait")

            self.tester.end_test(True)
            return True

        except Exception as e:
            self.tester.end_test(False, str(e))
            return False
        finally:
            self.tester.stop_app()

    def test_dashboard_buttons(self):
        """Тест кнопок фильтров на дашборде"""
        self.tester.start_test("Dashboard Filter Buttons")

        try:
            if not self.tester.start_app(wait_time=5):
                self.tester.end_test(False, "Не удалось запустить приложение")
                return False

            # Скриншот дашборда
            screenshot = self.tester.take_screenshot("dashboard")
            if screenshot:
                self.tester.log_step("Скриншот дашборда сделан", True)

            # TODO: Добавить проверку что кнопки помещаются (через image analysis)

            self.tester.end_test(True)
            return True

        except Exception as e:
            self.tester.end_test(False, str(e))
            return False
        finally:
            self.tester.stop_app()


def run_visual_tests(test_name: str = "all", screenshot_dir: str = None):
    """
    Запустить визуальные тесты

    Args:
        test_name: Имя теста или "all" для всех
        screenshot_dir: Директория для скриншотов
    """
    if not PYAUTOGUI_AVAILABLE:
        print("[ERROR] PyAutoGUI не установлен. Установите: pip install pyautogui")
        return False

    tester = VisualTester(screenshot_dir=screenshot_dir)
    crm_tests = CRMVisualTests(tester)

    available_tests = {
        'login': crm_tests.test_login_window,
        'main_window': crm_tests.test_main_window_after_login,
        'dashboard': crm_tests.test_dashboard_buttons,
    }

    if test_name == "all":
        for name, test_func in available_tests.items():
            print(f"\n>>> Running test: {name}")
            test_func()
    elif test_name in available_tests:
        available_tests[test_name]()
    else:
        print(f"[ERROR] Unknown test: {test_name}")
        print(f"Available tests: {', '.join(available_tests.keys())}")
        return False

    # Сохраняем отчет
    tester.save_report()
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visual Tester for Interior Studio CRM")
    parser.add_argument('--test', default='all', help='Test name or "all"')
    parser.add_argument('--screenshot-dir', help='Directory for screenshots')

    args = parser.parse_args()

    run_visual_tests(test_name=args.test, screenshot_dir=args.screenshot_dir)

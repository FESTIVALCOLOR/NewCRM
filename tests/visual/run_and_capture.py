# -*- coding: utf-8 -*-
"""
Run and Capture - Запуск приложения и захват скриншотов для анализа Claude

Этот скрипт:
1. Запускает приложение
2. Делает скриншоты на разных этапах
3. Сохраняет их для анализа

Использование:
    python tests/visual/run_and_capture.py [--scenario SCENARIO]

Сценарии:
    login      - Только окно входа
    dashboard  - Вход + дашборд
    crm        - Вход + CRM вкладка
    contracts  - Вход + вкладка договоров
    full       - Полный прогон всех вкладок
"""

import sys
import os
import time
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

# Добавляем корень проекта
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.3
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


class AppRunner:
    """Запуск и управление приложением"""

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.screenshot_dir = self.project_root / "tests" / "visual" / "captures"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.process = None
        self.screenshots = []

    def capture(self, name: str) -> str:
        """Сделать скриншот с именем"""
        if not HAS_PYAUTOGUI:
            print(f"[SKIP] PyAutoGUI not available for: {name}")
            return None

        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = self.screenshot_dir / filename

        try:
            img = pyautogui.screenshot()
            img.save(str(filepath))
            self.screenshots.append(str(filepath))
            print(f"[CAPTURE] {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"[ERROR] Screenshot failed: {e}")
            return None

    def start(self, wait: float = 3.0) -> bool:
        """Запустить приложение"""
        app_path = self.project_root / "main.py"
        print(f"[START] Launching {app_path}")

        try:
            self.process = subprocess.Popen(
                [sys.executable, str(app_path)],
                cwd=str(self.project_root)
            )
            print(f"[WAIT] {wait}s for app to load...")
            time.sleep(wait)

            if self.process.poll() is not None:
                print(f"[ERROR] App exited with code {self.process.returncode}")
                return False

            print("[OK] App is running")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to start: {e}")
            return False

    def stop(self):
        """Остановить приложение"""
        if self.process:
            print("[STOP] Terminating app...")
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except:
                self.process.kill()
            self.process = None

    def wait(self, seconds: float):
        """Ждать"""
        time.sleep(seconds)

    def click_at(self, x: int, y: int):
        """Клик по координатам"""
        if HAS_PYAUTOGUI:
            pyautogui.click(x, y)
            print(f"[CLICK] ({x}, {y})")

    def type_text(self, text: str):
        """Ввести текст"""
        if HAS_PYAUTOGUI:
            # Для кириллицы используем clipboard
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            print(f"[TYPE] {text}")

    def press(self, key: str):
        """Нажать клавишу"""
        if HAS_PYAUTOGUI:
            pyautogui.press(key)
            print(f"[PRESS] {key}")

    def hotkey(self, *keys):
        """Комбинация клавиш"""
        if HAS_PYAUTOGUI:
            pyautogui.hotkey(*keys)
            print(f"[HOTKEY] {'+'.join(keys)}")


def scenario_login_only(runner: AppRunner):
    """Сценарий: только окно входа"""
    print("\n=== SCENARIO: Login Window ===\n")

    if not runner.start(wait=3):
        return False

    runner.capture("01_login_window")
    runner.wait(1)
    runner.capture("02_login_window_2")

    runner.stop()
    return True


def scenario_dashboard(runner: AppRunner):
    """Сценарий: вход и дашборд"""
    print("\n=== SCENARIO: Dashboard ===\n")

    if not runner.start(wait=3):
        return False

    runner.capture("01_login_window")

    # TODO: Автоматический вход (нужны координаты полей)
    # runner.click_at(x, y)  # поле логина
    # runner.type_text("admin")
    # runner.click_at(x, y)  # поле пароля
    # runner.type_text("password")
    # runner.click_at(x, y)  # кнопка входа

    runner.wait(2)
    runner.capture("02_after_wait")

    runner.stop()
    return True


def scenario_full(runner: AppRunner):
    """Сценарий: полный прогон"""
    print("\n=== SCENARIO: Full Test ===\n")

    if not runner.start(wait=4):
        return False

    runner.capture("01_initial")

    # Делаем серию скриншотов с интервалом
    for i in range(2, 6):
        runner.wait(1)
        runner.capture(f"{i:02d}_state")

    runner.stop()
    return True


def main():
    parser = argparse.ArgumentParser(description="Run app and capture screenshots")
    parser.add_argument('--scenario', default='login',
                       choices=['login', 'dashboard', 'crm', 'contracts', 'full'],
                       help='Scenario to run')

    args = parser.parse_args()

    if not HAS_PYAUTOGUI:
        print("[ERROR] PyAutoGUI not installed!")
        print("Install with: pip install pyautogui pyperclip Pillow")
        return 1

    runner = AppRunner()

    scenarios = {
        'login': scenario_login_only,
        'dashboard': scenario_dashboard,
        'full': scenario_full,
    }

    scenario_func = scenarios.get(args.scenario, scenario_login_only)

    try:
        success = scenario_func(runner)
    finally:
        runner.stop()

    print(f"\n{'='*50}")
    print(f"Screenshots saved to: {runner.screenshot_dir}")
    print(f"Total captures: {len(runner.screenshots)}")
    for s in runner.screenshots:
        print(f"  - {s}")
    print(f"{'='*50}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

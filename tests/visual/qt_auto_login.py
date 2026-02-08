# -*- coding: utf-8 -*-
"""
Qt Auto Login - Автологин используя внутренние механизмы PyQt5

Этот скрипт интегрируется напрямую с PyQt5 приложением для автоматического входа.
"""

import sys
import os
from pathlib import Path

# Добавляем корень проекта
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt5.QtWidgets import QApplication, QLineEdit, QPushButton
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtTest import QTest
import time


class QtAutoLogin:
    """Автологин через Qt механизмы"""

    def __init__(self, login: str, password: str):
        self.login = login
        self.password = password
        self.app = None
        self.login_window = None

    def find_login_window(self):
        """Найти окно входа среди виджетов приложения"""
        for widget in QApplication.topLevelWidgets():
            # Ищем по названию класса или заголовку
            class_name = widget.__class__.__name__
            title = widget.windowTitle() if hasattr(widget, 'windowTitle') else ''

            print(f"Found widget: {class_name}, title: '{title}'")

            if 'Login' in class_name or 'Вход' in title or 'Festival' in title:
                return widget

        return None

    def find_input_fields(self, parent):
        """Найти поля ввода в окне"""
        line_edits = parent.findChildren(QLineEdit)
        buttons = parent.findChildren(QPushButton)

        print(f"Found {len(line_edits)} QLineEdit fields")
        print(f"Found {len(buttons)} QPushButton buttons")

        for i, edit in enumerate(line_edits):
            placeholder = edit.placeholderText()
            text = edit.text()
            echo = edit.echoMode()
            print(f"  LineEdit {i}: placeholder='{placeholder}', text='{text}', echoMode={echo}")

        for i, btn in enumerate(buttons):
            text = btn.text()
            print(f"  Button {i}: text='{text}'")

        return line_edits, buttons

    def do_login(self):
        """Выполнить вход"""
        self.login_window = self.find_login_window()

        if not self.login_window:
            print("Login window not found!")
            return False

        print(f"Found login window: {self.login_window}")

        line_edits, buttons = self.find_input_fields(self.login_window)

        if len(line_edits) < 2:
            print("Not enough input fields found!")
            return False

        # Обычно первое поле - логин, второе - пароль
        login_field = line_edits[0]
        password_field = line_edits[1]

        # Ищем кнопку входа
        login_button = None
        for btn in buttons:
            text = btn.text().lower()
            if 'войти' in text or 'вход' in text or 'login' in text or 'enter' in text:
                login_button = btn
                break

        if not login_button and buttons:
            login_button = buttons[0]  # Берём первую кнопку

        print(f"Login field: {login_field}")
        print(f"Password field: {password_field}")
        print(f"Login button: {login_button}")

        # Вводим данные через QTest
        print(f"Typing login: {self.login}")
        login_field.setFocus()
        login_field.clear()
        QTest.keyClicks(login_field, self.login)

        print(f"Typing password: {'*' * len(self.password)}")
        password_field.setFocus()
        password_field.clear()
        QTest.keyClicks(password_field, self.password)

        print("Clicking login button...")
        if login_button:
            QTest.mouseClick(login_button, Qt.LeftButton)

        print("Login completed!")
        return True


def setup_auto_login(login: str, password: str, delay_ms: int = 3000):
    """
    Настроить автологин с задержкой.
    Вызывается из main.py перед запуском приложения.

    Args:
        login: Логин пользователя
        password: Пароль пользователя
        delay_ms: Задержка перед автологином (мс)
    """
    auto_login = QtAutoLogin(login, password)

    # Запускаем автологин через таймер после загрузки UI
    QTimer.singleShot(delay_ms, auto_login.do_login)

    return auto_login


if __name__ == "__main__":
    # Тест - запуск с модифицированным main.py
    print("This module should be imported from main.py")
    print("Usage: Add 'from tests.visual.qt_auto_login import setup_auto_login' to main.py")

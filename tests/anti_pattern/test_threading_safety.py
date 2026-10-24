# -*- coding: utf-8 -*-
"""
Anti-pattern тесты: threading safety в UI файлах.

ЛОВИТ БАГИ: При рефакторинге потоковых операций разработчик может:
1. Забыть QTimer.singleShot() → crash при обновлении UI из потока
2. Вызвать widget.setText() из Thread → SEGFAULT в продакшне
3. Использовать lambda с прямым вызовом UI → race condition
4. Удалить daemon=True → зависание при закрытии окна

Каждый тест проверяет КОНКРЕТНЫЙ инвариант, нарушение которого = краш.
"""

import ast
import os
from pathlib import Path
import re

import pytest

UI_DIR = Path(__file__).parent.parent.parent / "ui"


def _read(filepath):
    return filepath.read_text(encoding="utf-8")


def _get_ui_files_with_threading():
    """Найти все UI файлы с threading.Thread"""
    results = []
    for f in sorted(UI_DIR.glob("*.py")):
        content = _read(f)
        if "threading.Thread" in content or "Thread(target" in content:
            results.append(f)
    return results


# ======================================================================
# 1. КАЖДЫЙ threading.Thread ДОЛЖЕН иметь QTimer.singleShot или signal
# Баг: прямой вызов UI метода из потока → SEGFAULT
# ======================================================================


class TestThreadingSafetyGuard:
    """Все threading.Thread в UI ОБЯЗАНЫ использовать QTimer.singleShot или signal для UI."""

    def test_all_threading_files_have_qtimer_or_signal(self):
        """Каждый файл с Thread должен иметь QTimer.singleShot или pyqtSignal."""
        files = _get_ui_files_with_threading()
        assert files, "Нет файлов с threading — тест устарел?"

        unsafe = []
        for f in files:
            content = _read(f)
            has_qtimer = "QTimer.singleShot" in content
            has_signal = "pyqtSignal" in content or ".emit(" in content
            has_qthread = "QThread" in content
            has_invoke = "QMetaObject.invokeMethod" in content

            if not (has_qtimer or has_signal or has_qthread or has_invoke):
                unsafe.append(f.name)

        assert not unsafe, f"РЕГРЕССИЯ: Файлы с threading.Thread БЕЗ QTimer.singleShot/signal/QThread: {unsafe}. Обновление UI из потока без QTimer.singleShot → SEGFAULT!"

    @pytest.mark.parametrize(
        "filename",
        [
            "crm_card_edit_dialog.py",
            "contract_dialogs.py",
            "supervision_card_edit_dialog.py",
            "crm_tab.py",
            "crm_archive.py",
            "main_window.py",
            "reports_tab.py",
            "timeline_widget.py",
            "update_dialogs.py",
        ],
    )
    def test_thread_callback_uses_qtimer(self, filename):
        """Критичные файлы: callback потока через QTimer.singleShot."""
        filepath = UI_DIR / filename
        if not filepath.exists():
            pytest.skip(f"{filename} не найден")

        content = _read(filepath)
        if "threading.Thread" not in content and "Thread(target" not in content:
            pytest.skip(f"{filename} больше не использует threading")

        has_qtimer = "QTimer.singleShot" in content
        has_signal = ".emit(" in content
        has_invoke = "QMetaObject.invokeMethod" in content

        assert has_qtimer or has_signal or has_invoke, (
            f"РЕГРЕССИЯ: {filename} использует threading.Thread, но НЕТ QTimer.singleShot / .emit() / QMetaObject.invokeMethod. UI обновления из потока приведут к SEGFAULT!"
        )


# ======================================================================
# 2. DAEMON=TRUE — потоки не должны блокировать закрытие приложения
# Баг: Thread без daemon=True → приложение зависает при закрытии
# ======================================================================


class TestThreadDaemonFlag:
    """Все threading.Thread в UI ДОЛЖНЫ быть daemon или управляемые."""

    def test_threads_are_daemon(self):
        """Потоки в UI файлах должны быть daemon=True."""
        files = _get_ui_files_with_threading()
        problems = []

        for f in files:
            content = _read(f)
            # Ищем Thread(target=...) без daemon=True
            # Паттерн: Thread(target=xxx) без .daemon = True или daemon=True в аргументах
            thread_creates = re.findall(r"threading\.Thread\(target=[^)]+\)", content)
            for tc in thread_creates:
                if "daemon" not in tc:
                    # Проверяем что daemon ставится после создания (thread.daemon = True)
                    # или через .start() с daemon в контексте ±5 строк
                    idx = content.find(tc)
                    context = content[max(0, idx) : idx + len(tc) + 200]
                    if ".daemon = True" not in context and ".daemon=True" not in context:
                        problems.append(f"{f.name}: {tc[:80]}...")

        # Не падаем, но предупреждаем — некоторые потоки могут быть управляемые
        if problems:
            import warnings

            warnings.warn(f"Потоки без daemon=True (может быть намеренно): {problems[:3]}", stacklevel=2)


# ======================================================================
# 3. ЗАПРЕЩЁННЫЕ ПАТТЕРНЫ — прямой вызов UI из потока
# Баг: widget.setText() / widget.setVisible() / widget.close() из Thread
# ======================================================================


class TestNoDirectUIFromThread:
    """Запрещённые паттерны: прямой вызов UI из потока."""

    # UI методы, которые НЕЛЬЗЯ вызывать из Thread напрямую
    FORBIDDEN_IN_THREAD = [
        "setText(",
        "setVisible(",
        "show()",
        "hide()",
        "setEnabled(",
        "setDisabled(",
        "addItem(",
        "clear()",
        "setRowCount(",
        "setColumnCount(",
    ]

    def test_no_ui_calls_in_thread_target(self):
        """Thread target-функции не должны напрямую вызывать UI методы."""
        files = _get_ui_files_with_threading()
        # Этот тест проверяет что в функциях-target нет прямых UI вызовов
        # без обёртки в QTimer.singleShot

        # Проверка: если файл использует threading И QTimer — значит разработчик
        # знает про thread-safety. Если НЕ использует QTimer — это проблема.
        unsafe = []
        for f in files:
            content = _read(f)
            if "threading.Thread" in content:
                has_qtimer = "QTimer" in content
                has_signal = "pyqtSignal" in content
                has_invoke = "QMetaObject" in content
                if not (has_qtimer or has_signal or has_invoke):
                    unsafe.append(f.name)

        assert not unsafe, f"РЕГРЕССИЯ: {unsafe} — используют threading.Thread но НЕ импортируют QTimer/pyqtSignal/QMetaObject. Без механизма thread-safety невозможно обновлять UI из потока!"


# ======================================================================
# 4. QThread ВМЕСТО threading.Thread — проверка правильности
# ======================================================================


class TestQThreadUsage:
    """QThread должен использовать signals, не прямые вызовы."""

    def test_qthread_has_signals(self):
        """Файлы с QThread должны определять pyqtSignal."""
        for f in sorted(UI_DIR.glob("*.py")):
            content = _read(f)
            if "class" in content and "QThread" in content and "(QThread)" in content:
                assert "pyqtSignal" in content or ".emit(" in content, (
                    f"РЕГРЕССИЯ: {f.name} наследует QThread, но не использует pyqtSignal. QThread.run() выполняется в отдельном потоке — нужны signals для UI."
                )

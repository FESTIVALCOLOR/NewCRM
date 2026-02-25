# -*- coding: utf-8 -*-
"""
Unit-тесты для utils/button_debounce.py
Проверяет декоратор защиты от двойных кликов.
"""
import sys
import os
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest

from utils.button_debounce import debounce_click, _last_click_time


@pytest.fixture(autouse=True)
def clear_debounce_state():
    """Очищать глобальное состояние debounce перед каждым тестом."""
    _last_click_time.clear()
    yield
    _last_click_time.clear()


def test_debounce_click_basic_call():
    """Декоратор не блокирует первый вызов функции."""
    call_count = [0]

    @debounce_click
    def my_action():
        call_count[0] += 1

    my_action()
    assert call_count[0] == 1, "Первый вызов должен выполниться"


def test_debounce_click_blocks_rapid_repeat():
    """Повторный вызов в пределах интервала должен быть заблокирован."""
    call_count = [0]

    @debounce_click(delay_ms=500)
    def my_action():
        call_count[0] += 1

    my_action()
    my_action()  # Должен быть проигнорирован
    my_action()  # Должен быть проигнорирован
    assert call_count[0] == 1, "Повторные быстрые вызовы должны игнорироваться"


def test_debounce_click_allows_after_delay():
    """После истечения задержки вызов должен проходить снова."""
    call_count = [0]

    @debounce_click(delay_ms=50)
    def my_action():
        call_count[0] += 1

    my_action()
    time.sleep(0.1)  # Ждём 100ms > 50ms задержка
    my_action()
    assert call_count[0] == 2, "После истечения задержки вызов должен выполниться"


def test_debounce_click_strips_bool_arg():
    """Qt передаёт bool checked — декоратор должен его отбросить."""
    received_args = []

    @debounce_click
    def my_action(*args):
        received_args.extend(args)

    my_action(True)  # Имитация Qt clicked сигнала с bool=True
    assert received_args == [], "Bool аргумент от Qt сигнала должен быть отброшен"


def test_debounce_click_strips_bool_false_arg():
    """Qt передаёт bool=False — декоратор должен его отбросить."""
    received_args = []

    @debounce_click
    def my_action(*args):
        received_args.extend(args)

    my_action(False)  # Имитация Qt clicked сигнала с bool=False
    assert received_args == [], "Bool=False аргумент от Qt сигнала должен быть отброшен"


def test_debounce_click_preserves_non_bool_args():
    """Не-bool аргументы должны передаваться в оригинальную функцию."""
    received_args = []

    @debounce_click
    def my_action(*args):
        received_args.extend(args)

    my_action("hello", 42)
    assert received_args == ["hello", 42], "Не-bool аргументы должны сохраняться"


def test_debounce_click_returns_none_when_blocked():
    """Заблокированный вызов должен возвращать None."""

    @debounce_click(delay_ms=500)
    def my_action():
        return "result"

    my_action()  # Первый вызов — выполняется
    result = my_action()  # Второй вызов — заблокирован
    assert result is None, "Заблокированный вызов должен возвращать None"


def test_debounce_click_different_functions_independent():
    """Разные задекорированные функции имеют независимые счётчики времени."""
    count_a = [0]
    count_b = [0]

    @debounce_click(delay_ms=500)
    def action_a():
        count_a[0] += 1

    @debounce_click(delay_ms=500)
    def action_b():
        count_b[0] += 1

    action_a()
    action_b()  # Другая функция — должна выполниться
    assert count_a[0] == 1
    assert count_b[0] == 1, "Разные функции должны иметь независимые debounce-счётчики"


def test_debounce_click_with_parametric_decorator():
    """@debounce_click(delay_ms=X) — параметрическая форма должна работать."""
    call_count = [0]

    @debounce_click(delay_ms=1000)
    def my_action():
        call_count[0] += 1

    my_action()
    assert call_count[0] == 1, "Параметрическая форма декоратора должна работать"


def test_debounce_click_functools_wraps():
    """Декоратор сохраняет имя оригинальной функции через functools.wraps."""

    @debounce_click
    def original_function_name():
        pass

    assert original_function_name.__name__ == 'original_function_name', \
        "functools.wraps должен сохранять имя функции"

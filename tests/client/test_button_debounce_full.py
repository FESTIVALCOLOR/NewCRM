# -*- coding: utf-8 -*-
"""
Полное покрытие utils/button_debounce.py — ~10 тестов.
"""

import pytest
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.button_debounce import debounce_click, _last_click_time


@pytest.fixture(autouse=True)
def _clear_debounce():
    """Очистка глобального состояния debounce между тестами."""
    _last_click_time.clear()
    yield
    _last_click_time.clear()


class TestDebounceClick:
    def test_first_call_passes(self):
        call_log = []

        @debounce_click
        def handler():
            call_log.append(1)

        handler()
        assert len(call_log) == 1

    def test_rapid_second_call_blocked(self):
        call_log = []

        @debounce_click(delay_ms=1000)
        def handler():
            call_log.append(1)

        handler()
        handler()
        assert len(call_log) == 1

    def test_after_delay_passes(self):
        call_log = []

        @debounce_click(delay_ms=50)
        def handler():
            call_log.append(1)

        handler()
        time.sleep(0.06)
        handler()
        assert len(call_log) == 2

    def test_strips_bool_arg_from_qt(self):
        received_args = []

        @debounce_click
        def handler(self_arg):
            received_args.append(self_arg)

        handler('self_value', False)  # Qt передаёт bool checked
        assert received_args == ['self_value']

    def test_decorator_without_parens(self):
        call_log = []

        @debounce_click
        def handler():
            call_log.append(1)

        handler()
        assert len(call_log) == 1

    def test_decorator_with_custom_delay(self):
        call_log = []

        @debounce_click(delay_ms=2000)
        def handler():
            call_log.append(1)

        handler()
        assert len(call_log) == 1

    def test_return_value_passed(self):
        @debounce_click
        def handler():
            return 42

        assert handler() == 42

    def test_blocked_returns_none(self):
        @debounce_click(delay_ms=1000)
        def handler():
            return 42

        handler()
        result = handler()
        assert result is None

    def test_preserves_function_name(self):
        @debounce_click
        def my_handler():
            pass

        assert my_handler.__name__ == 'my_handler'

    def test_different_functions_independent(self):
        log_a, log_b = [], []

        @debounce_click(delay_ms=1000)
        def handler_a():
            log_a.append(1)

        @debounce_click(delay_ms=1000)
        def handler_b():
            log_b.append(1)

        handler_a()
        handler_b()
        assert len(log_a) == 1
        assert len(log_b) == 1

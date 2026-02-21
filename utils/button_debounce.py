"""
Защита от двойных кликов на кнопки (O-06)
Декоратор debounce_click игнорирует повторные вызовы метода в течение указанного интервала.
"""
import functools
import time


_last_click_time = {}


def debounce_click(func=None, *, delay_ms=1000):
    """
    Декоратор: игнорирует повторные вызовы в течение delay_ms миллисекунд.

    Использование:
        @debounce_click
        def save_contract(self):
            ...

        @debounce_click(delay_ms=2000)
        def delete_contract(self, contract):
            ...
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            key = id(f)
            now = time.monotonic()
            if key in _last_click_time and (now - _last_click_time[key]) < delay_ms / 1000:
                return None
            _last_click_time[key] = now
            return f(*args, **kwargs)
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator

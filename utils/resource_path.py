# -*- coding: utf-8 -*-
"""
Утилита для определения путей к ресурсам.
Работает как в режиме разработки, так и в упакованном exe.
"""

import sys
import os


def resource_path(relative_path):
    """
    Получить абсолютный путь к ресурсу.

    Args:
        relative_path: Относительный путь к ресурсу (например, 'resources/logo.png')

    Returns:
        Абсолютный путь к ресурсу

    Example:
        >>> logo_path = resource_path('resources/logo.png')
        >>> icon_path = resource_path('resources/icons/edit.svg')
    """
    try:
        # PyInstaller создает временную папку и сохраняет путь в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Если не упаковано, используем текущую директорию
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

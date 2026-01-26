"""
Утилита для загрузки SVG иконок
"""

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
from utils.resource_path import resource_path
import os

class IconLoader:
    """Загрузчик SVG иконок"""

    ICONS_DIR = 'resources/icons'

    @staticmethod
    def load(icon_name, size=18):
        """
        Загрузка SVG иконки

        Args:
            icon_name: Имя файла (например, 'search.svg' или просто 'search')
            size: Размер иконки в пикселях

        Returns:
            QIcon или None
        """
        # Добавляем .svg если не указано
        if not icon_name.endswith('.svg'):
            icon_name += '.svg'

        icon_path = resource_path(os.path.join(IconLoader.ICONS_DIR, icon_name))

        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            return icon
        else:
            print(f"[WARN] Иконка не найдена: {icon_path}")
            return QIcon()
    
    @staticmethod
    def create_icon_button(icon_name, text='', tooltip='', icon_size=18):
        """
        Создание кнопки с SVG иконкой

        Args:
            icon_name: Имя SVG файла
            text: Текст кнопки
            tooltip: Подсказка
            icon_size: Размер иконки

        Returns:
            QPushButton настроенная кнопка (без стилей)
        """
        from PyQt5.QtWidgets import QPushButton

        btn = QPushButton()

        # Загружаем иконку
        icon = IconLoader.load(icon_name)
        if icon and not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(QSize(icon_size, icon_size))

        # Устанавливаем текст и подсказку
        if text:
            btn.setText(text)
        if tooltip:
            btn.setToolTip(tooltip)

        # Если текста нет - это кнопка только с иконкой
        # Устанавливаем свойство для QSS стилей
        if not text:
            btn.setProperty('icon-only', True)

        return btn

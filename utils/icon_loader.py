"""
Утилита для загрузки SVG иконок
"""

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, Qt
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
    def load_colored(icon_name, color='#808080', size=20):
        """
        Загрузка SVG иконки с заменой цвета

        Args:
            icon_name: Имя SVG файла
            color: Цвет в формате hex (#808080)
            size: Размер иконки в пикселях

        Returns:
            QIcon с заменённым цветом
        """
        if not icon_name.endswith('.svg'):
            icon_name += '.svg'

        icon_path = resource_path(os.path.join(IconLoader.ICONS_DIR, icon_name))

        if not os.path.exists(icon_path):
            print(f"[WARN] Иконка не найдена: {icon_path}")
            return QIcon()

        try:
            with open(icon_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            # Заменяем цвета в SVG
            svg_content = svg_content.replace('currentColor', color)
            for attr in ['stroke', 'fill']:
                for old_val in ['black', '#000', '#000000', 'white', '#fff', '#ffffff']:
                    svg_content = svg_content.replace(
                        f'{attr}="{old_val}"', f'{attr}="{color}"')
                    svg_content = svg_content.replace(
                        f"{attr}='{old_val}'", f"{attr}='{color}'")

            from PyQt5.QtSvg import QSvgRenderer
            from PyQt5.QtGui import QPixmap, QPainter
            from PyQt5.QtCore import QByteArray

            renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()

            return QIcon(pixmap)
        except Exception:
            return IconLoader.load(icon_name, size)

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

        # Accessibility: имя для UIA (pywinauto, screen readers)
        accessible_name = text or tooltip
        if accessible_name:
            btn.setAccessibleName(accessible_name)

        # Если текста нет - это кнопка только с иконкой
        # Устанавливаем свойство для QSS стилей
        if not text:
            btn.setProperty('icon-only', True)

        return btn

    @staticmethod
    def create_action_button(icon_name, tooltip='', bg_color='#ffffff',
                             hover_color='#f5f5f5', icon_size=20,
                             button_size=36, icon_color='#808080'):
        """
        Создание минималистичной кнопки действия (icon-only, без рамок)

        Args:
            icon_name: Имя SVG файла
            tooltip: Подсказка при наведении
            bg_color: Фон кнопки
            hover_color: Фон при наведении
            icon_size: Размер иконки в пикселях
            button_size: Размер кнопки в пикселях
            icon_color: Цвет иконки (hex)

        Returns:
            QPushButton — минималистичная кнопка
        """
        from PyQt5.QtWidgets import QPushButton

        btn = QPushButton()

        icon = IconLoader.load_colored(icon_name, color=icon_color, size=icon_size)
        if icon and not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(QSize(icon_size, icon_size))

        if tooltip:
            btn.setToolTip(tooltip)
            btn.setAccessibleName(tooltip)

        # Явные CSS размеры — гарантируют размер фона независимо от каскада
        btn.setStyleSheet(f'''
            QPushButton {{
                background-color: {bg_color};
                border: none;
                border-radius: 8px;
                padding: 0px;
                min-width: {button_size}px;
                max-width: {button_size}px;
                min-height: {button_size}px;
                max-height: {button_size}px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {hover_color};
            }}
        ''')

        # setFixedSize ПОСЛЕ setStyleSheet для гарантии
        btn.setFixedSize(button_size, button_size)

        btn.setProperty('icon-only', True)
        btn.setCursor(Qt.PointingHandCursor)

        return btn

# -*- coding: utf-8 -*-
"""
Вспомогательные функции для диалоговых окон
"""


def center_dialog_on_parent(dialog, parent=None):
    """
    Центрирование диалогового окна относительно родительского окна

    Args:
        dialog: QDialog или QWidget - окно для центрирования
        parent: QWidget - родительское окно (если None, используется dialog.parent())
    """
    if parent is None:
        parent = dialog.parent()

    # Если parent это виджет внутри окна, получаем главное окно
    if parent is not None:
        parent = parent.window()

    if parent is None:
        # Если родителя нет, центрируем на экране
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.desktop().availableGeometry(dialog)
        x = screen.x() + (screen.width() - dialog.width()) // 2
        y = screen.y() + (screen.height() - dialog.height()) // 2
        dialog.move(x, y)
    else:
        # ИСПРАВЛЕНО: Используем frameGeometry() для получения глобальных координат с рамкой
        parent_geometry = parent.frameGeometry()
        dialog_width = dialog.width()
        dialog_height = dialog.height()

        # Вычисляем центр относительно родительского окна
        x = parent_geometry.x() + (parent_geometry.width() - dialog_width) // 2
        y = parent_geometry.y() + (parent_geometry.height() - dialog_height) // 2

        # Проверяем, что диалог не выходит за границы экрана
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.desktop().availableGeometry(dialog)

        # Корректируем позицию если диалог выходит за границы
        if x < screen.x():
            x = screen.x() + 10
        if y < screen.y():
            y = screen.y() + 10
        if x + dialog_width > screen.x() + screen.width():
            x = screen.x() + screen.width() - dialog_width - 10
        if y + dialog_height > screen.y() + screen.height():
            y = screen.y() + screen.height() - dialog_height - 10

        dialog.move(x, y)

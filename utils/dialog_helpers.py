# -*- coding: utf-8 -*-
"""
Вспомогательные функции для диалоговых окон
"""


def create_progress_dialog(title, label_text, cancel_text, maximum, parent):
    """
    Создание стилизованного прогресс-диалога (frameless, 1px border).
    Заменяет 13+ копий boilerplate QProgressDialog в UI.

    Args:
        title: Заголовок окна (для accessibility)
        label_text: Текст надписи (например "Подготовка к загрузке...")
        cancel_text: Текст кнопки отмены (None — без кнопки)
        maximum: Максимальное значение прогресса
        parent: Родительский виджет

    Returns:
        QProgressDialog — настроенный и показанный
    """
    from PyQt5.QtWidgets import QProgressDialog
    from PyQt5.QtCore import Qt

    progress = QProgressDialog(label_text, cancel_text, 0, maximum, parent)
    progress.setWindowModality(Qt.WindowModal)
    progress.setWindowTitle(title)
    progress.setMinimumDuration(0)
    progress.setAutoClose(True)
    progress.setAutoReset(False)
    progress.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
    progress.setFixedSize(420, 144)

    progress.setStyleSheet("""
        QProgressDialog {
            background-color: white;
            border: 1px solid #E0E0E0;
            border-radius: 10px;
        }
        QLabel {
            color: #2C3E50;
            font-size: 12px;
            padding: 10px;
            min-width: 380px;
            max-width: 380px;
        }
        QProgressBar {
            border: none;
            border-radius: 4px;
            text-align: center;
            background-color: #F0F0F0;
            height: 20px;
            margin: 10px;
            min-width: 380px;
            max-width: 380px;
        }
        QProgressBar::chunk {
            background-color: #90EE90;
            border-radius: 2px;
        }
        QPushButton {
            background-color: #E74C3C;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #C0392B;
        }
        QDialogButtonBox {
            alignment: center;
        }
    """)
    progress.show()
    return progress


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

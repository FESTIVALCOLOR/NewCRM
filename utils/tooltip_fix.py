# -*- coding: utf-8 -*-
"""
Утилита для исправления черного фона всплывающих подсказок
"""
from PyQt5.QtGui import QPalette, QColor


def apply_tooltip_palette(widget):
    """
    Применяет светло-серую палитру для всплывающих подсказок к виджету

    Args:
        widget: QWidget или QDialog, к которому нужно применить палитру
    """
    palette = widget.palette()
    palette.setColor(QPalette.ToolTipBase, QColor('#f5f5f5'))
    palette.setColor(QPalette.ToolTipText, QColor('#333333'))
    widget.setPalette(palette)

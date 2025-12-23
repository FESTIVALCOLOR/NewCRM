# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtCore import QEvent, QObject


class NoWheelTabWidget(QTabWidget):
    """
    QTabWidget, который блокирует переключение вкладок колесом мыши,
    когда табвиджет не находится в фокусе
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Устанавливаем фильтр событий на сам виджет
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        """
        Фильтрация событий колеса мыши для предотвращения
        случайного переключения вкладок
        """
        # Блокируем события колеса мыши на tab bar
        if event.type() == QEvent.Wheel:
            # Проверяем, находится ли курсор над панелью вкладок
            tab_bar = self.tabBar()
            if tab_bar and tab_bar.underMouse():
                # Блокируем переключение вкладок колесом мыши
                return True

        return super().eventFilter(obj, event)


def disable_wheel_on_tabwidget(tab_widget):
    """
    Добавляет фильтр событий к существующему QTabWidget,
    чтобы заблокировать переключение колесом мыши

    Использование:
        tabs = QTabWidget()
        disable_wheel_on_tabwidget(tabs)
    """
    class WheelEventFilter(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.Wheel:
                tab_bar = tab_widget.tabBar()
                if tab_bar and tab_bar.underMouse():
                    return True
            return False

    filter_obj = WheelEventFilter(tab_widget)
    tab_widget.installEventFilter(filter_obj)
    # Сохраняем ссылку на фильтр, чтобы он не был удален сборщиком мусора
    if not hasattr(tab_widget, '_wheel_filters'):
        tab_widget._wheel_filters = []
    tab_widget._wheel_filters.append(filter_obj)

    return filter_obj

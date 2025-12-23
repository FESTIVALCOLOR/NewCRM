# -*- coding: utf-8 -*-
"""
Утилита для сохранения и восстановления настроек таблиц
"""
from PyQt5.QtCore import QSettings


class TableSettings:
    """Класс для управления настройками таблиц (сортировка)"""

    def __init__(self):
        self.settings = QSettings('FestivalColor', 'InteriorStudioCRM')

    def save_sort_order(self, table_name, column, order):
        """
        Сохранение настроек сортировки таблицы

        Args:
            table_name: название таблицы (clients, contracts, employees, salaries)
            column: номер колонки для сортировки
            order: порядок сортировки (0 = по возрастанию, 1 = по убыванию)
        """
        self.settings.setValue(f'{table_name}/sort_column', column)
        self.settings.setValue(f'{table_name}/sort_order', order)

    def get_sort_order(self, table_name):
        """
        Получение настроек сортировки таблицы

        Args:
            table_name: название таблицы

        Returns:
            tuple: (column, order) или (None, None) если настроек нет
        """
        column = self.settings.value(f'{table_name}/sort_column', None)
        order = self.settings.value(f'{table_name}/sort_order', None)

        if column is not None:
            column = int(column)
        if order is not None:
            order = int(order)

        return column, order

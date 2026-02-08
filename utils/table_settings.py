# -*- coding: utf-8 -*-
"""
Утилита для сохранения и восстановления настроек таблиц
"""
from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtWidgets import QTableWidget, QHeaderView, QStyledItemDelegate, QStyle


class NoFocusDelegate(QStyledItemDelegate):
    """
    Делегат который не рисует пунктирную рамку фокуса вокруг ячейки.
    Используется для таблиц где нужно выделение только строки без рамки на ячейке.
    """
    def paint(self, painter, option, index):
        # Убираем флаг State_HasFocus чтобы не рисовалась пунктирная рамка
        if option.state & QStyle.State_HasFocus:
            option.state = option.state ^ QStyle.State_HasFocus
        super().paint(painter, option, index)


class ProportionalResizeTable(QTableWidget):
    """
    Таблица с пропорциональным растягиванием колонок И возможностью ручного изменения.

    Решает проблему Qt где:
    - QHeaderView.Stretch = автозаполнение, но нельзя менять вручную
    - QHeaderView.Interactive = можно менять вручную, но не заполняет ширину

    Этот класс дает ОБА поведения:
    - Колонки автоматически растягиваются пропорционально при изменении размера окна
    - Пользователь может вручную менять ширину колонок
    - После ручного изменения пропорции пересчитываются
    - ВАЖНО: Общая ширина всех столбцов всегда равна ширине viewport
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._column_ratios = []  # Пропорции колонок (0.0 - 1.0)
        self._fixed_columns = {}  # {col_index: fixed_width}
        self._min_column_width = 50  # Минимальная ширина колонки
        self._initialized = False
        self._resizing_programmatically = False  # Флаг для предотвращения рекурсии
        self._initial_apply_done = False  # Флаг успешного первого применения
        self._pending_apply_attempts = 0  # Счётчик попыток применения

        # КРИТИЧНО: Отключаем горизонтальную прокрутку - таблица должна
        # всегда помещаться в viewport без скролла
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Убираем пунктирную рамку фокуса с ячеек - должна выделяться только строка
        self.setItemDelegate(NoFocusDelegate(self))

    def setup_proportional_resize(self, column_ratios: list, fixed_columns: dict = None,
                                   min_width: int = 50):
        """
        Настроить пропорциональное изменение размера колонок.

        Args:
            column_ratios: список пропорций [0.1, 0.15, 0.25, 0.2, 0.15, 0.15]
                          Сумма должна быть примерно 1.0 (для не-фиксированных колонок)
            fixed_columns: {col_index: width} - колонки с фиксированной шириной
                          Например: {6: 110} - колонка 6 всегда 110px
            min_width: минимальная ширина для любой колонки
        """
        self._column_ratios = column_ratios
        self._fixed_columns = fixed_columns or {}
        self._min_column_width = min_width

        # Настраиваем header
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(min_width)

        # Все колонки - Interactive для ручного изменения
        for col in range(self.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Interactive)

        # Подключаем сигнал изменения размера колонки пользователем
        header.sectionResized.connect(self._on_section_resized)

        self._initialized = True
        # Применяем начальные пропорции
        self._apply_ratios()

    def resizeEvent(self, event):
        """При изменении размера таблицы - перераспределить ширину колонок"""
        super().resizeEvent(event)
        if self._initialized and not self._resizing_programmatically:
            # Если это первый resizeEvent с валидной шириной - помечаем как выполненное
            if not self._initial_apply_done and self.viewport().width() > 50:
                self._initial_apply_done = True
            self._apply_ratios()

    def hideEvent(self, event):
        """При скрытии сбрасываем флаг для повторного применения при показе"""
        super().hideEvent(event)
        # Сбрасываем флаг чтобы при повторном показе (переключение вкладок)
        # пропорции применились заново
        self._initial_apply_done = False

    def showEvent(self, event):
        """При первом показе таблицы - применить пропорции

        ВАЖНО: При инициализации viewport может иметь нулевую ширину.
        showEvent вызывается когда виджет уже виден и имеет реальные размеры.
        Для диалогов и вложенных виджетов layout может быть ещё не завершён,
        поэтому используем многократные попытки с увеличивающейся задержкой.
        """
        super().showEvent(event)
        if self._initialized and not self._initial_apply_done:
            self._schedule_initial_apply()

    def _schedule_initial_apply(self):
        """Запланировать применение пропорций с повторными попытками"""
        from PyQt5.QtCore import QTimer
        self._pending_apply_attempts = 0
        # Первая попытка сразу (singleShot 0)
        QTimer.singleShot(0, self._try_initial_apply)

    def _try_initial_apply(self):
        """Попытаться применить пропорции, повторить если viewport ещё не готов"""
        from PyQt5.QtCore import QTimer

        viewport_width = self.viewport().width()

        if viewport_width > 50:  # Viewport готов (минимальная разумная ширина)
            self._apply_ratios()
            self._initial_apply_done = True
            return

        # Viewport ещё не готов - повторить
        self._pending_apply_attempts += 1

        if self._pending_apply_attempts < 10:  # Максимум 10 попыток
            # Увеличиваем задержку с каждой попыткой: 10, 20, 30, 50, 75, 100, 150, 200, 300 мс
            delays = [10, 20, 30, 50, 75, 100, 150, 200, 300, 500]
            delay = delays[min(self._pending_apply_attempts - 1, len(delays) - 1)]
            QTimer.singleShot(delay, self._try_initial_apply)

    def _ensure_total_width_fits(self):
        """
        Гарантирует что общая ширина ВИДИМЫХ колонок равна ширине viewport.
        Если колонки шире viewport - пропорционально урезаем.
        Если колонки уже viewport - пропорционально расширяем.
        """
        if self.columnCount() == 0 or not self._column_ratios:
            return

        viewport_width = self.viewport().width()
        if viewport_width <= 0:
            return

        # Получаем текущую общую ширину ВИДИМЫХ колонок
        total_width = sum(
            self.columnWidth(c) for c in range(self.columnCount())
            if not self.isColumnHidden(c)
        )

        # Если разница минимальна - ничего не делаем
        if abs(total_width - viewport_width) < 3:
            return

        self._resizing_programmatically = True
        try:
            # Вычисляем фактор масштабирования (только для ВИДИМЫХ колонок)
            fixed_total = sum(
                width for col, width in self._fixed_columns.items()
                if not self.isColumnHidden(col)
            )
            flexible_total = total_width - fixed_total
            target_flexible = viewport_width - fixed_total

            if flexible_total <= 0 or target_flexible <= 0:
                return

            scale = target_flexible / flexible_total

            # Масштабируем только ВИДИМЫЕ нефиксированные колонки
            for col in range(self.columnCount()):
                if col not in self._fixed_columns and not self.isColumnHidden(col):
                    current = self.columnWidth(col)
                    new_width = max(self._min_column_width, int(current * scale))
                    self.setColumnWidth(col, new_width)

        finally:
            self._resizing_programmatically = False

    def _apply_ratios(self):
        """Применить пропорции к текущей ширине viewport"""
        if not self._column_ratios or self.columnCount() == 0:
            return

        self._resizing_programmatically = True
        try:
            viewport_width = self.viewport().width()
            if viewport_width <= 0:
                return

            # Собираем информацию о ВИДИМЫХ колонках
            visible_cols = []
            visible_ratios = []
            hidden_cols = []

            for col in range(self.columnCount()):
                if self.isColumnHidden(col):
                    hidden_cols.append(col)
                else:
                    visible_cols.append(col)
                    # Получаем пропорцию для этой колонки (если есть)
                    if col < len(self._column_ratios) and col not in self._fixed_columns:
                        visible_ratios.append((col, self._column_ratios[col]))

            # Вычитаем фиксированные ВИДИМЫЕ колонки
            fixed_total = sum(
                width for col, width in self._fixed_columns.items()
                if col not in hidden_cols
            )
            available_width = viewport_width - fixed_total

            if available_width <= 0:
                return

            # Нормализуем пропорции видимых колонок чтобы сумма = 1.0
            total_visible_ratio = sum(r for _, r in visible_ratios)
            if total_visible_ratio <= 0:
                return

            # Вычисляем ширину для каждой колонки и находим последнюю видимую пропорциональную
            column_widths = {}
            last_visible_proportional_col = None
            total_assigned = 0

            for col in range(self.columnCount()):
                if self.isColumnHidden(col):
                    column_widths[col] = 0
                elif col in self._fixed_columns:
                    column_widths[col] = self._fixed_columns[col]
                    total_assigned += self._fixed_columns[col]
                elif col < len(self._column_ratios):
                    normalized_ratio = self._column_ratios[col] / total_visible_ratio
                    width = max(self._min_column_width,
                               int(available_width * normalized_ratio))
                    column_widths[col] = width
                    total_assigned += width
                    last_visible_proportional_col = col

            # Компенсируем ошибку округления - добавляем остаток к последней пропорциональной колонке
            if last_visible_proportional_col is not None:
                remainder = viewport_width - total_assigned
                if remainder > 0:
                    column_widths[last_visible_proportional_col] += remainder

            # Применяем вычисленные ширины
            for col, width in column_widths.items():
                self.setColumnWidth(col, width)
        finally:
            self._resizing_programmatically = False

    def _on_section_resized(self, col, old_size, new_size):
        """
        Пересчитать пропорции после ручного изменения пользователем.
        Вызывается когда пользователь тянет границу колонки.

        КРИТИЧНО: После ЛЮБОГО ручного изменения мы принудительно перераспределяем
        ширину всех колонок чтобы общая сумма всегда равнялась viewport.
        """
        if self._resizing_programmatically:
            return  # Игнорируем программные изменения

        if col in self._fixed_columns:
            return  # Фиксированные колонки не меняют

        if self.isColumnHidden(col):
            return  # Скрытые колонки игнорируем

        viewport_width = self.viewport().width()

        # Учитываем только ВИДИМЫЕ фиксированные колонки
        fixed_total = sum(
            width for c, width in self._fixed_columns.items()
            if not self.isColumnHidden(c)
        )
        available_width = viewport_width - fixed_total

        if available_width <= 0:
            return

        # Получаем индексы ВИДИМЫХ нефиксированных колонок
        flexible_cols = [
            c for c in range(self.columnCount())
            if c not in self._fixed_columns and not self.isColumnHidden(c)
        ]
        if col not in flexible_cols:
            return

        self._resizing_programmatically = True
        try:
            # Собираем текущие ширины ВСЕХ visible flexible колонок
            current_widths = {c: self.columnWidth(c) for c in flexible_cols}
            total_current = sum(current_widths.values())

            # Вычисляем насколько текущая сумма отличается от доступной ширины
            diff = total_current - available_width

            if abs(diff) < 2:
                # Разница минимальна - просто пересчитываем пропорции
                pass
            else:
                # Нужно перераспределить: отнимаем/добавляем разницу от ДРУГИХ колонок
                other_cols = [c for c in flexible_cols if c != col]
                other_widths = {c: current_widths[c] for c in other_cols}
                total_other = sum(other_widths.values())

                if total_other > 0:
                    # Распределяем diff пропорционально между другими колонками
                    for c in other_cols:
                        ratio = other_widths[c] / total_other
                        adjustment = int(diff * ratio)
                        new_width = other_widths[c] - adjustment
                        # Гарантируем минимальную ширину
                        new_width = max(self._min_column_width, new_width)
                        self.setColumnWidth(c, new_width)

                    # После корректировки проверяем, не превысили ли мы available_width
                    # Если да - урезаем текущую колонку
                    new_total = sum(self.columnWidth(c) for c in flexible_cols)
                    if new_total > available_width:
                        excess = new_total - available_width
                        corrected_width = max(self._min_column_width, new_size - excess)
                        self.setColumnWidth(col, corrected_width)

            # Пересчитываем пропорции на основе финальных ширин (для ВСЕХ колонок, включая скрытые)
            new_ratios = []
            for c in range(self.columnCount()):
                if c not in self._fixed_columns:
                    if self.isColumnHidden(c):
                        # Для скрытых колонок сохраняем старую пропорцию
                        if c < len(self._column_ratios):
                            new_ratios.append(self._column_ratios[c])
                        else:
                            new_ratios.append(0)
                    else:
                        width = self.columnWidth(c)
                        ratio = width / available_width if available_width > 0 else 0
                        new_ratios.append(ratio)

            # Нормализуем чтобы сумма была 1.0
            total = sum(new_ratios)
            if total > 0:
                self._column_ratios = [r / total for r in new_ratios]

        finally:
            self._resizing_programmatically = False

        # Финальная проверка - гарантируем что общая ширина = viewport
        self._ensure_total_width_fits()


def apply_no_focus_delegate(table):
    """
    Применить делегат без рамки фокуса к любой таблице (QTableWidget или QTableView).
    Вызывайте эту функцию после создания таблицы чтобы убрать пунктирную рамку
    вокруг ячейки при выделении строки.

    Пример:
        table = QTableWidget()
        apply_no_focus_delegate(table)
    """
    table.setItemDelegate(NoFocusDelegate(table))


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

    # ИСПРАВЛЕНИЕ 07.02.2026: Методы для сохранения состояния колонок CRM (#19)
    def save_column_collapsed_state(self, board_name: str, column_name: str, is_collapsed: bool):
        """
        Сохранение состояния сворачивания колонки

        Args:
            board_name: название доски (crm_individual, crm_template, crm_supervision)
            column_name: название колонки
            is_collapsed: свёрнута ли колонка
        """
        # Нормализуем название колонки для ключа (убираем спецсимволы)
        key = column_name.replace(':', '_').replace(' ', '_').replace('(', '').replace(')', '')
        self.settings.setValue(f'columns/{board_name}/{key}', is_collapsed)

    def get_column_collapsed_state(self, board_name: str, column_name: str, default=None):
        """
        Получение состояния сворачивания колонки

        Args:
            board_name: название доски
            column_name: название колонки
            default: значение по умолчанию если настроек нет (None = не было сохранено)

        Returns:
            bool или None: свёрнута ли колонка, или None если настройка не найдена
        """
        key = column_name.replace(':', '_').replace(' ', '_').replace('(', '').replace(')', '')
        # Используем специальный маркер чтобы отличить "не найдено" от False
        NOT_FOUND = "__NOT_FOUND__"
        value = self.settings.value(f'columns/{board_name}/{key}', NOT_FOUND)

        # Если настройка не найдена - возвращаем default (может быть None)
        if value == NOT_FOUND:
            return default

        # QSettings возвращает строку 'true'/'false', нужно преобразовать
        if isinstance(value, str):
            return value.lower() == 'true'
        return bool(value)

    def get_all_collapsed_columns(self, board_name: str) -> dict:
        """
        Получение всех сохранённых состояний колонок для доски

        Args:
            board_name: название доски

        Returns:
            dict: {column_key: is_collapsed}
        """
        self.settings.beginGroup(f'columns/{board_name}')
        keys = self.settings.childKeys()
        result = {}
        for key in keys:
            value = self.settings.value(key, False)
            if isinstance(value, str):
                result[key] = value.lower() == 'true'
            else:
                result[key] = bool(value)
        self.settings.endGroup()
        return result

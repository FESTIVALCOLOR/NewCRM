# -*- coding: utf-8 -*-
"""
Базовый класс для Kanban-вкладок CRM.

Содержит абстрактные методы и реально общий код, вынесенный из:
  - ui/crm_tab.py         (CRMTab)
  - ui/crm_supervision_tab.py (CRMSupervisionTab)

ВАЖНО: этот файл — заготовка для будущего рефакторинга.
crm_tab.py и crm_supervision_tab.py на данном этапе не изменяются.
"""

from abc import abstractmethod

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QColor

from utils.icon_loader import IconLoader
from utils.data_access import DataAccess
from utils.table_settings import TableSettings



# ===========================================================================
# Базовый виджет списка с Drag & Drop для Kanban-колонок
# ===========================================================================

class BaseDraggableList(QListWidget):
    """
    Общий базовый класс для перетаскиваемых списков карточек.

    Дочерние классы (DraggableListWidget, SupervisionDraggableList) идентичны
    по структуре: __init__, startDrag, dropEvent.

    Разница между ними — в типе источника, который проверяется в dropEvent:
    каждый допускает перетаскивание только «своего» типа.
    Поэтому dropEvent оставлен абстрактным — наследник обязан его реализовать.
    """

    item_dropped = pyqtSignal(int, object)

    def __init__(self, parent_column, can_drag=True):
        super().__init__()
        self.parent_column = parent_column
        self.can_drag = can_drag

        if self.can_drag:
            self.setDragDropMode(QListWidget.DragDrop)
            self.setDefaultDropAction(Qt.MoveAction)
            self.setAcceptDrops(True)
            self.setDragEnabled(True)
        else:
            self.setDragDropMode(QListWidget.NoDragDrop)
            self.setAcceptDrops(False)
            self.setDragEnabled(False)

        self.setSelectionMode(QListWidget.SingleSelection)

    def keyPressEvent(self, event):
        """Enter/Return на выбранной карточке → открыть редактирование."""
        from PyQt5.QtCore import Qt
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            item = self.currentItem()
            if item:
                widget = self.itemWidget(item)
                if widget and hasattr(widget, 'edit_card'):
                    widget.edit_card()
                    return
        super().keyPressEvent(event)

    def startDrag(self, supportedActions):
        """Начало перетаскивания — блокируем, если drag запрещён или нет выбранного элемента."""
        if not self.can_drag:
            return
        item = self.currentItem()
        if not item:
            return
        super().startDrag(supportedActions)

    @abstractmethod
    def dropEvent(self, event):
        """
        Обработка сброса карточки.
        Реализуется в конкретном подклассе, так как проверяет
        тип источника, специфичный для каждой доски.
        """
        raise NotImplementedError


# ===========================================================================
# Базовый класс колонки Kanban-доски
# ===========================================================================

class BaseKanbanColumn(QFrame):
    """
    Общий базовый класс колонки Kanban-доски.

    Общий код между CRMColumn и SupervisionColumn:
      - хранение состояния свернуто/развернуто (_is_collapsed)
      - методы toggle_collapse, _collapse_column, _expand_column
      - update_header_count
      - add_card (шаблонный метод, создание card_widget — абстрактно)
      - clear_cards

    Различия, остающиеся в наследниках:
      - Цвет заголовка (белый vs оранжевый #FFE5CC)
      - Класс вертикального лейбла (VerticalLabel vs VerticalLabelSupervision)
      - Класс карточки (CRMCard vs SupervisionCard)
      - Дополнительные аргументы __init__ (project_type, can_edit)
      - Логика умолчания для _apply_initial_collapse_state
    """

    # Сигнал перемещения карточки: подклассы переопределяют сигнатуру сигнала
    # (CRMColumn передаёт project_type, SupervisionColumn — нет).
    # Здесь сигнал не объявлен, чтобы не конфликтовать с наследниками.

    def __init__(self):
        super().__init__()
        self.column_name = ''
        self.header_label = None
        self.vertical_label = None
        self.cards_list = None
        self.collapse_btn = None  # Создаётся в подклассах (CRMColumn, SupervisionColumn)

        # Состояние сворачивания
        self._is_collapsed = False
        self._original_min_width = 300
        self._original_max_width = 600
        self._collapsed_width = 50

        # Настройки сохранения состояния
        self._settings = TableSettings()
        self._board_name = ''

    # ------------------------------------------------------------------
    # Абстрактные методы — должны быть реализованы в наследнике
    # ------------------------------------------------------------------

    @abstractmethod
    def init_ui(self):
        """Инициализация визуальных элементов колонки."""
        raise NotImplementedError

    @abstractmethod
    def _make_vertical_label(self):
        """
        Создать экземпляр вертикального лейбла для свёрнутой колонки.
        CRMColumn: VerticalLabel()
        SupervisionColumn: VerticalLabelSupervision()
        """
        raise NotImplementedError

    @abstractmethod
    def _create_card_widget(self, card_data):
        """
        Создать виджет карточки для переданных данных.
        CRMColumn: CRMCard(...)
        SupervisionColumn: SupervisionCard(...)
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Общие методы — одинаковы в обоих существующих классах
    # ------------------------------------------------------------------

    def _apply_initial_collapse_state(self):
        """
        Применить начальное состояние сворачивания из сохранённых настроек.
        Наследник может переопределить для добавления логики умолчания.
        """
        saved_state = self._settings.get_column_collapsed_state(
            self._board_name, self.column_name, default=None
        )
        if saved_state is not None and saved_state:
            self._collapse_column()

    def _collapse_column(self):
        """Свернуть колонку (без сохранения состояния в настройках)."""
        self._is_collapsed = True
        self.cards_list.hide()
        self.header_label.hide()
        self.collapse_btn.setIcon(IconLoader.load('arrow-right-circle'))
        self.collapse_btn.setToolTip('Развернуть колонку')
        self.setMinimumWidth(self._collapsed_width)
        self.setMaximumWidth(self._collapsed_width)

        # Создаём вертикальный лейбл при первом сворачивании
        if self.vertical_label is None:
            self.vertical_label = self._make_vertical_label()
            self.layout().insertWidget(1, self.vertical_label, 1)

        count = self.cards_list.count() if self.cards_list else 0
        short_name = self.column_name.split(':')[0].strip() if ':' in self.column_name else self.column_name
        self.vertical_label.setText(f"{short_name} ({count})")
        self.vertical_label.show()

    def _expand_column(self):
        """Развернуть колонку (без сохранения состояния в настройках)."""
        self._is_collapsed = False
        self.cards_list.show()
        self.header_label.show()
        self.collapse_btn.setIcon(IconLoader.load('arrow-left-circle'))
        self.collapse_btn.setToolTip('Свернуть колонку')
        self.setMinimumWidth(self._original_min_width)
        self.setMaximumWidth(self._original_max_width)

        if self.vertical_label:
            self.vertical_label.hide()

    def toggle_collapse(self):
        """Переключение состояния сворачивания с сохранением в настройках."""
        if self._is_collapsed:
            self._expand_column()
        else:
            self._collapse_column()

        self._settings.save_column_collapsed_state(
            self._board_name, self.column_name, self._is_collapsed
        )

    def update_header_count(self):
        """Обновление счётчика карточек в заголовке и в вертикальном лейбле."""
        count = self.cards_list.count() if self.cards_list else 0

        if count == 0:
            self.header_label.setText(self.column_name)
        else:
            self.header_label.setText(f"{self.column_name} ({count})")

        # Обновляем вертикальный лейбл если колонка свёрнута
        if self._is_collapsed and self.vertical_label:
            short_name = self.column_name.split(':')[0].strip() if ':' in self.column_name else self.column_name
            self.vertical_label.setText(f"{short_name} ({count})")

    def add_card(self, card_data, bulk=False):
        """
        Добавление карточки в колонку.

        Параметры:
            card_data -- словарь с данными карточки (обязателен ключ 'id')
            bulk      -- True означает режим массовой загрузки:
                         пропускает update_header_count для скорости
        """
        card_widget = self._create_card_widget(card_data)

        recommended_size = card_widget.sizeHint()
        exact_height = recommended_size.height()
        card_widget.setMinimumHeight(exact_height)

        item = QListWidgetItem()
        item.setData(Qt.UserRole, card_data.get('id'))
        item.setSizeHint(QSize(200, exact_height + 10))

        self.cards_list.addItem(item)
        self.cards_list.setItemWidget(item, card_widget)

        if not bulk:
            self.update_header_count()

    def clear_cards(self):
        """Очистить все карточки из колонки и обновить счётчик."""
        self.cards_list.clear()
        self.update_header_count()

    def find_card_item_by_id(self, card_id):
        """
        Найти QListWidgetItem по ID карточки.

        Возвращает (item, row) или (None, -1) если не найдено.
        """
        for row in range(self.cards_list.count()):
            item = self.cards_list.item(row)
            if item and item.data(Qt.UserRole) == card_id:
                return item, row
        return None, -1


# ===========================================================================
# Базовый класс главной вкладки Kanban
# ===========================================================================

class BaseKanbanTab(QWidget):
    """
    Базовый класс для CRMTab и CRMSupervisionTab.

    Общие паттерны:
      1. Инициализация DataAccess и guard-флагов
      2. Получение SyncManager из главного окна
      3. Обновление дашборда после refresh
      4. Шаблонный метод on_tab_changed с _loading_guard
      5. Создание QScrollArea с горизонтальной прокруткой для доски

    Что НЕ вынесено (слишком специфично):
      - Логика фильтров и архива (разная структура)
      - on_card_moved (разные сигнатуры сигналов и бизнес-логика)
      - load_cards_* (разные источники данных и параметры)
      - Диалоги (ExecutorSelectionDialog vs AssignExecutorsDialog)
    """

    def __init__(self, employee, api_client=None, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.api_client = api_client
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db

        # Флаги для предотвращения повторной загрузки данных
        self._data_loaded = False
        self._loading_guard = False

    # ------------------------------------------------------------------
    # Абстрактные методы — реализуются в каждой конкретной вкладке
    # ------------------------------------------------------------------

    @abstractmethod
    def init_ui(self):
        """Построить UI вкладки."""
        raise NotImplementedError

    @abstractmethod
    def load_active_data(self):
        """Загрузить актуальные (не архивные) данные доски."""
        raise NotImplementedError

    @abstractmethod
    def get_tab_title(self):
        """Вернуть строку заголовка вкладки (для QLabel в header)."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Общие утилиты
    # ------------------------------------------------------------------

    def _get_sync_manager(self):
        """Получить SyncManager из главного окна (если есть)."""
        mw = self.window()
        return getattr(mw, 'sync_manager', None)

    def _notify_dashboard_refresh(self):
        """Уведомить главное окно об обновлении данных (обновить дашборд)."""
        mw = self.window()
        if hasattr(mw, 'refresh_current_dashboard'):
            mw.refresh_current_dashboard()

    def _make_kanban_scroll_area(self):
        """
        Создать QScrollArea с горизонтальной прокруткой для доски.

        Возвращает (scroll_area, columns_layout) — горизонтальный layout
        для размещения колонок. Вызывающий код добавляет колонки в columns_layout
        и передаёт columns_widget в scroll_area.setWidget().
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        columns_widget = QWidget()
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(10)
        columns_layout.setContentsMargins(0, 5, 0, 0)
        columns_widget.setLayout(columns_layout)
        scroll.setWidget(columns_widget)

        return scroll, columns_layout

    def _make_header_layout(self, title_text):
        """
        Создать стандартный горизонтальный header-layout с заголовком
        и кнопкой обновления (refresh).

        Возвращает (header_layout, refresh_btn) — вызывающий код добавляет
        дополнительные кнопки перед установкой layout в main_layout.
        """
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        header = QLabel(title_text)
        header.setStyleSheet('font-size: 13px; font-weight: bold; color: #333333;')
        header_layout.addWidget(header)
        header_layout.addStretch(1)

        refresh_btn = IconLoader.create_action_button('refresh', 'Обновить данные с сервера')
        refresh_btn.clicked.connect(self.refresh_current_tab)
        header_layout.addWidget(refresh_btn)

        return header_layout, refresh_btn

    def on_tab_changed(self, index):
        """
        Шаблонный обработчик переключения вкладок.
        Использует prefer_local для мгновенного переключения без запроса к серверу.
        Наследник должен переопределить, вызвав super() или реализовав собственную логику.
        """
        if getattr(self, '_loading_guard', False):
            return
        self.data.prefer_local = True
        try:
            self._on_tab_changed_impl(index)
        finally:
            self.data.prefer_local = False

    def _on_tab_changed_impl(self, index):
        """
        Внутренняя реализация переключения вкладок.
        Переопределяется в наследнике вместо on_tab_changed.
        """
        pass

    def refresh_current_tab(self):
        """
        Базовая реализация обновления текущей вкладки.
        Наследник должен переопределить, вызвав super() в конце
        для уведомления дашборда.
        """
        self._notify_dashboard_refresh()

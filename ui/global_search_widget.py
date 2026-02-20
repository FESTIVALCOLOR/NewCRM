# -*- coding: utf-8 -*-
"""
Виджет глобального поиска по клиентам, договорам и проектам.
Встраивается в строку вкладок главного окна (corner widget).
"""
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QLineEdit, QListWidget,
                             QListWidgetItem, QApplication)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot, QEvent, QRectF, QPoint
from PyQt5.QtGui import QRegion, QPainterPath


class _SearchWorker(QThread):
    """Фоновый поток для выполнения поиска без блокировки UI"""
    finished = pyqtSignal(str, list)  # query, results

    def __init__(self, data_access, query, limit=20):
        super().__init__()
        self.data = data_access
        self.query = query
        self.limit = limit

    def run(self):
        try:
            result = self.data.global_search(self.query, limit=self.limit)
            items = result.get("results", [])
        except Exception:
            items = []
        self.finished.emit(self.query, items)


class GlobalSearchWidget(QWidget):
    """Виджет поиска с debounce и выпадающим списком результатов"""

    result_selected = pyqtSignal(str, int)  # entity_type, entity_id

    def __init__(self, data_access, parent=None):
        super().__init__(parent)
        self.data = data_access
        self._worker = None
        self._results_parented = False
        self._setup_ui()
        self._setup_debounce()

    def _setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по клиентам, договорам, проектам...")
        self.search_input.setFixedWidth(320)
        self.search_input.setFixedHeight(28)
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                padding: 2px 8px 2px 28px;
                background-color: #f5f5f5;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #ffd93c;
                background-color: #ffffff;
            }
        """)
        layout.addWidget(self.search_input)
        self.setLayout(layout)

        # Dropdown — дочерний виджет главного окна (не top-level),
        # позиционируется через mapTo для корректной привязки
        self.results_list = QListWidget()
        self.results_list.setFocusPolicy(Qt.NoFocus)
        self.results_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                background: white;
                font-size: 12px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:hover {
                background-color: #FFF8DC;
            }
            QListWidget::item:selected {
                background-color: #ffd93c;
            }
            QListWidget QScrollBar:vertical {
                background: transparent;
                width: 12px;
                margin: 6px 0px;
            }
            QListWidget QScrollBar::handle:vertical {
                background-color: #d9d9d9;
                border-radius: 4px;
                min-height: 20px;
                margin: 0px 2px;
            }
            QListWidget QScrollBar::handle:vertical:hover {
                background-color: #ffd93c;
            }
            QListWidget QScrollBar::add-line:vertical,
            QListWidget QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QListWidget QScrollBar::add-page:vertical,
            QListWidget QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        self.results_list.hide()
        self.results_list.itemClicked.connect(self._on_result_clicked)

        # Закрытие при клике вне виджета поиска
        QApplication.instance().installEventFilter(self)

    def _ensure_parented(self):
        """Привязать dropdown к главному окну (один раз)"""
        if self._results_parented:
            return
        main_win = self.window()
        if main_win and main_win is not self:
            self.results_list.setParent(main_win)
            self._results_parented = True

    def eventFilter(self, obj, event):
        """Закрываем dropdown при клике вне поиска"""
        if event.type() == QEvent.MouseButtonPress and self.results_list.isVisible():
            click_pos = event.globalPos()
            # Проверяем клик вне dropdown (через global coords)
            rl_pos = self.results_list.mapToGlobal(QPoint(0, 0))
            rl_rect = QRectF(rl_pos.x(), rl_pos.y(),
                             self.results_list.width(), self.results_list.height())
            if not rl_rect.contains(float(click_pos.x()), float(click_pos.y())):
                if not self.search_input.rect().contains(
                        self.search_input.mapFromGlobal(click_pos)):
                    self.results_list.hide()
        return super().eventFilter(obj, event)

    def _setup_debounce(self):
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self._perform_search)
        self.search_input.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self, text):
        if len(text.strip()) < 2:
            self.results_list.hide()
            return
        self.debounce_timer.start()

    def _perform_search(self):
        query = self.search_input.text().strip()
        if len(query) < 2:
            self.results_list.hide()
            return

        if self._worker and self._worker.isRunning():
            try:
                self._worker.finished.disconnect()
            except TypeError:
                pass
            self._worker.requestInterruption()
            self._worker.quit()

        self._worker = _SearchWorker(self.data, query, limit=20)
        self._worker.finished.connect(self._on_search_finished)
        self._worker.start()

        self.results_list.clear()
        loading_item = QListWidgetItem("Поиск...")
        loading_item.setFlags(Qt.NoItemFlags)
        self.results_list.addItem(loading_item)
        self._position_and_resize_dropdown()
        self.results_list.show()
        self.results_list.raise_()

    def _position_and_resize_dropdown(self):
        """Позиционирование и динамический размер dropdown"""
        self._ensure_parented()
        main_win = self.window()

        # Ширина dropdown = ширина search_input
        drop_w = max(self.search_input.width(), 320)
        self.results_list.setFixedWidth(drop_w)

        # Позиция: прямо под search_input, координаты относительно главного окна
        pos = self.search_input.mapTo(main_win, QPoint(0, self.search_input.height()))
        self.results_list.move(pos.x(), pos.y())

        # Динамическая высота
        item_height = 32
        count = self.results_list.count()
        content_height = count * item_height + 12
        max_height = int(main_win.height() * 0.65) if main_win else 400
        final_height = max(item_height + 12, min(content_height, max_height))
        self.results_list.setFixedHeight(final_height)

        # Маска — обрезаем по border-radius чтобы фон не вылазил
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, drop_w, final_height), 6, 6)
        self.results_list.setMask(QRegion(path.toFillPolygon().toPolygon()))

    @pyqtSlot(str, list)
    def _on_search_finished(self, query, items):
        """Обработка результатов поиска (вызывается в UI потоке)"""
        current = self.search_input.text().strip()
        if current != query:
            return

        self.results_list.clear()
        if not items:
            item = QListWidgetItem("Ничего не найдено")
            item.setFlags(Qt.NoItemFlags)
            self.results_list.addItem(item)
        else:
            type_labels = {"client": "Клиент", "contract": "Договор", "crm_card": "Проект"}
            for r in items:
                label = type_labels.get(r["type"], r["type"])
                text = f"[{label}] {r['title']}"
                if r.get("subtitle"):
                    text += f" - {r['subtitle']}"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, r)
                self.results_list.addItem(item)

        self._position_and_resize_dropdown()
        self.results_list.show()
        self.results_list.raise_()

    def _on_result_clicked(self, item):
        data = item.data(Qt.UserRole)
        if data:
            self.result_selected.emit(data["type"], data["id"])
        self.results_list.hide()
        self.search_input.clear()

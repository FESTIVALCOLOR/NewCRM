# -*- coding: utf-8 -*-
"""
Галерея файлов с адаптивной сеткой превью
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,

                             QScrollArea, QGridLayout, QFrame, QHBoxLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from ui.file_preview_widget import FilePreviewWidget


class FileGalleryWidget(QWidget):
    """Галерея файлов с адаптивной сеткой"""

    upload_requested = pyqtSignal(str)  # stage
    delete_requested = pyqtSignal(int, str)  # file_id, stage
    files_changed = pyqtSignal()  # Сигнал изменения списка файлов

    def __init__(self, title, stage, file_types, can_delete=True, can_upload=True, parent=None):
        super().__init__(parent)
        self.title = title
        self.stage = stage
        self.file_types = file_types  # ['image', 'pdf']
        self.can_delete = can_delete  # Право на удаление файлов
        self.can_upload = can_upload  # Право на загрузку файлов
        self.preview_widgets = []
        self.current_columns = 4  # Текущее количество столбцов

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Заголовок и кнопка загрузки
        header_layout = QHBoxLayout()

        title_label = QLabel(f"<b>{self.title}</b>")
        title_label.setStyleSheet("font-size: 11px; color: #2C3E50;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Кнопка загрузки (только если есть право на загрузку)
        if self.can_upload:
            upload_btn = QPushButton("Загрузить файлы")
            upload_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #7f8c8d;
                }
            """)
            upload_btn.setFixedHeight(28)
            upload_btn.clicked.connect(lambda: self.upload_requested.emit(self.stage))
            header_layout.addWidget(upload_btn)

        layout.addLayout(header_layout)

        # Контейнер с сеткой (без scroll area для автоподстройки высоты)
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(3)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.grid_container.setLayout(self.grid_layout)

        layout.addWidget(self.grid_container)

        self.setLayout(layout)

    def load_files(self, files, preview_generator):
        """Загрузка списка файлов с превью

        Args:
            files: список словарей с данными файлов
            preview_generator: функция для генерации QPixmap превью
        """
        # Очищаем существующие виджеты
        self.clear_previews()

        # Создаем превью для каждого файла
        for file_data in files:
            preview_pixmap = None

            if file_data['file_type'] == 'image':
                preview_pixmap = preview_generator(file_data)

            preview_widget = FilePreviewWidget(
                file_id=file_data['id'],
                file_name=file_data['file_name'],
                file_type=file_data['file_type'],
                public_link=file_data['public_link'],
                preview_pixmap=preview_pixmap,
                can_delete=self.can_delete
            )

            # Подключаем сигналы
            preview_widget.delete_requested.connect(
                lambda fid, stage=self.stage: self.delete_requested.emit(fid, stage)
            )

            self.preview_widgets.append(preview_widget)

        # Размещаем в сетке (4 превью в ряду по умолчанию)
        self.current_columns = 4
        self.arrange_previews(columns=4)

    def arrange_previews(self, columns=4):
        """Размещение превью в адаптивной сетке

        Args:
            columns: количество столбцов в сетке
        """
        for i, widget in enumerate(self.preview_widgets):
            row = i // columns
            col = i % columns
            self.grid_layout.addWidget(widget, row, col)

    def clear_previews(self):
        """Очистка всех превью"""
        for widget in self.preview_widgets:
            self.grid_layout.removeWidget(widget)
            widget.deleteLater()
        self.preview_widgets.clear()

    def get_files_count(self):
        """Получение количества файлов в галерее"""
        return len(self.preview_widgets)

    def resizeEvent(self, event):
        """Обработка изменения размера для адаптивной сетки"""
        super().resizeEvent(event)

        # Используем QTimer чтобы избежать множественных пересчетов
        if hasattr(self, '_resize_timer'):
            self._resize_timer.stop()

        from PyQt5.QtCore import QTimer
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._do_resize)
        self._resize_timer.start(100)  # Задержка 100мс

    def _get_effective_width(self):
        """Получение эффективной ширины для расчета столбцов"""
        # Ищем родительский QScrollArea
        from PyQt5.QtWidgets import QScrollArea
        widget = self.parent()
        while widget:
            if isinstance(widget.parent(), QScrollArea):
                scroll_area = widget.parent()
                # Возвращаем ширину viewport
                return scroll_area.viewport().width()
            widget = widget.parent()

        # Если не нашли scroll area, используем собственную ширину
        return self.width()

    def _do_resize(self):
        """Выполнение перестройки сетки"""
        # Используем эффективную ширину (viewport scroll area)
        effective_width = self._get_effective_width()

        # Рассчитываем количество столбцов на основе ширины
        available_width = effective_width - 20  # Учитываем отступы
        preview_width = 123  # ширина одного превью (120) + отступ (3)
        min_columns = 2

        # Динамическое распределение столбцов на основе доступной ширины
        columns = max(min_columns, available_width // preview_width)

        # Перестраиваем сетку ТОЛЬКО если изменилось количество столбцов
        if self.preview_widgets and columns != self.current_columns:
            self.current_columns = columns

            # Очищаем текущую сетку
            for i in reversed(range(self.grid_layout.count())):
                self.grid_layout.itemAt(i).widget().setParent(None)

            # Перестраиваем с новым количеством столбцов
            self.arrange_previews(columns)

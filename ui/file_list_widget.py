# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,

                             QPushButton, QScrollArea, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCursor, QPixmap
from utils.icon_loader import IconLoader


class FileListItemWidget(QWidget):
    """Виджет элемента списка файлов"""
    delete_requested = pyqtSignal(int)  # file_id
    file_clicked = pyqtSignal(str)  # public_link

    def __init__(self, file_id, file_name, file_type, public_link, can_delete=True, parent=None):
        super().__init__(parent)
        self.file_id = file_id
        self.file_name = file_name
        self.file_type = file_type
        self.public_link = public_link
        self.can_delete = can_delete

        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 2, 4, 2)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignVCenter)  # Вертикальное выравнивание

        # Иконка типа файла
        icon_label = QLabel()
        if self.file_type == 'pdf':
            icon_label.setText("PDF")
            icon_label.setStyleSheet("""
                QLabel {
                    background-color: #E74C3C;
                    color: white;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 2px 6px;
                    border-radius: 3px;
                    border: none;
                }
            """)
            icon_label.setToolTip("PDF")
        elif self.file_type == 'excel':
            icon_label.setText("XLS")
            icon_label.setStyleSheet("""
                QLabel {
                    background-color: #27AE60;
                    color: white;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 2px 6px;
                    border-radius: 3px;
                    border: none;
                }
            """)
            icon_label.setToolTip("Excel")
        else:
            icon_label.setText("FILE")
            icon_label.setStyleSheet("""
                QLabel {
                    background-color: #95A5A6;
                    color: white;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 2px 6px;
                    border-radius: 3px;
                    border: none;
                }
            """)

        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedHeight(20)
        layout.addWidget(icon_label, 0, Qt.AlignVCenter)

        # Имя файла (кликабельное)
        name_label = QLabel(f'<a href="{self.public_link}">{self.file_name}</a>')
        name_label.setOpenExternalLinks(True)
        name_label.setCursor(QCursor(Qt.PointingHandCursor))
        name_label.setStyleSheet("QLabel { color: #ffd93c; font-size: 10px; border: none; }")
        layout.addWidget(name_label, 1, Qt.AlignVCenter)

        # Кнопка удаления (только если есть право на удаление)
        if self.can_delete:
            delete_btn = IconLoader.create_icon_button('delete-red', '', 'Удалить файл', icon_size=12)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #E74C3C;
                    border: 1px solid #E74C3C;
                    border-radius: 6px;
                    padding: 0px;
                    min-height: 24px;
                    max-height: 24px;
                    min-width: 24px;
                    max-width: 24px;
                }
                QPushButton:hover {
                    background-color: #FFE5E5;
                    color: #C0392B;
                    border: 1px solid #C0392B;
                }
            """)
            delete_btn.setFixedSize(24, 24)
            delete_btn.setCursor(QCursor(Qt.PointingHandCursor))
            delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.file_id))
            layout.addWidget(delete_btn, 0, Qt.AlignVCenter)

        self.setLayout(layout)
        self.setMinimumHeight(28)
        self.setMaximumHeight(28)
        self.setStyleSheet("""
            FileListItemWidget {
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
            }
            FileListItemWidget:hover {
                background-color: #E9ECEF;
            }
        """)


class FileListWidget(QWidget):
    """Виджет списка файлов для стадий проекта"""
    upload_requested = pyqtSignal(str)  # stage
    delete_requested = pyqtSignal(int, str)  # file_id, stage

    def __init__(self, title, stage, file_types=None, can_delete=True, can_upload=True, parent=None):
        super().__init__(parent)
        self.title = title
        self.stage = stage
        self.file_types = file_types or []
        self.can_delete = can_delete  # Право на удаление файлов
        self.can_upload = can_upload  # Право на загрузку файлов
        self.file_items = []

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Заголовок и кнопка загрузки
        header_layout = QHBoxLayout()

        title_label = QLabel(self.title)
        title_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #2C3E50;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Кнопка загрузки (только если есть право на загрузку)
        if self.can_upload:
            upload_btn = QPushButton("Загрузить файлы")
            upload_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    padding: 0px 12px;
                    border-radius: 6px;
                    font-size: 10px;
                    min-height: 28px;
                    max-height: 28px;
                }
                QPushButton:hover { background-color: #7f8c8d; }
            """)
            upload_btn.setFixedHeight(28)
            upload_btn.clicked.connect(lambda: self.upload_requested.emit(self.stage))
            header_layout.addWidget(upload_btn)

        main_layout.addLayout(header_layout)

        # Область прокрутки для списка файлов
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setMinimumHeight(50)
        # ИСПРАВЛЕНИЕ 25.01.2026: Убрано ограничение максимальной высоты
        # Высота будет динамически рассчитываться в методе _update_height()

        self.files_container = QWidget()
        self.files_layout = QVBoxLayout()
        self.files_layout.setContentsMargins(0, 0, 0, 0)
        self.files_layout.setSpacing(3)
        self.files_container.setLayout(self.files_layout)

        self.scroll_area.setWidget(self.files_container)
        main_layout.addWidget(self.scroll_area)

        # Placeholder когда нет файлов
        self.empty_label = QLabel("Файлы не загружены")
        self.empty_label.setStyleSheet("color: #999; font-style: italic; padding: 5px;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.files_layout.addWidget(self.empty_label)

        self.setLayout(main_layout)
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

    def load_files(self, files, preview_generator=None):
        """Загрузка списка файлов

        Args:
            files: список словарей с данными файлов
            preview_generator: не используется (для совместимости с FileGalleryWidget)
        """
        # Очищаем текущий список
        self.clear_files()

        if not files:
            self.empty_label.show()
            return

        self.empty_label.hide()

        # Добавляем файлы
        for file_data in files:
            item = FileListItemWidget(
                file_id=file_data['id'],
                file_name=file_data['file_name'],
                file_type=file_data['file_type'],
                public_link=file_data['public_link'],
                can_delete=self.can_delete
            )
            item.delete_requested.connect(lambda fid, s=self.stage: self.delete_requested.emit(fid, s))

            self.files_layout.addWidget(item)
            self.file_items.append(item)

        self.files_layout.addStretch()

        # ИСПРАВЛЕНИЕ 25.01.2026: Динамическая высота в зависимости от количества файлов
        self._update_height()

    def _update_height(self):
        """Динамический расчет высоты в зависимости от количества файлов"""
        file_count = len(self.file_items)
        if file_count == 0:
            # Минимальная высота для пустого списка
            self.scroll_area.setFixedHeight(50)
        else:
            # 31px на каждый файл (28px высота + 3px spacing) + отступы, максимум 400px
            calculated_height = min(31 * file_count + 5, 400)
            self.scroll_area.setFixedHeight(calculated_height)

    def clear_files(self):
        """Очистка списка файлов"""
        for item in self.file_items:
            item.deleteLater()
        self.file_items.clear()

        # Удаляем все виджеты из layout кроме empty_label
        while self.files_layout.count() > 0:
            child = self.files_layout.takeAt(0)
            if child.widget() and child.widget() != self.empty_label:
                child.widget().deleteLater()

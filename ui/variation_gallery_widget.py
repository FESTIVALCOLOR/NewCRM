# -*- coding: utf-8 -*-
"""
Галерея файлов с поддержкой вариаций (вкладок)
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,

                             QHBoxLayout, QTabWidget, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QCursor
from ui.file_gallery_widget import FileGalleryWidget
from utils.icon_loader import IconLoader


class VariationGalleryWidget(QWidget):
    """Галерея файлов с поддержкой нескольких вариаций"""

    upload_requested = pyqtSignal(str, int)  # stage, variation
    delete_requested = pyqtSignal(int, str, int)  # file_id, stage, variation
    add_variation_requested = pyqtSignal(str)  # stage
    delete_variation_requested = pyqtSignal(str, int)  # stage, variation

    def __init__(self, title, stage, file_types, can_delete=True, can_upload=True, parent=None):
        super().__init__(parent)
        self.title = title
        self.stage = stage
        self.file_types = file_types
        self.can_delete = can_delete
        self.can_upload = can_upload
        self.variation_galleries = {}  # {variation_number: FileGalleryWidget}

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Заголовок и кнопки управления
        header_layout = QHBoxLayout()

        title_label = QLabel(f"<b>{self.title}</b>")
        title_label.setStyleSheet("font-size: 11px; color: #2C3E50;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Кнопки управления вариациями (только если есть право на загрузку)
        if self.can_upload:
            # Кнопка "Загрузить файлы" (первая)
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
                QPushButton:hover {
                    background-color: #7f8c8d;
                }
            """)
            upload_btn.setFixedHeight(28)
            upload_btn.setCursor(QCursor(Qt.PointingHandCursor))
            upload_btn.clicked.connect(self.on_upload_clicked)
            header_layout.addWidget(upload_btn)

            # Кнопка "Добавить папку" (квадратная с иконкой папки)
            add_variation_btn = QPushButton()
            folder_icon = IconLoader.load('folder.svg')
            if folder_icon and not folder_icon.isNull():
                add_variation_btn.setIcon(folder_icon)
                add_variation_btn.setIconSize(QSize(14, 14))
            else:
                # Fallback на текст если иконка не найдена
                add_variation_btn.setText("+")

            add_variation_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    border-radius: 6px;
                    padding: 0px;
                    min-height: 28px;
                    max-height: 28px;
                    min-width: 28px;
                    max-width: 28px;
                }
                QPushButton:hover {
                    background-color: #7f8c8d;
                }
            """)
            add_variation_btn.setFixedSize(28, 28)
            add_variation_btn.setToolTip('Добавить папку (новую вариацию)')
            add_variation_btn.setCursor(QCursor(Qt.PointingHandCursor))
            add_variation_btn.clicked.connect(self.on_add_variation_clicked)
            header_layout.addWidget(add_variation_btn)

            # Кнопка "Удалить папку" (красная с иконкой корзины, как у Референсов)
            delete_variation_btn = IconLoader.create_icon_button('delete', '', 'Удалить папку (текущую вариацию)', icon_size=14)
            delete_variation_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E74C3C;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 0px;
                    min-height: 28px;
                    max-height: 28px;
                    min-width: 28px;
                    max-width: 28px;
                }
                QPushButton:hover {
                    background-color: #C0392B;
                }
            """)
            delete_variation_btn.setFixedSize(28, 28)
            delete_variation_btn.setCursor(QCursor(Qt.PointingHandCursor))
            delete_variation_btn.clicked.connect(self.on_delete_variation_clicked)
            header_layout.addWidget(delete_variation_btn)
            self.delete_variation_btn = delete_variation_btn

        layout.addLayout(header_layout)

        # Вкладки для вариаций
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                background: white;
            }
            QTabBar::tab {
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                padding: 6px 12px;
                margin-right: 2px;
                font-size: 10px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background-color: #ffffff;
            }
        """)
        layout.addWidget(self.tab_widget)

        self.setLayout(layout)

        # Создаем вкладку "Вариация 1" по умолчанию
        self.add_variation_tab(1)

    def add_variation_tab(self, variation_number):
        """Добавить вкладку для вариации"""
        if variation_number in self.variation_galleries:
            return  # Вкладка уже существует

        # Создаем галерею для этой вариации (БЕЗ кнопки загрузить внутри)
        gallery = FileGalleryWidget(
            title="",  # Заголовок не нужен, т.к. есть название вкладки
            stage=self.stage,
            file_types=self.file_types,
            can_delete=self.can_delete,
            can_upload=False  # Кнопка загрузить теперь только в header
        )

        # Подключаем только сигнал удаления
        gallery.delete_requested.connect(
            lambda fid, s, v=variation_number: self.delete_requested.emit(fid, s, v)
        )

        # Добавляем вкладку
        tab_index = self.tab_widget.addTab(gallery, f"Вариация {variation_number}")
        self.variation_galleries[variation_number] = gallery

        # Переключаемся на новую вкладку
        self.tab_widget.setCurrentIndex(tab_index)

        return gallery

    def remove_variation_tab(self, variation_number):
        """Удалить вкладку вариации"""
        if variation_number not in self.variation_galleries:
            return

        gallery = self.variation_galleries[variation_number]

        # Находим индекс вкладки
        for i in range(self.tab_widget.count()):
            if self.tab_widget.widget(i) == gallery:
                self.tab_widget.removeTab(i)
                break

        # Удаляем из словаря
        del self.variation_galleries[variation_number]
        gallery.deleteLater()

    def on_upload_clicked(self):
        """Обработчик кнопки 'Загрузить файлы'"""
        # Определяем текущую активную вариацию
        current_variation = self.get_current_variation()

        # Отправляем сигнал загрузки с номером текущей вариации
        self.upload_requested.emit(self.stage, current_variation)

    def on_add_variation_clicked(self):
        """Обработчик кнопки 'Добавить папку'"""
        # Находим следующий номер вариации
        existing_variations = sorted(self.variation_galleries.keys())
        next_variation = existing_variations[-1] + 1 if existing_variations else 1

        # Отправляем сигнал о создании новой вариации
        self.add_variation_requested.emit(self.stage)

        # Добавляем вкладку (после успешного создания папки на Яндекс.Диске)
        self.add_variation_tab(next_variation)

    def on_delete_variation_clicked(self):
        """Обработчик кнопки 'Удалить папку'"""
        current_index = self.tab_widget.currentIndex()
        if current_index == -1:
            return

        # Находим номер текущей вариации
        current_variation = None
        current_widget = self.tab_widget.widget(current_index)
        for variation, gallery in self.variation_galleries.items():
            if gallery == current_widget:
                current_variation = variation
                break

        if current_variation is None:
            return

        # Запрещаем удаление последней вариации
        if len(self.variation_galleries) == 1:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(
                self,
                'Предупреждение',
                'Нельзя удалить последнюю вариацию',
                'warning'
            ).exec_()
            return

        # Отправляем сигнал об удалении вариации
        self.delete_variation_requested.emit(self.stage, current_variation)

    def load_files_for_variation(self, variation_number, files, preview_generator):
        """Загрузка файлов для конкретной вариации"""
        if variation_number not in self.variation_galleries:
            self.add_variation_tab(variation_number)

        gallery = self.variation_galleries[variation_number]
        gallery.load_files(files, preview_generator)

    def clear_all(self):
        """Очистка всех вариаций"""
        # Удаляем все вкладки кроме первой
        for variation in list(self.variation_galleries.keys()):
            if variation != 1:
                self.remove_variation_tab(variation)

        # Очищаем первую вариацию
        if 1 in self.variation_galleries:
            self.variation_galleries[1].clear_previews()

    def get_variation_count(self):
        """Получить количество вариаций"""
        return len(self.variation_galleries)

    def get_current_variation(self):
        """Получить номер текущей активной вариации"""
        current_index = self.tab_widget.currentIndex()
        if current_index == -1:
            return 1

        current_widget = self.tab_widget.widget(current_index)
        for variation, gallery in self.variation_galleries.items():
            if gallery == current_widget:
                return variation

        return 1

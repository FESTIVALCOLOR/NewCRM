# -*- coding: utf-8 -*-
"""
Виджет превью файла с кнопкой удаления
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QCursor
import webbrowser


class FilePreviewWidget(QWidget):
    """Виджет превью файла с кнопкой удаления"""

    delete_requested = pyqtSignal(int)  # file_id
    preview_clicked = pyqtSignal(str)  # public_link

    def __init__(self, file_id, file_name, file_type, public_link, preview_pixmap=None, can_delete=True, parent=None):
        super().__init__(parent)
        self.file_id = file_id
        self.file_name = file_name
        self.file_type = file_type
        self.public_link = public_link
        self.preview_pixmap = preview_pixmap
        self.can_delete = can_delete

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(3)

        # Контейнер превью с кнопкой удалить
        self.preview_container = QWidget()
        self.preview_container.setFixedSize(120, 80)

        # Превью изображения
        self.preview_label = QLabel(self.preview_container)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(120, 80)
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: #F8F9FA;
            }
        """)

        if self.preview_pixmap:
            # Масштабируем изображение с заполнением и обрезкой
            scaled_pixmap = self.preview_pixmap.scaled(
                120, 80,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            # Обрезаем по центру если изображение больше
            if scaled_pixmap.width() > 120 or scaled_pixmap.height() > 80:
                x_offset = (scaled_pixmap.width() - 120) // 2
                y_offset = (scaled_pixmap.height() - 80) // 2
                from PyQt5.QtCore import QRect
                scaled_pixmap = scaled_pixmap.copy(QRect(x_offset, y_offset, 120, 80))
            self.preview_label.setPixmap(scaled_pixmap)
        else:
            # Иконка для PDF/Excel
            if self.file_type == 'pdf':
                icon_text = "PDF"
                icon_color = "#E74C3C"
            elif self.file_type == 'excel':
                icon_text = "XLS"
                icon_color = "#27AE60"
            else:
                icon_text = "FILE"
                icon_color = "#95A5A6"

            self.preview_label.setText(icon_text)
            self.preview_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 24px;
                    font-weight: bold;
                    color: {icon_color};
                    background-color: #F8F9FA;
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                }}
            """)

        # Делаем превью кликабельным
        self.preview_label.setCursor(QCursor(Qt.PointingHandCursor))
        self.preview_label.mousePressEvent = lambda event: self.on_preview_click()

        # Кнопка удаления в правом верхнем углу (только если есть право на удаление)
        if self.can_delete:
            self.delete_btn = QPushButton('X', self.preview_container)
            self.delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #E74C3C;
                    border: 1px solid #E74C3C;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 0px;
                    min-height: 20px;
                    max-height: 20px;
                    min-width: 20px;
                    max-width: 20px;
                }
                QPushButton:hover {
                    background-color: #FFE5E5;
                    color: #C0392B;
                    border: 1px solid #C0392B;
                }
            """)
            self.delete_btn.setFixedSize(20, 20)
            self.delete_btn.setToolTip('Удалить файл')
            self.delete_btn.setCursor(QCursor(Qt.PointingHandCursor))
            self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.file_id))
            self.delete_btn.move(98, 2)  # Позиция в правом верхнем углу (120 - 20 - 2)
            self.delete_btn.hide()  # Скрываем по умолчанию

            # Обработчики событий для показа/скрытия кнопки при наведении
            self.preview_container.enterEvent = lambda event: self.delete_btn.show()
            self.preview_container.leaveEvent = lambda event: self.delete_btn.hide()

        layout.addWidget(self.preview_container)

        # Имя файла (обрезанное, полное имя в tooltip)
        name_display = self.file_name if len(self.file_name) <= 16 else self.file_name[:13] + '...'
        name_label = QLabel(name_display)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFixedWidth(120)
        name_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #555;
                padding: 1px;
            }
        """)
        name_label.setToolTip(self.file_name)
        layout.addWidget(name_label)

        self.setLayout(layout)
        self.setFixedWidth(126)

    def on_preview_click(self):
        """Обработчик клика по превью - открывает файл в браузере"""
        if self.public_link:
            webbrowser.open(self.public_link)
            self.preview_clicked.emit(self.public_link)

    def update_preview(self, pixmap):
        """Обновление превью изображения

        Args:
            pixmap: QPixmap с новым превью
        """
        if pixmap and not pixmap.isNull():
            # Масштабируем изображение с заполнением и обрезкой
            scaled_pixmap = pixmap.scaled(
                120, 80,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            # Обрезаем по центру если изображение больше
            if scaled_pixmap.width() > 120 or scaled_pixmap.height() > 80:
                x_offset = (scaled_pixmap.width() - 120) // 2
                y_offset = (scaled_pixmap.height() - 80) // 2
                from PyQt5.QtCore import QRect
                scaled_pixmap = scaled_pixmap.copy(QRect(x_offset, y_offset, 120, 80))
            self.preview_label.setPixmap(scaled_pixmap)

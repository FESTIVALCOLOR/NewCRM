# -*- coding: utf-8 -*-
"""
Диалоговые окна для системы обновлений
"""
import os
import re
import threading
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,

                             QLineEdit, QPushButton, QMessageBox, QProgressBar)
from PyQt5.QtCore import QTimer
from config import APP_VERSION


class VersionDialog(QDialog):
    """Диалог изменения версии программы (только для руководителя студии)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление версией")
        self.setFixedSize(450, 180)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Текущая версия
        current_label = QLabel(f"Текущая версия: <b>{APP_VERSION}</b>")
        current_label.setStyleSheet("font-size: 13px; padding: 5px;")
        layout.addWidget(current_label)

        # Поле ввода новой версии
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("Новая версия:"))
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("Например: 1.1.0")
        self.version_input.setStyleSheet("padding: 5px; font-size: 12px;")
        version_layout.addWidget(self.version_input)
        layout.addLayout(version_layout)

        # Подсказка
        hint_label = QLabel("Формат версии: X.Y.Z (три числа через точку)")
        hint_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(hint_label)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_btn = QPushButton("Сохранить")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_btn.clicked.connect(self.save_version)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f1f1;
                color: #333;
                padding: 8px 20px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def save_version(self):
        """Сохранение новой версии в config.py"""
        new_version = self.version_input.text().strip()

        # Валидация формата версии (X.Y.Z)
        if not re.match(r'^\d+\.\d+\.\d+$', new_version):
            QMessageBox.warning(
                self,
                "Ошибка",
                "Неверный формат версии.\nИспользуйте формат X.Y.Z (например, 1.2.0)"
            )
            return

        try:
            # Обновление в config.py
            config_path = 'config.py'

            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Замена строки версии
            new_content = re.sub(
                r'APP_VERSION = "[^"]*"',
                f'APP_VERSION = "{new_version}"',
                content
            )

            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            QMessageBox.information(
                self,
                "Успех",
                f"Версия изменена на {new_version}.\n\nПерезапустите приложение для применения изменений."
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось изменить версию:\n{e}"
            )


class UpdateDialog(QDialog):
    """Диалог обновления программы"""

    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.setWindowTitle("Доступно обновление")
        self.setFixedSize(550, 350)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Информация о новой версии
        version = self.update_info["version"]
        details = self.update_info.get("details", {})

        info_html = f"""
        <div style="padding: 10px;">
            <h2 style="color: #2196F3; margin-bottom: 10px;">Доступна новая версия: {version}</h2>
            <p style="margin: 5px 0;"><b>Дата выпуска:</b> {details.get('release_date', 'Неизвестно')}</p>
            <p style="margin: 5px 0;"><b>Размер:</b> {details.get('size_mb', '?')} МБ</p>
            <br>
            <p style="margin: 5px 0;"><b>Что нового:</b></p>
            <p style="margin: 5px 0; padding: 10px; background-color: #f5f5f5; border-left: 3px solid #2196F3;">
                {details.get('changelog', 'Нет описания изменений')}
            </p>
        </div>
        """

        info_label = QLabel(info_html)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(info_label)

        # Прогресс-бар для загрузки
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Статус загрузки
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        self.status_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.download_btn = QPushButton("Загрузить и установить")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 25px;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.download_btn.clicked.connect(self.download_and_install)

        self.later_btn = QPushButton("Позже")
        self.later_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f1f1;
                color: #333;
                padding: 10px 25px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.later_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.later_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def download_and_install(self):
        """Загрузка и установка обновления"""
        self.download_btn.setEnabled(False)
        self.later_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("Подготовка к загрузке...")

        def progress_callback(current, total):
            """Обновление прогресс-бара"""
            progress = int((current / total) * 100)
            QTimer.singleShot(0, lambda: self.progress_bar.setValue(progress))
            QTimer.singleShot(0, lambda: self.status_label.setText(
                f"Загружено: {current // 1024 // 1024} МБ из {total // 1024 // 1024} МБ"
            ))

        def download_thread():
            """Поток загрузки обновления"""
            from utils.update_manager import UpdateManager
            manager = UpdateManager()

            try:
                QTimer.singleShot(0, lambda: self.status_label.setText("Загрузка обновления..."))

                # Загрузка
                update_path = manager.download_update(
                    self.update_info["version"],
                    progress_callback
                )

                if not update_path:
                    raise Exception("Не удалось загрузить обновление")

                QTimer.singleShot(0, lambda: self.status_label.setText("Установка обновления..."))
                QTimer.singleShot(0, lambda: self.progress_bar.setValue(100))

                # Небольшая задержка для отображения 100%
                import time
                time.sleep(0.5)

                # Установка (перезапустит приложение)
                manager.install_update(update_path)

            except Exception as e:
                QTimer.singleShot(0, lambda: QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось загрузить обновление:\n{e}"
                ))
                QTimer.singleShot(0, lambda: self.download_btn.setEnabled(True))
                QTimer.singleShot(0, lambda: self.later_btn.setEnabled(True))
                QTimer.singleShot(0, lambda: self.progress_bar.setVisible(False))
                QTimer.singleShot(0, lambda: self.status_label.setVisible(False))

        # Запуск в отдельном потоке
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

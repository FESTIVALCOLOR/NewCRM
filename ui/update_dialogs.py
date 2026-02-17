# -*- coding: utf-8 -*-
"""
Диалоговые окна для системы обновлений
"""
import os
import re
import threading
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QMessageBox, QProgressBar,
                             QFileDialog, QTextEdit, QGroupBox)
from PyQt5.QtCore import QTimer
from config import APP_VERSION


class VersionDialog(QDialog):
    """Диалог управления версией и загрузки обновлений (только для руководителя студии)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление версией и обновлениями")
        self.setFixedSize(550, 520)
        self.selected_exe_path = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # === Блок сверки версии с сервером ===
        server_group = QGroupBox("Сверка версии с сервером")
        server_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; }")
        server_layout = QVBoxLayout()

        self.server_info_label = QLabel(f"Клиент: <b>{APP_VERSION}</b> | Сервер: <i>не проверено</i>")
        self.server_info_label.setStyleSheet("font-size: 12px; padding: 5px;")
        server_layout.addWidget(self.server_info_label)

        check_server_btn = QPushButton("Проверить версию сервера")
        check_server_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 6px 15px;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        check_server_btn.clicked.connect(self.check_server_version)
        server_layout.addWidget(check_server_btn)

        server_group.setLayout(server_layout)
        layout.addWidget(server_group)

        # === Блок изменения локальной версии ===
        version_group = QGroupBox("Изменение версии")
        version_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; }")
        version_layout_inner = QVBoxLayout()

        version_row = QHBoxLayout()
        version_row.addWidget(QLabel("Новая версия:"))
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("Например: 1.1.0")
        self.version_input.setStyleSheet("padding: 5px; font-size: 12px;")
        version_row.addWidget(self.version_input)

        save_version_btn = QPushButton("Сохранить")
        save_version_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 6px 15px;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        save_version_btn.clicked.connect(self.save_version)
        version_row.addWidget(save_version_btn)

        version_layout_inner.addLayout(version_row)

        hint_label = QLabel("Формат: X.Y.Z (три числа через точку)")
        hint_label.setStyleSheet("color: #666; font-size: 10px;")
        version_layout_inner.addWidget(hint_label)

        version_group.setLayout(version_layout_inner)
        layout.addWidget(version_group)

        # === Блок загрузки обновления на Яндекс.Диск ===
        upload_group = QGroupBox("Загрузка обновления на Яндекс.Диск")
        upload_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; }")
        upload_layout = QVBoxLayout()

        # Выбор exe файла
        file_row = QHBoxLayout()
        self.file_label = QLabel("Файл не выбран")
        self.file_label.setStyleSheet("color: #666; font-size: 11px; padding: 3px;")
        file_row.addWidget(self.file_label, 1)

        choose_btn = QPushButton("Выбрать .exe")
        choose_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 6px 15px;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #F57C00; }
        """)
        choose_btn.clicked.connect(self.choose_exe_file)
        file_row.addWidget(choose_btn)
        upload_layout.addLayout(file_row)

        # Описание изменений
        upload_layout.addWidget(QLabel("Описание изменений:"))
        self.changelog_input = QTextEdit()
        self.changelog_input.setPlaceholderText("Что нового в этой версии...")
        self.changelog_input.setMaximumHeight(70)
        self.changelog_input.setStyleSheet("font-size: 11px; padding: 3px;")
        upload_layout.addWidget(self.changelog_input)

        # Прогресс загрузки
        self.upload_progress = QProgressBar()
        self.upload_progress.setVisible(False)
        self.upload_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #FF9800;
                border-radius: 3px;
            }
        """)
        upload_layout.addWidget(self.upload_progress)

        self.upload_status_label = QLabel("")
        self.upload_status_label.setVisible(False)
        self.upload_status_label.setStyleSheet("color: #666; font-size: 10px;")
        upload_layout.addWidget(self.upload_status_label)

        # Кнопка загрузки
        self.upload_btn = QPushButton("Загрузить обновление на Яндекс.Диск")
        self.upload_btn.setEnabled(False)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #F57C00; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.upload_btn.clicked.connect(self.upload_to_yandex)
        upload_layout.addWidget(self.upload_btn)

        upload_group.setLayout(upload_layout)
        layout.addWidget(upload_group)

        # Кнопка закрыть
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f1f1;
                color: #333;
                padding: 8px 20px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #e0e0e0; }
        """)
        close_btn.clicked.connect(self.reject)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)

        self.setLayout(layout)

    def check_server_version(self):
        """Сверка версии клиента с сервером"""
        from utils.update_manager import UpdateManager

        manager = UpdateManager()
        result = manager.check_server_version()

        if result.get("error"):
            self.server_info_label.setText(
                f"Клиент: <b>{APP_VERSION}</b> | Сервер: <span style='color: red;'>ошибка: {result['error']}</span>"
            )
        elif result.get("match"):
            self.server_info_label.setText(
                f"Клиент: <b>{APP_VERSION}</b> | Сервер: <b>{result['server_version']}</b> "
                f"<span style='color: green;'>&#10004; совпадает</span>"
            )
        else:
            self.server_info_label.setText(
                f"Клиент: <b>{APP_VERSION}</b> | Сервер: <b>{result['server_version']}</b> "
                f"<span style='color: red;'>&#10008; не совпадает!</span>"
            )

    def choose_exe_file(self):
        """Выбор exe файла для загрузки"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать файл обновления", "",
            "Исполняемые файлы (*.exe);;Все файлы (*)"
        )
        if path:
            self.selected_exe_path = path
            file_size_mb = os.path.getsize(path) / (1024 * 1024)
            self.file_label.setText(f"{os.path.basename(path)} ({file_size_mb:.1f} МБ)")
            self.file_label.setStyleSheet("color: #333; font-size: 11px; padding: 3px;")
            self.upload_btn.setEnabled(True)

    def upload_to_yandex(self):
        """Загрузка обновления на Яндекс.Диск"""
        if not self.selected_exe_path:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите файл обновления (.exe)")
            return

        version = self.version_input.text().strip()
        if not version:
            version = APP_VERSION

        if not re.match(r'^\d+\.\d+\.\d+$', version):
            QMessageBox.warning(self, "Ошибка", "Укажите корректную версию формата X.Y.Z")
            return

        changelog = self.changelog_input.toPlainText().strip()

        self.upload_btn.setEnabled(False)
        self.upload_progress.setVisible(True)
        self.upload_progress.setRange(0, 0)  # Indeterminate
        self.upload_status_label.setVisible(True)
        self.upload_status_label.setText("Загрузка на Яндекс.Диск...")

        def upload_thread():
            from utils.update_manager import UpdateManager
            manager = UpdateManager()

            try:
                manager.upload_update_to_yandex(
                    self.selected_exe_path,
                    version,
                    changelog
                )

                QTimer.singleShot(0, lambda: self._upload_success(version))

            except Exception as e:
                error_msg = str(e)
                QTimer.singleShot(0, lambda: self._upload_error(error_msg))

        thread = threading.Thread(target=upload_thread, daemon=True)
        thread.start()

    def _upload_success(self, version):
        """Обновление загружено успешно"""
        self.upload_progress.setVisible(False)
        self.upload_status_label.setText(f"Версия {version} загружена на Яндекс.Диск")
        self.upload_status_label.setStyleSheet("color: green; font-size: 10px;")
        self.upload_btn.setEnabled(True)

        QMessageBox.information(
            self, "Успех",
            f"Обновление {version} загружено на Яндекс.Диск в папку CRM_UPDATES.\n\n"
            f"Файл version.json обновлён."
        )

    def _upload_error(self, error):
        """Ошибка загрузки"""
        self.upload_progress.setVisible(False)
        self.upload_status_label.setText(f"Ошибка: {error}")
        self.upload_status_label.setStyleSheet("color: red; font-size: 10px;")
        self.upload_btn.setEnabled(True)

        QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить обновление:\n{error}")

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

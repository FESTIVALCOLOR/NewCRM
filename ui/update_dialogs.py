# -*- coding: utf-8 -*-
"""
Диалоговые окна для системы обновлений
"""
import os
import re
import threading
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QProgressBar,
                             QFileDialog, QTextEdit, QGroupBox, QFrame,
                             QWidget)
from PyQt5.QtCore import Qt, pyqtSignal
from config import APP_VERSION
from ui.custom_title_bar import CustomTitleBar
from ui.custom_message_box import CustomMessageBox
from utils.resource_path import resource_path

ICONS_PATH = resource_path('resources/icons').replace('\\', '/')


class VersionDialog(QDialog):
    """Диалог управления версией и загрузки обновлений (только для руководителя студии)"""

    # Сигналы для межпоточного общения (надёжнее QTimer.singleShot)
    _sig_upload_ok = pyqtSignal(str)
    _sig_upload_err = pyqtSignal(str)
    _sig_build_progress = pyqtSignal(str)   # текст прогресса сборки
    _sig_build_ok = pyqtSignal(str)         # путь к собранному EXE
    _sig_build_err = pyqtSignal(str)        # ошибка сборки

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(560, 850)
        self.selected_exe_path = None
        self._is_uploading = False
        self._upload_lock = threading.Lock()
        self._sig_upload_ok.connect(self._upload_success)
        self._sig_upload_err.connect(self._upload_error)
        self._sig_build_progress.connect(self._on_build_progress)
        self._sig_build_ok.connect(self._on_build_ok)
        self._sig_build_err.connect(self._on_build_err)
        self._is_building = False
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Контейнер с рамкой
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
            }
        """)

        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)

        # Title Bar
        title_bar = CustomTitleBar(self, 'Управление версией и обновлениями', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        # Контент
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #FFFFFF;")

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 20)

        # === Блок сверки версии с сервером ===
        server_group = QGroupBox("Сверка версии с сервером")
        server_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 14px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }}
        """)
        server_layout = QVBoxLayout()
        server_layout.setContentsMargins(12, 8, 12, 12)

        self.server_info_label = QLabel(f"Клиент: <b>{APP_VERSION}</b> | Сервер: <i>не проверено</i>")
        self.server_info_label.setStyleSheet("font-size: 12px; padding: 5px; border: none;")
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
        version_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 14px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }}
        """)
        version_layout_inner = QVBoxLayout()
        version_layout_inner.setContentsMargins(12, 8, 12, 12)

        version_row = QHBoxLayout()
        lbl = QLabel("Новая версия:")
        lbl.setStyleSheet("border: none;")
        version_row.addWidget(lbl)
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("Например: 1.1.0")
        self.version_input.setStyleSheet("padding: 5px; font-size: 12px; border: 1px solid #d9d9d9; border-radius: 4px;")
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
        hint_label.setStyleSheet("color: #666; font-size: 10px; border: none;")
        version_layout_inner.addWidget(hint_label)

        version_group.setLayout(version_layout_inner)
        layout.addWidget(version_group)

        # === Блок сборки EXE ===
        build_group = QGroupBox("Сборка EXE")
        build_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 14px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }}
        """)
        build_layout = QVBoxLayout()
        build_layout.setContentsMargins(12, 8, 12, 12)

        self.build_status_label = QLabel("EXE будет собран автоматически после сохранения версии")
        self.build_status_label.setStyleSheet("color: #666; font-size: 11px; padding: 3px; border: none;")
        build_layout.addWidget(self.build_status_label)

        self.build_progress = QProgressBar()
        self.build_progress.setVisible(False)
        self.build_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
            }
        """)
        build_layout.addWidget(self.build_progress)

        self.build_btn = QPushButton("Собрать EXE вручную")
        self.build_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 6px 15px;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.build_btn.clicked.connect(self._start_build)
        build_layout.addWidget(self.build_btn)

        build_group.setLayout(build_layout)
        layout.addWidget(build_group)

        # === Блок загрузки обновления на Яндекс.Диск ===
        upload_group = QGroupBox("Загрузка обновления на Яндекс.Диск")
        upload_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 14px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }}
        """)
        upload_layout = QVBoxLayout()
        upload_layout.setContentsMargins(12, 8, 12, 12)

        # Выбор exe файла
        file_row = QHBoxLayout()
        self.file_label = QLabel("Файл не выбран")
        self.file_label.setStyleSheet("color: #666; font-size: 11px; padding: 3px; border: none;")
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
        changelog_header = QHBoxLayout()
        changelog_label = QLabel("Описание изменений:")
        changelog_label.setStyleSheet("border: none;")
        changelog_header.addWidget(changelog_label)
        changelog_header.addStretch()

        import_btn = QPushButton("Вставить из changelog")
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5; color: #555;
                padding: 3px 10px; border: 1px solid #d9d9d9;
                border-radius: 4px; font-size: 10px;
            }
            QPushButton:hover { background-color: #e8e8e8; }
        """)
        import_btn.clicked.connect(self._import_from_changelog)
        changelog_header.addWidget(import_btn)
        upload_layout.addLayout(changelog_header)

        self.changelog_input = QTextEdit()
        self.changelog_input.setPlaceholderText("Что нового в этой версии...")
        self.changelog_input.setMinimumHeight(120)
        self.changelog_input.setMaximumHeight(200)
        self.changelog_input.setStyleSheet("font-size: 11px; padding: 3px; border: 1px solid #d9d9d9; border-radius: 4px;")
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
        self.upload_status_label.setStyleSheet("color: #666; font-size: 10px; border: none;")
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

        layout.addStretch()

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

        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

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
            self.file_label.setStyleSheet("color: #333; font-size: 11px; padding: 3px; border: none;")
            self.upload_btn.setEnabled(True)

    def upload_to_yandex(self):
        """Загрузка обновления на Яндекс.Диск"""
        if not self.selected_exe_path or not self._upload_lock.acquire(blocking=False):
            return
        if self._is_uploading:
            self._upload_lock.release()
            return

        version = self.version_input.text().strip()
        if not version:
            version = APP_VERSION

        if not re.match(r'^\d+\.\d+\.\d+$', version):
            self._upload_lock.release()
            CustomMessageBox(self, "Ошибка", "Укажите корректную версию формата X.Y.Z", "warning").exec_()
            return

        changelog = self.changelog_input.toPlainText().strip()

        self._is_uploading = True
        self.upload_btn.setEnabled(False)
        self.upload_progress.setVisible(True)
        self.upload_progress.setRange(0, 0)  # Indeterminate
        self.upload_status_label.setVisible(True)
        self.upload_status_label.setText("Загрузка на Яндекс.Диск...")
        self.upload_status_label.setStyleSheet("color: #666; font-size: 10px; border: none;")

        def upload_thread():
            from utils.update_manager import UpdateManager
            manager = UpdateManager()

            try:
                manager.upload_update_to_yandex(
                    self.selected_exe_path,
                    version,
                    changelog
                )
                self._sig_upload_ok.emit(version)

            except Exception as e:
                self._sig_upload_err.emit(str(e))

        thread = threading.Thread(target=upload_thread, daemon=True)
        thread.start()

    def _upload_success(self, version):
        """Обновление загружено успешно"""
        self._is_uploading = False
        try:
            self._upload_lock.release()
        except RuntimeError:
            pass
        self.upload_progress.setRange(0, 100)
        self.upload_progress.setValue(100)
        self.upload_status_label.setText(f"Версия {version} загружена на Яндекс.Диск")
        self.upload_status_label.setStyleSheet("color: green; font-size: 10px; border: none;")
        self.upload_btn.setEnabled(True)

        CustomMessageBox(
            self, "Успех",
            f"Обновление {version} загружено на Яндекс.Диск.\n\n"
            f"Файл version.json обновлён.",
            "info"
        ).exec_()

    def _upload_error(self, error):
        """Ошибка загрузки"""
        self._is_uploading = False
        try:
            self._upload_lock.release()
        except RuntimeError:
            pass
        self.upload_progress.setRange(0, 100)
        self.upload_progress.setValue(0)
        self.upload_progress.setVisible(False)
        self.upload_status_label.setText(f"Ошибка: {error}")
        self.upload_status_label.setStyleSheet("color: red; font-size: 10px; border: none;")
        self.upload_btn.setEnabled(True)

        CustomMessageBox(self, "Ошибка", f"Не удалось загрузить обновление:\n{error}", "error").exec_()

    def _import_from_changelog(self):
        """Импорт описания из docs/changelog.md с очисткой markdown-разметки"""
        try:
            changelog_path = resource_path('docs/changelog.md')
            if not os.path.exists(changelog_path):
                CustomMessageBox(self, "Ошибка", "Файл docs/changelog.md не найден", "warning").exec_()
                return

            with open(changelog_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Извлекаем секцию текущей версии (от ## vX.Y.Z до следующего ## или конца)
            version = self.version_input.text().strip() or APP_VERSION
            # Ищем секцию версии
            import re as _re
            pattern = _re.compile(
                r'^## v?' + _re.escape(version) + r'.*?\n(.*?)(?=^## |\Z)',
                _re.MULTILINE | _re.DOTALL
            )
            match = pattern.search(content)
            if not match:
                # Если точную версию не нашли — берём первую секцию ##
                pattern2 = _re.compile(r'^## .+?\n(.*?)(?=^## |\Z)', _re.MULTILINE | _re.DOTALL)
                match = pattern2.search(content)

            if not match:
                CustomMessageBox(self, "Ошибка", "Не найдена секция версии в changelog.md", "warning").exec_()
                return

            text = match.group(1).strip()

            # Очистка markdown:
            # ### Заголовок → Заголовок:
            text = _re.sub(r'^#{1,4}\s+(.+)$', r'\1:', text, flags=_re.MULTILINE)
            # **текст** → текст
            text = _re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            # - пункт → пункт (убираем маркеры списка)
            text = _re.sub(r'^(\s*)- ', r'\1', text, flags=_re.MULTILINE)
            # Убираем лишние пустые строки (более 2 подряд)
            text = _re.sub(r'\n{3,}', '\n\n', text)

            self.changelog_input.setPlainText(text.strip())

        except Exception as e:
            CustomMessageBox(self, "Ошибка", f"Не удалось прочитать changelog:\n{e}", "error").exec_()

    def save_version(self):
        """Сохранение новой версии в config.py, server/config.py и docker-compose.yml"""
        import sys
        if getattr(sys, 'frozen', False):
            CustomMessageBox(
                self, "Недоступно",
                "Изменение версии недоступно из EXE.\n"
                "Используйте main.py для обновления версии.",
                "warning"
            ).exec_()
            return

        new_version = self.version_input.text().strip()

        if not re.match(r'^\d+\.\d+\.\d+$', new_version):
            CustomMessageBox(
                self, "Ошибка",
                "Неверный формат версии.\nИспользуйте формат X.Y.Z (например, 1.2.0)",
                "warning"
            ).exec_()
            return

        try:
            # 1. Клиентский config.py
            config_path = 'config.py'
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            new_content = re.sub(
                r'APP_VERSION = "[^"]*"',
                f'APP_VERSION = "{new_version}"',
                content
            )
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            # 2. Серверный config.py (автосинхронизация)
            server_config = 'server/config.py'
            if os.path.exists(server_config):
                with open(server_config, 'r', encoding='utf-8') as f:
                    sc = f.read()
                sc = re.sub(
                    r'app_version:\s*str\s*=\s*"[^"]*"',
                    f'app_version: str = "{new_version}"',
                    sc
                )
                with open(server_config, 'w', encoding='utf-8') as f:
                    f.write(sc)

            # 3. docker-compose.yml
            dc_path = 'docker-compose.yml'
            if os.path.exists(dc_path):
                with open(dc_path, 'r', encoding='utf-8') as f:
                    dc = f.read()
                dc = re.sub(
                    r'APP_VERSION:\s*\S+',
                    f'APP_VERSION: {new_version}',
                    dc
                )
                with open(dc_path, 'w', encoding='utf-8') as f:
                    f.write(dc)

            # 4. Обновить версию на работающем сервере через API
            server_updated = False
            try:
                from config import API_BASE_URL
                import requests as _req
                api_client = getattr(self.parent(), 'api_client', None)
                token = getattr(api_client, 'token', None) if api_client else None
                if token:
                    resp = _req.put(
                        f"{API_BASE_URL}/api/version",
                        json={"version": new_version},
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=5
                    )
                    server_updated = resp.status_code == 200
            except Exception:
                pass

            msg = f"Версия изменена на {new_version}."
            if server_updated:
                msg += "\nСервер обновлён."
            else:
                msg += "\nСервер будет обновлён после Docker rebuild."
            msg += "\n\nСборка EXE запущена..."

            CustomMessageBox(self, "Успех", msg, "info").exec_()

            # Автоматически запускаем сборку EXE
            self._start_build()

        except Exception as e:
            CustomMessageBox(
                self, "Ошибка",
                f"Не удалось изменить версию:\n{e}",
                "error"
            ).exec_()

    def _start_build(self):
        """Запуск сборки EXE через PyInstaller"""
        import sys as _sys
        if getattr(_sys, 'frozen', False):
            CustomMessageBox(
                self, "Недоступно",
                "Сборка EXE недоступна из EXE.\nИспользуйте main.py.",
                "warning"
            ).exec_()
            return

        if self._is_building:
            return

        self._is_building = True
        self.build_btn.setEnabled(False)
        self.build_progress.setVisible(True)
        self.build_progress.setRange(0, 0)  # indeterminate
        self.build_status_label.setText("Сборка EXE... (это займёт 1-2 минуты)")
        self.build_status_label.setStyleSheet("color: #2196F3; font-size: 11px; padding: 3px; border: none;")

        def build_thread():
            import subprocess as sp
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                spec_path = os.path.join(base_dir, 'InteriorStudio.spec')
                venv_pyinstaller = os.path.join(base_dir, '.venv', 'Scripts', 'pyinstaller.exe')

                if not os.path.exists(venv_pyinstaller):
                    self._sig_build_err.emit("pyinstaller.exe не найден в .venv")
                    return

                if not os.path.exists(spec_path):
                    self._sig_build_err.emit("InteriorStudio.spec не найден")
                    return

                self._sig_build_progress.emit("Запуск PyInstaller...")

                result = sp.run(
                    [venv_pyinstaller, spec_path, '--clean', '--noconfirm'],
                    cwd=base_dir,
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                exe_path = os.path.join(base_dir, 'dist', 'InteriorStudio.exe')

                if result.returncode == 0 and os.path.exists(exe_path):
                    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
                    self._sig_build_ok.emit(exe_path)
                else:
                    error = result.stderr[-500:] if result.stderr else "Неизвестная ошибка"
                    self._sig_build_err.emit(f"PyInstaller вернул код {result.returncode}\n{error}")

            except sp.TimeoutExpired:
                self._sig_build_err.emit("Таймаут сборки (>10 минут)")
            except Exception as e:
                self._sig_build_err.emit(str(e))

        thread = threading.Thread(target=build_thread, daemon=True)
        thread.start()

    def _on_build_progress(self, text):
        """Обновление статуса сборки"""
        self.build_status_label.setText(text)

    def _on_build_ok(self, exe_path):
        """Сборка завершена успешно"""
        self._is_building = False
        self.build_btn.setEnabled(True)
        self.build_progress.setRange(0, 100)
        self.build_progress.setValue(100)

        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        self.build_status_label.setText(f"EXE собран: {size_mb:.0f} МБ")
        self.build_status_label.setStyleSheet("color: green; font-size: 11px; padding: 3px; border: none;")

        # Автоматически подставляем собранный EXE в секцию загрузки
        self.selected_exe_path = exe_path
        self.file_label.setText(f"{os.path.basename(exe_path)} ({size_mb:.1f} МБ)")
        self.file_label.setStyleSheet("color: #333; font-size: 11px; padding: 3px; border: none;")
        self.upload_btn.setEnabled(True)

    def _on_build_err(self, error):
        """Ошибка сборки"""
        self._is_building = False
        self.build_btn.setEnabled(True)
        self.build_progress.setRange(0, 100)
        self.build_progress.setValue(0)
        self.build_progress.setVisible(False)
        self.build_status_label.setText(f"Ошибка сборки")
        self.build_status_label.setStyleSheet("color: red; font-size: 11px; padding: 3px; border: none;")

        CustomMessageBox(self, "Ошибка сборки", f"Не удалось собрать EXE:\n{error}", "error").exec_()


class UpdateDialog(QDialog):
    """Диалог обновления программы"""

    # Сигналы для межпоточного обновления UI
    _sig_progress = pyqtSignal(int, str)    # progress%, status_text
    _sig_status = pyqtSignal(str)           # status_text
    _sig_error = pyqtSignal(str)            # error_msg
    _sig_indeterminate = pyqtSignal(str)    # status_text (indeterminate progress)

    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(560, 380)

        self._sig_progress.connect(self._on_progress)
        self._sig_status.connect(self._on_status)
        self._sig_error.connect(self._on_error)
        self._sig_indeterminate.connect(self._on_indeterminate)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Контейнер с рамкой
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
            }
        """)

        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)

        # Title Bar
        title_bar = CustomTitleBar(self, 'Доступно обновление', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        # Контент
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #FFFFFF;")

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 16, 20, 20)

        # Информация о новой версии
        version = self.update_info["version"]
        details = self.update_info.get("details", {})

        # Заголовок (версия, дата, размер) — вне скролла
        header_html = f"""
        <h2 style="color: #2196F3; margin-bottom: 10px;">Доступна новая версия: {version}</h2>
        <p style="margin: 5px 0;"><b>Дата выпуска:</b> {details.get('release_date', 'Неизвестно')}</p>
        <p style="margin: 5px 0;"><b>Размер:</b> {details.get('size_mb', '?')} МБ</p>
        """
        header_label = QLabel(header_html)
        header_label.setWordWrap(True)
        header_label.setStyleSheet("font-size: 12px; border: none;")
        layout.addWidget(header_label)

        # Changelog в скроллируемом read-only поле
        changelog_text = details.get('changelog', 'Нет описания изменений')
        whats_new_label = QLabel("<b>Что нового:</b>")
        whats_new_label.setStyleSheet("font-size: 12px; border: none; margin-top: 5px;")
        layout.addWidget(whats_new_label)

        changelog_view = QTextEdit()
        changelog_view.setPlainText(changelog_text)
        changelog_view.setReadOnly(True)
        changelog_view.setMinimumHeight(120)
        changelog_view.setMaximumHeight(300)
        changelog_view.setStyleSheet(
            "QTextEdit { font-size: 12px; padding: 8px; "
            "background-color: #f5f5f5; border: 1px solid #E0E0E0; "
            "border-left: 3px solid #2196F3; border-radius: 4px; }"
        )
        layout.addWidget(changelog_view)

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
        self.status_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px; border: none;")
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
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
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
            QPushButton:hover { background-color: #e0e0e0; }
        """)
        self.later_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.later_btn)
        layout.addLayout(button_layout)

        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

    # ── Слоты для сигналов (выполняются в UI-потоке) ──

    def _on_progress(self, percent, text):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(percent)
        self.status_label.setText(text)

    def _on_status(self, text):
        self.status_label.setText(text)

    def _on_indeterminate(self, text):
        self.progress_bar.setRange(0, 0)
        self.status_label.setText(text)

    def _on_error(self, msg):
        self.download_btn.setEnabled(True)
        self.later_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        CustomMessageBox(self, "Ошибка", f"Не удалось загрузить обновление:\n{msg}", "error").exec_()

    def download_and_install(self):
        """Загрузка и установка обновления"""
        self.download_btn.setEnabled(False)
        self.later_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("Подготовка к загрузке...")

        self.progress_bar.setRange(0, 100)

        def progress_callback(current, total):
            if total > 0:
                progress = min(int((current / total) * 100), 100)
                self._sig_progress.emit(progress, f"Загружено: {current // 1024 // 1024} МБ из {total // 1024 // 1024} МБ")
            else:
                self._sig_indeterminate.emit(f"Загружено: {current // 1024 // 1024} МБ")

        def download_thread():
            from utils.update_manager import UpdateManager
            manager = UpdateManager()

            try:
                self._sig_status.emit("Загрузка обновления...")

                update_path = manager.download_update(
                    self.update_info["version"],
                    progress_callback
                )

                if not update_path:
                    raise Exception("Не удалось загрузить обновление")

                self._sig_progress.emit(100, "Установка обновления...")

                import time
                time.sleep(0.5)

                manager.install_update(update_path)

            except Exception as e:
                self._sig_error.emit(str(e))

        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

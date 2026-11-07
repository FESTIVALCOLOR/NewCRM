---
name: dialog-scaffold
description: Генерирует PyQt5 диалог Interior Studio CRM по стандартному шаблону проекта. FramelessWindowHint, QFrame#borderFrame (border 1px solid #E0E0E0, border-radius 10px), CustomTitleBar(simple_mode=True), DataAccess для CRUD, CustomMessageBox для ошибок/успеха, CustomQuestionBox для подтверждений. Без emoji — только SVG. Использовать когда пользователь говорит или в todo-списке есть: "создать диалог", "добавь форму", "окно редактирования", "dialog класс", "форма редактирования", "окно настроек".
argument-hint: "DialogClassName заголовок поле1 поле2"
disable-model-invocation: false
metadata:
  category: scaffolding
  version: "1.0"
---

# Dialog Scaffold — генерация PyQt5 диалога

Аргументы: `$ARGUMENTS` — имя класса (PascalCase) + заголовок окна + поля.

Пример: `/dialog-scaffold EditCityDialog "Редактировать город" name population`

## Полный шаблон диалога

```python
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFrame,
                              QWidget, QLabel, QLineEdit, QPushButton)
from PyQt5.QtCore import Qt
from database.db_manager import DatabaseManager
from utils.data_access import DataAccess
from ui.custom_title_bar import CustomTitleBar
from ui.custom_message_box import CustomMessageBox, CustomQuestionBox


class <ИМЯ>Dialog(QDialog):
    """<Заголовок> диалог"""

    def __init__(self, parent, api_client=None, item_id=None):
        super().__init__(parent)
        self.api_client = api_client
        self.item_id = item_id
        self.db = DatabaseManager()
        self.data = DataAccess(api_client=api_client, db=self.db)

        # --- Frameless окно ---
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setMinimumWidth(480)

        self._init_ui()
        if item_id:
            self._load_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Рамка 1px ---
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

        # --- Title Bar ---
        title_bar = CustomTitleBar(self, '<Заголовок>', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        # --- Контент ---
        content = QWidget()
        content.setStyleSheet("background-color: #FFFFFF; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px;")
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Поля ввода (генерировать по аргументам)
        self.<поле>_edit = QLineEdit()
        self.<поле>_edit.setPlaceholderText('<Подсказка>')
        self.<поле>_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #4096FF; }
        """)
        layout.addWidget(QLabel('<Метка>:'))
        layout.addWidget(self.<поле>_edit)

        # --- Кнопки ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton('Отмена')
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5; color: #595959;
                border: 1px solid #d9d9d9; border-radius: 6px;
                padding: 8px 20px; font-size: 13px;
            }
            QPushButton:hover { background-color: #E8E8E8; }
        """)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton('Сохранить')
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #1677FF; color: white;
                border: none; border-radius: 6px;
                padding: 8px 20px; font-size: 13px;
            }
            QPushButton:hover { background-color: #0958D9; }
            QPushButton:disabled { background-color: #BAD7FF; }
        """)
        self.btn_save.clicked.connect(self._save)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        border_layout.addWidget(content)
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)

    def _load_data(self):
        """Загрузить данные через DataAccess для редактирования."""
        try:
            item = self.data.get_<сущность>(self.item_id)
            if item:
                self.<поле>_edit.setText(str(item.get('<поле>', '')))
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Не удалось загрузить: {e}', 'error').exec_()

    def _save(self):
        """Сохранить через DataAccess (API-first → SQLite fallback)."""
        <поле> = self.<поле>_edit.text().strip()
        if not <поле>:
            CustomMessageBox(self, 'Ошибка', 'Заполните обязательные поля', 'warning').exec_()
            return

        try:
            data = {'<поле>': <поле>}
            if self.item_id:
                result = self.data.update_<сущность>(self.item_id, data)
            else:
                result = self.data.create_<сущность>(data)

            if result:
                CustomMessageBox(self, 'Успех', 'Сохранено', 'success').exec_()
                self.accept()
            else:
                CustomMessageBox(self, 'Ошибка', 'Не удалось сохранить', 'error').exec_()
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Ошибка: {e}', 'error').exec_()
```

## Правила проекта для диалогов

| Правило | Как делать |
|---------|-----------|
| Рамка | `border: 1px solid #E0E0E0; border-radius: 10px` |
| Окно | `Qt.FramelessWindowHint | Qt.Window` + `setMouseTracking(True)` |
| Заголовок | `CustomTitleBar(self, 'Заголовок', simple_mode=True)` |
| Ошибка | `CustomMessageBox(self, 'Ошибка', msg, 'error').exec_()` |
| Подтверждение | `CustomQuestionBox(self, 'Вопрос', msg).exec_() == QDialog.Accepted` |
| Данные | `DataAccess(api_client=api_client, db=self.db)` — НЕ api_client напрямую |
| Иконки | SVG через `IconLoader` — NO emoji |
| Потоки | `QTimer.singleShot(0, callback)` при emit из threading.Thread |
| Border-radius | ВСЕ виджеты внутри borderFrame ДОЛЖНЫ иметь соответствующий border-radius (top→title, bottom→content/buttons) |
| Выравнивание кнопок | `setFixedHeight(28)` + CSS `max-height: 26px; padding: 0px 14px; font-size: 12px; border: 1px solid #d9d9d9` (НЕ setFixedSize) |
| Окраска строк таблицы | `setAlternatingRowColors(False)` + делегат `QStyledItemDelegate.paint()` через `palette.Base/AlternateBase` |

## После генерации

Открыть в UI (в нужном табе):
```python
dialog = <ИМЯ>Dialog(self, api_client=self.api_client, item_id=item_id)
if dialog.exec_() == QDialog.Accepted:
    self._refresh_table()
```

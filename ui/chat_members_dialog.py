"""
Диалог управления участниками внутреннего чата.
"""

import threading

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.custom_title_bar import CustomTitleBar


class ChatMembersDialog(QDialog):
    """Просмотр и добавление участников чата."""

    def __init__(self, chat_id: int, chat_type: str, employee: dict, api_client, parent=None):
        super().__init__(parent)
        self._chat_id = chat_id
        self._chat_type = chat_type
        self._employee = employee
        self._api = api_client
        self._members = []
        self._all_employees = []

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setObjectName("borderFrame")
        frame.setStyleSheet("""
            QFrame#borderFrame {
                background: #fff;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
            }
        """)
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)

        title_bar = CustomTitleBar(self, "Участники чата", simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background: #fff;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        fl.addWidget(title_bar)

        content = QWidget()
        content.setStyleSheet("background: #fff; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(16, 12, 16, 16)
        cl.setSpacing(10)

        # Список участников
        cl.addWidget(QLabel("Текущие участники:"))
        self._members_list = QListWidget()
        self._members_list.setFixedHeight(160)
        cl.addWidget(self._members_list)

        # Кнопка "Добавить участника" (только при наличии права manage)
        self._add_btn = QPushButton("Добавить участника")
        self._add_btn.setFixedHeight(32)
        self._add_btn.setStyleSheet("""
            QPushButton {
                background: #ffd93c; border: none; border-radius: 4px;
                font-weight: bold; font-size: 12px; padding: 0 16px;
            }
            QPushButton:hover { background: #f5c800; }
        """)
        self._add_btn.clicked.connect(self._show_add_panel)
        cl.addWidget(self._add_btn)

        # Панель добавления (скрыта по умолчанию)
        self._add_panel = QWidget()
        add_pl = QVBoxLayout(self._add_panel)
        add_pl.setContentsMargins(0, 0, 0, 0)
        add_pl.setSpacing(6)
        add_pl.addWidget(QLabel("Выберите сотрудника:"))
        self._add_list = QListWidget()
        self._add_list.setFixedHeight(140)
        add_pl.addWidget(self._add_list)

        btn_row = QHBoxLayout()
        add_confirm = QPushButton("Добавить")
        add_confirm.setFixedHeight(28)
        add_confirm.setStyleSheet("""
            QPushButton {
                background: #ffd93c; border: none; border-radius: 4px;
                font-size: 12px; padding: 0 14px;
            }
            QPushButton:hover { background: #f5c800; }
        """)
        add_confirm.clicked.connect(self._confirm_add)
        btn_row.addWidget(add_confirm)
        btn_row.addStretch()
        add_pl.addLayout(btn_row)

        self._add_panel.setVisible(False)
        cl.addWidget(self._add_panel)

        # Кнопка закрыть
        close_btn = QPushButton("Закрыть")
        close_btn.setFixedHeight(32)
        close_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #d9d9d9; border-radius: 4px;
                font-size: 12px; padding: 0 16px; background: #fff;
            }
            QPushButton:hover { background: #f5f5f5; }
        """)
        close_btn.clicked.connect(self.accept)
        cl.addWidget(close_btn)

        fl.addWidget(content)
        outer.addWidget(frame)

    def _load_data(self):
        def _worker():
            chat = self._api.get_internal_chat(self._chat_id)
            members = chat.get("members", []) if chat else []
            employees = self._api.get_employees() or []
            QTimer.singleShot(0, lambda: self._fill_data(members, employees))

        threading.Thread(target=_worker, daemon=True).start()

    def _fill_data(self, members, employees):
        self._members = members
        self._all_employees = employees

        self._members_list.clear()
        member_ids = set()
        for m in members:
            display = m.get("display_name") or m.get("guest_name") or "—"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, m)
            self._members_list.addItem(item)
            if m.get("employee_id"):
                member_ids.add(m["employee_id"])

        # Сотрудники которых ещё нет в чате
        self._add_list.clear()
        for emp in employees:
            if emp.get("id") not in member_ids:
                name = f"{emp.get('last_name', '')} {emp.get('first_name', '')}".strip() or emp.get("login", "")
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, emp.get("id"))
                self._add_list.addItem(item)

    def _show_add_panel(self):
        self._add_panel.setVisible(not self._add_panel.isVisible())
        self.adjustSize()

    def _confirm_add(self):
        item = self._add_list.currentItem()
        if not item:
            return
        emp_id = item.data(Qt.UserRole)

        def _worker():
            self._api.add_chat_member(self._chat_id, emp_id)
            QTimer.singleShot(0, self._load_data)

        threading.Thread(target=_worker, daemon=True).start()
        self._add_panel.setVisible(False)

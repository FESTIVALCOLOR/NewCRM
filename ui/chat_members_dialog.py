"""
Диалог управления участниками внутреннего чата.
"""

import threading

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
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
    """Просмотр и управление участниками чата."""

    _sig_data = pyqtSignal(object, object)  # (members_list, employees_list)
    _sig_reload = pyqtSignal()

    def __init__(self, chat_id: int, chat_type: str, employee: dict, api_client, parent=None, crm_card_id: int = None):
        super().__init__(parent)
        self._chat_id = chat_id
        self._chat_type = chat_type
        self._employee = employee
        self._api = api_client
        self._crm_card_id = crm_card_id
        self._members = []
        self._all_employees = []

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumWidth(440)
        self._sig_data.connect(self._fill_data)
        self._sig_reload.connect(self._load_data)
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

        # --- Текущие участники ---
        cl.addWidget(QLabel("Текущие участники:"))
        self._members_list = QListWidget()
        self._members_list.setFixedHeight(180)
        self._members_list.setStyleSheet("""
            QListWidget { border: 1px solid #E0E0E0; border-radius: 4px; background: #fafafa; }
            QListWidget::item { border-bottom: 1px solid #f0f0f0; }
            QListWidget::item:hover { background: #f5f5f5; }
        """)
        cl.addWidget(self._members_list)

        # --- Кнопка добавить ---
        self._add_btn = QPushButton("Добавить участника")
        self._add_btn.setFixedHeight(32)
        self._add_btn.setStyleSheet("""
            QPushButton {
                background: #ffd93c; border: none; border-radius: 4px;
                font-weight: bold; font-size: 12px; padding: 0 16px;
            }
            QPushButton:hover { background: #f5c800; }
            QPushButton:disabled { background: #f0f0f0; color: #aaa; }
        """)
        self._add_btn.clicked.connect(self._show_add_panel)
        cl.addWidget(self._add_btn)

        # --- Панель добавления (скрыта) ---
        self._add_panel = QWidget()
        add_pl = QVBoxLayout(self._add_panel)
        add_pl.setContentsMargins(0, 0, 0, 0)
        add_pl.setSpacing(6)

        self._add_hint = QLabel("Выберите сотрудника:")
        self._add_hint.setStyleSheet("font-size: 12px; color: #555;")
        add_pl.addWidget(self._add_hint)

        self._add_list = QListWidget()
        self._add_list.setFixedHeight(140)
        self._add_list.setStyleSheet("""
            QListWidget { border: 1px solid #E0E0E0; border-radius: 4px; }
            QListWidget::item { padding: 4px 8px; }
            QListWidget::item:selected { background: #FFF8DC; }
            QListWidget::item:hover { background: #F5F5F5; }
        """)
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

        # --- Закрыть ---
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

    # ----------------------------------------------------------

    def _load_data(self):
        def _worker():
            chat = self._api.get_internal_chat(self._chat_id)
            members = chat.get("members", []) if chat else []

            employees = []
            if self._crm_card_id:
                try:
                    card = self._api.get_crm_card(self._crm_card_id)
                    if card:
                        exec_ids = set()
                        for se in card.get("stage_executors", []):
                            if se.get("executor_id"):
                                exec_ids.add(se["executor_id"])
                        for field in ["senior_manager_id", "sdp_id", "gap_id", "manager_id", "surveyor_id"]:
                            if card.get(field):
                                exec_ids.add(card[field])
                        if exec_ids:
                            all_emps = self._api.get_employees(limit=500) or []
                            employees = [e for e in all_emps if e.get("id") in exec_ids]
                except Exception:
                    pass

            if not employees:
                employees = self._api.get_employees() or []

            self._sig_data.emit(members, employees)

        threading.Thread(target=_worker, daemon=True).start()

    def _fill_data(self, members, employees):
        self._members = members
        self._all_employees = employees

        self._members_list.clear()
        member_ids = set()

        for m in members:
            display = m.get("display_name") or m.get("guest_name") or "—"
            role = m.get("role_in_project", "")
            label_text = f"{display}  ({role})" if role else display

            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(8, 3, 8, 3)
            rl.setSpacing(8)

            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 12px;")
            rl.addWidget(lbl, stretch=1)

            member_id = m.get("id")
            emp_id = m.get("employee_id")
            if member_id and emp_id and emp_id != self._employee.get("id"):
                del_btn = QPushButton("×")
                del_btn.setFixedSize(22, 22)
                del_btn.setToolTip("Удалить из чата")
                del_btn.setStyleSheet("""
                    QPushButton {
                        background: transparent; border: 1px solid #ffcccc;
                        border-radius: 4px; color: #cc0000; font-size: 15px;
                        font-weight: bold; padding: 0;
                    }
                    QPushButton:hover { background: #ffeeee; }
                """)
                del_btn.clicked.connect(lambda checked, mid=member_id: self._remove_member(mid))
                rl.addWidget(del_btn)

            item = QListWidgetItem()
            item.setData(Qt.UserRole, m)
            item.setSizeHint(row.sizeHint())
            self._members_list.addItem(item)
            self._members_list.setItemWidget(item, row)

            if emp_id:
                member_ids.add(emp_id)

        # Сотрудники ещё не в чате
        self._add_list.clear()
        available = 0
        for emp in employees:
            if emp.get("id") not in member_ids:
                name = emp.get("full_name") or emp.get("login") or f"Сотрудник #{emp.get('id')}"
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, emp.get("id"))
                self._add_list.addItem(item)
                available += 1

        hint = "Выберите сотрудника:" if available else "Все сотрудники уже в чате"
        self._add_hint.setText(hint)
        self._add_btn.setEnabled(available > 0)

    def _show_add_panel(self):
        self._add_panel.setVisible(not self._add_panel.isVisible())
        self.adjustSize()

    def _confirm_add(self):
        item = self._add_list.currentItem()
        if not item:
            return
        emp_id = item.data(Qt.UserRole)
        self._add_panel.setVisible(False)

        def _worker():
            self._api.add_chat_member(self._chat_id, emp_id)
            self._sig_reload.emit()

        threading.Thread(target=_worker, daemon=True).start()

    def _remove_member(self, member_id: int):
        from PyQt5.QtWidgets import QMessageBox

        if (
            QMessageBox.question(
                self,
                "Удалить участника",
                "Удалить участника из чата?",
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        ):

            def _worker():
                self._api.remove_chat_member(self._chat_id, member_id)
                self._sig_reload.emit()

            threading.Thread(target=_worker, daemon=True).start()

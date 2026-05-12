"""
Диалог управления участниками внутреннего чата.
"""

import threading

from PyQt5.QtCore import QSize, Qt, pyqtSignal
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

from ui.custom_message_box import CustomQuestionBox
from ui.custom_title_bar import CustomTitleBar
from utils.permissions import _has_perm


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
        self._show_phone = _has_perm(employee, api_client, "chat.client.show_phone") if chat_type == "client" else False

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
        content.setAutoFillBackground(True)
        content.setStyleSheet("background: #F9FAFB; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(16, 14, 16, 16)
        cl.setSpacing(8)

        # --- Текущие участники ---
        sect_lbl = QLabel("Текущие участники:")
        sect_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #555;")
        cl.addWidget(sect_lbl)
        self._members_list = QListWidget()
        self._members_list.setFixedHeight(180)
        self._members_list.setStyleSheet("""
            QListWidget { border: 1px solid #E0E0E0; border-radius: 4px; background: #fff; }
            QListWidget::item { border-bottom: 1px solid #f0f0f0; }
            QListWidget::item:hover { background: #f5f5f5; }
        """)
        cl.addWidget(self._members_list)

        # --- Кнопка добавить ---
        self._add_btn = QPushButton("Добавить участника")
        self._add_btn.setFixedHeight(28)
        self._add_btn.setStyleSheet("""
            QPushButton {
                background: #ffd93c; border: none; border-radius: 4px;
                font-weight: bold; font-size: 12px; padding: 0 16px;
                max-height: 26px;
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
        self._add_hint.setStyleSheet("font-size: 11px; font-weight: bold; color: #555;")
        add_pl.addWidget(self._add_hint)

        self._add_list = QListWidget()
        self._add_list.setFixedHeight(140)
        self._add_list.setStyleSheet("""
            QListWidget { border: 1px solid #E0E0E0; border-radius: 4px; background: #fff; }
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
        close_btn.setFixedHeight(28)
        close_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #d9d9d9; border-radius: 4px;
                font-size: 12px; padding: 0 16px; background: #fff;
                max-height: 26px;
            }
            QPushButton:hover { background: #f5f5f5; }
        """)
        close_btn.clicked.connect(self.accept)
        cl.addWidget(close_btn)

        fl.addWidget(content)
        outer.addWidget(frame)

    # ----------------------------------------------------------

    # Должности с доступом к чатам любой карточки
    _ADMIN_POSITIONS = {
        "Руководитель студии",
        "Старший менеджер проектов",
        "СДП",
        "ГАП",
        "Менеджер",
        "ДАН",
        "Дизайнер авторского надзора",
    }

    def _load_data(self):
        def _worker():
            chat = self._api.get_internal_chat(self._chat_id)
            members = chat.get("members", []) if chat else []
            employees = []
            if self._crm_card_id:
                try:
                    card = self._api.get_crm_card(self._crm_card_id) or {}
                    # Собираем ID сотрудников, привязанных к карточке
                    card_emp_ids: set[int] = set()
                    for field in ("senior_manager_id", "sdp_id", "gap_id", "manager_id", "surveyor_id"):
                        v = card.get(field)
                        if v:
                            card_emp_ids.add(v)
                    for se in card.get("stage_executors", []):
                        eid = se.get("executor_id") or se.get("employee_id")
                        if eid:
                            card_emp_ids.add(eid)
                    all_emps = self._api.get_employees(limit=500) or []
                    # Показываем сотрудников карточки + всех с административными должностями
                    employees = [e for e in all_emps if e.get("id") in card_emp_ids or e.get("position") in self._ADMIN_POSITIONS]
                except Exception:
                    pass
            if not employees:
                # Запасной вариант: все сотрудники
                employees = self._api.get_employees(limit=500) or []
            self._sig_data.emit(members, employees)

        threading.Thread(target=_worker, daemon=True).start()

    def _fill_data(self, members, employees):
        self._members = members
        self._all_employees = employees

        self._members_list.clear()
        member_ids = set()

        # Сортировка: сотрудники первыми, гости (клиенты) последними; внутри — по роли
        def _member_sort_key(m):
            is_guest = m.get("member_type") == "guest" or not m.get("employee_id")
            role = (m.get("role_in_project") or "").lower()
            return (1 if is_guest else 0, role)

        for m in sorted(members, key=_member_sort_key):
            display = m.get("display_name") or m.get("guest_name") or "—"
            role = m.get("role_in_project", "")
            is_guest = m.get("member_type") == "guest" or not m.get("employee_id")

            row = QWidget()
            row.setStyleSheet("background: #F0FFF0;" if is_guest else "background: transparent;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(8, 4, 8, 4)
            rl.setSpacing(6)
            rl.setAlignment(Qt.AlignVCenter)

            # Цветной маркер типа участника
            dot = QLabel("К" if is_guest else "С")
            dot.setFixedSize(20, 20)
            dot.setAlignment(Qt.AlignCenter)
            dot.setStyleSheet(
                "background: #43A047; color: #fff; border-radius: 10px; font-size: 9px; font-weight: bold;"
                if is_guest
                else "background: #1565C0; color: #fff; border-radius: 10px; font-size: 9px; font-weight: bold;"
            )
            rl.addWidget(dot)

            name_col = QVBoxLayout()
            name_col.setSpacing(0)
            name_col.setContentsMargins(0, 0, 0, 0)
            label_text = f"{display}  ({role})" if role else display
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 12px; background: transparent;")
            name_col.addWidget(lbl)
            phone = m.get("guest_phone") or ""
            if phone and is_guest and self._show_phone:
                ph_lbl = QLabel(phone)
                ph_lbl.setStyleSheet("font-size: 10px; color: #666; background: transparent;")
                ph_lbl.setToolTip(f"Телефон клиента: {phone}")
                name_col.addWidget(ph_lbl)
            rl.addLayout(name_col, stretch=1)

            member_id = m.get("id")
            emp_id = m.get("employee_id")
            _del_style = """
                QPushButton {
                    background: transparent; border: 1px solid #ffcccc;
                    border-radius: 4px; color: #cc0000; font-size: 16px;
                    font-weight: bold; padding: 0;
                    min-width: 28px; max-width: 28px;
                    min-height: 28px; max-height: 28px;
                }
                QPushButton:hover { background: #ffeeee; }
            """
            if member_id and emp_id and emp_id != self._employee.get("id"):
                del_btn = QPushButton("×")
                del_btn.setFixedSize(28, 28)
                del_btn.setToolTip("Удалить из чата")
                del_btn.setStyleSheet(_del_style)
                del_btn.clicked.connect(lambda checked, mid=member_id: self._remove_member(mid))
                rl.addWidget(del_btn, 0, Qt.AlignVCenter)
            elif member_id and is_guest and self._chat_type == "client":
                # Кнопка аннулирования доступа клиента
                revoke_btn = QPushButton("×")
                revoke_btn.setFixedSize(28, 28)
                revoke_btn.setToolTip("Аннулировать доступ клиента")
                revoke_btn.setStyleSheet(_del_style)
                revoke_btn.clicked.connect(lambda checked, mid=member_id: self._revoke_guest(mid))
                rl.addWidget(revoke_btn, 0, Qt.AlignVCenter)

            row_h = 52 if (phone and is_guest and self._show_phone) else 40
            item = QListWidgetItem()
            item.setData(Qt.UserRole, m)
            item.setSizeHint(QSize(0, row_h + 1))  # +1 для border-bottom разделителя
            row.setFixedHeight(row_h)
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
        visible = not self._add_panel.isVisible()
        self._add_panel.setVisible(visible)
        # Плавное расширение без прыжка: задаём минимальную высоту
        if visible:
            self.setMinimumHeight(520)
        else:
            self.setMinimumHeight(0)

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
        dlg = CustomQuestionBox(self, "Удалить участника", "Удалить участника из чата?")
        if dlg.exec_() != dlg.Accepted:
            return

        def _worker():
            self._api.remove_chat_member(self._chat_id, member_id)
            self._sig_reload.emit()

        threading.Thread(target=_worker, daemon=True).start()

    def _revoke_guest(self, member_id: int):
        dlg = CustomQuestionBox(self, "Аннулировать доступ", "Аннулировать ссылку-приглашение и удалить клиента из чата?")
        if dlg.exec_() != dlg.Accepted:
            return

        def _worker():
            self._api.revoke_client_access(self._chat_id, member_id)
            self._sig_reload.emit()

        threading.Thread(target=_worker, daemon=True).start()

# -*- coding: utf-8 -*-
"""
Виджет настроек уведомлений.
Позволяет Директору настраивать уведомления для любого сотрудника,
обычным сотрудникам — только свои.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QGroupBox, QComboBox, QFrame, QScrollArea,
)
from PyQt5.QtCore import Qt, QTimer

from ui.custom_message_box import CustomMessageBox

SUPERUSER_ROLES = {'Руководитель студии', 'Директор', 'Администратор'}


class NotificationSettingsWidget(QWidget):
    """Виджет настроек уведомлений для вкладки администрирования"""

    def __init__(self, parent=None, api_client=None, data_access=None, employee=None):
        super().__init__(parent)
        self.api_client = api_client
        self.data_access = data_access
        self.employee = employee or {}
        self._current_employee_id = None
        self._target_employee = None
        self._employees = []
        self._settings = {}

        self._setup_ui()
        QTimer.singleShot(100, self._load_employees)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Заголовок
        title = QLabel("Настройки уведомлений")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1a1a1a;")
        layout.addWidget(title)

        # Выбор сотрудника (только для Директора)
        self._employee_frame = QFrame()
        self._employee_frame.setStyleSheet(
            "QFrame { background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 8px; }"
        )
        emp_layout = QHBoxLayout(self._employee_frame)
        emp_layout.setContentsMargins(12, 10, 12, 10)

        emp_label = QLabel("Сотрудник:")
        emp_label.setStyleSheet("font-size: 13px; color: #555; border: none;")
        self._emp_combo = QComboBox()
        self._emp_combo.setMinimumWidth(250)
        self._emp_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
                background: white;
            }
        """)
        self._emp_combo.currentIndexChanged.connect(self._on_employee_changed)

        emp_layout.addWidget(emp_label)
        emp_layout.addWidget(self._emp_combo)
        emp_layout.addStretch()

        layout.addWidget(self._employee_frame)

        # Секция Telegram
        tg_group = QGroupBox("Telegram уведомления")
        tg_group.setStyleSheet("""
            QGroupBox {
                font-size: 13px; font-weight: 600; color: #1a1a1a;
                border: 1px solid #e0e0e0; border-radius: 8px;
                padding-top: 16px; margin-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px; padding: 0 6px;
                background: white;
            }
        """)
        tg_layout = QVBoxLayout(tg_group)

        self._chk_telegram = QCheckBox("Включить Telegram уведомления")
        self._chk_telegram.setStyleSheet("font-size: 13px;")

        self._lbl_tg_status = QLabel("Статус: не определён")
        self._lbl_tg_status.setStyleSheet("font-size: 12px; color: #888;")

        tg_layout.addWidget(self._chk_telegram)
        tg_layout.addWidget(self._lbl_tg_status)
        layout.addWidget(tg_group)

        # Секция типов событий
        events_group = QGroupBox("Типы событий")
        events_group.setStyleSheet(tg_group.styleSheet())
        events_layout = QVBoxLayout(events_group)

        self._chk_crm_stage = QCheckBox("Смена стадии CRM")
        self._chk_assigned = QCheckBox("Назначение исполнителем")
        self._chk_deadline = QCheckBox("Предупреждение о дедлайне")
        self._chk_payment = QCheckBox("Создание оплаты")
        self._chk_supervision = QCheckBox("Авторский надзор")

        for chk in [self._chk_crm_stage, self._chk_assigned, self._chk_deadline,
                    self._chk_payment, self._chk_supervision]:
            chk.setStyleSheet("font-size: 13px; padding: 2px 0;")
            events_layout.addWidget(chk)

        layout.addWidget(events_group)

        # Секция фильтра по типам проектов
        self._projects_group = QGroupBox("Типы проектов (каналы)")
        self._projects_group.setStyleSheet(tg_group.styleSheet())
        projects_layout = QVBoxLayout(self._projects_group)

        self._chk_individual = QCheckBox("Индивидуальные проекты")
        self._chk_template = QCheckBox("Шаблонные проекты")

        for chk in [self._chk_individual, self._chk_template]:
            chk.setStyleSheet("font-size: 13px; padding: 2px 0;")
            projects_layout.addWidget(chk)

        layout.addWidget(self._projects_group)

        # Секция дублирования уведомлений
        self._duplication_group = QGroupBox("Дублирование уведомлений")
        self._duplication_group.setStyleSheet(tg_group.styleSheet())
        dup_layout = QVBoxLayout(self._duplication_group)

        self._chk_duplicate_info = QCheckBox("Получать информационные дубли (уведомления подчинённых)")
        self._chk_revision_info = QCheckBox("Получать уведомления об исправлениях подчинённых")

        for chk in [self._chk_duplicate_info, self._chk_revision_info]:
            chk.setStyleSheet("font-size: 13px; padding: 2px 0;")
            dup_layout.addWidget(chk)

        layout.addWidget(self._duplication_group)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._btn_test = QPushButton("Тест уведомления")
        self._btn_test.setFixedHeight(36)
        self._btn_test.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                padding: 0 20px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #ebebeb; }
        """)
        self._btn_test.clicked.connect(self._send_test)

        self._btn_save = QPushButton("Сохранить")
        self._btn_save.setFixedHeight(36)
        self._btn_save.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                border: 1px solid #e6c435;
                border-radius: 6px;
                padding: 0 24px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #f0c800; }
        """)
        self._btn_save.clicked.connect(self._save_settings)

        btn_layout.addWidget(self._btn_test)
        btn_layout.addWidget(self._btn_save)
        layout.addLayout(btn_layout)
        layout.addStretch()

    def _load_employees(self):
        """Загрузить список сотрудников"""
        role = self.employee.get('role', '')
        is_director = role in SUPERUSER_ROLES

        if is_director and self.data_access:
            try:
                employees = self.data_access.get_all_employees() or []
                self._employees = [e for e in employees if e.get('status') == 'активный']
            except Exception:
                self._employees = []
        else:
            # Обычный сотрудник видит только себя
            self._employees = [self.employee] if self.employee.get('id') else []
            self._employee_frame.setVisible(False)

        self._emp_combo.blockSignals(True)
        self._emp_combo.clear()
        for emp in self._employees:
            self._emp_combo.addItem(emp.get('full_name', ''), emp.get('id'))
        self._emp_combo.blockSignals(False)

        # По умолчанию — текущий пользователь
        own_id = self.employee.get('id')
        for i in range(self._emp_combo.count()):
            if self._emp_combo.itemData(i) == own_id:
                self._emp_combo.setCurrentIndex(i)
                break
        else:
            if self._emp_combo.count() > 0:
                self._emp_combo.setCurrentIndex(0)

        self._on_employee_changed()

    def _on_employee_changed(self):
        """Загрузить настройки выбранного сотрудника"""
        idx = self._emp_combo.currentIndex()
        if idx < 0:
            return
        emp_id = self._emp_combo.itemData(idx)
        if not emp_id:
            return
        self._current_employee_id = emp_id

        # Найти целевого сотрудника для проверки его прав
        self._target_employee = self.employee  # по умолчанию — текущий пользователь
        for emp in self._employees:
            if emp.get('id') == emp_id:
                self._target_employee = emp
                break

        # Видимость секций — по правам ЦЕЛЕВОГО сотрудника
        self._update_section_visibility()

        if self.data_access:
            try:
                settings = self.data_access.get_notification_settings(emp_id) or {}
                self._apply_settings(settings)
            except Exception as e:
                print(f"[NotificationSettings] Ошибка загрузки: {e}")

    def _update_section_visibility(self):
        """Показать/скрыть секции настроек по правам ЦЕЛЕВОГО сотрудника.

        Директор, просматривая Чертёжника, видит только те секции,
        которые доступны Чертёжнику. Это совпадает с тем, что видит
        сам Чертёжник в своих настройках.
        """
        from utils.permissions import _has_perm
        target = self._target_employee or self.employee

        self._projects_group.setVisible(
            _has_perm(target, self.api_client, 'notifications.settings_projects'))
        self._duplication_group.setVisible(
            _has_perm(target, self.api_client, 'notifications.settings_duplication'))
        self._chk_supervision.setVisible(
            _has_perm(target, self.api_client, 'notifications.settings_supervision'))
        self._chk_payment.setVisible(
            _has_perm(target, self.api_client, 'notifications.settings_payment'))

    def _apply_settings(self, settings: dict):
        """Применить настройки к чекбоксам"""
        self._chk_telegram.setChecked(settings.get('telegram_enabled', True))
        self._chk_crm_stage.setChecked(settings.get('notify_crm_stage', True))
        self._chk_assigned.setChecked(settings.get('notify_assigned', True))
        self._chk_deadline.setChecked(settings.get('notify_deadline', True))
        self._chk_payment.setChecked(settings.get('notify_payment', False))
        self._chk_supervision.setChecked(settings.get('notify_supervision', False))
        self._chk_individual.setChecked(settings.get('notify_individual', True))
        self._chk_template.setChecked(settings.get('notify_template', True))
        self._chk_duplicate_info.setChecked(settings.get('notify_duplicate_info', False))
        self._chk_revision_info.setChecked(settings.get('notify_revision_info', False))

        connected = settings.get('telegram_connected', False)
        if connected:
            self._lbl_tg_status.setText("Статус: Telegram подключён")
            self._lbl_tg_status.setStyleSheet("font-size: 12px; color: #27ae60; font-weight: 600;")
        else:
            self._lbl_tg_status.setText("Статус: Telegram не подключён (отправьте приглашение)")
            self._lbl_tg_status.setStyleSheet("font-size: 12px; color: #e74c3c;")

    def _save_settings(self):
        """Сохранить настройки"""
        if not self._current_employee_id:
            return

        data = {
            'telegram_enabled': self._chk_telegram.isChecked(),
            'email_enabled': False,
            'notify_crm_stage': self._chk_crm_stage.isChecked(),
            'notify_assigned': self._chk_assigned.isChecked(),
            'notify_deadline': self._chk_deadline.isChecked(),
            'notify_payment': self._chk_payment.isChecked(),
            'notify_supervision': self._chk_supervision.isChecked(),
            'notify_individual': self._chk_individual.isChecked(),
            'notify_template': self._chk_template.isChecked(),
            'notify_duplicate_info': self._chk_duplicate_info.isChecked(),
            'notify_revision_info': self._chk_revision_info.isChecked(),
        }

        if self.data_access:
            try:
                result = self.data_access.update_notification_settings(
                    self._current_employee_id, data
                )
                if result:
                    CustomMessageBox(
                        self, 'Сохранено',
                        'Настройки уведомлений сохранены.',
                        'success'
                    ).exec_()
                else:
                    CustomMessageBox(
                        self, 'Ошибка',
                        'Не удалось сохранить настройки.',
                        'error'
                    ).exec_()
            except Exception as e:
                CustomMessageBox(
                    self, 'Ошибка',
                    f'Ошибка сохранения: {e}',
                    'error'
                ).exec_()

    def _send_test(self):
        """Отправить тестовое уведомление"""
        if not self._current_employee_id:
            return

        if self.api_client:
            try:
                response = self.api_client._request(
                    'POST',
                    f"{self.api_client.base_url}/api/v1/notifications/test",
                    params={"employee_id": self._current_employee_id}
                )
                if response and response.status_code == 200:
                    CustomMessageBox(
                        self, 'Тест отправлен',
                        'Тестовое уведомление отправлено в Telegram.',
                        'success'
                    ).exec_()
                else:
                    CustomMessageBox(
                        self, 'Ошибка',
                        'Не удалось отправить тест. Проверьте настройки Telegram бота.',
                        'error'
                    ).exec_()
            except Exception as e:
                CustomMessageBox(
                    self, 'Ошибка',
                    f'Ошибка отправки теста: {e}',
                    'error'
                ).exec_()

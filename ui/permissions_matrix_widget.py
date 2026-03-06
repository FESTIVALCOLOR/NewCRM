# -*- coding: utf-8 -*-
"""
Виджет матрицы прав доступа для администрирования.
Роли — столбцы, права — строки, сгруппированные по категориям.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QCheckBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QBrush

from ui.custom_message_box import CustomMessageBox
from utils.data_access import DataAccess


# =========================
# Группы прав (порядок отображения)
# =========================

# S-12: Синхронизировано с server/permissions.py PERMISSION_NAMES
PERMISSION_GROUPS = {
    'Сотрудники': ['employees.create', 'employees.update', 'employees.delete'],
    'Клиенты': ['clients.delete'],
    'Договоры': ['contracts.update', 'contracts.delete'],
    'CRM': [
        'crm_cards.update', 'crm_cards.move', 'crm_cards.delete',
        'crm_cards.assign_executor', 'crm_cards.delete_executor',
        'crm_cards.reset_stages', 'crm_cards.reset_approval',
        'crm_cards.complete_approval', 'crm_cards.reset_designer',
        'crm_cards.reset_draftsman',
    ],
    'Надзор': [
        'supervision.update', 'supervision.move', 'supervision.pause_resume',
        'supervision.reset_stages', 'supervision.complete_stage',
        'supervision.delete_order',
    ],
    'Платежи': ['payments.create', 'payments.update', 'payments.delete'],
    'Зарплаты': ['salaries.create', 'salaries.update', 'salaries.delete'],
    'Ставки': ['rates.create', 'rates.delete'],
    'Агенты': ['agents.create', 'agents.update', 'agents.delete'],
    'Города': ['cities.create', 'cities.delete'],
    'Мессенджер': ['messenger.create_chat', 'messenger.delete_chat', 'messenger.view_chat'],
}

# Роли — столбцы таблицы
ROLES = [
    'Руководитель студии',
    'Старший менеджер проектов',
    'СДП',
    'ГАП',
    'Менеджер',
    'ДАН',
]

# =========================
# Дефолтные права по ролям
# =========================

DEFAULT_ROLE_PERMISSIONS = {
    "Руководитель студии": {
        "employees.create", "employees.update", "employees.delete",
        "clients.delete", "contracts.update", "contracts.delete",
        "crm_cards.update", "crm_cards.move", "crm_cards.delete",
        "crm_cards.assign_executor", "crm_cards.delete_executor",
        "crm_cards.reset_stages", "crm_cards.reset_approval",
        "crm_cards.complete_approval", "crm_cards.reset_designer",
        "crm_cards.reset_draftsman",
        "supervision.update", "supervision.move", "supervision.pause_resume",
        "supervision.reset_stages", "supervision.complete_stage",
        "supervision.delete_order",
        "payments.create", "payments.update", "payments.delete",
        "salaries.create", "salaries.update", "salaries.delete",
        "rates.create", "rates.delete",
        "agents.create", "agents.update", "agents.delete",
        "cities.create", "cities.delete",
        "messenger.create_chat", "messenger.delete_chat", "messenger.view_chat",
    },
    "Старший менеджер проектов": {
        "employees.update",
        "clients.delete", "contracts.update", "contracts.delete",
        "crm_cards.update", "crm_cards.move", "crm_cards.delete",
        "crm_cards.assign_executor", "crm_cards.delete_executor",
        "crm_cards.reset_stages", "crm_cards.reset_approval",
        "crm_cards.complete_approval", "crm_cards.reset_designer",
        "crm_cards.reset_draftsman",
        "supervision.update", "supervision.move", "supervision.pause_resume",
        "supervision.reset_stages", "supervision.complete_stage",
        "supervision.delete_order",
        "payments.create", "payments.update", "payments.delete",
        "salaries.create", "salaries.update",
        "rates.create", "rates.delete",
        "agents.create", "agents.update", "agents.delete",
        "cities.create", "cities.delete",
        "messenger.create_chat", "messenger.delete_chat", "messenger.view_chat",
    },
    "СДП": {"crm_cards.reset_designer", "crm_cards.reset_draftsman", "messenger.view_chat"},
    "ГАП": {"crm_cards.reset_designer", "crm_cards.reset_draftsman", "messenger.view_chat"},
    "Менеджер": {"crm_cards.reset_designer", "crm_cards.reset_draftsman"},
    "ДАН": {"supervision.complete_stage", "messenger.view_chat"},
}

# Русские описания прав (fallback, если API недоступен)
PERMISSION_DESCRIPTIONS = {
    "employees.create": "Создание сотрудников",
    "employees.update": "Редактирование сотрудников",
    "employees.delete": "Удаление сотрудников",
    "clients.delete": "Удаление клиентов",
    "contracts.update": "Редактирование договоров",
    "contracts.delete": "Удаление договоров",
    "crm_cards.update": "Редактирование CRM карточек",
    "crm_cards.move": "Перемещение CRM карточек",
    "crm_cards.delete": "Удаление CRM карточек",
    "crm_cards.assign_executor": "Назначение исполнителей",
    "crm_cards.delete_executor": "Удаление исполнителей",
    "crm_cards.reset_stages": "Сброс стадий CRM",
    "crm_cards.reset_approval": "Сброс согласования",
    "crm_cards.complete_approval": "Завершение согласования",
    "crm_cards.reset_designer": "Сброс отметки дизайнера",
    "crm_cards.reset_draftsman": "Сброс отметки чертежника",
    "supervision.update": "Редактирование карточек надзора",
    "supervision.move": "Перемещение карточек надзора",
    "supervision.pause_resume": "Приостановка/возобновление надзора",
    "supervision.reset_stages": "Сброс стадий надзора",
    "supervision.complete_stage": "Завершение стадии надзора",
    "supervision.delete_order": "Удаление заказа надзора",
    "payments.create": "Создание платежей",
    "payments.update": "Редактирование платежей",
    "payments.delete": "Удаление платежей",
    "salaries.create": "Создание зарплат",
    "salaries.update": "Редактирование зарплат",
    "salaries.delete": "Удаление зарплат",
    "agents.create": "Создание агентов",
    "agents.update": "Редактирование агентов",
    "agents.delete": "Удаление агентов",
    "cities.create": "Создание городов",
    "cities.delete": "Удаление городов",
    "messenger.create_chat": "Создание чатов",
    "messenger.delete_chat": "Удаление чатов",
    "messenger.view_chat": "Просмотр/открытие чатов",
}


class PermissionsMatrixWidget(QWidget):
    """
    Виджет матрицы прав доступа.
    Роли — горизонтально (столбцы), права — вертикально (строки).
    Категории прав отображаются как заголовки-разделители.
    """

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        self.api_client = api_client
        self.data_access = DataAccess(api_client=self.api_client)
        self.definitions = dict(PERMISSION_DESCRIPTIONS)
        # Словарь: (perm_name, role) -> QCheckBox
        self._checkboxes = {}
        # Маппинг строк таблицы: row -> perm_name (None для строк-заголовков категорий)
        self._row_perm_map = {}

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок
        title_label = QLabel('Матрица прав доступа по ролям')
        title_label.setStyleSheet(
            'font-size: 14px; font-weight: bold; color: #333333; margin-bottom: 5px;'
        )
        layout.addWidget(title_label)

        desc_label = QLabel(
            'Настройте, какие действия доступны каждой роли. '
            'Изменения вступят в силу после сохранения.'
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet('font-size: 12px; color: #757575; margin-bottom: 10px;')
        layout.addWidget(desc_label)

        # Таблица
        self.table = QTableWidget()
        self.table.setObjectName('permissions_matrix_table')
        self._setup_table()
        layout.addWidget(self.table, 1)

        # Кнопки внизу
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        reset_btn = QPushButton('Сбросить по умолчанию')
        reset_btn.setFixedHeight(36)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #333333;
                padding: 0px 20px;
                border-radius: 4px;
                border: 1px solid #d9d9d9;
                font-size: 13px;
                font-weight: bold;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #f5f5f5; border-color: #c0c0c0; }
            QPushButton:pressed { background-color: #e8e8e8; }
        """)
        reset_btn.clicked.connect(self._on_reset_defaults)
        buttons_layout.addWidget(reset_btn)

        buttons_layout.addStretch()

        save_btn = QPushButton('Сохранить')
        save_btn.setFixedHeight(36)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                border: none;
                font-size: 13px;
                font-weight: bold;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)
        save_btn.clicked.connect(self._on_save)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

    def _setup_table(self):
        """Создание и настройка таблицы матрицы"""
        table = self.table

        # Стили таблицы (как в rates_dialog.py)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #d9d9d9;
                border-radius: 8px;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #d9d9d9;
                font-weight: bold;
                font-size: 12px;
            }
        """)

        # Подсчитаем количество строк: категории + права
        total_rows = 0
        for group_name, perm_names in PERMISSION_GROUPS.items():
            total_rows += 1  # строка-заголовок категории
            total_rows += len(perm_names)

        # Столбец 0 = Название права, далее — по одному на роль
        col_count = 1 + len(ROLES)
        table.setColumnCount(col_count)
        table.setRowCount(total_rows)

        # Заголовки столбцов
        headers = ['Право'] + ROLES
        table.setHorizontalHeaderLabels(headers)

        # Настройка заголовков
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col_idx in range(1, col_count):
            header.setSectionResizeMode(col_idx, QHeaderView.ResizeToContents)
        header.setMinimumSectionSize(90)

        # Скрываем вертикальный заголовок (номера строк)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(32)

        # Отключаем редактирование ячеек
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)

        # Заполняем строки
        row = 0
        bold_font = QFont()
        bold_font.setBold(True)
        bold_font.setPointSize(10)

        category_bg = QBrush(QColor('#f0f0f0'))

        for group_name, perm_names in PERMISSION_GROUPS.items():
            # === Строка-заголовок категории ===
            category_item = QTableWidgetItem(group_name)
            category_item.setFont(bold_font)
            category_item.setBackground(category_bg)
            category_item.setFlags(Qt.ItemIsEnabled)  # нередактируемая
            table.setItem(row, 0, category_item)

            # Заполняем остальные ячейки категории серым фоном
            for col_idx in range(1, col_count):
                filler = QTableWidgetItem('')
                filler.setBackground(category_bg)
                filler.setFlags(Qt.ItemIsEnabled)
                table.setItem(row, col_idx, filler)

            self._row_perm_map[row] = None
            row += 1

            # === Строки прав внутри категории ===
            for perm_name in perm_names:
                desc = self.definitions.get(perm_name, perm_name)
                perm_item = QTableWidgetItem(desc)
                perm_item.setFlags(Qt.ItemIsEnabled)
                perm_item.setToolTip(perm_name)
                table.setItem(row, 0, perm_item)

                # Чекбоксы для каждой роли
                for col_idx, role in enumerate(ROLES, start=1):
                    cb = QCheckBox()
                    # Контейнер для центрирования чекбокса
                    container = QWidget()
                    cb_layout = QHBoxLayout(container)
                    cb_layout.addWidget(cb)
                    cb_layout.setAlignment(Qt.AlignCenter)
                    cb_layout.setContentsMargins(0, 0, 0, 0)
                    table.setCellWidget(row, col_idx, container)

                    self._checkboxes[(perm_name, role)] = cb

                self._row_perm_map[row] = perm_name
                row += 1

    # =========================
    # Загрузка данных
    # =========================

    def _load_data(self):
        """Загрузить матрицу прав: сначала из API, при ошибке — дефолтные"""
        # Загружаем описания прав из API
        self._load_definitions()

        # Загружаем матрицу
        try:
            result = self.data_access.get_role_permissions_matrix()
            if result and isinstance(result, dict):
                # Сервер возвращает {"roles": {role: [perms]}}
                matrix = result.get("roles", result)
                if matrix:
                    self._apply_matrix(matrix)
                    return
        except Exception:
            pass
        # Fallback — из дефолтных
        self._apply_matrix(DEFAULT_ROLE_PERMISSIONS)

    def _load_definitions(self):
        """Загрузить русские описания прав из API"""
        try:
            defs = self.data_access.get_permission_definitions()
            if isinstance(defs, list):
                for d in defs:
                    name = d.get('name', '')
                    desc = d.get('description', '')
                    if name and desc:
                        self.definitions[name] = desc

                # Обновляем текст в первом столбце таблицы
                for row, perm_name in self._row_perm_map.items():
                    if perm_name:
                        desc = self.definitions.get(perm_name, perm_name)
                        item = self.table.item(row, 0)
                        if item:
                            item.setText(desc)
                            item.setToolTip(perm_name)
        except Exception:
            pass

    def _apply_matrix(self, matrix_data):
        """
        Применить данные матрицы к чекбоксам.
        matrix_data: dict[role_name] -> set/list прав
        """
        # Сначала снимаем все чекбоксы
        for cb in self._checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)

        # Устанавливаем по данным
        for role, perms in matrix_data.items():
            if role not in ROLES:
                continue
            perm_set = set(perms) if not isinstance(perms, set) else perms
            for perm_name in perm_set:
                cb = self._checkboxes.get((perm_name, role))
                if cb:
                    cb.blockSignals(True)
                    cb.setChecked(True)
                    cb.blockSignals(False)

    def _collect_matrix(self):
        """Собрать текущее состояние чекбоксов в словарь матрицы"""
        matrix = {}
        for role in ROLES:
            perms = []
            for group_perms in PERMISSION_GROUPS.values():
                for perm_name in group_perms:
                    cb = self._checkboxes.get((perm_name, role))
                    if cb and cb.isChecked():
                        perms.append(perm_name)
            matrix[role] = perms
        return matrix

    # =========================
    # Обработчики кнопок
    # =========================

    def _on_save(self):
        """Сохранить матрицу прав"""
        matrix = self._collect_matrix()
        try:
            result = self.data_access.save_role_permissions_matrix({
                "roles": matrix,
                "apply_to_employees": True,
            })
            if result:
                CustomMessageBox(
                    self,
                    'Успешно',
                    'Матрица прав доступа сохранена.',
                    'success'
                ).exec_()
                return
        except Exception as e:
            print(f"[WARN] Ошибка сохранения матрицы прав: {e}")

        # Если API недоступен или вернул None — уведомляем пользователя
        CustomMessageBox(
            self,
            'Ошибка',
            'Не удалось сохранить матрицу прав.\n'
            'Проверьте подключение к серверу.',
            'error'
        ).exec_()

    def _on_reset_defaults(self):
        """Сбросить матрицу к дефолтным значениям"""
        from PyQt5.QtWidgets import QDialog

        reply = CustomMessageBox(
            self,
            'Подтверждение',
            'Сбросить все права до значений по умолчанию?\n\n'
            'Текущие настройки будут потеряны.',
            'warning'
        )
        if reply.exec_() == QDialog.Accepted:
            self._apply_matrix(DEFAULT_ROLE_PERMISSIONS)
            CustomMessageBox(
                self,
                'Готово',
                'Матрица прав сброшена до значений по умолчанию.\n'
                'Не забудьте нажать "Сохранить" для применения.',
                'info'
            ).exec_()

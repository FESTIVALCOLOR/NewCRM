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

from ui.custom_message_box import CustomMessageBox, CustomQuestionBox
from utils.data_access import DataAccess


# =========================
# Группы прав (порядок отображения)
# =========================

# S-12: Синхронизировано с server/permissions.py PERMISSION_NAMES
# Агенты и Города убраны из матрицы — доступ только у суперпользователей
PERMISSION_GROUPS = {
    'Доступ к страницам': [
        'access.clients', 'access.contracts', 'access.crm', 'access.supervision',
        'access.reports', 'access.employees', 'access.salaries',
        'access.employee_reports', 'access.admin', 'access.dashboards',
    ],
    'Сотрудники': ['employees.create', 'employees.update', 'employees.delete'],
    'Клиенты': ['clients.create', 'clients.view', 'clients.update', 'clients.delete'],
    'Договоры': ['contracts.create', 'contracts.view', 'contracts.update', 'contracts.delete'],
    'CRM': [
        'crm_cards.update', 'crm_cards.move', 'crm_cards.delete',
        'crm_cards.assign_executor', 'crm_cards.reset_approval',
        'crm_cards.complete_approval', 'crm_cards.reset_designer',
        'crm_cards.reset_draftsman',
        'crm_cards.files_upload', 'crm_cards.files_delete',
        'crm_cards.deadlines', 'crm_cards.payments',
    ],
    'Надзор': [
        'supervision.update', 'supervision.move', 'supervision.pause_resume',
        'supervision.complete_stage', 'supervision.delete_order',
        'supervision.assign_executor',
        'supervision.files_upload', 'supervision.files_delete',
        'supervision.deadlines', 'supervision.payments',
    ],
    'Платежи': ['payments.create', 'payments.update', 'payments.delete'],
    'Зарплаты': [
        'salaries.create', 'salaries.update', 'salaries.delete',
        'salaries.mark_to_pay', 'salaries.mark_paid',
    ],
    'Тарифы': ['rates.create', 'rates.delete'],
    'Мессенджер': [
        'messenger.create_chat', 'messenger.delete_chat',
        'messenger.view_chat', 'messenger.manage_scripts',
    ],
    'Уведомления': [
        'notifications.settings_projects', 'notifications.settings_duplication',
    ],
}

# Роли — столбцы таблицы (9 ролей)
ROLES = [
    'Руководитель студии',
    'Старший менеджер проектов',
    'СДП',
    'ГАП',
    'Менеджер',
    'ДАН',
    'Дизайнер',
    'Чертёжник',
    'Замерщик',
]

# =========================
# Дефолтные права по ролям
# =========================

# Наборы прав для повторного использования
_ACCESS_ALL = {
    "access.clients", "access.contracts", "access.crm", "access.supervision",
    "access.reports", "access.employees", "access.salaries", "access.employee_reports",
    "access.admin", "access.dashboards",
}
_ACCESS_MANAGER = {
    "access.clients", "access.contracts", "access.crm", "access.supervision",
    "access.reports", "access.employees", "access.salaries", "access.employee_reports",
    "access.dashboards",
}
_BASE_MANAGER = {
    # Клиенты CRUD
    "clients.create", "clients.view", "clients.update", "clients.delete",
    # Договоры CRUD
    "contracts.create", "contracts.view", "contracts.update", "contracts.delete",
    # CRM
    "crm_cards.update", "crm_cards.move", "crm_cards.delete",
    "crm_cards.assign_executor", "crm_cards.reset_approval", "crm_cards.complete_approval",
    "crm_cards.files_upload", "crm_cards.files_delete",
    "crm_cards.deadlines", "crm_cards.payments",
    # Надзор
    "supervision.update", "supervision.move", "supervision.pause_resume",
    "supervision.complete_stage", "supervision.delete_order",
    "supervision.assign_executor", "supervision.files_upload", "supervision.files_delete",
    "supervision.deadlines", "supervision.payments",
    # Платежи
    "payments.create", "payments.update", "payments.delete",
    # Зарплаты
    "salaries.create", "salaries.update",
    "salaries.mark_to_pay", "salaries.mark_paid",
    # Тарифы
    "rates.create", "rates.delete",
    # Мессенджер
    "messenger.create_chat", "messenger.delete_chat", "messenger.view_chat",
}

DEFAULT_ROLE_PERMISSIONS = {
    "Руководитель студии": _ACCESS_ALL | _BASE_MANAGER | {
        "employees.create", "employees.update", "employees.delete",
        "crm_cards.reset_designer", "crm_cards.reset_draftsman",
        "salaries.delete",
        "messenger.manage_scripts",
    },
    "Старший менеджер проектов": _ACCESS_MANAGER | _BASE_MANAGER | {
        "employees.update",
        "crm_cards.reset_designer", "crm_cards.reset_draftsman",
    },
    "СДП": {
        "access.crm", "access.reports", "access.employees", "access.dashboards",
        "crm_cards.reset_designer", "crm_cards.reset_draftsman",
        "messenger.view_chat",
    },
    "ГАП": {
        "access.crm", "access.reports", "access.employees", "access.dashboards",
        "crm_cards.reset_designer", "crm_cards.reset_draftsman",
        "messenger.view_chat",
    },
    "Менеджер": {
        "access.crm", "access.supervision", "access.reports", "access.employees",
        "access.dashboards",
        "crm_cards.reset_designer", "crm_cards.reset_draftsman",
    },
    "ДАН": {
        "access.supervision",
        "supervision.complete_stage",
        "supervision.files_upload",
        "messenger.view_chat",
    },
    "Дизайнер": {
        "access.crm",
        "crm_cards.files_upload",
    },
    "Чертёжник": {
        "access.crm",
        "crm_cards.files_upload",
    },
    "Замерщик": {
        "access.crm",
    },
}

# Русские описания прав (fallback, если API недоступен)
PERMISSION_DESCRIPTIONS = {
    # Доступ к страницам
    "access.clients": "Доступ к странице Клиенты",
    "access.contracts": "Доступ к странице Договора",
    "access.crm": "Доступ к странице СРМ",
    "access.supervision": "Доступ к странице СРМ надзора",
    "access.reports": "Доступ к Отчетам и Статистике",
    "access.employees": "Доступ к странице Сотрудники",
    "access.salaries": "Доступ к странице Зарплаты",
    "access.employee_reports": "Доступ к Отчетам по сотрудникам",
    "access.admin": "Доступ к администрированию",
    "access.dashboards": "Показ дашбордов внизу страницы",
    # Сотрудники
    "employees.create": "Создание сотрудников",
    "employees.update": "Редактирование сотрудников",
    "employees.delete": "Удаление сотрудников",
    # Клиенты
    "clients.create": "Создание клиентов",
    "clients.view": "Просмотр клиентов",
    "clients.update": "Редактирование клиентов",
    "clients.delete": "Удаление клиентов",
    # Договоры
    "contracts.create": "Создание договоров",
    "contracts.view": "Просмотр договоров",
    "contracts.update": "Редактирование договоров",
    "contracts.delete": "Удаление договоров",
    # CRM
    "crm_cards.update": "Редактирование CRM карточек",
    "crm_cards.move": "Управление стадиями CRM",
    "crm_cards.delete": "Удаление CRM карточек",
    "crm_cards.assign_executor": "Назначение/переназначение исполнителей",
    "crm_cards.reset_approval": "Сброс согласования",
    "crm_cards.complete_approval": "Согласование с клиентом",
    "crm_cards.reset_designer": "Сброс отметки дизайнера",
    "crm_cards.reset_draftsman": "Сброс отметки чертежника",
    "crm_cards.files_upload": "Загрузка файлов в CRM",
    "crm_cards.files_delete": "Удаление файлов в CRM",
    "crm_cards.deadlines": "Управление дедлайнами CRM",
    "crm_cards.payments": "Оплаты в CRM карточках",
    # Надзор
    "supervision.update": "Редактирование карточек надзора",
    "supervision.move": "Перемещение карточек надзора",
    "supervision.pause_resume": "Приостановка/возобновление надзора",
    "supervision.complete_stage": "Завершение стадии надзора",
    "supervision.delete_order": "Удаление заказа надзора",
    "supervision.assign_executor": "Назначение исполнителей надзора",
    "supervision.files_upload": "Загрузка файлов в надзоре",
    "supervision.files_delete": "Удаление файлов в надзоре",
    "supervision.deadlines": "Управление дедлайнами надзора",
    "supervision.payments": "Оплаты в карточках надзора",
    # Платежи
    "payments.create": "Создание платежей",
    "payments.update": "Редактирование платежей",
    "payments.delete": "Удаление платежей",
    # Зарплаты
    "salaries.create": "Создание зарплат",
    "salaries.update": "Редактирование зарплат",
    "salaries.delete": "Удаление зарплат",
    "salaries.mark_to_pay": "Пометка к оплате",
    "salaries.mark_paid": "Пометка оплачено",
    # Тарифы
    "rates.create": "Создание/редактирование тарифов",
    "rates.delete": "Удаление тарифов",
    # Мессенджер
    "messenger.create_chat": "Создание чатов",
    "messenger.delete_chat": "Удаление чатов",
    "messenger.view_chat": "Просмотр/открытие чатов",
    "messenger.manage_scripts": "Управление скриптами мессенджера",
    # Уведомления
    "notifications.settings_projects": "Настройка каналов по типам проектов",
    "notifications.settings_duplication": "Настройка дублирования уведомлений",
}


PERMISSION_TOOLTIPS = {
    # Доступ к страницам
    "access.clients": "Сотрудник видит вкладку «Клиенты» в главном меню",
    "access.contracts": "Сотрудник видит вкладку «Договоры» в главном меню",
    "access.crm": "Сотрудник видит вкладку «CRM» с канбан-доской проектов",
    "access.supervision": "Сотрудник видит вкладку «Авторский надзор»",
    "access.reports": "Сотрудник видит вкладку «Отчёты и статистика»",
    "access.employees": "Сотрудник видит вкладку «Сотрудники»",
    "access.salaries": "Сотрудник видит вкладку «Зарплаты»",
    "access.employee_reports": "Сотрудник видит раздел отчётов по сотрудникам",
    "access.admin": "Сотрудник видит кнопку «Администрирование» — управление правами, агентами, городами",
    # Сотрудники
    "employees.create": "Может добавлять новых сотрудников в систему",
    "employees.update": "Может редактировать данные сотрудников (ФИО, должность, контакты)",
    "employees.delete": "Может удалять и увольнять сотрудников",
    # Клиенты
    "clients.create": "Может создавать новых клиентов",
    "clients.view": "Может просматривать карточки клиентов",
    "clients.update": "Может редактировать данные клиентов",
    "clients.delete": "Может удалять клиентов из системы",
    # Договоры
    "contracts.create": "Может создавать новые договоры",
    "contracts.view": "Может просматривать детали договоров",
    "contracts.update": "Может редактировать условия договоров (площадь, сумма, статус)",
    "contracts.delete": "Может удалять договоры из системы",
    # CRM
    "crm_cards.update": "Может редактировать данные в карточке проекта (теги, дедлайн, описание)",
    "crm_cards.move": "Управление рабочим процессом: принять работу, отправить на исправление, отправить клиенту",
    "crm_cards.delete": "Может удалять карточки проектов с канбан-доски",
    "crm_cards.assign_executor": "Может назначать и переназначать исполнителей на стадии проекта",
    "crm_cards.reset_approval": "Может сбросить согласование проекта для повторной отправки клиенту",
    "crm_cards.complete_approval": "Может отмечать этапы согласования с клиентом как завершённые",
    "crm_cards.reset_designer": "Может сбросить отметку о завершении работы дизайнера для доработки",
    "crm_cards.reset_draftsman": "Может сбросить отметку о завершении работы чертёжника для доработки",
    "crm_cards.files_upload": "Может загружать файлы в карточку проекта (чертежи, визуализации)",
    "crm_cards.files_delete": "Может удалять файлы из карточки проекта",
    "crm_cards.deadlines": "Может устанавливать и изменять дедлайны стадий проекта",
    "crm_cards.payments": "Видит и управляет вкладкой «Оплаты» в карточке проекта",
    # Надзор
    "supervision.update": "Может редактировать данные карточки авторского надзора",
    "supervision.move": "Может перемещать карточки надзора между стадиями на канбан-доске",
    "supervision.pause_resume": "Может приостановить или возобновить работу по карточке надзора",
    "supervision.complete_stage": "Может отмечать стадии надзора как завершённые",
    "supervision.delete_order": "Может удалять заказы авторского надзора",
    "supervision.assign_executor": "Может назначать исполнителей на стадии надзора",
    "supervision.files_upload": "Может загружать файлы в карточку надзора (акты, фото)",
    "supervision.files_delete": "Может удалять файлы из карточки надзора",
    "supervision.deadlines": "Может устанавливать и изменять дедлайны стадий надзора",
    "supervision.payments": "Видит и управляет оплатами в карточке надзора",
    # Платежи
    "payments.create": "Может создавать новые платежи и начисления",
    "payments.update": "Может редактировать суммы и условия платежей",
    "payments.delete": "Может удалять платежи из системы",
    # Зарплаты
    "salaries.create": "Может создавать записи о зарплатах",
    "salaries.update": "Может редактировать суммы и данные зарплат",
    "salaries.delete": "Может удалять записи о зарплатах",
    "salaries.mark_to_pay": "Может помечать зарплаты как «К оплате»",
    "salaries.mark_paid": "Может помечать зарплаты как «Оплачено»",
    # Тарифы
    "rates.create": "Может создавать и редактировать тарифные ставки",
    "rates.delete": "Может удалять тарифные ставки",
    # Мессенджер
    "messenger.create_chat": "Может создавать новые чаты в мессенджере",
    "messenger.delete_chat": "Может удалять чаты из мессенджера",
    "messenger.view_chat": "Может просматривать и открывать чаты",
    "messenger.manage_scripts": "Может управлять скриптами автоматических сообщений",
    # Уведомления
    "notifications.settings_projects": "Сотрудник видит настройку каналов по типам проектов (индивидуальные / шаблонные)",
    "notifications.settings_duplication": "Сотрудник видит настройку дублирования уведомлений подчинённых",
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

        # Исправление черного фона всплывающих подсказок
        from utils.tooltip_fix import apply_tooltip_palette
        apply_tooltip_palette(self)

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
                padding: 4px 2px;
                border: none;
                border-bottom: 1px solid #d9d9d9;
                font-weight: bold;
                font-size: 11px;
            }
            QToolTip {
                background-color: #f5f5f5;
                color: #333333;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 6px 10px;
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

        # Заголовки столбцов — с переносом слов для длинных названий ролей
        headers = ['Право'] + [r.replace(' ', '\n') for r in ROLES]
        table.setHorizontalHeaderLabels(headers)

        # Настройка заголовков
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col_idx in range(1, col_count):
            header.setSectionResizeMode(col_idx, QHeaderView.Fixed)
            header.resizeSection(col_idx, 90)
        header.setMinimumSectionSize(70)
        # Высота заголовка для 2-3 строк текста
        header.setFixedHeight(52)

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
                tooltip = PERMISSION_TOOLTIPS.get(perm_name, perm_name)
                perm_item.setToolTip(tooltip)
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

                    # Подтверждение при включении access.admin
                    if perm_name == 'access.admin':
                        cb.stateChanged.connect(
                            lambda state, r=role, c=cb: self._on_admin_access_changed(state, r, c)
                        )

                self._row_perm_map[row] = perm_name
                row += 1

    # Права, автоматически выдаваемые при access.admin
    _ADMIN_AUTO_PERMS = [
        'agents.create', 'agents.update', 'agents.delete',
        'cities.create', 'cities.delete',
    ]

    def _on_admin_access_changed(self, state, role, checkbox):
        """Подтверждение при включении access.admin для роли"""
        if state == Qt.Checked:
            from PyQt5.QtWidgets import QDialog
            reply = CustomQuestionBox(
                self,
                'Доступ к администрированию',
                f'Предоставить роли "{role}" доступ к администрированию?\n\n'
                'Это включает управление агентами, городами,\n'
                'правами доступа и другими настройками.'
            ).exec_()
            if reply != QDialog.Accepted:
                checkbox.blockSignals(True)
                checkbox.setChecked(False)
                checkbox.blockSignals(False)

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
                            tooltip = PERMISSION_TOOLTIPS.get(perm_name, perm_name)
                            item.setToolTip(tooltip)
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
        """Собрать текущее состояние чекбоксов в словарь матрицы.

        Если access.admin включён для роли — автоматически добавляет
        права на агентов и города (они не видны в матрице, но нужны).
        """
        matrix = {}
        for role in ROLES:
            perms = []
            for group_perms in PERMISSION_GROUPS.values():
                for perm_name in group_perms:
                    cb = self._checkboxes.get((perm_name, role))
                    if cb and cb.isChecked():
                        perms.append(perm_name)
            # Автоматически добавляем agents/cities при access.admin
            if 'access.admin' in perms:
                for auto_perm in self._ADMIN_AUTO_PERMS:
                    if auto_perm not in perms:
                        perms.append(auto_perm)
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
                # Сбрасываем клиентский кеш прав — изменения должны подхватиться
                from utils.permissions import invalidate_cache
                invalidate_cache()
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

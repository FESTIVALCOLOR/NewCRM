# -*- coding: utf-8 -*-
"""
Виджет «Таблица сроков надзора» для карточки CRM надзора.
Содержит 12 стадий закупки с бюджетами, статусами, экспортом.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QDateEdit,
    QAbstractItemView, QFileDialog, QComboBox
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont, QBrush
from utils.calendar_helpers import add_today_button_to_dateedit
from datetime import datetime, timedelta


# Цвета статусов
STATUS_COLORS = {
    'Не начато': '#FFFFFF',
    'В работе': '#FFF8E1',
    'Закуплено': '#E3F2FD',
    'Доставлено': '#E8F5E9',
    'Просрочено': '#FFEBEE',
}

STATUS_OPTIONS = ['Не начато', 'В работе', 'Закуплено', 'Доставлено', 'Просрочено']


def networkdays(start_date, end_date):
    """Расчёт рабочих дней"""
    if not start_date or not end_date:
        return 0
    if isinstance(start_date, str):
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            return 0
    if isinstance(end_date, str):
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return 0
    if end_date < start_date:
        return 0
    count = 0
    current = start_date
    while current < end_date:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


class SupervisionTimelineWidget(QWidget):
    """Виджет таблицы сроков надзора"""

    COLUMNS = [
        'Стадия', 'План. дата', 'Факт. дата', 'Дней',
        'Бюджет план', 'Бюджет факт', 'Экономия',
        'Поставщик', 'Комиссия', 'Статус', 'Примечания'
    ]

    def __init__(self, card_data, data, db=None, api_client=None, employee=None, parent=None):
        super().__init__(parent)
        self.card_data = card_data
        self.data = data
        self.db = db
        self.api_client = api_client
        self.employee = employee
        self.entries = []
        self._loading = False

        self.card_id = card_data.get('id')

        # Получаем данные контракта
        self.contract_data = {}
        contract_id = card_data.get('contract_id')
        if contract_id:
            try:
                contracts = self.data.get_all_contracts()
                for c in contracts:
                    if c.get('id') == contract_id:
                        self.contract_data = c
                        break
            except Exception:
                pass

        self._build_ui()
        self._load_data()

    @staticmethod
    def _make_cell_label(text, bg_color, align='center', bold=False, font_size=12,
                         color='#333333'):
        """Создать QLabel для ячейки (обход глобального stylesheet)"""
        lbl = QLabel(text)
        weight = 'bold' if bold else 'normal'
        lbl.setStyleSheet(
            f'background-color: {bg_color}; color: {color}; padding: 4px 6px; '
            f'font-size: {font_size}px; font-weight: {weight}; border-radius: 2px;'
        )
        qt_align = Qt.AlignCenter if align == 'center' else (Qt.AlignLeft | Qt.AlignVCenter)
        if align == 'right':
            qt_align = Qt.AlignRight | Qt.AlignVCenter
        lbl.setAlignment(qt_align)
        return lbl

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 20)
        layout.setSpacing(6)

        # === ШАПКА ===
        address = self.contract_data.get('address', '-')
        self.lbl_address = QLabel(f'Адрес: {address}')
        self.lbl_address.setStyleSheet('font-size: 12px; font-weight: bold; color: #333;')
        layout.addWidget(self.lbl_address)

        # Легенда статусов
        legend = QLabel(
            'Статусы:  '
            '<span style="background:#FFFFFF; border:1px solid #ddd; padding:2px 6px; border-radius:2px;">Не начато</span>  '
            '<span style="background:#FFF8E1; padding:2px 6px; border-radius:2px;">В работе</span>  '
            '<span style="background:#E3F2FD; padding:2px 6px; border-radius:2px;">Закуплено</span>  '
            '<span style="background:#E8F5E9; padding:2px 6px; border-radius:2px;">Доставлено</span>  '
            '<span style="background:#FFEBEE; padding:2px 6px; border-radius:2px;">Просрочено</span>'
        )
        legend.setStyleSheet('font-size: 10px; color: #888; margin-top: 2px;')
        legend.setTextFormat(Qt.RichText)
        layout.addWidget(legend)

        # === ТАБЛИЦА ===
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, len(self.COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.Fixed)

        self.table.setColumnWidth(1, 120)   # План. дата
        self.table.setColumnWidth(2, 120)   # Факт. дата
        self.table.setColumnWidth(3, 60)    # Дней
        self.table.setColumnWidth(4, 100)   # Бюджет план
        self.table.setColumnWidth(5, 100)   # Бюджет факт
        self.table.setColumnWidth(6, 90)    # Экономия
        self.table.setColumnWidth(7, 120)   # Поставщик
        self.table.setColumnWidth(8, 90)    # Комиссия
        self.table.setColumnWidth(9, 110)   # Статус
        self.table.setColumnWidth(10, 150)  # Примечания

        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E0E0E0;
                gridline-color: #E0E0E0;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #2F5496;
                color: white;
                border: 1px solid #1B3A6E;
                padding: 6px;
                font-weight: bold;
                font-size: 10px;
            }
        """)

        layout.addWidget(self.table, 1)

        # === СВОДКА ===
        self.summary_widget = QWidget()
        summary_layout = QHBoxLayout(self.summary_widget)
        summary_layout.setContentsMargins(0, 4, 0, 0)

        self.lbl_budget_plan = QLabel('Бюджет план: 0')
        self.lbl_budget_fact = QLabel('Бюджет факт: 0')
        self.lbl_savings = QLabel('Экономия: 0')
        self.lbl_defects = QLabel('Дефекты: 0/0')
        self.lbl_visits = QLabel('Визиты: 0')

        for lbl in [self.lbl_budget_plan, self.lbl_budget_fact, self.lbl_savings, self.lbl_defects, self.lbl_visits]:
            lbl.setStyleSheet('font-size: 11px; font-weight: bold; color: #333; padding: 0 8px;')
            summary_layout.addWidget(lbl)

        summary_layout.addStretch()
        layout.addWidget(self.summary_widget)

        # === КНОПКИ ===
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_excel = QPushButton('Экспорт в Excel')
        self.btn_excel.setFixedHeight(32)
        self.btn_excel.setStyleSheet("""
            QPushButton {
                background-color: #217346; color: white; border: none;
                border-radius: 4px; padding: 0 16px; font-size: 12px;
            }
            QPushButton:hover { background-color: #1a5c38; }
        """)
        self.btn_excel.clicked.connect(self._export_excel)
        btn_layout.addWidget(self.btn_excel)

        self.btn_pdf = QPushButton('Экспорт в PDF (без бюджетов)')
        self.btn_pdf.setFixedHeight(32)
        self.btn_pdf.setStyleSheet("""
            QPushButton {
                background-color: #C62828; color: white; border: none;
                border-radius: 4px; padding: 0 16px; font-size: 12px;
            }
            QPushButton:hover { background-color: #a52222; }
        """)
        self.btn_pdf.clicked.connect(self._export_pdf)
        btn_layout.addWidget(self.btn_pdf)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    # Стадии надзора для локальной инициализации
    SUPERVISION_STAGES = [
        ('STAGE_1_CERAMIC', 'Стадия 1: Закупка керамогранита'),
        ('STAGE_2_PLUMBING', 'Стадия 2: Закупка сантехники'),
        ('STAGE_3_EQUIPMENT', 'Стадия 3: Закупка оборудования'),
        ('STAGE_4_DOORS', 'Стадия 4: Закупка дверей и окон'),
        ('STAGE_5_WALL', 'Стадия 5: Закупка настенных материалов'),
        ('STAGE_6_FLOOR', 'Стадия 6: Закупка напольных материалов'),
        ('STAGE_7_STUCCO', 'Стадия 7: Лепной декор'),
        ('STAGE_8_LIGHTING', 'Стадия 8: Освещение'),
        ('STAGE_9_APPLIANCES', 'Стадия 9: Бытовая техника'),
        ('STAGE_10_CUSTOM_FURNITURE', 'Стадия 10: Закупка заказной мебели'),
        ('STAGE_11_FACTORY_FURNITURE', 'Стадия 11: Закупка фабричной мебели'),
        ('STAGE_12_DECOR', 'Стадия 12: Закупка декора'),
    ]

    def _load_data(self):
        """Загрузка данных"""
        if not self.card_id:
            return

        self._loading = True
        try:
            entries = self.data.get_supervision_timeline(self.card_id)
            if not entries:
                # Автоинициализация через API
                result = self.data.init_supervision_timeline(self.card_id)
                if result and 'entries' in result:
                    entries = result['entries']
                else:
                    # API мог вернуть ошибку (404) — пробуем локальную инициализацию
                    entries = self.data.get_supervision_timeline(self.card_id)
                    if not entries:
                        self._init_timeline_locally()
                        entries = self.data.get_supervision_timeline(self.card_id)

            self.entries = entries or []
            self._recalculate_all_days()
            self._populate_table()
            self._update_summary()
        except Exception as e:
            print(f"[SupervisionTimelineWidget] Ошибка загрузки: {e}")
        finally:
            self._loading = False

    def _init_timeline_locally(self):
        """Локальная инициализация таблицы сроков (fallback при ошибке API)"""
        try:
            db = self.data.db
            if not db:
                return
            stage_entries = [
                {
                    'stage_code': code,
                    'stage_name': name,
                    'sort_order': i + 1,
                    'status': 'Не начато',
                    'executor': ''
                }
                for i, (code, name) in enumerate(self.SUPERVISION_STAGES)
            ]
            db.init_supervision_timeline(self.card_id, stage_entries)
            print(f"[SupervisionTimelineWidget] Локальная инициализация таблицы сроков для карточки {self.card_id}")
        except Exception as e:
            print(f"[SupervisionTimelineWidget] Ошибка локальной инициализации: {e}")

    def _create_date_edit(self, date_str, row, stage_code, is_plan=True):
        """Создать QDateEdit в контейнере для центрирования"""
        date_container = QWidget()
        date_container.setStyleSheet('background-color: transparent;')
        date_layout = QHBoxLayout(date_container)
        date_layout.setContentsMargins(2, 0, 2, 0)
        date_layout.setSpacing(0)
        date_layout.setAlignment(Qt.AlignVCenter)

        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat('dd.MM.yyyy')
        date_edit.setSpecialValueText(' ')
        date_edit.setMinimumDate(QDate(2020, 1, 1))

        if date_str:
            d = QDate.fromString(date_str, 'yyyy-MM-dd')
            if d.isValid():
                date_edit.setDate(d)
            else:
                date_edit.setDate(date_edit.minimumDate())
        else:
            date_edit.setDate(date_edit.minimumDate())

        # Календарь открывается на текущем месяце через CustomCalendarWidget.showEvent()

        date_edit.setStyleSheet('''
            QDateEdit {
                background-color: #FFF2CC;
                border: 1px solid #CCCCCC;
                border-radius: 2px;
                padding: 0px 4px;
                min-height: 20px;
                max-height: 20px;
                font-size: 12px;
            }
            QDateEdit::drop-down {
                border: none;
                width: 20px;
            }
            QCalendarWidget QWidget {
                background-color: #ffffff;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #ffffff;
                border-radius: 0px;
            }
            QCalendarWidget QToolButton {
                background-color: #ffffff;
                color: #333333;
                border-radius: 2px;
                padding: 4px;
            }
            QCalendarWidget QSpinBox {
                background-color: #ffffff;
                border-radius: 0px;
            }
        ''')

        # CustomCalendarWidget с защитой от мелькания popup при конструировании
        # (showEvent guard: if not self.window().isVisible(): return)
        custom_cal = add_today_button_to_dateedit(date_edit)
        custom_cal.setStyleSheet('QWidget { background-color: #ffffff; }')

        if is_plan:
            date_edit.dateChanged.connect(
                lambda d, r=row, sc=stage_code: self._on_plan_date_changed(r, sc, d)
            )
        else:
            date_edit.dateChanged.connect(
                lambda d, r=row, sc=stage_code: self._on_fact_date_changed(r, sc, d)
            )

        date_layout.addWidget(date_edit)
        return date_container

    def _populate_table(self):
        """Заполнение таблицы (QLabel для цветных ячеек — обход global stylesheet)"""
        self._loading = True
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(0)
            self.table.setRowCount(len(self.entries))

            for row, entry in enumerate(self.entries):
                self.table.setRowHeight(row, 32)
                stage_code = entry.get('stage_code', '')
                status = entry.get('status', 'Не начато')
                bg = STATUS_COLORS.get(status, '#FFFFFF')

                # Кол 0: Стадия
                self.table.setCellWidget(row, 0,
                    self._make_cell_label(entry.get('stage_name', ''), bg, 'left'))

                # Кол 1: План. дата
                plan_date = entry.get('plan_date', '')
                self.table.setCellWidget(row, 1,
                    self._create_date_edit(plan_date, row, stage_code, is_plan=True))

                # Кол 2: Факт. дата
                fact_date = entry.get('actual_date', '')
                self.table.setCellWidget(row, 2,
                    self._create_date_edit(fact_date, row, stage_code, is_plan=False))

                # Кол 3: Дней
                days_val = entry.get('actual_days', '') or ''
                self.table.setCellWidget(row, 3,
                    self._make_cell_label(str(days_val) if days_val else '', bg))

                # Кол 4: Бюджет план
                bp = entry.get('budget_planned', 0) or 0
                self.table.setCellWidget(row, 4,
                    self._make_cell_label(f'{bp:,.0f}' if bp else '', bg, 'right'))

                # Кол 5: Бюджет факт
                ba = entry.get('budget_actual', 0) or 0
                self.table.setCellWidget(row, 5,
                    self._make_cell_label(f'{ba:,.0f}' if ba else '', bg, 'right'))

                # Кол 6: Экономия
                savings = entry.get('budget_savings', 0) or 0
                savings_color = '#333333'
                if savings > 0:
                    savings_color = '#4CAF50'
                elif savings < 0:
                    savings_color = '#F44336'
                self.table.setCellWidget(row, 6,
                    self._make_cell_label(f'{savings:,.0f}' if savings else '', bg,
                                          'right', color=savings_color))

                # Кол 7: Поставщик
                self.table.setCellWidget(row, 7,
                    self._make_cell_label(entry.get('supplier', '') or '', bg, 'left'))

                # Кол 8: Комиссия
                commission = entry.get('commission', 0) or 0
                self.table.setCellWidget(row, 8,
                    self._make_cell_label(f'{commission:,.0f}' if commission else '', bg, 'right'))

                # Кол 9: Статус (QComboBox)
                status_combo = QComboBox()
                status_combo.addItems(STATUS_OPTIONS)
                idx = STATUS_OPTIONS.index(status) if status in STATUS_OPTIONS else 0
                status_combo.setCurrentIndex(idx)
                status_combo.setStyleSheet("""
                    QComboBox {
                        border: 1px solid #E0E0E0; padding: 2px;
                        font-size: 11px; background: white;
                    }
                """)
                status_combo.currentTextChanged.connect(
                    lambda text, r=row, sc=stage_code: self._on_status_changed(r, sc, text)
                )
                self.table.setCellWidget(row, 9, status_combo)

                # Кол 10: Примечания
                self.table.setCellWidget(row, 10,
                    self._make_cell_label(entry.get('notes', '') or '', bg, 'left'))

        finally:
            self.table.setUpdatesEnabled(True)
            self._loading = False

    def _on_plan_date_changed(self, row, stage_code, new_date):
        """Изменение плановой даты"""
        if self._loading:
            return
        date_str = new_date.toString('yyyy-MM-dd') if new_date.isValid() and new_date > QDate(2020, 1, 1) else ''
        if row < len(self.entries):
            self.entries[row]['plan_date'] = date_str
        self._save_entry(stage_code, {'plan_date': date_str})

    def _on_fact_date_changed(self, row, stage_code, new_date):
        """Изменение фактической даты"""
        if self._loading:
            return
        date_str = new_date.toString('yyyy-MM-dd') if new_date.isValid() and new_date > QDate(2020, 1, 1) else ''
        if row < len(self.entries):
            self.entries[row]['actual_date'] = date_str
        # Пересчитываем дни для всех стадий (т.к. изменение одной стадии влияет на следующую)
        self._recalculate_all_days()
        # Сохраняем текущую запись
        self._save_entry(stage_code, {
            'actual_date': date_str,
            'actual_days': self.entries[row].get('actual_days', 0) if row < len(self.entries) else 0
        })
        # Перестроить таблицу для обновления QLabel дней
        self._populate_table()

    def _recalculate_all_days(self):
        """Пересчёт дней для всех стадий.
        Логика: дни = разница между фактической датой текущей стадии и предыдущей.
        Для стадии 1: дни = факт.дата стадии 1 - дата начала надзора (start_date).
        """
        start_date = self.card_data.get('start_date', '') or self.card_data.get('created_at', '')
        # Преобразуем дату создания если нужно (может быть в формате с временем)
        if start_date and 'T' in start_date:
            start_date = start_date.split('T')[0]
        if start_date and ' ' in start_date:
            start_date = start_date.split(' ')[0]

        prev_date = start_date  # Начальная дата для первой стадии

        for entry in self.entries:
            fact_date = entry.get('actual_date', '')
            if fact_date and prev_date:
                days = networkdays(prev_date, fact_date)
                entry['actual_days'] = days
            else:
                entry['actual_days'] = 0

            # Следующая стадия считает от факт. даты текущей
            if fact_date:
                prev_date = fact_date

    def _on_status_changed(self, row, stage_code, new_status):
        """Изменение статуса"""
        if self._loading:
            return
        if row < len(self.entries):
            self.entries[row]['status'] = new_status
        self._save_entry(stage_code, {'status': new_status})
        # Перестроить таблицу для обновления цветов QLabel
        self._populate_table()

    def _save_entry(self, stage_code, updates):
        """Сохранение изменений на сервер"""
        if self.card_id and stage_code:
            try:
                self.data.update_supervision_timeline_entry(self.card_id, stage_code, updates)
            except Exception as e:
                print(f"[SupervisionTimelineWidget] Ошибка сохранения: {e}")

    def _update_summary(self):
        """Обновление сводки"""
        total_plan = sum(e.get('budget_planned', 0) or 0 for e in self.entries)
        total_fact = sum(e.get('budget_actual', 0) or 0 for e in self.entries)
        total_savings = sum(e.get('budget_savings', 0) or 0 for e in self.entries)
        total_defects = sum(e.get('defects_found', 0) or 0 for e in self.entries)
        total_resolved = sum(e.get('defects_resolved', 0) or 0 for e in self.entries)
        total_visits = sum(e.get('site_visits', 0) or 0 for e in self.entries)

        self.lbl_budget_plan.setText(f'Бюджет план: {total_plan:,.0f}')
        self.lbl_budget_fact.setText(f'Бюджет факт: {total_fact:,.0f}')
        self.lbl_savings.setText(f'Экономия: {total_savings:,.0f}')
        self.lbl_defects.setText(f'Дефекты: {total_defects}/{total_resolved}')
        self.lbl_visits.setText(f'Визиты: {total_visits}')

    def _export_excel(self):
        """Экспорт в Excel"""
        if not self.card_id:
            return
        try:
            file_bytes = self.data.export_supervision_timeline_excel(self.card_id)
            if file_bytes:
                path, _ = QFileDialog.getSaveFileName(
                    self, 'Сохранить Excel', f'supervision_timeline_{self.card_id}.xlsx',
                    'Excel (*.xlsx)'
                )
                if path:
                    with open(path, 'wb') as f:
                        f.write(file_bytes)
        except Exception as e:
            print(f"[SupervisionTimelineWidget] Ошибка экспорта Excel: {e}")

    def _export_pdf(self):
        """Экспорт в PDF (без бюджетов)"""
        if not self.card_id:
            return
        try:
            file_bytes = self.data.export_supervision_timeline_pdf(self.card_id)
            if file_bytes:
                path, _ = QFileDialog.getSaveFileName(
                    self, 'Сохранить PDF', f'supervision_timeline_{self.card_id}.pdf',
                    'PDF (*.pdf)'
                )
                if path:
                    with open(path, 'wb') as f:
                        f.write(file_bytes)
        except Exception as e:
            print(f"[SupervisionTimelineWidget] Ошибка экспорта PDF: {e}")

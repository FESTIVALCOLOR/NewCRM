# -*- coding: utf-8 -*-
"""
Виджет «Таблица сроков надзора» для карточки CRM надзора.
Содержит 12 стадий закупки с бюджетами, статусами, экспортом.
Все редактируемые поля: QLabel + кнопка-карандаш → inline-редактор → автосохранение.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QPushButton, QHeaderView, QDateEdit,
    QAbstractItemView, QFileDialog, QComboBox, QLineEdit,
    QTextEdit, QDialog, QDialogButtonBox, QGroupBox,
    QTableWidgetItem
)
from PyQt5.QtCore import Qt, QDate, QUrl
from PyQt5.QtGui import QDoubleValidator, QDesktopServices
from utils.calendar_helpers import add_today_button_to_dateedit
from utils.icon_loader import IconLoader
from utils.table_settings import apply_no_focus_delegate
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


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
        'Стадия', 'Исполнитель', 'План. дата', 'Факт. дата', 'Дней', 'Расхожд.',
        'Бюджет план', 'Бюджет факт', 'Экономия',
        'Поставщик', 'Комиссия', 'Статус', 'Примечания'
    ]

    # Минимальные ширины столбцов
    COLUMN_WIDTHS = [200, 140, 110, 110, 55, 65, 100, 100, 90, 130, 90, 110, 160]

    def __init__(self, card_data, data, db=None, api_client=None, employee=None, parent=None):
        super().__init__(parent)
        # Сохраняем ссылку на диалог ДО того, как QTabWidget перехватит parent
        self._dialog = parent
        self.card_data = card_data
        self.data = data
        self.db = db
        self.api_client = api_client
        self.employee = employee
        self.entries = []
        self.totals = {}
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

        # Список исполнителей для выпадающего списка
        self._executor_names = self._get_executor_names()

        self._build_ui()
        self._load_data()

    def _get_executor_names(self):
        """Получить список ФИО исполнителей из карточки"""
        names = []
        sm = self.card_data.get('senior_manager_name', '') or ''
        dan = self.card_data.get('dan_name', '') or ''
        if sm:
            names.append(sm)
        if dan:
            names.append(dan)
        # Если ничего не нашли — пустой список
        return names

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

    def _create_pencil_btn(self, tooltip='Редактировать'):
        """Создать кнопку-карандаш для ячейки"""
        pencil_btn = IconLoader.create_action_button(
            'edit', tooltip=tooltip,
            bg_color='transparent', hover_color='#E3F2FD',
            icon_size=14, button_size=22, icon_color='#666666'
        )
        return pencil_btn

    def _create_editable_cell(self, text, bg_color, row, stage_code, field_name,
                              align='center', is_date=False, is_number=False,
                              is_multiline=False, tooltip_text=None):
        """Создать ячейку QLabel + кнопка-карандаш для редактирования.

        При нажатии карандаша → переключается в inline-редактор.
        При потере фокуса или Enter → автосохранение.
        """
        container = QWidget()
        container.setStyleSheet('background-color: transparent;')
        layout = QHBoxLayout(container)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignVCenter)

        # QLabel с текущим значением
        lbl = QLabel(text)
        qt_align = Qt.AlignCenter if align == 'center' else (Qt.AlignLeft | Qt.AlignVCenter)
        if align == 'right':
            qt_align = Qt.AlignRight | Qt.AlignVCenter
        lbl.setAlignment(qt_align)
        lbl.setStyleSheet(
            f'background-color: {bg_color}; color: #333333; padding: 2px 4px; '
            f'font-size: 12px; border-radius: 2px; border: 1px solid #E0E0E0;'
        )
        lbl.setMinimumWidth(40)

        # Tooltip для примечаний
        if tooltip_text:
            lbl.setToolTip(tooltip_text)
        elif is_date and text:
            lbl.setToolTip('Нажмите карандаш для изменения даты')
        elif not text:
            lbl.setToolTip('Нажмите карандаш для ввода')

        # Кнопка-карандаш
        pencil_btn = self._create_pencil_btn()

        if is_date:
            pencil_btn.clicked.connect(
                lambda checked, r=row, sc=stage_code, fn=field_name, cur=text:
                    self._edit_date_cell(r, sc, fn, cur)
            )
        elif is_multiline:
            pencil_btn.clicked.connect(
                lambda checked, r=row, sc=stage_code, fn=field_name, cur=text:
                    self._edit_multiline_cell(r, sc, fn, cur)
            )
        else:
            pencil_btn.clicked.connect(
                lambda checked, r=row, sc=stage_code, fn=field_name, cur=text, num=is_number:
                    self._edit_text_cell(r, sc, fn, cur, num)
            )

        layout.addWidget(lbl, 1)
        layout.addWidget(pencil_btn, 0)
        return container

    def _edit_date_cell(self, row, stage_code, field_name, current_text):
        """Переключить ячейку даты в режим редактирования (QDateEdit)"""
        col = 2 if field_name == 'plan_date' else 3

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

        date_edit.blockSignals(True)
        # Парсим текст даты (формат dd.MM.yyyy)
        if current_text:
            d = QDate.fromString(current_text, 'dd.MM.yyyy')
            if d.isValid():
                date_edit.setDate(d)
            else:
                date_edit.setDate(QDate.currentDate())
        else:
            date_edit.setDate(QDate.currentDate())
        date_edit.blockSignals(False)

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

        custom_cal = add_today_button_to_dateedit(date_edit)
        custom_cal.setStyleSheet('QWidget { background-color: #ffffff; }')

        date_edit.dateChanged.connect(
            lambda d, r=row, sc=stage_code, fn=field_name:
                self._on_date_edited(r, sc, fn, d)
        )

        date_layout.addWidget(date_edit)
        self.table.setCellWidget(row, col, date_container)
        date_edit.setFocus()

    def _on_date_edited(self, row, stage_code, field_name, new_date):
        """Обработка изменения даты через карандаш"""
        if self._loading:
            return
        date_str = new_date.toString('yyyy-MM-dd') if new_date.isValid() and new_date > QDate(2020, 1, 1) else ''

        if row < len(self.entries):
            self.entries[row][field_name] = date_str

        if field_name == 'actual_date':
            self._recalculate_all_days()
            self._save_entry(stage_code, {
                'actual_date': date_str,
                'actual_days': self.entries[row].get('actual_days', 0) if row < len(self.entries) else 0
            })
        else:
            self._save_entry(stage_code, {'plan_date': date_str})

        # Перестроить таблицу
        self._populate_table()
        self._update_summary()

    def _edit_text_cell(self, row, stage_code, field_name, current_text, is_number=False):
        """Переключить ячейку в inline QLineEdit"""
        col = self._field_to_col(field_name)
        if col < 0:
            return

        line_edit = QLineEdit()
        # Убираем форматирование числа (запятые)
        clean_text = current_text.replace(',', '').replace(' ', '') if current_text else ''
        line_edit.setText(clean_text)
        if is_number:
            line_edit.setValidator(QDoubleValidator(0, 999999999, 2))

        line_edit.setStyleSheet('''
            QLineEdit {
                background-color: #FFF2CC;
                border: 1px solid #CCCCCC;
                border-radius: 2px;
                padding: 2px 4px;
                font-size: 12px;
            }
        ''')

        def save_and_close():
            text = line_edit.text().strip()
            value = None
            if is_number:
                try:
                    value = float(text) if text else 0
                except ValueError:
                    value = 0
            else:
                value = text

            if row < len(self.entries):
                self.entries[row][field_name] = value

            updates = {field_name: value}

            # Автоподсчёт экономии при изменении бюджета
            if field_name in ('budget_planned', 'budget_actual'):
                bp = self.entries[row].get('budget_planned', 0) or 0
                ba = self.entries[row].get('budget_actual', 0) or 0
                savings = bp - ba
                self.entries[row]['budget_savings'] = savings
                updates['budget_savings'] = savings

            self._save_entry(stage_code, updates)
            self._populate_table()
            self._update_summary()

        line_edit.editingFinished.connect(save_and_close)

        self.table.setCellWidget(row, col, line_edit)
        line_edit.setFocus()
        line_edit.selectAll()

    def _edit_multiline_cell(self, row, stage_code, field_name, current_text):
        """Открыть диалог для многострочного ввода (примечания)"""
        # Получаем полный текст из entries (не обрезанный display_text)
        full_text = ''
        if row < len(self.entries):
            full_text = self.entries[row].get(field_name, '') or ''

        dlg = QDialog(self)
        dlg.setWindowTitle('Редактировать примечание')
        dlg.setMinimumSize(400, 200)
        dlg.setStyleSheet('QDialog { background-color: white; border: 1px solid #E0E0E0; }')

        dlg_layout = QVBoxLayout(dlg)
        text_edit = QTextEdit()
        text_edit.setPlainText(full_text)
        text_edit.setStyleSheet('''
            QTextEdit {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        ''')
        dlg_layout.addWidget(text_edit)

        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Save).setText('Сохранить')
        btn_box.button(QDialogButtonBox.Cancel).setText('Отмена')
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        dlg_layout.addWidget(btn_box)

        if dlg.exec_() == QDialog.Accepted:
            text = text_edit.toPlainText().strip()
            if row < len(self.entries):
                self.entries[row][field_name] = text
            self._save_entry(stage_code, {field_name: text})
            self._populate_table()
            self._update_summary()

    def _field_to_col(self, field_name):
        """Маппинг имени поля → номер столбца"""
        mapping = {
            'executor': 1,
            'plan_date': 2,
            'actual_date': 3,
            'actual_days': 4,
            'deviation': 5,
            'budget_planned': 6,
            'budget_actual': 7,
            'budget_savings': 8,
            'supplier': 9,
            'commission': 10,
            'status': 11,
            'notes': 12,
        }
        return mapping.get(field_name, -1)

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

        # Все столбцы — Interactive (пользователь может растягивать)
        header = self.table.horizontalHeader()
        for col in range(len(self.COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.Interactive)

        # Установить начальные ширины
        for col, width in enumerate(self.COLUMN_WIDTHS):
            self.table.setColumnWidth(col, width)

        # Последний столбец занимает оставшееся пространство
        header.setStretchLastSection(True)

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
        self.lbl_commission = QLabel('Комиссия: 0')

        for lbl in [self.lbl_budget_plan, self.lbl_budget_fact, self.lbl_savings, self.lbl_commission]:
            lbl.setStyleSheet('font-size: 11px; font-weight: bold; color: #333; padding: 0 8px;')
            summary_layout.addWidget(lbl)

        summary_layout.addStretch()
        layout.addWidget(self.summary_widget)

        # === КНОПКИ ЭКСПОРТА ===
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        EXCEL_STYLE = """
            QPushButton {
                background-color: #217346; color: white; border: none;
                border-radius: 4px; padding: 0 14px; font-size: 11px;
            }
            QPushButton:hover { background-color: #1a5c38; }
        """
        PDF_STYLE = """
            QPushButton {
                background-color: #C62828; color: white; border: none;
                border-radius: 4px; padding: 0 14px; font-size: 11px;
            }
            QPushButton:hover { background-color: #a52222; }
        """

        self.btn_excel_comm = QPushButton('Excel (с комиссией)')
        self.btn_excel_comm.setFixedHeight(32)
        self.btn_excel_comm.setStyleSheet(EXCEL_STYLE)
        self.btn_excel_comm.clicked.connect(lambda: self._export_excel(include_commission=True))
        btn_layout.addWidget(self.btn_excel_comm)

        self.btn_excel_no_comm = QPushButton('Excel (без комиссии)')
        self.btn_excel_no_comm.setFixedHeight(32)
        self.btn_excel_no_comm.setStyleSheet(EXCEL_STYLE)
        self.btn_excel_no_comm.clicked.connect(lambda: self._export_excel(include_commission=False))
        btn_layout.addWidget(self.btn_excel_no_comm)

        self.btn_pdf_comm = QPushButton('PDF (с комиссией)')
        self.btn_pdf_comm.setFixedHeight(32)
        self.btn_pdf_comm.setStyleSheet(PDF_STYLE)
        self.btn_pdf_comm.clicked.connect(lambda: self._export_pdf(include_commission=True))
        btn_layout.addWidget(self.btn_pdf_comm)

        self.btn_pdf_no_comm = QPushButton('PDF (без комиссии)')
        self.btn_pdf_no_comm.setFixedHeight(32)
        self.btn_pdf_no_comm.setStyleSheet(PDF_STYLE)
        self.btn_pdf_no_comm.clicked.connect(lambda: self._export_pdf(include_commission=False))
        btn_layout.addWidget(self.btn_pdf_no_comm)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # === БЛОК ФАЙЛОВ ===
        self._build_files_section(layout)

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
            timeline_result = self.data.get_supervision_timeline(self.card_id)
            entries = timeline_result.get('entries', []) if isinstance(timeline_result, dict) else (timeline_result or [])
            totals = timeline_result.get('totals', {}) if isinstance(timeline_result, dict) else {}

            if not entries:
                # Автоинициализация через API
                result = self.data.init_supervision_timeline(self.card_id)
                if result and 'entries' in result:
                    entries = result['entries']
                    totals = result.get('totals', {})
                else:
                    # API мог вернуть ошибку (404) — пробуем локальную инициализацию
                    timeline_result = self.data.get_supervision_timeline(self.card_id)
                    entries = timeline_result.get('entries', []) if isinstance(timeline_result, dict) else (timeline_result or [])
                    totals = timeline_result.get('totals', {}) if isinstance(timeline_result, dict) else {}
                    if not entries:
                        self._init_timeline_locally()
                        timeline_result = self.data.get_supervision_timeline(self.card_id)
                        entries = timeline_result.get('entries', []) if isinstance(timeline_result, dict) else (timeline_result or [])
                        totals = timeline_result.get('totals', {}) if isinstance(timeline_result, dict) else {}

            self.entries = entries or []
            self.totals = totals or {}
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

    def _calculate_deviation(self, plan_date_str, actual_date_str):
        """Расчёт расхождения между плановой и фактической датой (в днях).
        Положительное = опоздание, отрицательное = раньше срока."""
        if not plan_date_str or not actual_date_str:
            return None
        try:
            plan = datetime.strptime(plan_date_str, '%Y-%m-%d').date()
            actual = datetime.strptime(actual_date_str, '%Y-%m-%d').date()
            return (actual - plan).days
        except (ValueError, TypeError):
            return None

    def _populate_table(self):
        """Заполнение таблицы: QLabel + карандаш для всех редактируемых полей"""
        self._loading = True
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(0)
            # +1 строка для "Итого"
            total_rows = len(self.entries) + 1 if self.entries else 0
            self.table.setRowCount(total_rows)

            for row, entry in enumerate(self.entries):
                self.table.setRowHeight(row, 36)
                stage_code = entry.get('stage_code', '')
                status = entry.get('status', 'Не начато')
                bg = STATUS_COLORS.get(status, '#FFFFFF')

                # Кол 0: Стадия (только чтение)
                stage_lbl = self._make_cell_label(entry.get('stage_name', ''), bg, 'left')
                self.table.setCellWidget(row, 0, stage_lbl)

                # Кол 1: Исполнитель (QComboBox с привязанными к карточке)
                executor_combo = QComboBox()
                executor_combo.addItem('')
                for name in self._executor_names:
                    executor_combo.addItem(name)
                current_executor = entry.get('executor', '') or ''
                # Если текущий исполнитель не в списке — добавить
                if current_executor and current_executor not in self._executor_names:
                    executor_combo.addItem(current_executor)
                idx = executor_combo.findText(current_executor)
                if idx >= 0:
                    executor_combo.setCurrentIndex(idx)
                executor_combo.setStyleSheet(
                    "QComboBox { border: 1px solid #E0E0E0; padding: 2px;"
                    " font-size: 11px; background: white; }")
                executor_combo.currentTextChanged.connect(
                    lambda text, r=row, sc=stage_code:
                        self._on_executor_changed(r, sc, text))
                self.table.setCellWidget(row, 1, executor_combo)

                # Кол 2: План. дата (карандаш → QDateEdit)
                plan_date = entry.get('plan_date', '')
                plan_text = ''
                if plan_date:
                    try:
                        d = QDate.fromString(plan_date, 'yyyy-MM-dd')
                        plan_text = d.toString('dd.MM.yyyy') if d.isValid() else ''
                    except Exception:
                        pass
                plan_cell = self._create_editable_cell(
                    plan_text, bg, row, stage_code, 'plan_date',
                    align='center', is_date=True)
                self.table.setCellWidget(row, 2, plan_cell)

                # Кол 3: Факт. дата (карандаш → QDateEdit)
                fact_date = entry.get('actual_date', '')
                fact_text = ''
                fact_bg = bg
                if fact_date:
                    try:
                        d = QDate.fromString(fact_date, 'yyyy-MM-dd')
                        fact_text = d.toString('dd.MM.yyyy') if d.isValid() else ''
                        fact_bg = '#E8F5E9'
                    except Exception:
                        pass
                fact_cell = self._create_editable_cell(
                    fact_text, fact_bg, row, stage_code, 'actual_date',
                    align='center', is_date=True)
                self.table.setCellWidget(row, 3, fact_cell)

                # Кол 4: Дней (авто-расчёт, только чтение)
                days_val = entry.get('actual_days', '') or ''
                days_lbl = self._make_cell_label(str(days_val) if days_val else '', bg)
                self.table.setCellWidget(row, 4, days_lbl)

                # Кол 5: Расхождение (авто-расчёт, цвет)
                deviation = self._calculate_deviation(plan_date, fact_date)
                entry['_deviation'] = deviation  # кэшируем
                dev_text = ''
                dev_color = '#333333'
                if deviation is not None:
                    dev_text = str(deviation)
                    if deviation > 0:
                        dev_color = '#F44336'  # красный — опоздание
                    elif deviation < 0:
                        dev_color = '#4CAF50'  # зелёный — раньше срока
                dev_lbl = self._make_cell_label(dev_text, bg, 'center', color=dev_color)
                self.table.setCellWidget(row, 5, dev_lbl)

                # Кол 6: Бюджет план (карандаш → число)
                bp = entry.get('budget_planned', 0) or 0
                bp_text = f'{bp:,.0f}' if bp else ''
                bp_cell = self._create_editable_cell(
                    bp_text, bg, row, stage_code, 'budget_planned',
                    align='right', is_number=True)
                self.table.setCellWidget(row, 6, bp_cell)

                # Кол 7: Бюджет факт (карандаш → число)
                ba = entry.get('budget_actual', 0) or 0
                ba_text = f'{ba:,.0f}' if ba else ''
                ba_cell = self._create_editable_cell(
                    ba_text, bg, row, stage_code, 'budget_actual',
                    align='right', is_number=True)
                self.table.setCellWidget(row, 7, ba_cell)

                # Кол 8: Экономия (авто-расчёт, только чтение)
                savings = entry.get('budget_savings', 0) or 0
                savings_color = '#333333'
                if savings > 0:
                    savings_color = '#4CAF50'
                elif savings < 0:
                    savings_color = '#F44336'
                savings_text = f'{savings:,.0f}' if savings else ''
                savings_lbl = self._make_cell_label(
                    savings_text, bg, 'right', color=savings_color)
                self.table.setCellWidget(row, 8, savings_lbl)

                # Кол 9: Поставщик (карандаш → текст)
                supplier = entry.get('supplier', '') or ''
                supplier_cell = self._create_editable_cell(
                    supplier, bg, row, stage_code, 'supplier',
                    align='left')
                self.table.setCellWidget(row, 9, supplier_cell)

                # Кол 10: Комиссия (карандаш → число)
                commission = entry.get('commission', 0) or 0
                comm_text = f'{commission:,.0f}' if commission else ''
                comm_cell = self._create_editable_cell(
                    comm_text, bg, row, stage_code, 'commission',
                    align='right', is_number=True)
                self.table.setCellWidget(row, 10, comm_cell)

                # Кол 11: Статус (QComboBox)
                status_combo = QComboBox()
                status_combo.addItems(STATUS_OPTIONS)
                idx = STATUS_OPTIONS.index(status) if status in STATUS_OPTIONS else 0
                status_combo.setCurrentIndex(idx)
                status_combo.setStyleSheet(
                    "QComboBox { border: 1px solid #E0E0E0; padding: 2px;"
                    " font-size: 11px; background: white; }")
                status_combo.currentTextChanged.connect(
                    lambda text, r=row, sc=stage_code:
                        self._on_status_changed(r, sc, text))
                self.table.setCellWidget(row, 11, status_combo)

                # Кол 12: Примечания (карандаш → многострочный диалог)
                notes = entry.get('notes', '') or ''
                display_notes = notes[:40] + '...' if len(notes) > 40 else notes
                tip = notes if notes else 'Нажмите карандаш для ввода примечания'
                notes_cell = self._create_editable_cell(
                    display_notes, bg, row, stage_code, 'notes',
                    align='left', is_multiline=True, tooltip_text=tip)
                self.table.setCellWidget(row, 12, notes_cell)

            # === СТРОКА "ИТОГО" ===
            if self.entries:
                self._add_totals_row(len(self.entries))

            # Зафиксировать высоту таблицы — ровно под строки + заголовок
            row_count = self.table.rowCount()
            total_h = self.table.horizontalHeader().height() + 4
            for i in range(row_count):
                total_h += self.table.rowHeight(i)
            self.table.setFixedHeight(total_h)

        finally:
            self.table.setUpdatesEnabled(True)
            self._loading = False

    def _add_totals_row(self, row):
        """Добавить строку 'Итого' в конец таблицы (не редактируемая, жирный шрифт, серый фон)"""
        totals_bg = '#F5F5F5'
        self.table.setRowHeight(row, 36)

        # Кол 0: "Итого" (жирный)
        totals_label = self._make_cell_label('Итого', totals_bg, 'left', bold=True)
        self.table.setCellWidget(row, 0, totals_label)

        # Кол 1 (Исполнитель), 2 (План), 3 (Факт): пустые
        for col in (1, 2, 3):
            empty_lbl = self._make_cell_label('', totals_bg)
            self.table.setCellWidget(row, col, empty_lbl)

        # Кол 4: Итого дней
        total_days = sum(e.get('actual_days', 0) or 0 for e in self.entries)
        days_text = str(total_days) if total_days else ''
        days_lbl = self._make_cell_label(days_text, totals_bg, 'center', bold=True)
        self.table.setCellWidget(row, 4, days_lbl)

        # Кол 5: Итого расхождений (сумма положительных = опоздания)
        total_deviation = sum(
            e.get('_deviation', 0) or 0
            for e in self.entries
            if e.get('_deviation') is not None and e.get('_deviation', 0) > 0
        )
        dev_text = str(total_deviation) if total_deviation else ''
        dev_color = '#F44336' if total_deviation > 0 else '#333333'
        dev_lbl = self._make_cell_label(dev_text, totals_bg, 'center', bold=True, color=dev_color)
        self.table.setCellWidget(row, 5, dev_lbl)

        # Суммы бюджетов
        total_bp = sum(e.get('budget_planned', 0) or 0 for e in self.entries)
        total_ba = sum(e.get('budget_actual', 0) or 0 for e in self.entries)
        total_savings = sum(e.get('budget_savings', 0) or 0 for e in self.entries)
        total_commission = sum(e.get('commission', 0) or 0 for e in self.entries)

        # Кол 6: Бюджет план
        bp_text = f'{total_bp:,.0f}' if total_bp else ''
        bp_lbl = self._make_cell_label(bp_text, totals_bg, 'right', bold=True)
        self.table.setCellWidget(row, 6, bp_lbl)

        # Кол 7: Бюджет факт
        ba_text = f'{total_ba:,.0f}' if total_ba else ''
        ba_lbl = self._make_cell_label(ba_text, totals_bg, 'right', bold=True)
        self.table.setCellWidget(row, 7, ba_lbl)

        # Кол 8: Экономия
        savings_color = '#333333'
        if total_savings > 0:
            savings_color = '#4CAF50'
        elif total_savings < 0:
            savings_color = '#F44336'
        savings_text = f'{total_savings:,.0f}' if total_savings else ''
        savings_lbl = self._make_cell_label(savings_text, totals_bg, 'right', bold=True, color=savings_color)
        self.table.setCellWidget(row, 8, savings_lbl)

        # Кол 9: Поставщик — пусто
        empty_supplier = self._make_cell_label('', totals_bg)
        self.table.setCellWidget(row, 9, empty_supplier)

        # Кол 10: Комиссия
        comm_text = f'{total_commission:,.0f}' if total_commission else ''
        comm_lbl = self._make_cell_label(comm_text, totals_bg, 'right', bold=True)
        self.table.setCellWidget(row, 10, comm_lbl)

        # Кол 11-12: пустые
        for col in (11, 12):
            empty_lbl = self._make_cell_label('', totals_bg)
            self.table.setCellWidget(row, col, empty_lbl)

    def _on_executor_changed(self, row, stage_code, new_executor):
        """Изменение исполнителя"""
        if self._loading:
            return
        if row < len(self.entries):
            self.entries[row]['executor'] = new_executor
        self._save_entry(stage_code, {'executor': new_executor})

    def _on_status_changed(self, row, stage_code, new_status):
        """Изменение статуса"""
        if self._loading:
            return
        if row < len(self.entries):
            self.entries[row]['status'] = new_status
        self._save_entry(stage_code, {'status': new_status})
        # Перестроить таблицу для обновления цветов QLabel
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
        total_commission = sum(e.get('commission', 0) or 0 for e in self.entries)

        self.lbl_budget_plan.setText(f'Бюджет план: {total_plan:,.0f}')
        self.lbl_budget_fact.setText(f'Бюджет факт: {total_fact:,.0f}')

        savings_style = 'font-size: 11px; font-weight: bold; padding: 0 8px;'
        if total_savings > 0:
            savings_style += ' color: #4CAF50;'
        elif total_savings < 0:
            savings_style += ' color: #F44336;'
        else:
            savings_style += ' color: #333;'
        self.lbl_savings.setStyleSheet(savings_style)
        self.lbl_savings.setText(f'Экономия: {total_savings:,.0f}')
        self.lbl_commission.setText(f'Комиссия: {total_commission:,.0f}')

    def _export_excel(self, include_commission=True):
        """Экспорт в Excel (с/без комиссии)"""
        if not self.card_id:
            return
        try:
            file_bytes = self.data.export_supervision_timeline_excel(
                self.card_id, include_commission=include_commission)
            if file_bytes:
                suffix = ' с комиссией' if include_commission else ' без комиссии'
                path, _ = QFileDialog.getSaveFileName(
                    self, 'Сохранить Excel',
                    f'Таблица сроков{suffix} {self.contract_data.get("address", "")}.xlsx',
                    'Excel (*.xlsx)'
                )
                if path:
                    with open(path, 'wb') as f:
                        f.write(file_bytes)
        except Exception as e:
            logger.error("Ошибка экспорта Excel авторского надзора: %s", e, exc_info=True)

    def _export_pdf(self, include_commission=False):
        """Экспорт в PDF (с/без комиссии)"""
        if not self.card_id:
            return
        try:
            file_bytes = self.data.export_supervision_timeline_pdf(
                self.card_id, include_commission=include_commission)
            if not file_bytes:
                from ui.custom_message_box import CustomMessageBox
                CustomMessageBox(self, 'Предупреждение',
                                 'Сервер не вернул данные для PDF-экспорта.', 'warning').exec_()
                return
            suffix = ' с комиссией' if include_commission else ' без комиссии'
            path, _ = QFileDialog.getSaveFileName(
                self, 'Сохранить PDF',
                f'Таблица сроков{suffix} {self.contract_data.get("address", "")} от {QDate.currentDate().toString("dd.MM.yyyy")}.pdf',
                'PDF (*.pdf)'
            )
            if path:
                with open(path, 'wb') as f:
                    f.write(file_bytes)
                logger.info("Авторский надзор таймлайн PDF сохранён: %s", path)
                from utils.pdf_utils import open_file
                open_file(path)
        except Exception as e:
            logger.error("Ошибка экспорта PDF авторского надзора: %s", e, exc_info=True)
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Ошибка', f'Не удалось экспортировать PDF:\n{e}', 'error').exec_()

    # === БЛОК ФАЙЛОВ ===

    def _build_files_section(self, parent_layout):
        """Создание блока файлов под кнопками экспорта"""
        GROUP_BOX_STYLE = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: #FAFAFA;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #2C3E50;
            }
        """

        files_group = QGroupBox("Файлы авторского надзора")
        files_group.setStyleSheet(GROUP_BOX_STYLE)
        fl = QVBoxLayout()

        # Кнопка загрузки — компактная, во всю ширину
        upload_btn = IconLoader.create_icon_button(
            'upload', 'Загрузить файл', 'Загрузить файл на Яндекс.Диск', icon_size=12)
        upload_btn.setFixedHeight(32)
        upload_btn.setStyleSheet('''
            QPushButton {
                background-color: #ffd93c; color: #333333;
                padding: 4px 16px; border-radius: 4px;
                font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { background-color: #e6c435; }
        ''')
        upload_btn.clicked.connect(self._upload_file)
        fl.addWidget(upload_btn)

        # Таблица файлов
        self.files_table = QTableWidget()
        apply_no_focus_delegate(self.files_table)
        self.files_table.setColumnCount(4)
        self.files_table.setHorizontalHeaderLabels(
            ['Название файла', 'Тип', 'Дата загрузки', 'Действия'])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.files_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.files_table.verticalHeader().setDefaultSectionSize(32)

        fl.addWidget(self.files_table, 1)
        files_group.setLayout(fl)
        parent_layout.addWidget(files_group)

    def _upload_file(self):
        """Загрузка файла — делегируем родительскому диалогу"""
        dialog = self._dialog or self.window()
        if dialog and hasattr(dialog, 'upload_supervision_file'):
            dialog.upload_supervision_file()

    def load_files(self):
        """Загрузить список файлов (вызывается из родительского диалога)"""
        if not hasattr(self, 'files_table'):
            return
        try:
            contract_id = self.card_data.get('contract_id')
            if not contract_id:
                return

            api_files = self.data.get_project_files(contract_id, stage='supervision')
            if not api_files:
                all_files = self.data.get_project_files(contract_id)
                api_files = [f for f in (all_files or [])
                             if f.get('file_type') == 'Файл надзора' or f.get('stage') == 'supervision']

            files = [
                {
                    'id': f.get('id'),
                    'file_name': f.get('file_name'),
                    'file_type': f.get('file_type'),
                    'yandex_path': f.get('yandex_path'),
                    'public_link': f.get('public_link'),
                    'created_at': f.get('upload_date') or f.get('created_at')
                }
                for f in (api_files or [])
            ]

            self.files_table.setRowCount(len(files))

            for row, file_data in enumerate(files):
                name_item = QTableWidgetItem(file_data['file_name'] or 'Без названия')
                name_item.setData(Qt.UserRole, file_data['id'])
                self.files_table.setItem(row, 0, name_item)

                type_item = QTableWidgetItem(file_data['file_type'] or 'Файл')
                self.files_table.setItem(row, 1, type_item)

                from utils.date_utils import format_date
                date_str = format_date(file_data['created_at']) if file_data['created_at'] else ''
                date_item = QTableWidgetItem(date_str)
                self.files_table.setItem(row, 2, date_item)

                actions_widget = QWidget()
                actions_layout = QHBoxLayout()
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(4)

                file_link = file_data.get('public_link') or ''
                if file_link:
                    open_btn = IconLoader.create_icon_button('eye', '', 'Открыть файл', icon_size=12)
                    open_btn.setFixedSize(20, 20)
                    open_btn.setStyleSheet('''
                        QPushButton {
                            background-color: #d4e4bc; border: 1px solid #c0d4a8;
                            border-radius: 4px; padding: 0px;
                        }
                        QPushButton:hover { background-color: #c0d4a8; }
                    ''')
                    open_btn.clicked.connect(
                        lambda checked, link=file_link: QDesktopServices.openUrl(QUrl(link)))
                    actions_layout.addWidget(open_btn)

                delete_btn = IconLoader.create_icon_button('delete2', '', 'Удалить файл', icon_size=12)
                delete_btn.setFixedSize(20, 20)
                delete_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #FFE6E6; border: 1px solid #FFCCCC;
                        border-radius: 4px; padding: 0px;
                    }
                    QPushButton:hover { background-color: #FFCCCC; }
                ''')
                delete_btn.clicked.connect(
                    lambda checked, fid=file_data['id'], fpath=file_data.get('yandex_path'):
                        self._delete_file(fid, fpath))
                actions_layout.addWidget(delete_btn)

                actions_layout.setAlignment(Qt.AlignCenter)
                actions_widget.setLayout(actions_layout)
                self.files_table.setCellWidget(row, 3, actions_widget)

        except Exception as e:
            logger.error("Ошибка загрузки файлов в timeline widget: %s", e)

    def _delete_file(self, file_id, yandex_path):
        """Удалить файл — делегируем родительскому диалогу"""
        dialog = self._dialog or self.window()
        if dialog and hasattr(dialog, 'delete_supervision_file'):
            dialog.delete_supervision_file(file_id, yandex_path)

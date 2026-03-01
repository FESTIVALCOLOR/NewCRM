# -*- coding: utf-8 -*-
"""
Виджет «Таблица выездов и дефектов» для карточки авторского надзора.
Индивидуальные записи выездов: стадия (выпадающий список), дата, ФИО исполнителя, примечание.
Кнопка «Добавить строку», итого по месяцам, экспорт PDF/Excel, блок «Отчёты».
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QPushButton, QHeaderView, QDateEdit,
    QAbstractItemView, QFileDialog, QComboBox, QLineEdit,
    QGroupBox, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QDate, QUrl
from PyQt5.QtGui import QDesktopServices
from utils.calendar_helpers import add_today_button_to_dateedit
from utils.icon_loader import IconLoader
from utils.table_settings import apply_no_focus_delegate
import logging

logger = logging.getLogger(__name__)

# 12 стадий надзора
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

STAGE_NAMES = [name for _, name in SUPERVISION_STAGES]
STAGE_CODE_MAP = {name: code for code, name in SUPERVISION_STAGES}
STAGE_NAME_MAP = {code: name for code, name in SUPERVISION_STAGES}


class SupervisionVisitsWidget(QWidget):
    """Виджет таблицы выездов и дефектов"""

    COLUMNS = ['Стадия', 'Выезд на объект', 'ФИО исполнителя (ДАН)', 'Примечание', '']
    COLUMN_WIDTHS = [250, 150, 200, 250, 40]

    def __init__(self, card_data, data, db=None, api_client=None, employee=None, parent=None):
        super().__init__(parent)
        # Сохраняем ссылку на диалог ДО того, как QTabWidget перехватит parent
        self._dialog = parent
        self.card_data = card_data
        self.data = data
        self.db = db
        self.api_client = api_client
        self.employee = employee
        self.visits = []
        self._loading = False

        self.card_id = card_data.get('id')

        # Данные контракта для имён файлов
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
        director = self.card_data.get('studio_director_name', '') or ''
        if director:
            names.append(director)
        if sm:
            names.append(sm)
        if dan:
            names.append(dan)
        return names

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 20)
        layout.setSpacing(6)

        # === ШАПКА ===
        address = self.contract_data.get('address', '-')
        self.lbl_address = QLabel(f'Адрес: {address}')
        self.lbl_address.setStyleSheet('font-size: 12px; font-weight: bold; color: #333;')
        layout.addWidget(self.lbl_address)

        # === КНОПКА ДОБАВИТЬ ===
        add_row = QHBoxLayout()
        self.btn_add = QPushButton('Добавить строку')
        self.btn_add.setFixedHeight(32)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #2F5496; color: white; border: none;
                border-radius: 4px; padding: 0 20px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1B3A6E; }
        """)
        self.btn_add.clicked.connect(self._add_row)
        add_row.addWidget(self.btn_add)
        add_row.addStretch()
        layout.addLayout(add_row)

        # === ТАБЛИЦА ВЫЕЗДОВ ===
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)

        header = self.table.horizontalHeader()
        # Столбцы 0-3 — Interactive (пользователь может растягивать)
        for col in range(len(self.COLUMNS) - 1):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
        for col, width in enumerate(self.COLUMN_WIDTHS[:4]):
            self.table.setColumnWidth(col, width)
        # Столбец 3 (Примечание) растягивается на оставшееся пространство
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        # Столбец удаления — фиксированная узкая ширина
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 36)
        header.setStretchLastSection(False)

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

        # === СВОДКА (итого по месяцам) ===
        self.lbl_summary = QLabel('')
        self.lbl_summary.setStyleSheet(
            'font-size: 11px; font-weight: bold; color: #333; padding: 4px 0;')
        self.lbl_summary.setWordWrap(True)
        layout.addWidget(self.lbl_summary)

        # === КНОПКИ ЭКСПОРТА ===
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

        self.btn_pdf = QPushButton('Экспорт в PDF')
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

        # === БЛОК «ОТЧЁТЫ» (файлы) ===
        self._build_reports_section(layout)

    def _build_reports_section(self, parent_layout):
        """Блок загрузки файлов «Отчёты»"""
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

        reports_group = QGroupBox("Отчёты")
        reports_group.setStyleSheet(GROUP_BOX_STYLE)
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
        upload_btn.clicked.connect(self._upload_report)
        fl.addWidget(upload_btn)

        # Таблица файлов
        self.reports_table = QTableWidget()
        apply_no_focus_delegate(self.reports_table)
        self.reports_table.setColumnCount(4)
        self.reports_table.setHorizontalHeaderLabels(
            ['Название файла', 'Тип', 'Дата загрузки', 'Действия'])
        self.reports_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.reports_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.reports_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.reports_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.reports_table.setAlternatingRowColors(True)
        self.reports_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.reports_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.reports_table.verticalHeader().setDefaultSectionSize(32)

        fl.addWidget(self.reports_table, 1)
        reports_group.setLayout(fl)
        parent_layout.addWidget(reports_group)

    # === ЗАГРУЗКА ДАННЫХ ===

    def _load_data(self):
        """Загрузить выезды с сервера"""
        if not self.card_id:
            return
        self._loading = True
        try:
            result = self.data.get_supervision_visits(self.card_id)
            self.visits = result if isinstance(result, list) else []
            self._populate_table()
            self._update_summary()
        except Exception as e:
            logger.error("Ошибка загрузки выездов: %s", e)
        finally:
            self._loading = False

    def _populate_table(self):
        """Заполнить таблицу выездов"""
        self._loading = True
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(self.visits))
            for row, visit in enumerate(self.visits):
                self.table.setRowHeight(row, 36)
                visit_id = visit.get('id')

                # Кол 0: Стадия (QComboBox)
                stage_combo = QComboBox()
                stage_combo.addItems(STAGE_NAMES)
                current_name = visit.get('stage_name', '')
                idx = STAGE_NAMES.index(current_name) if current_name in STAGE_NAMES else 0
                stage_combo.setCurrentIndex(idx)
                stage_combo.setStyleSheet(
                    "QComboBox { border: 1px solid #E0E0E0; padding: 2px;"
                    " font-size: 11px; background: white; }")
                stage_combo.currentTextChanged.connect(
                    lambda text, vid=visit_id, r=row: self._on_stage_changed(r, vid, text))
                self.table.setCellWidget(row, 0, stage_combo)

                # Кол 1: Дата выезда (QDateEdit)
                date_container = QWidget()
                date_container.setStyleSheet('background-color: transparent;')
                dl = QHBoxLayout(date_container)
                dl.setContentsMargins(2, 0, 2, 0)
                dl.setSpacing(0)

                date_edit = QDateEdit()
                date_edit.setCalendarPopup(True)
                date_edit.setDisplayFormat('dd.MM.yyyy')
                date_edit.setMinimumDate(QDate(2020, 1, 1))

                visit_date = visit.get('visit_date', '')
                date_edit.blockSignals(True)
                if visit_date:
                    d = QDate.fromString(visit_date, 'yyyy-MM-dd')
                    if d.isValid():
                        date_edit.setDate(d)
                    else:
                        date_edit.setDate(QDate.currentDate())
                else:
                    date_edit.setDate(QDate.currentDate())
                date_edit.blockSignals(False)

                date_edit.setStyleSheet('''
                    QDateEdit {
                        background-color: white; border: 1px solid #E0E0E0;
                        border-radius: 2px; padding: 0px 4px;
                        min-height: 24px; font-size: 12px;
                    }
                    QDateEdit::drop-down { border: none; width: 20px; }
                    QCalendarWidget QWidget { background-color: #ffffff; }
                    QCalendarWidget QToolButton {
                        background-color: #ffffff; color: #333333;
                        border-radius: 2px; padding: 4px;
                    }
                    QCalendarWidget QSpinBox {
                        background-color: #ffffff; border-radius: 0px;
                    }
                ''')
                add_today_button_to_dateedit(date_edit)
                date_edit.dateChanged.connect(
                    lambda d, vid=visit_id, r=row: self._on_date_changed(r, vid, d))
                dl.addWidget(date_edit)
                self.table.setCellWidget(row, 1, date_container)

                # Кол 2: ФИО исполнителя (QComboBox)
                executor_combo = QComboBox()
                executor_combo.addItem('')
                for name in self._executor_names:
                    executor_combo.addItem(name)
                current_executor = visit.get('executor_name', '') or ''
                if current_executor and current_executor not in self._executor_names:
                    executor_combo.addItem(current_executor)
                idx = executor_combo.findText(current_executor)
                if idx >= 0:
                    executor_combo.setCurrentIndex(idx)
                executor_combo.setStyleSheet(
                    "QComboBox { border: 1px solid #E0E0E0; padding: 2px;"
                    " font-size: 11px; background: white; }")
                executor_combo.currentTextChanged.connect(
                    lambda text, vid=visit_id, r=row:
                        self._on_field_edited(r, vid, 'executor_name', text.strip()))
                self.table.setCellWidget(row, 2, executor_combo)

                # Кол 3: Примечание (QLineEdit)
                notes_edit = QLineEdit(visit.get('notes', '') or '')
                notes_edit.setStyleSheet('''
                    QLineEdit {
                        background-color: white; border: 1px solid #E0E0E0;
                        border-radius: 2px; padding: 2px 4px; font-size: 12px;
                    }
                ''')
                notes_edit.editingFinished.connect(
                    lambda vid=visit_id, r=row, le=notes_edit:
                        self._on_field_edited(r, vid, 'notes', le.text().strip()))
                self.table.setCellWidget(row, 3, notes_edit)

                # Кол 4: Кнопка удаления
                del_btn = IconLoader.create_action_button(
                    'delete2', tooltip='Удалить строку',
                    bg_color='#FFE6E6', hover_color='#FFCCCC',
                    icon_size=14, button_size=28, icon_color='#C62828'
                )
                del_btn.clicked.connect(
                    lambda checked, vid=visit_id: self._delete_row(vid))
                self.table.setCellWidget(row, 4, del_btn)

        finally:
            self.table.setUpdatesEnabled(True)
            self._loading = False

    def _update_summary(self):
        """Обновить сводку: итого по месяцам"""
        months = {}
        for v in self.visits:
            vd = v.get('visit_date', '') or ''
            if len(vd) >= 7:
                ym = vd[:7]  # YYYY-MM
                months[ym] = months.get(ym, 0) + 1

        total = len(self.visits)
        parts = []
        for ym in sorted(months.keys()):
            try:
                d = QDate.fromString(ym + '-01', 'yyyy-MM-dd')
                month_names = [
                    '', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
                ]
                name = f"{month_names[d.month()]} {d.year()}"
            except Exception:
                name = ym
            parts.append(f"{name}: {months[ym]}")

        summary = ' | '.join(parts) + f' | Всего: {total}' if parts else f'Всего выездов: {total}'
        self.lbl_summary.setText(summary)

    # === ОБРАБОТЧИКИ ИЗМЕНЕНИЙ ===

    def _delete_row(self, visit_id):
        """Удалить запись выезда"""
        if not visit_id or not self.card_id:
            return
        from ui.custom_message_box import CustomQuestionBox
        if CustomQuestionBox(self, 'Удаление', 'Удалить эту запись выезда?').exec_():
            try:
                self.data.delete_supervision_visit(self.card_id, visit_id)
                dialog = self._dialog
                if dialog and hasattr(dialog, '_add_project_history'):
                    dialog._add_project_history('row_deleted', 'Удалена запись выезда')
                self._load_data()
            except Exception as e:
                logger.error("Ошибка удаления выезда %s: %s", visit_id, e)

    def _add_row(self):
        """Добавить новую запись выезда"""
        if not self.card_id:
            return
        data = {
            'stage_code': SUPERVISION_STAGES[0][0],
            'stage_name': SUPERVISION_STAGES[0][1],
            'visit_date': QDate.currentDate().toString('yyyy-MM-dd'),
            'executor_name': '',
            'notes': '',
        }
        try:
            result = self.data.create_supervision_visit(self.card_id, data)
            if result:
                dialog = self._dialog
                if dialog and hasattr(dialog, '_add_project_history'):
                    dialog._add_project_history('row_added', 'Добавлена запись выезда')
                self._load_data()
        except Exception as e:
            logger.error("Ошибка добавления выезда: %s", e)

    def _on_stage_changed(self, row, visit_id, new_stage_name):
        """Изменение стадии"""
        if self._loading:
            return
        stage_code = STAGE_CODE_MAP.get(new_stage_name, '')
        self._save_visit(visit_id, {
            'stage_name': new_stage_name,
            'stage_code': stage_code
        })
        if row < len(self.visits):
            self.visits[row]['stage_name'] = new_stage_name
            self.visits[row]['stage_code'] = stage_code

    def _on_date_changed(self, row, visit_id, new_date):
        """Изменение даты"""
        if self._loading:
            return
        date_str = new_date.toString('yyyy-MM-dd') if new_date.isValid() else ''
        self._save_visit(visit_id, {'visit_date': date_str})
        if row < len(self.visits):
            self.visits[row]['visit_date'] = date_str
        self._update_summary()

    def _on_field_edited(self, row, visit_id, field_name, value):
        """Изменение текстового поля"""
        if self._loading:
            return
        self._save_visit(visit_id, {field_name: value})
        if row < len(self.visits):
            self.visits[row][field_name] = value

    def _save_visit(self, visit_id, updates):
        """Сохранить изменения"""
        if not visit_id:
            return
        try:
            self.data.update_supervision_visit(self.card_id, visit_id, updates)
            dialog = self._dialog
            if dialog and hasattr(dialog, '_add_project_history'):
                fields = ', '.join(f'{k}={v}' for k, v in updates.items())
                dialog._add_project_history('data_change', f'Выезд: {fields}')
        except Exception as e:
            logger.error("Ошибка сохранения выезда %s: %s", visit_id, e)

    # === ЭКСПОРТ ===

    def _export_excel(self):
        """Экспорт выездов в Excel"""
        if not self.card_id:
            return
        try:
            file_bytes = self.data.export_supervision_visits_excel(self.card_id)
            if file_bytes:
                path, _ = QFileDialog.getSaveFileName(
                    self, 'Сохранить Excel',
                    f'Выезды {self.contract_data.get("address", "")}.xlsx',
                    'Excel (*.xlsx)')
                if path:
                    with open(path, 'wb') as f:
                        f.write(file_bytes)
        except Exception as e:
            logger.error("Ошибка экспорта Excel выездов: %s", e)

    def _export_pdf(self):
        """Экспорт выездов в PDF"""
        if not self.card_id:
            return
        try:
            file_bytes = self.data.export_supervision_visits_pdf(self.card_id)
            if not file_bytes:
                from ui.custom_message_box import CustomMessageBox
                CustomMessageBox(self, 'Предупреждение',
                                 'Сервер не вернул данные для PDF-экспорта.', 'warning').exec_()
                return
            path, _ = QFileDialog.getSaveFileName(
                self, 'Сохранить PDF',
                f'Выезды {self.contract_data.get("address", "")} от {QDate.currentDate().toString("dd.MM.yyyy")}.pdf',
                'PDF (*.pdf)')
            if path:
                with open(path, 'wb') as f:
                    f.write(file_bytes)
                from utils.pdf_utils import open_file
                open_file(path)
        except Exception as e:
            logger.error("Ошибка экспорта PDF выездов: %s", e)
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Ошибка', f'Не удалось экспортировать PDF:\n{e}', 'error').exec_()

    # === ФАЙЛЫ «ОТЧЁТЫ» ===

    def _upload_report(self):
        """Загрузка файла — делегируем родительскому диалогу"""
        dialog = self._dialog or self.window()
        if dialog and hasattr(dialog, 'upload_supervision_report_file'):
            dialog.upload_supervision_report_file()

    def load_reports(self):
        """Загрузить список файлов-отчётов (вызывается из родительского диалога)"""
        if not hasattr(self, 'reports_table'):
            return
        try:
            contract_id = self.card_data.get('contract_id')
            if not contract_id:
                return

            api_files = self.data.get_project_files(contract_id, stage='supervision_reports')
            if not api_files:
                all_files = self.data.get_project_files(contract_id)
                api_files = [f for f in (all_files or [])
                             if f.get('stage') == 'supervision_reports']

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

            self.reports_table.setRowCount(len(files))

            for row, file_data in enumerate(files):
                name_item = QTableWidgetItem(file_data['file_name'] or 'Без названия')
                name_item.setData(Qt.UserRole, file_data['id'])
                self.reports_table.setItem(row, 0, name_item)

                type_item = QTableWidgetItem(file_data['file_type'] or 'Файл')
                self.reports_table.setItem(row, 1, type_item)

                from utils.date_utils import format_date
                date_str = format_date(file_data['created_at']) if file_data['created_at'] else ''
                date_item = QTableWidgetItem(date_str)
                self.reports_table.setItem(row, 2, date_item)

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
                        self._delete_report(fid, fpath))
                actions_layout.addWidget(delete_btn)

                actions_layout.setAlignment(Qt.AlignCenter)
                actions_widget.setLayout(actions_layout)
                self.reports_table.setCellWidget(row, 3, actions_widget)

        except Exception as e:
            logger.error("Ошибка загрузки отчётов: %s", e)

    def _delete_report(self, file_id, yandex_path):
        """Удалить файл-отчёт — делегируем родительскому диалогу"""
        dialog = self._dialog or self.window()
        if dialog and hasattr(dialog, 'delete_supervision_file'):
            dialog.delete_supervision_file(file_id, yandex_path)

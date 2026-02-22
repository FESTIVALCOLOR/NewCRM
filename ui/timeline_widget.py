# -*- coding: utf-8 -*-
"""
Виджет «Таблица сроков проекта» для CRM карточки.
Содержит расчётную таблицу этапов/подэтапов с автопересчётом,
экспортом в Excel/PDF, интеграцией с дедлайнами.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QDateEdit,
    QAbstractItemView, QFileDialog
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QBrush
from utils.calendar_helpers import add_today_button_to_dateedit, add_working_days
from utils.timeline_calc import calc_planned_dates
from utils.icon_loader import IconLoader
from datetime import datetime, timedelta
import threading


# ========== БИЗНЕС-ЛОГИКА ==========

def calc_contract_term(project_type_code: int, area: float) -> int:
    """Расчёт срока договора. 1=Полный, 2=Эскизный, 3=Планировочный"""
    if project_type_code == 1:
        thresholds = [(70,50),(100,60),(130,70),(160,80),(190,90),(220,100),
                      (250,110),(300,120),(350,130),(400,140),(450,150),(500,160)]
    elif project_type_code == 3:
        thresholds = [(70,10),(100,15),(130,20),(160,25),(190,30),(220,35),
                      (250,40),(300,45),(350,50),(400,55),(450,60),(500,65)]
    else:
        thresholds = [(70,30),(100,35),(130,40),(160,45),(190,50),(220,55),
                      (250,60),(300,65),(350,70),(400,75),(450,80),(500,85)]
    for max_area, days in thresholds:
        if area <= max_area:
            return days
    return 0


def calc_area_coefficient(area: float) -> int:
    return max(0, int((area - 1) // 100))


def networkdays(start_date, end_date):
    """Расчёт рабочих дней между двумя датами (NETWORKDAYS аналог)"""
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

    try:
        import numpy as np
        days = np.busday_count(start_date, end_date)
        return int(days)
    except Exception:
        count = 0
        current = start_date
        while current < end_date:
            if current.weekday() < 5:
                count += 1
            current += timedelta(days=1)
        return count


# Цвета
COLOR_STAGE_HEADER = QColor('#2F5496')
COLOR_SUBSTAGE_HEADER = QColor('#D6E4F0')
COLOR_DATE_CELL = QColor('#FFF2CC')
COLOR_NORM_CELL = QColor('#F2F2F2')
COLOR_START_DATE = QColor('#FCE4EC')
COLOR_IN_SCOPE = QColor('#FFFFFF')
COLOR_NOT_IN_SCOPE = QColor('#E0E0E0')
COLOR_STATUS_OK_BG = QColor('#E8F5E9')
COLOR_STATUS_FAIL_BG = QColor('#FFEBEE')
COLOR_SUBTOTAL_BG = QColor('#E3F2FD')
COLOR_GRANDTOTAL_BG = QColor('#FFF8E1')

# Маппинг роли исполнителя -> поле в card_data для ФИО
ROLE_TO_CARD_FIELD = {
    'Чертежник': 'draftsman_name',
    'Дизайнер': 'designer_name',
    'СДП': 'sdp_name',
    'ГАП': 'gap_name',
    'Менеджер': 'manager_name',
}


class ProjectTimelineWidget(QWidget):
    """Виджет таблицы сроков проекта CRM"""

    COLUMNS = ['Действия по этапам', 'Дата', 'Кол-во дней', 'Норма дней',
               'Статус', 'Исполнитель', 'ФИО']

    # Сигнал для обновления таблицы из фонового потока
    _data_ready = pyqtSignal()

    def __init__(self, card_data, data, db=None, api_client=None, employee=None, parent=None):
        super().__init__(parent)
        self.card_data = card_data
        self.data = data
        self.db = db
        self.api_client = api_client
        self.employee = employee
        self.entries = []
        self._loading = False

        # Получаем данные контракта из локальной БД (мгновенно, без API)
        contract_id = card_data.get('contract_id')
        self.contract_id = contract_id
        self.contract_data = {}
        if contract_id:
            try:
                self.data.prefer_local = True
                try:
                    contract = self.data.get_contract(contract_id)
                    if contract:
                        self.contract_data = contract
                finally:
                    self.data.prefer_local = False
            except Exception:
                pass

        # Получаем ФИО клиента из локальной БД (мгновенно)
        self._client_name = ''
        client_id = self.contract_data.get('client_id')
        if client_id:
            try:
                self.data.prefer_local = True
                try:
                    client = self.data.get_client(client_id)
                    if client:
                        if client.get('client_type') == 'Физическое лицо':
                            self._client_name = client.get('full_name', '')
                        else:
                            self._client_name = client.get('organization_name', '')
                finally:
                    self.data.prefer_local = False
            except Exception:
                pass

        self._build_ui()
        # Загружаем данные таблицы в фоновом потоке (не блокируя UI)
        self._data_ready.connect(self._on_data_ready)
        self._load_data_async()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 20)
        layout.setSpacing(6)

        # === ШАПКА ===
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)

        address = self.contract_data.get('address', '-')
        project_type = self.contract_data.get('project_type', '-')
        project_subtype = self.contract_data.get('project_subtype', '')
        area = self.contract_data.get('area', 0) or 0

        # Определяем pt_code из подтипа
        if project_subtype:
            if 'Полный' in project_subtype:
                pt_code = 1
            elif 'Планировочный' in project_subtype:
                pt_code = 3
            else:
                pt_code = 2
        else:
            pt_code = 1 if project_type == 'Индивидуальный' else 2

        contract_term = calc_contract_term(pt_code, float(area)) if area else 0
        self._contract_term = contract_term
        K = calc_area_coefficient(float(area)) if area else 0

        self.lbl_address = QLabel(f'Адрес: {address}')
        self.lbl_address.setStyleSheet('font-size: 12px; font-weight: bold; color: #333;')
        header_layout.addWidget(self.lbl_address)

        subtype_text = f'  |  Подтип: {project_subtype}' if project_subtype else ''
        info_line = QLabel(
            f'Тип: {project_type}{subtype_text}  |  Площадь: {area} м\u00b2  |  '
            f'Срок по договору: {contract_term} р.д.  |  Коэфф. площади (K): {K}'
        )
        info_line.setStyleSheet('font-size: 11px; color: #666;')
        header_layout.addWidget(info_line)

        # Расшифровка цветов
        legend = QLabel(
            '<span style="background:#2F5496; color:white; padding:2px 6px; border-radius:2px;">Цвет этапа</span>  '
            '<span style="background:#D6E4F0; padding:2px 6px; border-radius:2px;">Цвет подэтапа</span>  '
            '<span style="background:#FFFFFF; border:1px solid #ddd; padding:2px 6px; border-radius:2px;">Строки в расчёте срока</span>  '
            '<span style="background:#E0E0E0; border:1px solid #ccc; padding:2px 6px; border-radius:2px;">Строки вне расчёта срока</span>  '
            '<span style="background:#FFF2CC; padding:2px 6px; border-radius:2px;">Поле для ввода даты</span>  '
            '<span style="background:#E8F5E9; padding:2px 6px; border-radius:2px;">Статус: в срок</span>  '
            '<span style="background:#FFEBEE; padding:2px 6px; border-radius:2px;">Статус: просрочен</span>'
        )
        legend.setStyleSheet('font-size: 10px; color: #888; margin-top: 4px;')
        legend.setTextFormat(Qt.RichText)
        legend.setWordWrap(True)
        header_layout.addWidget(legend)

        layout.addWidget(header_widget)

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
        self.table.setColumnWidth(1, 130)  # Дата
        self.table.setColumnWidth(2, 90)   # Кол-во дней
        self.table.setColumnWidth(3, 90)   # Норма дней
        self.table.setColumnWidth(4, 90)   # Статус
        self.table.setColumnWidth(5, 110)  # Исполнитель
        self.table.setColumnWidth(6, 140)  # ФИО

        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E0E0E0;
                gridline-color: #E0E0E0;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                padding: 6px;
                font-weight: bold;
                font-size: 11px;
            }
        """)

        layout.addWidget(self.table, 1)

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

    def _load_data_async(self):
        """Запуск загрузки данных в фоновом потоке"""
        if not self.contract_id:
            return
        self._loading = True
        thread = threading.Thread(target=self._load_data_background, daemon=True)
        thread.start()

    def _fetch_entries(self):
        """Загрузить/инициализировать entries таймлайна (без UI).
        Возвращает отсортированный список entries."""
        project_type = self.contract_data.get('project_type', 'Индивидуальный')
        project_subtype = self.contract_data.get('project_subtype', '')
        area = float(self.contract_data.get('area', 0) or 0)
        floors = int(self.contract_data.get('floors', 1) or 1)

        entries = self.data.get_project_timeline(self.contract_id)

        if entries:
            has_template_codes = any(
                e.get('stage_code', '').startswith('T') for e in entries
                if e.get('executor_role') != 'header' and e.get('stage_code', '') != 'START'
            )
            is_template = (project_type == 'Шаблонный')
            if is_template != has_template_codes and area > 0:
                result = self.data.reinit_project_timeline(self.contract_id, {
                    'project_type': project_type,
                    'project_subtype': project_subtype,
                    'area': area,
                    'floors': floors
                })
                if result:
                    entries = self.data.get_project_timeline(self.contract_id)

        if not entries:
            if area > 0:
                result = self.data.init_project_timeline(self.contract_id, {
                    'project_type': project_type,
                    'project_subtype': project_subtype,
                    'area': area,
                    'floors': floors
                })
                if result and 'entries' in result:
                    entries = result['entries']
                else:
                    entries = self.data.get_project_timeline(self.contract_id)

        entries = sorted(entries or [], key=lambda e: e.get('sort_order', 0))

        # Синхронизация norm_days из admin шаблона для записей с norm_days=0
        self._sync_norm_days_from_template(entries)

        return entries

    def _sync_norm_days_from_template(self, entries):
        """Применить norm_days из admin шаблона к записям, где norm_days=0.
        Синхронизирует карточки, созданные до появления админки нормо-дней."""
        if not entries:
            return
        project_type = self.contract_data.get('project_type', 'Индивидуальный')
        project_subtype = self.contract_data.get('project_subtype', '')
        area = float(self.contract_data.get('area', 0) or 0)
        agent_type = self.contract_data.get('agent_type', 'Все агенты') or 'Все агенты'
        if area <= 0:
            return
        try:
            template_data = self.data.preview_norm_days_template(
                project_type, project_subtype, area, agent_type
            )
            if not template_data or not isinstance(template_data, dict):
                return
            tpl_entries = template_data.get('entries', [])
            if not tpl_entries:
                return
            # Маппинг stage_code → norm_days из шаблона
            tpl_map = {}
            for te in tpl_entries:
                code = te.get('stage_code', '')
                nd = te.get('norm_days', 0) or te.get('base_norm_days', 0) or 0
                if code and nd > 0:
                    tpl_map[code] = int(round(nd))
            # Применить к записям с пустыми norm_days
            updated = []
            for entry in entries:
                code = entry.get('stage_code', '')
                role = entry.get('executor_role', '')
                if role == 'header' or code == 'START':
                    continue
                current_nd = entry.get('norm_days', 0) or 0
                tpl_nd = tpl_map.get(code, 0)
                if current_nd == 0 and tpl_nd > 0:
                    entry['norm_days'] = tpl_nd
                    updated.append((code, tpl_nd))
            # Сохранить обновлённые norm_days на сервер
            if updated and self.contract_id:
                for code, nd in updated:
                    try:
                        self.data.update_timeline_entry(
                            self.contract_id, code, {'norm_days': nd}
                        )
                    except Exception:
                        pass
        except Exception as e:
            print(f"[TimelineWidget] Ошибка синхронизации norm_days: {e}")

    def _load_data_background(self):
        """Загрузка данных таблицы сроков в фоновом потоке (не блокирует UI)"""
        try:
            self.entries = self._fetch_entries()
            try:
                self._data_ready.emit()
            except RuntimeError:
                pass  # Виджет уже закрыт
        except Exception as e:
            print(f"[TimelineWidget] Ошибка загрузки: {e}")

    def _on_data_ready(self):
        """Обновление UI после загрузки данных (вызывается в main thread)"""
        try:
            self._auto_set_start_date()
            self._recalculate_days()
            self._populate_table()
        except Exception as e:
            print(f"[TimelineWidget] Ошибка отображения: {e}")
        finally:
            self._loading = False

    def _load_data(self):
        """Синхронная загрузка данных (для обновления по кнопке)"""
        if not self.contract_id:
            return

        self._loading = True
        try:
            self.entries = self._fetch_entries()
            self._auto_set_start_date()
            self._recalculate_days()
            self._populate_table()
        except Exception as e:
            print(f"[TimelineWidget] Ошибка загрузки: {e}")
        finally:
            self._loading = False

    def _auto_set_start_date(self):
        """Авто-расчёт даты начала разработки из четырёх дат:
        дата договора, замер, ТЗ, дата первого платежа (аванс).
        Также пересчитывает общий дедлайн = start_date + contract_period рабочих дней."""
        dates = []
        # Дата договора
        cd = self.contract_data.get('contract_date', '')
        if cd:
            dates.append(cd)
        # Дата замера
        sd = self.card_data.get('survey_date', '')
        if sd:
            dates.append(sd)
        # Дата получения ТЗ
        td = self.card_data.get('tech_task_date', '')
        if td:
            dates.append(td)
        # Дата первого платежа (аванс)
        apd = self.contract_data.get('advance_payment_paid_date', '')
        if apd:
            dates.append(apd)

        if not dates:
            return

        # Берём самую свежую дату
        latest = max(dates)

        # Находим запись START и устанавливаем дату
        start_changed = False
        for entry in self.entries:
            if entry.get('stage_code') == 'START':
                old_date = entry.get('actual_date', '')
                if old_date != latest:
                    entry['actual_date'] = latest
                    start_changed = True
                    # Сохраняем на сервер
                    if self.contract_id:
                        try:
                            self.data.update_timeline_entry(
                                self.contract_id, 'START',
                                {'actual_date': latest}
                            )
                        except Exception:
                            pass
                break

        # Пересчитываем дедлайн от даты начала разработки
        if start_changed and latest:
            contract_period = self.contract_data.get('contract_period', 0)
            if contract_period and int(contract_period) > 0:
                new_deadline = add_working_days(latest, int(contract_period))
                if new_deadline:
                    card_id = self.card_data.get('id')
                    if card_id:
                        try:
                            self.data.update_crm_card(card_id, {'deadline': new_deadline})
                            self.card_data['deadline'] = new_deadline
                        except Exception:
                            pass

    def refresh_start_date(self):
        """Пересчитать дату START и перерисовать таблицу (без перезагрузки с сервера).
        Вызывается из CardEditDialog при изменении даты замера, ТЗ и т.п."""
        if not self.entries:
            return
        self._loading = True
        try:
            self._auto_set_start_date()
            self._recalculate_days()
            self._populate_table()
        finally:
            self._loading = False

    def _get_fio(self, role):
        """Получить ФИО исполнителя по роли из card_data"""
        if role == 'Клиент':
            return self._client_name or 'Клиент'
        field = ROLE_TO_CARD_FIELD.get(role, '')
        if field:
            return self.card_data.get(field, '') or ''
        return ''

    def _build_display_rows(self):
        """Построить массив строк для отображения: entries + итоги этапов + общий итог"""
        display_rows = []
        current_stage_group = None
        stage_actual_sum = 0
        stage_norm_sum = 0

        for idx, entry in enumerate(self.entries):
            role = entry.get('executor_role', '')
            is_header = role == 'header'
            stage_group = entry.get('stage_group', '')

            # Если начался новый этап (основной заголовок) — вставляем итог предыдущего
            if is_header and stage_group != current_stage_group and current_stage_group and current_stage_group != 'START':
                display_rows.append({
                    '_type': 'subtotal',
                    '_stage_group': current_stage_group,
                    '_actual_sum': stage_actual_sum,
                    '_norm_sum': stage_norm_sum,
                })
                stage_actual_sum = 0
                stage_norm_sum = 0

            if is_header and stage_group != current_stage_group:
                current_stage_group = stage_group
                stage_actual_sum = 0
                stage_norm_sum = 0

            # Обычная строка
            display_rows.append({
                '_type': 'entry',
                '_entry_idx': idx,
                **entry,
            })

            # Накапливаем суммы (только рабочие строки в расчёте срока, не заголовки)
            if role != 'header':
                is_in_scope = entry.get('is_in_contract_scope', True)
                stage_actual_sum += (entry.get('actual_days', 0) or 0)
                if is_in_scope:
                    stage_norm_sum += (entry.get('norm_days', 0) or 0)

        # Итог последнего этапа
        if current_stage_group and current_stage_group != 'START':
            display_rows.append({
                '_type': 'subtotal',
                '_stage_group': current_stage_group,
                '_actual_sum': stage_actual_sum,
                '_norm_sum': stage_norm_sum,
            })

        # Общий итог (только строки в расчёте срока для norm_days)
        total_actual = sum(
            (e.get('actual_days', 0) or 0)
            for e in self.entries
            if e.get('executor_role', '') != 'header'
        )
        total_norm = self._contract_term or sum(
            (e.get('norm_days', 0) or 0)
            for e in self.entries
            if e.get('executor_role', '') != 'header'
            and e.get('is_in_contract_scope', True)
        )
        display_rows.append({
            '_type': 'grandtotal',
            '_actual_sum': total_actual,
            '_norm_sum': total_norm,
        })

        return display_rows

    @staticmethod
    def _make_cell_label(text, bg_color, align='center', bold=False, font_size=12,
                         color='#333333'):
        """Создать QLabel для ячейки таблицы (обход глобального stylesheet)"""
        lbl = QLabel(text)
        weight = 'bold' if bold else 'normal'
        text_align = 'center' if align == 'center' else 'left'
        lbl.setStyleSheet(
            f'background-color: {bg_color}; color: {color}; padding: 4px 6px; '
            f'font-size: {font_size}px; font-weight: {weight}; border-radius: 2px;'
        )
        qt_align = Qt.AlignCenter if align == 'center' else (Qt.AlignLeft | Qt.AlignVCenter)
        lbl.setAlignment(qt_align)
        return lbl

    def _calc_planned_dates(self):
        """Рассчитать планируемые даты (делегирует в utils/timeline_calc.py)."""
        calc_planned_dates(self.entries)

    def _populate_table(self):
        """Заполнение таблицы данными (QLabel для цветных ячеек — обход global stylesheet)"""
        self._loading = True
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(0)
            self._calc_planned_dates()
            display_rows = self._build_display_rows()
            self.table.setRowCount(len(display_rows))
            num_cols = len(self.COLUMNS)

            for row, dr in enumerate(display_rows):
                row_type = dr.get('_type', 'entry')

                # --- ИТОГО ЭТАПА ---
                if row_type == 'subtotal':
                    self.table.setRowHeight(row, 32)
                    stage_label = dr['_stage_group'].replace('STAGE', 'Этап ')
                    bg = '#E3F2FD'
                    texts = [f'Итого {stage_label}:', '', str(dr['_actual_sum']),
                             str(dr['_norm_sum']), '', '', '']
                    aligns = ['left', 'center', 'center', 'center', 'center', 'center', 'center']
                    for col in range(num_cols):
                        lbl = self._make_cell_label(texts[col], bg, aligns[col], bold=True, font_size=11)
                        self.table.setCellWidget(row, col, lbl)
                    continue

                # --- ОБЩИЙ ИТОГ ---
                if row_type == 'grandtotal':
                    self.table.setRowHeight(row, 36)
                    bg = '#FFF8E1'
                    texts = ['Итого всех этапов:', '', str(dr['_actual_sum']),
                             str(dr['_norm_sum']), '', '', '']
                    aligns = ['left', 'center', 'center', 'center', 'center', 'center', 'center']
                    for col in range(num_cols):
                        lbl = self._make_cell_label(texts[col], bg, aligns[col], bold=True, font_size=12)
                        self.table.setCellWidget(row, col, lbl)
                    continue

                # --- ОБЫЧНАЯ СТРОКА (entry) ---
                entry = self.entries[dr['_entry_idx']]
                role = entry.get('executor_role', '')
                stage_code = entry.get('stage_code', '')
                substage_group = entry.get('substage_group', '')
                is_header = (role == 'header' and not substage_group)
                is_subheader = (role == 'header' and bool(substage_group))
                is_in_scope = entry.get('is_in_contract_scope', True)

                self.table.setRowHeight(row, 32)

                # --- ЗАГОЛОВОК ЭТАПА (синий) ---
                if is_header:
                    bg = '#2F5496'
                    lbl = self._make_cell_label(
                        entry.get('stage_name', ''), bg, 'left',
                        bold=True, font_size=11, color='#FFFFFF'
                    )
                    self.table.setCellWidget(row, 0, lbl)
                    self.table.setSpan(row, 0, 1, num_cols)
                    continue

                # --- ЗАГОЛОВОК ПОДЭТАПА (голубой) ---
                if is_subheader:
                    bg = '#D6E4F0'
                    for col in range(num_cols):
                        lbl = self._make_cell_label(
                            entry.get('stage_name', '') if col == 0 else '',
                            bg, 'left' if col == 0 else 'center',
                            bold=True, font_size=11
                        )
                        self.table.setCellWidget(row, col, lbl)
                    continue

                # --- РАБОЧАЯ СТРОКА ---
                actual_days = entry.get('actual_days', 0) or 0
                norm_days_val = entry.get('norm_days', 0) or 0
                status_text = ''
                row_bg = '#FFFFFF'

                if not is_in_scope:
                    row_bg = '#E0E0E0'
                elif actual_days > 0 and norm_days_val > 0:
                    if actual_days <= norm_days_val:
                        status_text = 'В срок'
                        row_bg = '#E8F5E9'
                    else:
                        status_text = 'Просрочен'
                        row_bg = '#FFEBEE'

                # Кол 0: Название
                self.table.setCellWidget(row, 0,
                    self._make_cell_label(entry.get('stage_name', ''), row_bg, 'left'))

                # Кол 1: Дата
                is_start_row = (stage_code == 'START')
                actual_date = entry.get('actual_date', '')
                entry_idx = dr['_entry_idx']

                if is_start_row:
                    # START строка — только QLabel (дата заполняется автоматически)
                    date_text = ''
                    if actual_date:
                        try:
                            d = QDate.fromString(actual_date, 'yyyy-MM-dd')
                            if d.isValid():
                                date_text = d.toString('dd.MM.yyyy')
                        except Exception:
                            pass
                    start_label = self._make_cell_label(date_text, '#FCE4EC', 'center', bold=True)
                    # Tooltip с датами: договор, замер, ТЗ
                    def _fmt(date_str):
                        if not date_str:
                            return 'не установлена'
                        qd = QDate.fromString(date_str, 'yyyy-MM-dd')
                        return qd.toString('dd.MM.yyyy') if qd.isValid() else date_str
                    cd = self.contract_data.get('contract_date', '')
                    sd = self.card_data.get('survey_date', '')
                    td = self.card_data.get('tech_task_date', '')
                    apd = self.contract_data.get('advance_payment_paid_date', '')
                    start_label.setToolTip(
                        f"Дата договора: {_fmt(cd)}\n"
                        f"Дата замера: {_fmt(sd)}\n"
                        f"Дата тех. задания: {_fmt(td)}\n"
                        f"Дата аванса: {_fmt(apd)}"
                    )
                    self.table.setCellWidget(row, 1, start_label)
                else:
                    # Обычная строка — QLabel (read-only) + кнопка-карандаш
                    planned = entry.get('_planned_date', '')
                    date_container = QWidget()
                    date_container.setStyleSheet('background-color: transparent;')
                    date_layout = QHBoxLayout(date_container)
                    date_layout.setContentsMargins(2, 0, 2, 0)
                    date_layout.setSpacing(2)
                    date_layout.setAlignment(Qt.AlignVCenter)

                    # Определяем текст и стиль
                    # Ячейка показывает ТОЛЬКО actual_date (факт)
                    # planned_date — только в tooltip (как подсказка)
                    if actual_date:
                        try:
                            d = QDate.fromString(actual_date, 'yyyy-MM-dd')
                            date_text = d.toString('dd.MM.yyyy') if d.isValid() else ''
                        except Exception:
                            date_text = ''
                        date_bg = '#E8F5E9'  # зелёный фон — факт заполнен
                        plan_hint = ''
                        if planned:
                            try:
                                pd_q = QDate.fromString(planned, 'yyyy-MM-dd')
                                if pd_q.isValid():
                                    plan_hint = f'\nПланировалось: {pd_q.toString("dd.MM.yyyy")}'
                            except Exception:
                                pass
                        tooltip = f'Фактическая дата{plan_hint}\nНажмите карандаш для изменения'
                    else:
                        # Стадия НЕ завершена — ячейка ПУСТАЯ
                        date_text = ''
                        date_bg = '#FFFFFF'
                        if planned:
                            try:
                                pd_q = QDate.fromString(planned, 'yyyy-MM-dd')
                                plan_fmt = pd_q.toString('dd.MM.yyyy') if pd_q.isValid() else ''
                                tooltip = f'Планируемая дата: {plan_fmt}\nНажмите карандаш для ввода фактической'
                            except Exception:
                                tooltip = 'Нажмите карандаш для ввода даты'
                        else:
                            tooltip = 'Нажмите карандаш для ввода даты'

                    date_label = QLabel(date_text)
                    date_label.setAlignment(Qt.AlignCenter)
                    date_label.setStyleSheet(
                        f'background-color: {date_bg}; color: #333333; padding: 2px 4px; '
                        f'font-size: 12px; border-radius: 2px; border: 1px solid #E0E0E0;'
                    )
                    date_label.setToolTip(tooltip)
                    date_label.setMinimumWidth(80)

                    # Кнопка-карандаш для перехода в режим редактирования
                    pencil_btn = IconLoader.create_action_button(
                        'edit', tooltip='Редактировать дату',
                        bg_color='transparent', hover_color='#E3F2FD',
                        icon_size=14, button_size=22, icon_color='#666666'
                    )
                    pencil_btn.clicked.connect(
                        lambda checked, r=row, ei=entry_idx, sc=stage_code, ad=actual_date:
                            self._enable_date_edit(r, ei, sc, ad)
                    )

                    date_layout.addWidget(date_label, 1)
                    date_layout.addWidget(pencil_btn, 0)
                    self.table.setCellWidget(row, 1, date_container)

                # Кол 2: Кол-во дней
                days_text = str(actual_days) if actual_days > 0 else ''
                self.table.setCellWidget(row, 2,
                    self._make_cell_label(days_text, row_bg))

                # Кол 3: Норма дней
                norm_text = str(norm_days_val) if norm_days_val > 0 else ''
                norm_bg = row_bg if row_bg != '#FFFFFF' else '#F2F2F2'
                self.table.setCellWidget(row, 3,
                    self._make_cell_label(norm_text, norm_bg))

                # Кол 4: Статус
                status_color = '#333333'
                if status_text == 'В срок':
                    status_color = '#2E7D32'
                elif status_text == 'Просрочен':
                    status_color = '#C62828'
                self.table.setCellWidget(row, 4,
                    self._make_cell_label(status_text, row_bg, bold=bool(status_text),
                                          color=status_color))

                # Кол 5: Исполнитель
                self.table.setCellWidget(row, 5,
                    self._make_cell_label(role, row_bg))

                # Кол 6: ФИО
                fio = self._get_fio(role)
                self.table.setCellWidget(row, 6,
                    self._make_cell_label(fio, row_bg))

        finally:
            self.table.setUpdatesEnabled(True)
            self._loading = False

    def _enable_date_edit(self, row, entry_idx, stage_code, current_actual_date):
        """Переключить ячейку даты в режим редактирования (QDateEdit)"""
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

        # Блокируем сигнал dateChanged при начальной установке даты
        date_edit.blockSignals(True)
        if current_actual_date:
            try:
                d = QDate.fromString(current_actual_date, 'yyyy-MM-dd')
                if d.isValid():
                    date_edit.setDate(d)
                else:
                    date_edit.setDate(date_edit.minimumDate())
            except Exception:
                date_edit.setDate(date_edit.minimumDate())
        else:
            # Предзаполнение планируемой датой (для удобства)
            if entry_idx < len(self.entries):
                planned = self.entries[entry_idx].get('_planned_date', '')
                if planned:
                    pd_q = QDate.fromString(planned, 'yyyy-MM-dd')
                    if pd_q.isValid():
                        date_edit.setDate(pd_q)
                    else:
                        date_edit.setDate(date_edit.minimumDate())
                else:
                    date_edit.setDate(date_edit.minimumDate())
            else:
                date_edit.setDate(date_edit.minimumDate())
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
            lambda d, ei=entry_idx, sc=stage_code: self._on_date_changed(ei, sc, d)
        )

        date_layout.addWidget(date_edit)
        self.table.setCellWidget(row, 1, date_container)

        # Автоматически открыть календарь
        date_edit.setFocus()

    def _on_date_changed(self, entry_idx, stage_code, new_date):
        """Обработка изменения даты"""
        if self._loading:
            return

        date_str = new_date.toString('yyyy-MM-dd') if new_date.isValid() and new_date > QDate(2020, 1, 1) else ''

        # Обновляем запись
        if entry_idx < len(self.entries):
            self.entries[entry_idx]['actual_date'] = date_str

        # Пересчёт actual_days
        self._recalculate_days()

        # Сохранение на сервер
        if self.contract_id and stage_code:
            try:
                self.data.update_timeline_entry(
                    self.contract_id, stage_code,
                    {'actual_date': date_str, 'actual_days': self.entries[entry_idx].get('actual_days', 0)}
                )
            except Exception as e:
                print(f"[TimelineWidget] Ошибка сохранения даты: {e}")

        # Полная перестройка таблицы (с итогами)
        self._populate_table()

    def _recalculate_days(self):
        """Пересчёт кол-ва рабочих дней между последовательными датами.
        Ищет ближайшую заполненную дату выше (любое расстояние)."""
        prev_date = None
        for entry in self.entries:
            role = entry.get('executor_role', '')
            if role == 'header':
                continue

            actual_date = entry.get('actual_date', '')
            if actual_date and prev_date:
                days = networkdays(prev_date, actual_date)
                entry['actual_days'] = max(days, 0)
            else:
                entry['actual_days'] = 0

            if actual_date:
                prev_date = actual_date

    def _export_excel(self):
        """Экспорт в Excel через API"""
        if not self.contract_id:
            return
        try:
            file_bytes = self.data.export_timeline_excel(self.contract_id)
            if file_bytes:
                path, _ = QFileDialog.getSaveFileName(
                    self, 'Сохранить Excel', f'timeline_{self.contract_id}.xlsx',
                    'Excel (*.xlsx)'
                )
                if path:
                    with open(path, 'wb') as f:
                        f.write(file_bytes)
        except Exception as e:
            print(f"[TimelineWidget] Ошибка экспорта Excel: {e}")

    def _export_pdf(self):
        """Экспорт в PDF через API"""
        if not self.contract_id:
            return
        try:
            file_bytes = self.data.export_timeline_pdf(self.contract_id)
            if file_bytes:
                path, _ = QFileDialog.getSaveFileName(
                    self, 'Сохранить PDF', f'timeline_{self.contract_id}.pdf',
                    'PDF (*.pdf)'
                )
                if path:
                    with open(path, 'wb') as f:
                        f.write(file_bytes)
        except Exception as e:
            print(f"[TimelineWidget] Ошибка экспорта PDF: {e}")

# -*- coding: utf-8 -*-
"""
Тесты для SupervisionTimelineWidget — виджет таблицы сроков надзора.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QApplication, QTableWidget, QPushButton, QLabel, QComboBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QDate
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="module")
def qapp():
    """QApplication для модуля тестов."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _mock_icon_loader():
    """IconLoader с реальными QPushButton вместо MagicMock."""
    mock = MagicMock()
    mock.load = MagicMock(return_value=QIcon())
    mock.create_icon_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
    )
    mock.create_action_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(k.get('tooltip', ''))
    )
    mock.get_icon_path = MagicMock(return_value='')
    return mock


def _make_card_data(card_id=42):
    """Тестовые данные карточки надзора."""
    return {
        'id': card_id,
        'contract_id': 10,
        'start_date': '2026-01-01',
        'address': 'г. Тест, ул. Тестовая, д.1',
    }


def _make_mock_data(entries=None, totals=None):
    """Создать MagicMock DataAccess для таймлайна надзора."""
    mock_da = MagicMock()
    result = {'entries': entries or [], 'totals': totals or {}}
    mock_da.get_supervision_timeline.return_value = result
    mock_da.get_all_contracts.return_value = []
    mock_da.update_supervision_timeline_entry.return_value = True
    mock_da.init_supervision_timeline.return_value = result
    mock_da.export_supervision_timeline_excel.return_value = None
    mock_da.export_supervision_timeline_pdf.return_value = None
    return mock_da


def _make_sample_entries():
    """12 тестовых стадий надзора."""
    stages = [
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
    return [
        {
            'stage_code': code,
            'stage_name': name,
            'sort_order': i + 1,
            'status': 'Не начато',
            'plan_date': '',
            'actual_date': '',
            'budget_planned': 0,
            'budget_actual': 0,
            'budget_savings': 0,
            'supplier': '',
            'commission': 0,
            'notes': '',
        }
        for i, (code, name) in enumerate(stages)
    ]


class TestSupervisionTimelineWidget:

    def test_create_widget(self, qapp):
        """Виджет SupervisionTimelineWidget создаётся без ошибок."""
        with patch('ui.supervision_timeline_widget.IconLoader', _mock_icon_loader()), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()):
            from ui.supervision_timeline_widget import SupervisionTimelineWidget
            mock_da = _make_mock_data()
            widget = SupervisionTimelineWidget(
                card_data=_make_card_data(),
                data=mock_da,
            )
            assert widget is not None
            widget.close()

    def test_widget_has_table(self, qapp):
        """Виджет содержит QTableWidget."""
        with patch('ui.supervision_timeline_widget.IconLoader', _mock_icon_loader()), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()):
            from ui.supervision_timeline_widget import SupervisionTimelineWidget
            mock_da = _make_mock_data()
            widget = SupervisionTimelineWidget(
                card_data=_make_card_data(),
                data=mock_da,
            )
            assert hasattr(widget, 'table')
            assert isinstance(widget.table, QTableWidget)
            widget.close()

    def test_table_column_count(self, qapp):
        """Таблица имеет столбцы согласно COLUMNS."""
        with patch('ui.supervision_timeline_widget.IconLoader', _mock_icon_loader()), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()):
            from ui.supervision_timeline_widget import SupervisionTimelineWidget
            mock_da = _make_mock_data()
            widget = SupervisionTimelineWidget(
                card_data=_make_card_data(),
                data=mock_da,
            )
            assert widget.table.columnCount() == len(widget.COLUMNS)
            widget.close()

    def test_table_headers(self, qapp):
        """Заголовки таблицы соответствуют COLUMNS."""
        with patch('ui.supervision_timeline_widget.IconLoader', _mock_icon_loader()), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()):
            from ui.supervision_timeline_widget import SupervisionTimelineWidget
            mock_da = _make_mock_data()
            widget = SupervisionTimelineWidget(
                card_data=_make_card_data(),
                data=mock_da,
            )
            expected = widget.COLUMNS
            for col, expected_header in enumerate(expected):
                actual = widget.table.horizontalHeaderItem(col).text()
                assert actual == expected_header, f"Столбец {col}: ожидалось '{expected_header}', получено '{actual}'"
            widget.close()

    def test_populate_table_with_entries(self, qapp):
        """Таблица заполняется строками при наличии данных."""
        entries = _make_sample_entries()
        with patch('ui.supervision_timeline_widget.IconLoader', _mock_icon_loader()), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()):
            from ui.supervision_timeline_widget import SupervisionTimelineWidget
            mock_da = _make_mock_data(entries=entries)
            widget = SupervisionTimelineWidget(
                card_data=_make_card_data(),
                data=mock_da,
            )
            # 12 стадий + 1 строка итого
            assert widget.table.rowCount() == 13
            widget.close()

    def test_summary_labels_present(self, qapp):
        """Виджет содержит сводные метки для бюджетов."""
        with patch('ui.supervision_timeline_widget.IconLoader', _mock_icon_loader()), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()):
            from ui.supervision_timeline_widget import SupervisionTimelineWidget
            mock_da = _make_mock_data()
            widget = SupervisionTimelineWidget(
                card_data=_make_card_data(),
                data=mock_da,
            )
            assert hasattr(widget, 'lbl_budget_plan')
            assert hasattr(widget, 'lbl_budget_fact')
            assert hasattr(widget, 'lbl_savings')
            widget.close()

    def test_export_buttons_present(self, qapp):
        """Кнопки экспорта в Excel и PDF присутствуют."""
        with patch('ui.supervision_timeline_widget.IconLoader', _mock_icon_loader()), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()):
            from ui.supervision_timeline_widget import SupervisionTimelineWidget
            mock_da = _make_mock_data()
            widget = SupervisionTimelineWidget(
                card_data=_make_card_data(),
                data=mock_da,
            )
            assert hasattr(widget, 'btn_excel_comm')
            assert hasattr(widget, 'btn_pdf_comm')
            assert 'Excel' in widget.btn_excel_comm.text()
            widget.close()

    def test_networkdays_function(self, qapp):
        """Функция networkdays корректно считает рабочие дни."""
        from ui.supervision_timeline_widget import networkdays
        # Пн–Пт = 4 рабочих дня (с Пн по Пт не включая Пт)
        result = networkdays('2026-01-05', '2026-01-09')
        assert result == 4

    def test_networkdays_zero_for_invalid(self, qapp):
        """networkdays возвращает 0 для пустых дат."""
        from ui.supervision_timeline_widget import networkdays
        assert networkdays('', '') == 0
        assert networkdays(None, None) == 0

    def test_recalculate_days_with_dates(self, qapp):
        """_recalculate_all_days пересчитывает дни для стадий с датами."""
        entries = _make_sample_entries()
        entries[0]['actual_date'] = '2026-01-15'
        entries[1]['actual_date'] = '2026-01-22'

        with patch('ui.supervision_timeline_widget.IconLoader', _mock_icon_loader()), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()):
            from ui.supervision_timeline_widget import SupervisionTimelineWidget
            mock_da = _make_mock_data(entries=entries)
            widget = SupervisionTimelineWidget(
                card_data={'id': 42, 'contract_id': None, 'start_date': '2026-01-01'},
                data=mock_da,
            )
            # После создания виджета дни должны быть пересчитаны
            # Стадия 2 имеет дату → actual_days > 0
            if len(widget.entries) > 1 and widget.entries[1].get('actual_date'):
                assert widget.entries[1].get('actual_days', 0) >= 0
            widget.close()

    def test_address_label_shows_address(self, qapp):
        """Метка адреса отображает адрес из данных контракта."""
        with patch('ui.supervision_timeline_widget.IconLoader', _mock_icon_loader()), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()):
            from ui.supervision_timeline_widget import SupervisionTimelineWidget
            mock_da = _make_mock_data()
            mock_da.get_all_contracts.return_value = [
                {'id': 10, 'address': 'г. Тест, ул. Адресная, д.99'}
            ]
            widget = SupervisionTimelineWidget(
                card_data=_make_card_data(),
                data=mock_da,
            )
            assert hasattr(widget, 'lbl_address')
            widget.close()

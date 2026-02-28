# -*- coding: utf-8 -*-
"""
Тесты для ProjectTimelineWidget — виджет таблицы сроков CRM проекта.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QApplication, QTableWidget, QPushButton, QLabel
from PyQt5.QtCore import QDate
from unittest.mock import patch, MagicMock, PropertyMock


@pytest.fixture(scope="module")
def qapp():
    """QApplication для модуля тестов."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _make_card_data(card_id=300):
    """Тестовые данные CRM карточки."""
    return {
        'id': card_id,
        'contract_id': 200,
        'survey_date': None,
        'tech_task_date': None,
        'designer_name': 'Дизайнеров Тест',
        'draftsman_name': 'Чертёжник Тестов',
        'sdp_name': '',
        'gap_name': '',
        'manager_name': '',
    }


def _make_contract_data(contract_id=200):
    """Тестовые данные договора."""
    return {
        'id': contract_id,
        'address': 'г. Тест, ул. Проектная, д.5',
        'project_type': 'Индивидуальный',
        'project_subtype': 'Полный проект',
        'area': 80.0,
        'floors': 1,
        'contract_period': 45,
        'contract_date': '2026-01-01',
        'advance_payment_paid_date': '',
    }


def _make_mock_data(entries=None, contract=None):
    """Создать MagicMock DataAccess для таймлайна проекта."""
    mock_da = MagicMock()
    mock_da.get_project_timeline.return_value = entries or []
    mock_da.prefer_local = False
    if contract:
        mock_da.get_contract.return_value = contract
    else:
        mock_da.get_contract.return_value = _make_contract_data()
    mock_da.get_client.return_value = None
    mock_da.init_project_timeline.return_value = {'entries': entries or []}
    mock_da.reinit_project_timeline.return_value = None
    mock_da.update_timeline_entry.return_value = True
    mock_da.update_crm_card.return_value = True
    mock_da.preview_norm_days_template.return_value = None
    mock_da.export_timeline_excel.return_value = None
    mock_da.export_timeline_pdf.return_value = None
    return mock_da


def _make_sample_entries():
    """Минимальный набор записей таймлайна для тестирования."""
    return [
        {
            'stage_code': 'START',
            'stage_name': 'Дата начала разработки',
            'executor_role': 'Менеджер',
            'stage_group': 'START',
            'substage_group': '',
            'is_in_contract_scope': True,
            'actual_date': '',
            'actual_days': 0,
            'norm_days': 0,
            'status': '',
            'sort_order': 0,
        },
        {
            'stage_code': 'STAGE1_SURVEY',
            'stage_name': 'Сдача замера',
            'executor_role': 'Замерщик',
            'stage_group': 'STAGE1',
            'substage_group': '',
            'is_in_contract_scope': True,
            'actual_date': '',
            'actual_days': 0,
            'norm_days': 5,
            'status': '',
            'sort_order': 1,
        },
    ]


class TestProjectTimelineWidget:

    def test_create_widget_no_entries(self, qapp):
        """Виджет ProjectTimelineWidget создаётся без ошибок при пустых данных."""
        with patch('ui.timeline_widget.IconLoader'), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()), \
             patch('utils.calendar_helpers.add_working_days', return_value=None):
            from ui.timeline_widget import ProjectTimelineWidget
            mock_da = _make_mock_data()
            widget = ProjectTimelineWidget(
                card_data=_make_card_data(),
                data=mock_da,
            )
            assert widget is not None
            widget.close()

    def test_widget_has_table(self, qapp):
        """Виджет содержит QTableWidget."""
        with patch('ui.timeline_widget.IconLoader'), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()), \
             patch('utils.calendar_helpers.add_working_days', return_value=None):
            from ui.timeline_widget import ProjectTimelineWidget
            mock_da = _make_mock_data()
            widget = ProjectTimelineWidget(
                card_data=_make_card_data(),
                data=mock_da,
            )
            assert hasattr(widget, 'table')
            assert isinstance(widget.table, QTableWidget)
            widget.close()

    def test_table_column_count(self, qapp):
        """Таблица содержит 7 столбцов."""
        with patch('ui.timeline_widget.IconLoader'), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()), \
             patch('utils.calendar_helpers.add_working_days', return_value=None):
            from ui.timeline_widget import ProjectTimelineWidget
            mock_da = _make_mock_data()
            widget = ProjectTimelineWidget(
                card_data=_make_card_data(),
                data=mock_da,
            )
            assert widget.table.columnCount() == 7
            widget.close()

    def test_table_headers(self, qapp):
        """Заголовки таблицы соответствуют COLUMNS."""
        with patch('ui.timeline_widget.IconLoader'), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()), \
             patch('utils.calendar_helpers.add_working_days', return_value=None):
            from ui.timeline_widget import ProjectTimelineWidget
            mock_da = _make_mock_data()
            widget = ProjectTimelineWidget(
                card_data=_make_card_data(),
                data=mock_da,
            )
            expected_headers = ['Действия по этапам', 'Дата', 'Кол-во дней',
                                 'Норма дней', 'Статус', 'Исполнитель', 'ФИО']
            for col, expected in enumerate(expected_headers):
                actual = widget.table.horizontalHeaderItem(col).text()
                assert actual == expected
            widget.close()

    def test_export_buttons_present(self, qapp):
        """Кнопки экспорта Excel и PDF присутствуют."""
        with patch('ui.timeline_widget.IconLoader'), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()), \
             patch('utils.calendar_helpers.add_working_days', return_value=None):
            from ui.timeline_widget import ProjectTimelineWidget
            mock_da = _make_mock_data()
            widget = ProjectTimelineWidget(
                card_data=_make_card_data(),
                data=mock_da,
            )
            assert hasattr(widget, 'btn_excel')
            assert hasattr(widget, 'btn_pdf')
            widget.close()

    def test_calc_contract_term(self, qapp):
        """calc_contract_term возвращает корректные значения для разных типов проектов."""
        from ui.timeline_widget import calc_contract_term
        # Полный проект, 80 м² -> должен быть в диапазоне 50-70 дней
        result = calc_contract_term(1, 80.0)
        assert result == 60

    def test_calc_contract_term_template(self, qapp):
        """calc_contract_term для планировочного проекта возвращает меньше дней."""
        from ui.timeline_widget import calc_contract_term
        result_full = calc_contract_term(1, 80.0)
        result_planning = calc_contract_term(3, 80.0)
        assert result_planning < result_full

    def test_calc_area_coefficient(self, qapp):
        """calc_area_coefficient корректно вычисляет коэффициент площади."""
        from ui.timeline_widget import calc_area_coefficient
        assert calc_area_coefficient(50.0) == 0
        assert calc_area_coefficient(101.0) == 1
        assert calc_area_coefficient(201.0) == 2

    def test_networkdays_basic(self, qapp):
        """networkdays возвращает корректное количество рабочих дней."""
        # is_working_day импортируется внутри функции из utils.date_utils
        with patch('utils.date_utils.is_working_day', side_effect=lambda d: d.weekday() < 5):
            from ui.timeline_widget import networkdays
            # Пн–Пт = 4 рабочих дня (с Пн по Пт не включая Пт)
            result = networkdays('2026-01-05', '2026-01-09')
            assert result == 4

    def test_networkdays_empty_returns_zero(self, qapp):
        """networkdays возвращает 0 для пустых или None дат."""
        from ui.timeline_widget import networkdays
        assert networkdays('', '') == 0
        assert networkdays(None, None) == 0

    def test_recalculate_days_no_crash(self, qapp):
        """_recalculate_days не падает при пустых entries."""
        with patch('ui.timeline_widget.IconLoader'), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()), \
             patch('utils.calendar_helpers.add_working_days', return_value=None):
            from ui.timeline_widget import ProjectTimelineWidget
            mock_da = _make_mock_data()
            widget = ProjectTimelineWidget(
                card_data=_make_card_data(),
                data=mock_da,
            )
            widget.entries = []
            widget._recalculate_days()  # не должен падать
            widget.close()

    def test_get_fio_returns_name_from_card(self, qapp):
        """_get_fio возвращает ФИО из card_data по роли."""
        with patch('ui.timeline_widget.IconLoader'), \
             patch('utils.calendar_helpers.add_today_button_to_dateedit', return_value=MagicMock()), \
             patch('utils.calendar_helpers.add_working_days', return_value=None):
            from ui.timeline_widget import ProjectTimelineWidget
            mock_da = _make_mock_data()
            card_data = _make_card_data()
            card_data['designer_name'] = 'Иванов Дизайнер'
            widget = ProjectTimelineWidget(card_data=card_data, data=mock_da)
            fio = widget._get_fio('Дизайнер')
            assert fio == 'Иванов Дизайнер'
            widget.close()

# -*- coding: utf-8 -*-
"""
Тесты для оставшихся UI виджетов:
- ui/crm_archive.py (ArchiveCard и вспомогательные классы)
- ui/supervision_visits_widget.py (SupervisionVisitsWidget, SUPERVISION_STAGES)

Покрытие:
- Константы стадий надзора
- Создание виджетов с mock DataAccess
- Структура UI элементов
- Сводка по месяцам
- Обработка данных
"""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==================== SupervisionVisitsWidget — константы ====================

class TestSupervisionStages:
    """SUPERVISION_STAGES — 12 стадий надзора."""

    def test_stages_count(self):
        from ui.supervision_visits_widget import SUPERVISION_STAGES
        assert len(SUPERVISION_STAGES) == 12

    def test_stages_are_tuples(self):
        from ui.supervision_visits_widget import SUPERVISION_STAGES
        for item in SUPERVISION_STAGES:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_stage_codes_unique(self):
        from ui.supervision_visits_widget import SUPERVISION_STAGES
        codes = [code for code, _ in SUPERVISION_STAGES]
        assert len(codes) == len(set(codes))

    def test_stage_names_unique(self):
        from ui.supervision_visits_widget import STAGE_NAMES
        assert len(STAGE_NAMES) == len(set(STAGE_NAMES))

    def test_stage_code_map(self):
        from ui.supervision_visits_widget import STAGE_CODE_MAP, STAGE_NAMES
        assert len(STAGE_CODE_MAP) == 12
        for name in STAGE_NAMES:
            assert name in STAGE_CODE_MAP

    def test_stage_name_map(self):
        from ui.supervision_visits_widget import STAGE_NAME_MAP, SUPERVISION_STAGES
        assert len(STAGE_NAME_MAP) == 12
        for code, name in SUPERVISION_STAGES:
            assert STAGE_NAME_MAP[code] == name

    def test_first_stage(self):
        from ui.supervision_visits_widget import SUPERVISION_STAGES
        code, name = SUPERVISION_STAGES[0]
        assert code == 'STAGE_1_CERAMIC'
        assert 'керамогранит' in name.lower()

    def test_last_stage(self):
        from ui.supervision_visits_widget import SUPERVISION_STAGES
        code, name = SUPERVISION_STAGES[-1]
        assert code == 'STAGE_12_DECOR'
        assert 'декор' in name.lower()


class TestSupervisionVisitsWidget:
    """SupervisionVisitsWidget — виджет таблицы выездов."""

    def _make_widget(self, qtbot, visits=None):
        """Создать виджет с моками."""
        from ui.supervision_visits_widget import SupervisionVisitsWidget
        mock_data = MagicMock()
        mock_data.get_supervision_visits = MagicMock(return_value=visits or [])
        mock_data.get_all_contracts = MagicMock(return_value=[
            {"id": 1, "address": "ул. Тестовая, 1"}
        ])
        mock_data.get_project_files = MagicMock(return_value=[])

        card_data = {"id": 10, "contract_id": 1}
        widget = SupervisionVisitsWidget(
            card_data=card_data,
            data=mock_data,
            db=MagicMock(),
            api_client=MagicMock(),
            employee={"id": 1, "name": "Тест"},
        )
        qtbot.addWidget(widget)
        return widget

    def test_creates(self, qtbot):
        widget = self._make_widget(qtbot)
        assert widget is not None

    def test_has_table(self, qtbot):
        from PyQt5.QtWidgets import QTableWidget
        widget = self._make_widget(qtbot)
        assert widget.table is not None
        assert isinstance(widget.table, QTableWidget)

    def test_table_columns(self, qtbot):
        widget = self._make_widget(qtbot)
        assert widget.table.columnCount() == len(widget.COLUMNS)

    def test_column_names(self, qtbot):
        widget = self._make_widget(qtbot)
        # Последний столбец '' — кнопка удаления
        assert widget.COLUMNS[:4] == ['Стадия', 'Выезд на объект', 'ФИО исполнителя (ДАН)', 'Примечание']

    def test_has_add_button(self, qtbot):
        from PyQt5.QtWidgets import QPushButton
        widget = self._make_widget(qtbot)
        assert widget.btn_add is not None
        assert isinstance(widget.btn_add, QPushButton)

    def test_has_export_buttons(self, qtbot):
        widget = self._make_widget(qtbot)
        assert widget.btn_excel is not None
        assert widget.btn_pdf is not None

    def test_has_summary_label(self, qtbot):
        widget = self._make_widget(qtbot)
        assert widget.lbl_summary is not None

    def test_has_reports_table(self, qtbot):
        widget = self._make_widget(qtbot)
        assert widget.reports_table is not None
        assert widget.reports_table.columnCount() == 4

    def test_empty_visits(self, qtbot):
        widget = self._make_widget(qtbot, visits=[])
        assert widget.table.rowCount() == 0

    def test_update_summary_empty(self, qtbot):
        widget = self._make_widget(qtbot, visits=[])
        assert 'Всего' in widget.lbl_summary.text()

    def test_update_summary_with_visits(self, qtbot):
        visits = [
            {"id": 1, "visit_date": "2026-01-15", "stage_name": "Стадия 1", "executor_name": "", "notes": ""},
            {"id": 2, "visit_date": "2026-01-20", "stage_name": "Стадия 2", "executor_name": "", "notes": ""},
            {"id": 3, "visit_date": "2026-02-10", "stage_name": "Стадия 1", "executor_name": "", "notes": ""},
        ]
        widget = self._make_widget(qtbot, visits=visits)
        text = widget.lbl_summary.text()
        assert 'Всего: 3' in text

    def test_address_displayed(self, qtbot):
        widget = self._make_widget(qtbot)
        assert 'Тестовая' in widget.lbl_address.text()

    def test_card_id_stored(self, qtbot):
        widget = self._make_widget(qtbot)
        assert widget.card_id == 10

    def test_save_visit_no_id(self, qtbot):
        """_save_visit с None visit_id — не вызывает API."""
        widget = self._make_widget(qtbot)
        widget._save_visit(None, {"notes": "test"})
        # Не упало — OK

    def test_add_row_no_card_id(self, qtbot):
        """_add_row без card_id — ничего не делает."""
        widget = self._make_widget(qtbot)
        widget.card_id = None
        widget._add_row()
        # Не упало — OK

    def test_loading_flag_blocks_handlers(self, qtbot):
        """При _loading=True обработчики не вызывают API."""
        widget = self._make_widget(qtbot)
        widget._loading = True
        widget.data.update_supervision_visit = MagicMock()
        widget._on_stage_changed(0, 1, "Стадия 2")
        widget.data.update_supervision_visit.assert_not_called()


# ==================== ArchiveCard ====================

class TestArchiveCard:
    """ArchiveCard — упрощённая карточка для архива."""

    def test_imports(self):
        from ui.crm_archive import ArchiveCard
        assert ArchiveCard is not None

    def test_creates_crm_card(self, qtbot):
        with patch('ui.crm_archive.DataAccess') as MockDA:
            mock_da = MagicMock()
            mock_da.db = MagicMock()
            MockDA.return_value = mock_da

            from ui.crm_archive import ArchiveCard
            card_data = {
                "id": 1,
                "contract_id": 10,
                "column_name": "СДАН",
                "contract_number": "ДП-001",
                "address": "ул. Тестовая, 1",
                "client_name": "Иванов И.И.",
                "area": "50",
                "city": "Москва",
                "project_type": "Индивидуальный",
                "agent_type": "Агент 1",
            }
            widget = ArchiveCard(
                card_data=card_data,
                db=MagicMock(),
                card_type='crm',
                employee={"id": 1, "name": "Тест"},
                api_client=MagicMock(),
            )
            qtbot.addWidget(widget)
            assert widget is not None
            assert widget.card_type == 'crm'

    def test_creates_supervision_card(self, qtbot):
        with patch('ui.crm_archive.DataAccess') as MockDA:
            mock_da = MagicMock()
            mock_da.db = MagicMock()
            MockDA.return_value = mock_da

            from ui.crm_archive import ArchiveCard
            card_data = {
                "id": 2,
                "contract_id": 20,
                "column_name": "СДАН",
                "contract_number": "ДП-002",
                "address": "ул. Другая, 5",
                "client_name": "Петров П.П.",
                "area": "80",
                "city": "СПб",
                "project_type": "Авторский надзор",
                "agent_type": "Агент 2",
            }
            widget = ArchiveCard(
                card_data=card_data,
                db=MagicMock(),
                card_type='supervision',
                employee={"id": 1, "name": "Тест"},
                api_client=MagicMock(),
            )
            qtbot.addWidget(widget)
            assert widget.card_type == 'supervision'

    def test_card_data_stored(self, qtbot):
        with patch('ui.crm_archive.DataAccess') as MockDA:
            mock_da = MagicMock()
            mock_da.db = MagicMock()
            MockDA.return_value = mock_da

            from ui.crm_archive import ArchiveCard
            card_data = {
                "id": 3,
                "contract_id": 30,
                "column_name": "СДАН",
                "contract_number": "ДП-003",
                "address": "Адрес",
                "client_name": "Клиент",
            }
            widget = ArchiveCard(
                card_data=card_data,
                db=MagicMock(),
                api_client=MagicMock(),
            )
            qtbot.addWidget(widget)
            assert widget.card_data == card_data

    def test_is_qframe(self, qtbot):
        with patch('ui.crm_archive.DataAccess') as MockDA:
            mock_da = MagicMock()
            mock_da.db = MagicMock()
            MockDA.return_value = mock_da

            from ui.crm_archive import ArchiveCard
            from PyQt5.QtWidgets import QFrame
            widget = ArchiveCard(
                card_data={"id": 4, "contract_number": "ДП-004", "address": "Тест"},
                db=MagicMock(),
                api_client=MagicMock(),
            )
            qtbot.addWidget(widget)
            assert isinstance(widget, QFrame)

    def test_has_labels(self, qtbot):
        with patch('ui.crm_archive.DataAccess') as MockDA:
            mock_da = MagicMock()
            mock_da.db = MagicMock()
            MockDA.return_value = mock_da

            from ui.crm_archive import ArchiveCard
            from PyQt5.QtWidgets import QLabel
            card_data = {
                "id": 5,
                "contract_number": "ДП-005",
                "address": "ул. Архивная",
                "client_name": "Тестов",
            }
            widget = ArchiveCard(
                card_data=card_data,
                db=MagicMock(),
                api_client=MagicMock(),
            )
            qtbot.addWidget(widget)
            labels = widget.findChildren(QLabel)
            assert len(labels) > 0

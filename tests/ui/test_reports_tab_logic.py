# -*- coding: utf-8 -*-
"""
Покрытие ui/reports_tab.py — чистая бизнес-логика.
~25 тестов.

Тестируем ТОЛЬКО чистые функции и логику ReportsTab, не требующую QApplication:
- Преобразование периодов в метки месяцев
- Сбор фильтров
- Сброс фильтров
- Парсинг кеша для секций
- Формат KPI-значений
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ['QT_QPA_PLATFORM'] = 'offscreen'


# ──────────────────────────────────────────────────────────
# Хелперы
# ──────────────────────────────────────────────────────────

def _create_reports_tab():
    """Создать ReportsTab с моками — без реального QApplication"""
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    with patch('ui.reports_tab.DataAccess') as MockDA:
        mock_da = MagicMock()
        MockDA.return_value = mock_da
        mock_da.get_contract_years.return_value = [2024, 2025, 2026]
        mock_da.get_all_agents.return_value = [
            {"name": "Фестиваль", "color": "#F57C00"},
            {"name": "Петрович", "color": "#2196F3"},
        ]
        mock_da.get_cities.return_value = ["Москва", "СПб", "Казань"]

        from ui.reports_tab import ReportsTab
        employee = MagicMock()
        employee.role = "admin"
        tab = ReportsTab(employee=employee, api_client=None)
        tab.data_access = mock_da
        return tab, mock_da


# ──────────────────────────────────────────────────────────
# 1. _periods_to_labels
# ──────────────────────────────────────────────────────────

class TestPeriodsToLabels:
    """Тест преобразования периодов YYYY-MM в короткие метки"""

    def test_monthly_periods(self):
        tab, _ = _create_reports_tab()
        result = tab._periods_to_labels(["2025-01", "2025-02", "2025-12"])
        assert result == ["Янв", "Фев", "Дек"]

    def test_empty_periods(self):
        tab, _ = _create_reports_tab()
        result = tab._periods_to_labels([])
        assert result == []

    def test_invalid_period_format(self):
        tab, _ = _create_reports_tab()
        result = tab._periods_to_labels(["2025", "invalid", ""])
        assert result == ["2025", "invalid", ""]

    def test_mixed_valid_invalid(self):
        tab, _ = _create_reports_tab()
        result = tab._periods_to_labels(["2025-03", "bad", "2025-06"])
        assert result == ["Мар", "bad", "Июн"]

    def test_all_months(self):
        tab, _ = _create_reports_tab()
        periods = [f"2025-{m:02d}" for m in range(1, 13)]
        result = tab._periods_to_labels(periods)
        expected = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн",
                    "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
        assert result == expected

    def test_out_of_range_month(self):
        """Месяц > 12 — fallback на исходную строку"""
        tab, _ = _create_reports_tab()
        result = tab._periods_to_labels(["2025-13"])
        assert result == ["2025-13"]


# ──────────────────────────────────────────────────────────
# 2. _get_current_filters
# ──────────────────────────────────────────────────────────

class TestGetCurrentFilters:
    """Тест сбора текущих фильтров в словарь"""

    def test_all_filters_default(self):
        """Все фильтры по умолчанию = пустой словарь"""
        tab, _ = _create_reports_tab()
        filters = tab._get_current_filters()
        assert isinstance(filters, dict)
        # На индексе 0 все комбобоксы имеют "Все" → пустые фильтры
        assert "year" not in filters
        assert "quarter" not in filters
        assert "month" not in filters

    def test_year_filter_set(self):
        """Установка года"""
        tab, _ = _create_reports_tab()
        # Загружаем опции фильтра, чтобы "2025" появился в списке
        tab._load_filter_options()
        tab.filter_year.setCurrentText("2025")
        filters = tab._get_current_filters()
        assert filters.get("year") == 2025

    def test_quarter_filter_set(self):
        """Установка квартала"""
        tab, _ = _create_reports_tab()
        tab.filter_quarter.setCurrentText("Q2")
        filters = tab._get_current_filters()
        assert filters.get("quarter") == 2

    def test_month_filter_set(self):
        """Установка месяца"""
        tab, _ = _create_reports_tab()
        tab.filter_month.setCurrentIndex(3)  # Март
        filters = tab._get_current_filters()
        assert filters.get("month") == 3

    def test_agent_filter_set(self):
        """Установка агента"""
        tab, _ = _create_reports_tab()
        # Нужно загрузить опции фильтра
        tab._load_filter_options()
        tab.filter_agent.setCurrentText("Фестиваль")
        filters = tab._get_current_filters()
        assert filters.get("agent_type") == "Фестиваль"

    def test_project_type_filter_set(self):
        """Установка типа проекта"""
        tab, _ = _create_reports_tab()
        tab.filter_project_type.setCurrentText("Индивидуальный")
        filters = tab._get_current_filters()
        assert filters.get("project_type") == "Индивидуальный"

    def test_invalid_year_text(self):
        """Нечисловой год → не добавляется"""
        tab, _ = _create_reports_tab()
        tab.filter_year.setCurrentText("abc")
        filters = tab._get_current_filters()
        assert "year" not in filters


# ──────────────────────────────────────────────────────────
# 3. reset_filters
# ──────────────────────────────────────────────────────────

class TestResetFilters:
    """Тест сброса фильтров"""

    def test_reset_clears_all(self):
        """После сброса все фильтры в положении 0"""
        tab, _ = _create_reports_tab()
        # Загружаем опции фильтров (год, агенты, города)
        tab._load_filter_options()
        tab.filter_year.setCurrentText("2025")
        tab.filter_quarter.setCurrentText("Q3")
        tab.filter_month.setCurrentIndex(5)
        tab.reset_filters()

        assert tab.filter_year.currentIndex() == 0
        assert tab.filter_quarter.currentIndex() == 0
        assert tab.filter_month.currentIndex() == 0
        assert tab.filter_agent.currentIndex() == 0
        assert tab.filter_city.currentIndex() == 0
        assert tab.filter_project_type.currentIndex() == 0


# ──────────────────────────────────────────────────────────
# 4. _update_kpi_section — значения из кеша
# ──────────────────────────────────────────────────────────

class TestUpdateKPISection:
    """Тест обновления KPI-карточек из кеша"""

    def test_kpi_cards_updated_from_cache(self):
        tab, _ = _create_reports_tab()
        tab._cache = {
            "summary": {
                "total_clients": 100,
                "new_clients": 20,
                "returning_clients": 5,
                "total_contracts": 80,
                "total_amount": 5000000,
                "avg_amount": 62500,
                "total_area": 3000,
                "avg_area": 37,
                "by_agent": [],
                "trend_clients": 10,
                "trend_contracts": -3,
                "trend_amount": 15,
            }
        }
        tab._update_kpi_section()
        # Проверяем что карточки обновились (value_label.text())
        assert "100" in tab._kpi_cards["total_clients"].value_label.text()
        assert "20" in tab._kpi_cards["new_clients"].value_label.text()
        assert "80" in tab._kpi_cards["total_contracts"].value_label.text()

    def test_kpi_empty_cache(self):
        """Пустой кеш — карточки показывают 0"""
        tab, _ = _create_reports_tab()
        tab._cache = {"summary": {}}
        tab._update_kpi_section()
        assert "0" in tab._kpi_cards["total_clients"].value_label.text()


# ──────────────────────────────────────────────────────────
# 5. _update_clients_section — мини-дашборд
# ──────────────────────────────────────────────────────────

class TestUpdateClientsSection:
    """Тест обновления секции клиентов"""

    def test_mini_dashboard_values(self):
        tab, _ = _create_reports_tab()
        tab._cache = {
            "summary": {
                "total_clients": 50,
                "new_clients": 10,
                "returning_clients": 3,
            },
            "clients_dynamics": [
                {"period": "2025-01", "new_clients": 5, "returning_clients": 2,
                 "individual": 4, "legal": 3},
            ],
            "dist_agent": [
                {"name": "Петрович", "count": 10},
                {"name": "Фестиваль", "count": 20},
            ],
        }
        tab._update_clients_section()
        assert "50" in tab._mini_clients["total"].value_label.text()
        assert "10" in tab._mini_clients["new"].value_label.text()


# ──────────────────────────────────────────────────────────
# 6. _update_crm_section — мини-KPI
# ──────────────────────────────────────────────────────────

class TestUpdateCRMSection:
    """Тест обновления CRM секции"""

    def test_crm_mini_kpi_values(self):
        tab, _ = _create_reports_tab()
        tab._cache = {
            "crm_individual": {
                "on_time_stats": {
                    "projects_pct": 75.0,
                    "stages_pct": 82.0,
                    "avg_deviation_days": 3.2,
                },
                "paused_count": 2,
                "funnel": [],
                "stage_durations": [],
            },
            "crm_template": {},
        }
        tab._update_crm_section()
        assert "75" in tab._crm_individual["mini_cards"]["on_time_pct"].value_label.text()
        assert "82" in tab._crm_individual["mini_cards"]["stages_on_time_pct"].value_label.text()
        assert "2" in tab._crm_individual["mini_cards"]["paused"].value_label.text()


# ──────────────────────────────────────────────────────────
# 7. _update_supervision_section
# ──────────────────────────────────────────────────────────

class TestUpdateSupervisionSection:
    """Тест обновления секции авторского надзора"""

    def test_supervision_mini_dashboard(self):
        tab, _ = _create_reports_tab()
        tab._cache = {
            "supervision": {
                "total": 15,
                "active": 8,
                "by_project_type": {"individual": 9, "template": 6},
                "by_agent": [],
                "stages": [],
                "budget": {},
                "by_city": [],
                "defects": {"found": 5, "resolved": 4},
                "site_visits": 20,
            }
        }
        tab._update_supervision_section()
        assert "15" in tab._mini_supervision["total"].value_label.text()
        assert "8" in tab._mini_supervision["active"].value_label.text()
        assert "9" in tab._mini_supervision["individual"].value_label.text()
        assert "6" in tab._mini_supervision["template"].value_label.text()


# ──────────────────────────────────────────────────────────
# 8. ensure_data_loaded — ленивая загрузка
# ──────────────────────────────────────────────────────────

class TestEnsureDataLoaded:
    """Тест ленивой загрузки"""

    def test_first_call_triggers_load(self):
        tab, mock_da = _create_reports_tab()
        tab._data_loaded = False
        tab._loading = False
        # Мокаем reload_all_sections чтобы не запускать потоки
        tab.reload_all_sections = MagicMock()
        tab.ensure_data_loaded()
        tab.reload_all_sections.assert_called_once()

    def test_second_call_no_reload(self):
        tab, mock_da = _create_reports_tab()
        tab._data_loaded = True
        tab._loading = False
        tab.reload_all_sections = MagicMock()
        tab.ensure_data_loaded()
        tab.reload_all_sections.assert_not_called()

    def test_loading_in_progress_no_duplicate(self):
        tab, mock_da = _create_reports_tab()
        tab._data_loaded = False
        tab._loading = True
        tab.reload_all_sections = MagicMock()
        tab.ensure_data_loaded()
        tab.reload_all_sections.assert_not_called()

# -*- coding: utf-8 -*-
"""
Unit-тесты DataAccess — 6 новых методов отчётов.
Проверка API-first + fallback + offline логики.
"""
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture(autouse=True)
def mock_pyqt():
    """Мокаем PyQt5 сигналы для DataAccess"""
    with patch('utils.data_access.get_offline_manager', return_value=None):
        yield


def _make_data_access(mock_api=None, mock_db=None):
    """Создать DataAccess с моками"""
    from utils.data_access import DataAccess
    da = DataAccess.__new__(DataAccess)
    da.api_client = mock_api
    da.db = mock_db or MagicMock()
    da._is_online = mock_api is not None
    da.prefer_local = False
    return da


SAMPLE_SUMMARY = {
    "total_clients": 42,
    "new_clients": 10,
    "returning_clients": 5,
    "total_contracts": 30,
    "total_amount": 5000000,
    "avg_amount": 166666,
    "total_area": 2500,
    "avg_area": 83,
    "by_agent": [
        {"agent_name": "Фестиваль", "agent_color": "#F57C00", "clients": 20,
         "contracts": 15, "amount": 2500000, "area": 1200},
    ],
    "trend_clients": 10.5,
    "trend_contracts": -5.0,
    "trend_amount": 15.3,
}

SAMPLE_CLIENTS_DYNAMICS = [
    {"period": "2025-01", "new_clients": 5, "returning_clients": 2,
     "individual": 4, "legal": 3},
    {"period": "2025-02", "new_clients": 3, "returning_clients": 1,
     "individual": 2, "legal": 2},
]

SAMPLE_CONTRACTS_DYNAMICS = [
    {"period": "2025-01", "individual_count": 5, "template_count": 3,
     "supervision_count": 1, "total_amount": 1000000},
]

SAMPLE_CRM_ANALYTICS = {
    "funnel": [{"stage": "Замеры", "count": 10}, {"stage": "Дизайн", "count": 8}],
    "on_time_stats": {"projects_pct": 75.0, "stages_pct": 82.0, "avg_deviation_days": 3.2},
    "stage_durations": [{"stage": "Замеры", "avg_actual_days": 5.0, "norm_days": 4}],
    "paused_count": 2,
}

SAMPLE_SUPERVISION = {
    "total": 15,
    "active": 8,
    "stages": [{"stage": "Закупка 1", "active": 3, "completed": 5}],
    "by_agent": [{"agent_name": "Фестиваль", "agent_color": "#F57C00", "count": 10}],
    "by_city": [{"city": "Москва", "count": 7}],
    "by_project_type": {"individual": 9, "template": 6},
    "budget": {"total_planned": 1000000, "total_actual": 900000, "total_savings": 100000,
               "savings_pct": 10.0},
    "defects": {"found": 5, "resolved": 4},
    "site_visits": 20,
}

SAMPLE_DISTRIBUTION = [
    {"name": "Москва", "count": 15, "amount": 3000000, "area": 1000},
    {"name": "СПб", "count": 10, "amount": 2000000, "area": 800},
]


# ============================================================================
# API доступен → читаем из API
# ============================================================================

class TestReportsFromAPI:
    """Когда API доступен, DataAccess читает из API"""

    @pytest.fixture
    def mock_api(self):
        api = MagicMock()
        api.is_online = True
        api.get_reports_summary.return_value = SAMPLE_SUMMARY
        api.get_reports_clients_dynamics.return_value = SAMPLE_CLIENTS_DYNAMICS
        api.get_reports_contracts_dynamics.return_value = SAMPLE_CONTRACTS_DYNAMICS
        api.get_reports_crm_analytics.return_value = SAMPLE_CRM_ANALYTICS
        api.get_reports_supervision_analytics.return_value = SAMPLE_SUPERVISION
        api.get_reports_distribution.return_value = SAMPLE_DISTRIBUTION
        return api

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_get_reports_summary_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_reports_summary(year=2025)
        assert result == SAMPLE_SUMMARY
        mock_api.get_reports_summary.assert_called_once_with(year=2025)
        mock_db.get_reports_summary.assert_not_called()

    def test_get_reports_clients_dynamics_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_reports_clients_dynamics(year=2025)
        assert result == SAMPLE_CLIENTS_DYNAMICS
        mock_api.get_reports_clients_dynamics.assert_called_once_with(year=2025)
        mock_db.get_reports_clients_dynamics.assert_not_called()

    def test_get_reports_contracts_dynamics_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_reports_contracts_dynamics(year=2025, agent_type="Фестиваль")
        assert result == SAMPLE_CONTRACTS_DYNAMICS
        mock_api.get_reports_contracts_dynamics.assert_called_once_with(
            year=2025, agent_type="Фестиваль"
        )

    def test_get_reports_crm_analytics_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_reports_crm_analytics(project_type="Индивидуальный")
        assert result == SAMPLE_CRM_ANALYTICS
        mock_api.get_reports_crm_analytics.assert_called_once_with(
            project_type="Индивидуальный"
        )

    def test_get_reports_supervision_analytics_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_reports_supervision_analytics(year=2025, quarter=1)
        assert result == SAMPLE_SUPERVISION
        mock_api.get_reports_supervision_analytics.assert_called_once_with(
            year=2025, quarter=1
        )

    def test_get_reports_distribution_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_reports_distribution("city", year=2025)
        assert result == SAMPLE_DISTRIBUTION
        mock_api.get_reports_distribution.assert_called_once_with("city", year=2025)


# ============================================================================
# API недоступен → fallback на DB
# ============================================================================

class TestReportsFallbackToDB:
    """Когда API бросает ошибку, DataAccess использует fallback на локальную БД"""

    @pytest.fixture
    def mock_api_failing(self):
        api = MagicMock()
        api.is_online = True
        api.get_reports_summary.return_value = None  # API вернул None
        api.get_reports_clients_dynamics.return_value = None
        api.get_reports_contracts_dynamics.return_value = None
        api.get_reports_crm_analytics.return_value = None
        api.get_reports_supervision_analytics.return_value = None
        api.get_reports_distribution.return_value = None
        return api

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.get_reports_summary.return_value = SAMPLE_SUMMARY
        db.get_reports_clients_dynamics.return_value = SAMPLE_CLIENTS_DYNAMICS
        db.get_reports_contracts_dynamics.return_value = SAMPLE_CONTRACTS_DYNAMICS
        db.get_reports_crm_analytics.return_value = SAMPLE_CRM_ANALYTICS
        db.get_reports_supervision_analytics.return_value = SAMPLE_SUPERVISION
        db.get_reports_distribution.return_value = SAMPLE_DISTRIBUTION
        return db

    def test_fallback_summary(self, mock_api_failing, mock_db):
        da = _make_data_access(mock_api_failing, mock_db)
        result = da.get_reports_summary()
        assert result == SAMPLE_SUMMARY
        mock_db.get_reports_summary.assert_called_once()

    def test_fallback_clients_dynamics(self, mock_api_failing, mock_db):
        da = _make_data_access(mock_api_failing, mock_db)
        result = da.get_reports_clients_dynamics()
        assert result == SAMPLE_CLIENTS_DYNAMICS
        mock_db.get_reports_clients_dynamics.assert_called_once()

    def test_fallback_contracts_dynamics(self, mock_api_failing, mock_db):
        da = _make_data_access(mock_api_failing, mock_db)
        result = da.get_reports_contracts_dynamics()
        assert result == SAMPLE_CONTRACTS_DYNAMICS
        mock_db.get_reports_contracts_dynamics.assert_called_once()

    def test_fallback_crm_analytics(self, mock_api_failing, mock_db):
        da = _make_data_access(mock_api_failing, mock_db)
        result = da.get_reports_crm_analytics()
        assert result == SAMPLE_CRM_ANALYTICS
        mock_db.get_reports_crm_analytics.assert_called_once()

    def test_fallback_supervision(self, mock_api_failing, mock_db):
        da = _make_data_access(mock_api_failing, mock_db)
        result = da.get_reports_supervision_analytics()
        assert result == SAMPLE_SUPERVISION
        mock_db.get_reports_supervision_analytics.assert_called_once()

    def test_fallback_distribution(self, mock_api_failing, mock_db):
        da = _make_data_access(mock_api_failing, mock_db)
        result = da.get_reports_distribution("city")
        assert result == SAMPLE_DISTRIBUTION
        mock_db.get_reports_distribution.assert_called_once()


# ============================================================================
# Без API (offline) → только DB
# ============================================================================

class TestReportsOffline:
    """Без api_client DataAccess использует только локальную БД"""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.get_reports_summary.return_value = SAMPLE_SUMMARY
        db.get_reports_clients_dynamics.return_value = SAMPLE_CLIENTS_DYNAMICS
        db.get_reports_contracts_dynamics.return_value = SAMPLE_CONTRACTS_DYNAMICS
        db.get_reports_crm_analytics.return_value = SAMPLE_CRM_ANALYTICS
        db.get_reports_supervision_analytics.return_value = SAMPLE_SUPERVISION
        db.get_reports_distribution.return_value = SAMPLE_DISTRIBUTION
        return db

    def test_offline_summary(self, mock_db):
        da = _make_data_access(mock_api=None, mock_db=mock_db)
        result = da.get_reports_summary(year=2025)
        assert result == SAMPLE_SUMMARY
        mock_db.get_reports_summary.assert_called_once_with(year=2025)

    def test_offline_clients_dynamics(self, mock_db):
        da = _make_data_access(mock_api=None, mock_db=mock_db)
        result = da.get_reports_clients_dynamics()
        assert result == SAMPLE_CLIENTS_DYNAMICS

    def test_offline_contracts_dynamics(self, mock_db):
        da = _make_data_access(mock_api=None, mock_db=mock_db)
        result = da.get_reports_contracts_dynamics()
        assert result == SAMPLE_CONTRACTS_DYNAMICS

    def test_offline_crm_analytics(self, mock_db):
        da = _make_data_access(mock_api=None, mock_db=mock_db)
        result = da.get_reports_crm_analytics(project_type="Шаблонный")
        assert result == SAMPLE_CRM_ANALYTICS

    def test_offline_supervision(self, mock_db):
        da = _make_data_access(mock_api=None, mock_db=mock_db)
        result = da.get_reports_supervision_analytics()
        assert result == SAMPLE_SUPERVISION

    def test_offline_distribution(self, mock_db):
        da = _make_data_access(mock_api=None, mock_db=mock_db)
        result = da.get_reports_distribution("agent")
        assert result == SAMPLE_DISTRIBUTION


# ============================================================================
# Оба слоя бросают ошибку → пустой ответ
# ============================================================================

class TestReportsBothFail:
    """Когда и API, и DB бросают ошибку, возвращается пустой словарь"""

    @pytest.fixture
    def mock_api_error(self):
        api = MagicMock()
        api.is_online = True
        api.get_reports_summary.side_effect = Exception("API error")
        api.get_reports_clients_dynamics.side_effect = Exception("API error")
        api.get_reports_contracts_dynamics.side_effect = Exception("API error")
        api.get_reports_crm_analytics.side_effect = Exception("API error")
        api.get_reports_supervision_analytics.side_effect = Exception("API error")
        api.get_reports_distribution.side_effect = Exception("API error")
        return api

    @pytest.fixture
    def mock_db_error(self):
        db = MagicMock()
        db.get_reports_summary.side_effect = Exception("DB error")
        db.get_reports_clients_dynamics.side_effect = Exception("DB error")
        db.get_reports_contracts_dynamics.side_effect = Exception("DB error")
        db.get_reports_crm_analytics.side_effect = Exception("DB error")
        db.get_reports_supervision_analytics.side_effect = Exception("DB error")
        db.get_reports_distribution.side_effect = Exception("DB error")
        return db

    def test_both_fail_summary(self, mock_api_error, mock_db_error):
        da = _make_data_access(mock_api_error, mock_db_error)
        result = da.get_reports_summary()
        assert result == {} or result is None

    def test_both_fail_clients_dynamics(self, mock_api_error, mock_db_error):
        da = _make_data_access(mock_api_error, mock_db_error)
        result = da.get_reports_clients_dynamics()
        assert result == {} or result is None

    def test_both_fail_distribution(self, mock_api_error, mock_db_error):
        da = _make_data_access(mock_api_error, mock_db_error)
        result = da.get_reports_distribution("city")
        assert result == {} or result is None


# ============================================================================
# Передача параметров — kwargs проксируются правильно
# ============================================================================

class TestReportsKwargsProxy:
    """Проверка передачи параметров между слоями"""

    @pytest.fixture
    def mock_api(self):
        api = MagicMock()
        api.is_online = True
        api.get_reports_summary.return_value = SAMPLE_SUMMARY
        api.get_reports_clients_dynamics.return_value = SAMPLE_CLIENTS_DYNAMICS
        api.get_reports_contracts_dynamics.return_value = SAMPLE_CONTRACTS_DYNAMICS
        api.get_reports_crm_analytics.return_value = SAMPLE_CRM_ANALYTICS
        api.get_reports_supervision_analytics.return_value = SAMPLE_SUPERVISION
        api.get_reports_distribution.return_value = SAMPLE_DISTRIBUTION
        return api

    def test_summary_passes_all_filters(self, mock_api):
        da = _make_data_access(mock_api)
        da.get_reports_summary(
            year=2025, quarter=2, month=6,
            agent_type="Петрович", city="Москва", project_type="Шаблонный"
        )
        mock_api.get_reports_summary.assert_called_once_with(
            year=2025, quarter=2, month=6,
            agent_type="Петрович", city="Москва", project_type="Шаблонный"
        )

    def test_distribution_passes_dimension(self, mock_api):
        da = _make_data_access(mock_api)
        da.get_reports_distribution("agent", year=2025, quarter=3)
        mock_api.get_reports_distribution.assert_called_once_with(
            "agent", year=2025, quarter=3
        )

    def test_crm_analytics_passes_project_type(self, mock_api):
        da = _make_data_access(mock_api)
        da.get_reports_crm_analytics(project_type="Шаблонный", year=2025, month=1)
        mock_api.get_reports_crm_analytics.assert_called_once_with(
            project_type="Шаблонный", year=2025, month=1
        )

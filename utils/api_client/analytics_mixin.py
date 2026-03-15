# -*- coding: utf-8 -*-
"""Миксин API-клиента для аналитики сотрудников и опросов."""
from typing import Optional, Dict, List, Any


class AnalyticsMixin:

    # ── Аналитика сотрудников ────────────────────────────────────────

    def get_analytics_dashboard(self, project_type: str,
                                year: int = None, quarter: int = None,
                                month: int = None) -> Dict[str, Any]:
        """GET /api/v1/employee-analytics/dashboard"""
        params = {'project_type': project_type}
        if year:
            params['year'] = year
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/employee-analytics/dashboard",
            params=params
        )
        return self._handle_response(response)

    def get_analytics_by_role(self, role_code: str, project_type: str,
                              year: int = None, quarter: int = None,
                              month: int = None) -> Dict[str, Any]:
        """GET /api/v1/employee-analytics/role/{role_code}"""
        params = {'project_type': project_type}
        if year:
            params['year'] = year
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/employee-analytics/role/{role_code}",
            params=params
        )
        return self._handle_response(response)

    def get_analytics_employee_detail(self, employee_id: int,
                                      project_type: str,
                                      year: int = None,
                                      quarter: int = None,
                                      month: int = None) -> Dict[str, Any]:
        """GET /api/v1/employee-analytics/{employee_id}/detail"""
        params = {'project_type': project_type}
        if year:
            params['year'] = year
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/employee-analytics/{employee_id}/detail",
            params=params
        )
        return self._handle_response(response)

    # ── Опросы ────────────────────────────────────────────────────────

    def create_survey(self, contract_id: int, project_type: str) -> Dict[str, Any]:
        """POST /api/surveys/create"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/surveys/create",
            json={'contract_id': contract_id, 'project_type': project_type}
        )
        return self._handle_response(response)

    def get_surveys_by_contract(self, contract_id: int,
                                project_type: str = None) -> List[Dict[str, Any]]:
        """GET /api/surveys/contract/{contract_id}"""
        params = {}
        if project_type:
            params['project_type'] = project_type
        response = self._request(
            'GET',
            f"{self.base_url}/api/surveys/contract/{contract_id}",
            params=params
        )
        return self._handle_response(response)

    def resend_survey(self, survey_id: int) -> Dict[str, Any]:
        """POST /api/surveys/{survey_id}/resend"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/surveys/{survey_id}/resend"
        )
        return self._handle_response(response)

    def get_survey_stats(self, project_type: str = None) -> Dict[str, Any]:
        """GET /api/surveys/stats"""
        params = {}
        if project_type:
            params['project_type'] = project_type
        response = self._request(
            'GET',
            f"{self.base_url}/api/surveys/stats",
            params=params
        )
        return self._handle_response(response)

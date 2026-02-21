from typing import Optional, List, Dict, Any


class SalariesMixin:

    def get_salaries(self, report_month: str = None, employee_id: int = None) -> List[Dict[str, Any]]:
        """Получить зарплаты"""
        params = {}
        if report_month:
            params['report_month'] = report_month
        if employee_id:
            params['employee_id'] = employee_id
        response = self._request(
            'GET',
            f"{self.base_url}/api/salaries",
            params=params
        )
        return self._handle_response(response)

    def get_salary(self, salary_id: int) -> Dict[str, Any]:
        """Получить зарплату по ID"""
        response = self._request('GET', f"{self.base_url}/api/salaries/{salary_id}")
        return self._handle_response(response)

    def create_salary(self, salary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать запись о зарплате"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/salaries",
            json=salary_data
        )
        return self._handle_response(response)

    def update_salary(self, salary_id: int, salary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить запись о зарплате"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/salaries/{salary_id}",
            json=salary_data
        )
        return self._handle_response(response)

    def delete_salary(self, salary_id: int) -> bool:
        """Удалить запись о зарплате"""
        response = self._request('DELETE', f"{self.base_url}/api/salaries/{salary_id}")
        self._handle_response(response)
        return True

    def get_salary_report(self, report_month: str = None, employee_id: int = None, payment_type: str = None) -> Dict[str, Any]:
        """Получить отчет по зарплатам"""
        params = {}
        if report_month:
            params['report_month'] = report_month
        if employee_id:
            params['employee_id'] = employee_id
        if payment_type:
            params['payment_type'] = payment_type
        response = self._request(
            'GET',
            f"{self.base_url}/api/salaries/report",
            params=params
        )
        return self._handle_response(response)

    def add_salary(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Добавить запись о зарплате (alias для create_salary)"""
        return self.create_salary(payment_data)

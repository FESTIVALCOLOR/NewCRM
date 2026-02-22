from typing import Optional, List, Dict, Any


class EmployeesMixin:

    def get_employees(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить список сотрудников"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/employees",
            params={"skip": skip, "limit": limit}
        )
        return self._handle_response(response)

    def get_employees_by_position(self, position: str) -> List[Dict[str, Any]]:
        """Получить сотрудников по должности (фильтрация на клиенте)"""
        all_employees = self.get_employees(limit=500)
        return [
            emp for emp in all_employees
            if emp.get('position') == position or emp.get('secondary_position') == position
        ]

    def get_employee(self, employee_id: int) -> Dict[str, Any]:
        """Получить сотрудника по ID"""
        response = self._request('GET', f"{self.base_url}/api/employees/{employee_id}")
        return self._handle_response(response)

    def create_employee(self, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать нового сотрудника"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/employees",
            json=employee_data
        )
        return self._handle_response(response, success_codes=[200, 201])

    def update_employee(self, employee_id: int, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить сотрудника"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/employees/{employee_id}",
            json=employee_data
        )
        return self._handle_response(response)

    def delete_employee(self, employee_id: int) -> bool:
        """Удалить сотрудника"""
        response = self._request('DELETE', f"{self.base_url}/api/employees/{employee_id}")
        self._handle_response(response)
        return True

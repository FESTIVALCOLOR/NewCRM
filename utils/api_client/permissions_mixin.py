from typing import Optional, List, Dict, Any


class PermissionsMixin:

    def get_permission_definitions(self) -> List[Dict[str, str]]:
        """Получить список всех доступных прав с описаниями"""
        response = self._request('GET', f"{self.base_url}/api/permissions/definitions")
        return self._handle_response(response)

    def get_employee_permissions(self, employee_id: int) -> Dict[str, Any]:
        """Получить права конкретного сотрудника"""
        response = self._request('GET', f"{self.base_url}/api/permissions/{employee_id}")
        return self._handle_response(response)

    def set_employee_permissions(self, employee_id: int, permissions: List[str]) -> Dict[str, Any]:
        """Установить права сотрудника (полная замена)"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/permissions/{employee_id}",
            json={"permissions": permissions}
        )
        return self._handle_response(response)

    def reset_employee_permissions(self, employee_id: int) -> Dict[str, Any]:
        """Сбросить права сотрудника до дефолтных по роли"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/permissions/{employee_id}/reset-to-defaults"
        )
        return self._handle_response(response)

    def get_role_permissions_matrix(self) -> Dict[str, Any]:
        """Получить матрицу прав по ролям"""
        response = self._request('GET', f"{self.base_url}/api/permissions/role-matrix")
        return self._handle_response(response)

    def save_role_permissions_matrix(self, data: dict) -> Dict[str, Any]:
        """Сохранить матрицу прав по ролям"""
        response = self._request('PUT', f"{self.base_url}/api/permissions/role-matrix", json=data)
        return self._handle_response(response)

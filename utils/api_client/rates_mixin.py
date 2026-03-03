from typing import Optional, List, Dict, Any


class RatesMixin:

    def get_rates(self, project_type: str = None, role: str = None) -> List[Dict[str, Any]]:
        """Получить тарифы"""
        params = {}
        if project_type:
            params['project_type'] = project_type
        if role:
            params['role'] = role
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/rates",
            params=params
        )
        return self._handle_response(response)

    def get_rate(self, rate_id: int) -> Dict[str, Any]:
        """Получить тариф по ID"""
        response = self._request('GET', f"{self.base_url}/api/v1/rates/{rate_id}")
        return self._handle_response(response)

    def create_rate(self, rate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать тариф"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/rates",
            json=rate_data
        )
        return self._handle_response(response)

    def update_rate(self, rate_id: int, rate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить тариф"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/v1/rates/{rate_id}",
            json=rate_data
        )
        return self._handle_response(response)

    def delete_rate(self, rate_id: int) -> bool:
        """Удалить тариф"""
        response = self._request('DELETE', f"{self.base_url}/api/v1/rates/{rate_id}")
        self._handle_response(response)
        return True

    def get_template_rates(self, role: str = None) -> List[Dict[str, Any]]:
        """Получить шаблонные тарифы"""
        params = {}
        if role:
            params['role'] = role
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/rates/template",
            params=params
        )
        return self._handle_response(response)

    def save_template_rate(self, role: str, area_from: float, area_to: float, price: float) -> Dict[str, Any]:
        """Сохранить шаблонный тариф"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/rates/template",
            json={
                'role': role,
                'area_from': area_from,
                'area_to': area_to,
                'price': price
            }
        )
        return self._handle_response(response)

    def save_individual_rate(self, role: str, rate_per_m2: float, stage_name: str = None) -> Dict[str, Any]:
        """Сохранить индивидуальный тариф"""
        data = {
            'role': role,
            'rate_per_m2': rate_per_m2
        }
        if stage_name:
            data['stage_name'] = stage_name
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/rates/individual",
            json=data
        )
        return self._handle_response(response)

    def delete_individual_rate(self, role: str, stage_name: str = None) -> bool:
        """Удалить индивидуальный тариф"""
        params = {'role': role}
        if stage_name:
            params['stage_name'] = stage_name
        response = self._request(
            'DELETE',
            f"{self.base_url}/api/v1/rates/individual",
            params=params
        )
        self._handle_response(response)
        return True

    def save_supervision_rate(self, stage_name: str, executor_rate: float, manager_rate: float) -> Dict[str, Any]:
        """Сохранить тариф надзора"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/rates/supervision",
            json={
                'stage_name': stage_name,
                'executor_rate': executor_rate,
                'manager_rate': manager_rate
            }
        )
        return self._handle_response(response)

    def save_surveyor_rate(self, city: str, price: float) -> Dict[str, Any]:
        """Сохранить тариф замерщика"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/rates/surveyor",
            json={
                'city': city,
                'price': price
            }
        )
        return self._handle_response(response)

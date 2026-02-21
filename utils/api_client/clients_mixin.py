from typing import Optional, List, Dict, Any


class ClientsMixin:

    def get_clients(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить список клиентов"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/clients",
            params={"skip": skip, "limit": limit}
        )
        return self._handle_response(response)

    def get_clients_paginated(
        self, skip: int = 0, limit: int = 100
    ) -> tuple:
        """Получить список клиентов с информацией о пагинации.

        Возвращает кортеж (список клиентов, общее количество записей).
        Общее количество читается из заголовка X-Total-Count ответа сервера.
        """
        response = self._request(
            'GET',
            f"{self.base_url}/api/clients",
            params={"skip": skip, "limit": limit}
        )
        data = self._handle_response(response)
        # Читаем общее количество записей из заголовка X-Total-Count
        total = int(response.headers.get("X-Total-Count", len(data)))
        return data, total

    def get_client(self, client_id: int) -> Dict[str, Any]:
        """Получить клиента по ID"""
        response = self._request('GET', f"{self.base_url}/api/clients/{client_id}")
        return self._handle_response(response)

    def create_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать нового клиента"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/clients",
            json=client_data
        )
        return self._handle_response(response)

    def update_client(self, client_id: int, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить клиента"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/clients/{client_id}",
            json=client_data
        )
        return self._handle_response(response)

    def delete_client(self, client_id: int) -> bool:
        """Удалить клиента"""
        response = self._request('DELETE', f"{self.base_url}/api/clients/{client_id}")
        self._handle_response(response)
        return True

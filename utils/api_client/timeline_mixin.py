from typing import Optional, List, Dict, Any


class TimelineMixin:

    def get_project_timeline(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получить таблицу сроков проекта"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/timeline/{contract_id}"
        )
        return self._handle_response(response)

    def init_project_timeline(self, contract_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Инициализировать таблицу сроков проекта из шаблона"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/timeline/{contract_id}/init",
            json=data
        )
        return self._handle_response(response)

    def reinit_project_timeline(self, contract_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Пересоздать таблицу сроков проекта (удалить и создать заново)"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/timeline/{contract_id}/reinit",
            json=data
        )
        return self._handle_response(response)

    def update_timeline_entry(self, contract_id: int, stage_code: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить запись таблицы сроков"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/timeline/{contract_id}/entry/{stage_code}",
            json=data
        )
        return self._handle_response(response)

    def get_timeline_summary(self, contract_id: int) -> Dict[str, Any]:
        """Получить сводку по таблице сроков"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/timeline/{contract_id}/summary"
        )
        return self._handle_response(response)

    def export_timeline_excel(self, contract_id: int) -> bytes:
        """Экспорт таблицы сроков в Excel (возвращает байты файла)"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/timeline/{contract_id}/export/excel"
        )
        if response.status_code == 200:
            return response.content
        self._handle_response(response)
        return b''

    def export_timeline_pdf(self, contract_id: int) -> bytes:
        """Экспорт таблицы сроков в PDF (возвращает байты файла)"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/timeline/{contract_id}/export/pdf"
        )
        if response.status_code == 200:
            return response.content
        self._handle_response(response)
        return b''

    def get_supervision_timeline(self, card_id: int) -> List[Dict[str, Any]]:
        """Получить таблицу сроков надзора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/supervision-timeline/{card_id}"
        )
        return self._handle_response(response)

    def init_supervision_timeline(self, card_id: int, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Инициализировать таблицу сроков надзора"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/supervision-timeline/{card_id}/init",
            json=data or {}
        )
        return self._handle_response(response)

    def update_supervision_timeline_entry(self, card_id: int, stage_code: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить запись таблицы сроков надзора"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/supervision-timeline/{card_id}/entry/{stage_code}",
            json=data
        )
        return self._handle_response(response)

    def get_supervision_timeline_summary(self, card_id: int) -> Dict[str, Any]:
        """Получить сводку по таблице сроков надзора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/supervision-timeline/{card_id}/summary"
        )
        return self._handle_response(response)

    def export_supervision_timeline_excel(self, card_id: int) -> bytes:
        """Экспорт таблицы сроков надзора в Excel"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/supervision-timeline/{card_id}/export/excel"
        )
        if response.status_code == 200:
            return response.content
        self._handle_response(response)
        return b''

    def export_supervision_timeline_pdf(self, card_id: int) -> bytes:
        """Экспорт таблицы сроков надзора в PDF"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/supervision-timeline/{card_id}/export/pdf"
        )
        if response.status_code == 200:
            return response.content
        self._handle_response(response)
        return b''

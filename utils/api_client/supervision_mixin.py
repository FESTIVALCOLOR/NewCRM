from typing import Optional, List, Dict, Any


class SupervisionMixin:

    def get_supervision_cards(self, status: str = "active") -> List[Dict]:
        """
        Получить карточки авторского надзора

        Args:
            status: "active" - активные (АВТОРСКИЙ НАДЗОР), "archived" - архивные

        Returns:
            Список карточек надзора
        """
        response = self._request(
            'GET',
            f"{self.base_url}/api/supervision/cards",
            params={"status": status}
        )
        return self._handle_response(response)

    def get_supervision_card(self, card_id: int) -> Dict:
        """Получить одну карточку надзора"""
        response = self._request('GET', f"{self.base_url}/api/supervision/cards/{card_id}")
        return self._handle_response(response)

    def create_supervision_card(self, card_data: Dict[str, Any]) -> Dict:
        """
        Создать новую карточку авторского надзора

        Args:
            card_data: Данные карточки (contract_id, column_name, и др.)

        Returns:
            Созданная карточка
        """
        response = self._request(
            'POST',
            f"{self.base_url}/api/supervision/cards",
            json=card_data
        )
        return self._handle_response(response)

    def update_supervision_card(self, card_id: int, updates: Dict[str, Any]) -> Dict:
        """Обновить карточку надзора"""
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/supervision/cards/{card_id}",
            json=updates
        )
        return self._handle_response(response)

    def move_supervision_card(self, card_id: int, column_name: str) -> Dict:
        """Переместить карточку надзора в другую колонку"""
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/supervision/cards/{card_id}/column",
            json={"column_name": column_name}
        )
        return self._handle_response(response)

    def pause_supervision_card(self, card_id: int, pause_reason: str) -> Dict:
        """Приостановить карточку надзора"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/supervision/cards/{card_id}/pause",
            json={"pause_reason": pause_reason}
        )
        return self._handle_response(response)

    def resume_supervision_card(self, card_id: int, employee_id: int = None) -> Dict:
        """Возобновить карточку надзора"""
        data = {}
        if employee_id:
            data['employee_id'] = employee_id
        response = self._request(
            'POST',
            f"{self.base_url}/api/supervision/cards/{card_id}/resume",
            json=data if data else None
        )
        return self._handle_response(response)

    def delete_supervision_order(self, contract_id: int, supervision_card_id: int) -> bool:
        """Удалить заказ надзора"""
        response = self._request(
            'DELETE',
            f"{self.base_url}/api/supervision/orders/{supervision_card_id}",
            params={'contract_id': contract_id}
        )
        self._handle_response(response)
        return True

    def complete_supervision_stage(self, card_id: int, stage_name: str = None) -> Dict[str, Any]:
        """Завершить стадию надзора"""
        data = {}
        if stage_name:
            data['stage_name'] = stage_name
        response = self._request(
            'POST',
            f"{self.base_url}/api/supervision/cards/{card_id}/complete-stage",
            json=data
        )
        return self._handle_response(response)

    def reset_supervision_stage_completion(self, card_id: int) -> Dict[str, Any]:
        """Сбросить выполнение стадий надзора"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/supervision/cards/{card_id}/reset-stages"
        )
        return self._handle_response(response)

    def get_supervision_addresses(self) -> List[str]:
        """Получить адреса надзора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/supervision/addresses"
        )
        return self._handle_response(response)

    def get_contract_id_by_supervision_card(self, card_id: int) -> int:
        """Получить ID договора по ID карточки надзора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/supervision/cards/{card_id}/contract"
        )
        result = self._handle_response(response)
        return result.get('contract_id')

    def get_supervision_history(self, card_id: int) -> List[Dict[str, Any]]:
        """Получить историю карточки надзора"""
        response = self._request('GET', f"{self.base_url}/api/supervision/cards/{card_id}/history")
        return self._handle_response(response)

    def add_supervision_history(self, card_id: int, entry_type: str, message: str, employee_id: int) -> Dict[str, Any]:
        """
        Добавить запись в историю надзора

        Args:
            card_id: ID карточки надзора
            entry_type: Тип записи ('moved', 'accepted', 'comment' и т.д.)
            message: Текст сообщения
            employee_id: ID сотрудника, выполнившего действие
        """
        history_data = {
            'entry_type': entry_type,
            'message': message,
            'created_by': employee_id
        }
        response = self._request(
            'POST',
            f"{self.base_url}/api/supervision/cards/{card_id}/history",
            json=history_data
        )
        return self._handle_response(response)

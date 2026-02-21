from typing import Optional, List, Dict, Any


class CrmMixin:

    def get_crm_cards(self, project_type: str) -> List[Dict]:
        """
        Получить CRM карточки по типу проекта

        Args:
            project_type: Тип проекта ("Индивидуальный" или "Шаблонный")

        Returns:
            Список карточек с полной информацией
        """
        response = self._request(
            'GET',
            f"{self.base_url}/api/crm/cards",
            params={"project_type": project_type}
        )
        return self._handle_response(response)

    def get_crm_card(self, card_id: int) -> Dict:
        """
        Получить одну CRM карточку

        Args:
            card_id: ID карточки

        Returns:
            Данные карточки с исполнителями стадий
        """
        # Пробуем получить через специальный endpoint
        try:
            response = self._request('GET', f"{self.base_url}/api/crm/cards/{card_id}")
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] get_crm_card endpoint error: {e}")

        # Fallback: получаем все карточки и фильтруем по ID
        print(f"[API] Fallback: поиск карточки {card_id} через get_crm_cards")
        for project_type in ['Индивидуальный', 'Шаблонный']:
            try:
                cards = self.get_crm_cards(project_type)
                for card in cards:
                    if card.get('id') == card_id:
                        print(f"[API] Карточка {card_id} найдена в {project_type}")
                        return card
            except Exception as e:
                print(f"[API] Ошибка поиска в {project_type}: {e}")

        from utils.api_client.exceptions import APIError
        raise APIError(f"CRM карточка с ID {card_id} не найдена")

    def create_crm_card(self, card_data: Dict[str, Any]) -> Dict:
        """
        Создать новую CRM карточку

        Args:
            card_data: Данные карточки (contract_id, column_name, и др.)

        Returns:
            Созданная карточка
        """
        response = self._request(
            'POST',
            f"{self.base_url}/api/crm/cards",
            json=card_data
        )
        return self._handle_response(response)

    def update_crm_card(self, card_id: int, updates: Dict[str, Any]) -> Dict:
        """
        Обновить CRM карточку (частичное обновление)

        Args:
            card_id: ID карточки
            updates: Словарь с обновляемыми полями

        Returns:
            Обновлённые данные карточки
        """
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/crm/cards/{card_id}",
            json=updates
        )
        return self._handle_response(response)

    def move_crm_card(self, card_id: int, column_name: str) -> Dict:
        """
        Переместить CRM карточку в другую колонку

        Args:
            card_id: ID карточки
            column_name: Название колонки ("Новый заказ", "В работе" и т.д.)

        Returns:
            Обновлённые данные карточки
        """
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/crm/cards/{card_id}/column",
            json={"column_name": column_name}
        )
        return self._handle_response(response)

    def delete_crm_card(self, card_id: int) -> bool:
        """Удалить CRM карточку"""
        response = self._request('DELETE', f"{self.base_url}/api/crm/cards/{card_id}")
        self._handle_response(response)
        return True

    def assign_stage_executor(self, card_id: int, stage_data: Dict[str, Any]) -> Dict:
        """
        Назначить исполнителя на стадию

        Args:
            card_id: ID карточки
            stage_data: Данные назначения
                {
                    "stage_name": str,
                    "executor_id": int,
                    "deadline": str (optional, YYYY-MM-DD)
                }

        Returns:
            Данные созданного назначения
        """
        response = self._request(
            'POST',
            f"{self.base_url}/api/crm/cards/{card_id}/stage-executor",
            json=stage_data
        )
        return self._handle_response(response)

    def complete_stage(self, card_id: int, stage_name: str, completed: bool = True) -> Dict:
        """
        Отметить стадию как завершённую

        Args:
            card_id: ID карточки
            stage_name: Название стадии
            completed: True - завершена, False - отменить завершение

        Returns:
            Обновлённые данные назначения
        """
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/crm/cards/{card_id}/stage-executor/{stage_name}",
            json={"completed": completed}
        )
        return self._handle_response(response)

    def get_archived_crm_cards(self, project_type: str = None) -> List[Dict]:
        """
        Получить архивные CRM карточки (статус СДАН)

        Args:
            project_type: Тип проекта ("Индивидуальный" или "Шаблонный"), если None - все

        Returns:
            Список архивных карточек
        """
        params = {}
        if project_type:
            params['project_type'] = project_type
        params['archived'] = True

        response = self._request(
            'GET',
            f"{self.base_url}/api/crm/cards",
            params=params
        )
        return self._handle_response(response)

    def get_stage_executors(self, card_id: int) -> List[Dict[str, Any]]:
        """Получить исполнителей стадий для карточки"""
        response = self._request('GET', f"{self.base_url}/api/crm/cards/{card_id}")
        card_data = self._handle_response(response)
        return card_data.get('stage_executors', [])

    def update_stage_executor(self, card_id: int, stage_name: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить исполнителя стадии"""
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/crm/cards/{card_id}/stage-executor/{stage_name}",
            json=update_data
        )
        return self._handle_response(response)

    def delete_stage_executor(self, executor_id: int) -> bool:
        """Удалить назначение исполнителя"""
        response = self._request('DELETE', f"{self.base_url}/api/crm/stage-executors/{executor_id}")
        self._handle_response(response)
        return True

    def complete_stage_for_executor(self, crm_card_id: int, stage_name: str, executor_id: int) -> bool:
        """Отметить стадию как выполненную для исполнителя"""
        try:
            response = self._request(
                'PATCH',
                f"{self.base_url}/api/crm/cards/{crm_card_id}/stage-executor/{stage_name}/complete",
                json={'executor_id': executor_id}
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка завершения стадии: {e}")
            return False

    def reset_stage_completion(self, card_id: int) -> Dict[str, Any]:
        """Сбросить выполнение стадий карточки"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/crm/cards/{card_id}/reset-stages"
        )
        return self._handle_response(response)

    def reset_approval_stages(self, card_id: int) -> Dict[str, Any]:
        """Сбросить стадии согласования карточки"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/crm/cards/{card_id}/reset-approval"
        )
        return self._handle_response(response)

    def get_submitted_stages(self, card_id: int) -> List[Dict[str, Any]]:
        """Получить отправленные стадии карточки"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/crm/cards/{card_id}/submitted-stages"
        )
        return self._handle_response(response)

    def get_stage_history(self, card_id: int) -> List[Dict[str, Any]]:
        """Получить историю стадий карточки"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/crm/cards/{card_id}/stage-history"
        )
        return self._handle_response(response)

    def reset_designer_completion(self, crm_card_id: int) -> bool:
        """Сбросить отметку о завершении дизайнером"""
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/crm/cards/{crm_card_id}/reset-designer"
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка сброса отметки дизайнера: {e}")
            return False

    def reset_draftsman_completion(self, crm_card_id: int) -> bool:
        """Сбросить отметку о завершении чертежником"""
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/crm/cards/{crm_card_id}/reset-draftsman"
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка сброса отметки чертежника: {e}")
            return False

    def get_approval_stage_deadlines(self, crm_card_id: int) -> List[Dict[str, Any]]:
        """Получить дедлайны стадий согласования"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/crm/cards/{crm_card_id}/approval-deadlines"
        )
        return self._handle_response(response)

    def complete_approval_stage(self, crm_card_id: int, stage_name: str) -> bool:
        """Завершить стадию согласования"""
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/crm/cards/{crm_card_id}/complete-approval-stage",
                json={'stage_name': stage_name}
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка завершения стадии согласования: {e}")
            return False

    def save_manager_acceptance(self, crm_card_id: int, stage_name: str,
                                executor_name: str, manager_id: int) -> bool:
        """Сохранить принятие работы менеджером"""
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/crm/cards/{crm_card_id}/manager-acceptance",
                json={
                    'stage_name': stage_name,
                    'executor_name': executor_name,
                    'manager_id': manager_id
                }
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка сохранения принятия: {e}")
            return False

    def get_accepted_stages(self, crm_card_id: int) -> List[Dict[str, Any]]:
        """Получить список принятых стадий"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/crm/cards/{crm_card_id}/accepted-stages"
        )
        return self._handle_response(response)

    def get_workflow_state(self, card_id: int) -> List[Dict[str, Any]]:
        """Получить состояние рабочего процесса карточки"""
        response = self._request('GET', f"{self.base_url}/api/crm/cards/{card_id}/workflow/state")
        return self._handle_response(response) or []

    def workflow_submit(self, card_id: int) -> Dict[str, Any]:
        """Сдача работы"""
        response = self._request('POST', f"{self.base_url}/api/crm/cards/{card_id}/workflow/submit")
        return self._handle_response(response)

    def workflow_accept(self, card_id: int) -> Dict[str, Any]:
        """Приемка работы"""
        response = self._request('POST', f"{self.base_url}/api/crm/cards/{card_id}/workflow/accept")
        return self._handle_response(response)

    def workflow_reject(self, card_id: int, corrections_path: str = '') -> Dict[str, Any]:
        """Отправить на исправление с путем к папке правок на ЯД"""
        data = {}
        if corrections_path:
            data['revision_file_path'] = corrections_path
        response = self._request('POST', f"{self.base_url}/api/crm/cards/{card_id}/workflow/reject", json=data)
        return self._handle_response(response)

    def workflow_client_send(self, card_id: int) -> Dict[str, Any]:
        """Отправить на согласование клиенту"""
        response = self._request('POST', f"{self.base_url}/api/crm/cards/{card_id}/workflow/client-send")
        return self._handle_response(response)

    def workflow_client_ok(self, card_id: int) -> Dict[str, Any]:
        """Клиент согласовал"""
        response = self._request('POST', f"{self.base_url}/api/crm/cards/{card_id}/workflow/client-ok")
        return self._handle_response(response)

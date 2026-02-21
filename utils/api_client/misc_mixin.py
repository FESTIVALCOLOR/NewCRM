from typing import Optional, List, Dict, Any
from datetime import datetime


class MiscMixin:

    def health_check(self) -> bool:
        """Проверка доступности сервера"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/health",
                timeout=5,
                retry=False  # Быстрая проверка без повторов
            )
            self._is_online = response.status_code == 200
            return self._is_online
        except Exception:
            self._is_online = False
            return False

    def get_notifications(self, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Получить уведомления"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/notifications",
            params={"unread_only": unread_only}
        )
        return self._handle_response(response)

    def mark_notification_read(self, notification_id: int) -> bool:
        """Отметить уведомление как прочитанное"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/notifications/{notification_id}/read"
        )
        return response.status_code == 200

    def sync(self, last_sync_timestamp: datetime, entity_types: List[str],
             retry: bool = True, timeout: int = None, mark_offline: bool = False) -> Dict[str, Any]:
        """
        Получить обновления с сервера (фоновая синхронизация)

        Args:
            last_sync_timestamp: Время последней синхронизации
            entity_types: Типы сущностей ['clients', 'contracts', 'employees']
            retry: Включить retry логику (по умолчанию True)
            timeout: Таймаут в секундах (по умолчанию DEFAULT_TIMEOUT)
            mark_offline: Помечать клиент как offline при ошибке (по умолчанию False для sync)
                          Фоновая синхронизация НЕ должна блокировать пользовательские запросы

        Returns:
            dict с обновленными данными
        """
        response = self._request(
            'POST',
            f"{self.base_url}/api/sync",
            json={
                "last_sync_timestamp": last_sync_timestamp.isoformat(),
                "entity_types": entity_types
            },
            retry=retry,
            timeout=timeout,
            mark_offline=mark_offline
        )
        return self._handle_response(response)

    def get_all_stage_executors(self) -> List[Dict[str, Any]]:
        """Получить всех исполнителей стадий для синхронизации"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/sync/stage-executors"
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка получения исполнителей стадий: {e}")
            return []

    def get_all_approval_deadlines(self) -> List[Dict[str, Any]]:
        """Получить все дедлайны согласования для синхронизации"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/sync/approval-deadlines"
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка получения дедлайнов согласования: {e}")
            return []

    def get_all_action_history(self) -> List[Dict[str, Any]]:
        """Получить всю историю действий для синхронизации"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/sync/action-history"
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка получения истории действий: {e}")
            return []

    def get_all_supervision_history(self) -> List[Dict[str, Any]]:
        """Получить всю историю проектов надзора для синхронизации"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/sync/supervision-history"
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка получения истории надзора: {e}")
            return []

    def get_action_history(self, entity_type: str, entity_id: int) -> List[Dict[str, Any]]:
        """Получить историю действий для сущности"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/action-history/{entity_type}/{entity_id}"
        )
        return self._handle_response(response)

    def create_action_history(self, history_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать запись истории действий"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/action-history",
            json=history_data
        )
        return self._handle_response(response)

    def add_action_history(self, user_id: int, action_type: str, entity_type: str,
                           entity_id: int, description: str) -> bool:
        """Добавить запись в историю действий"""
        try:
            history_data = {
                'user_id': user_id,
                'action_type': action_type,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'description': description
            }
            self.create_action_history(history_data)
            return True
        except Exception as e:
            print(f"[API] Ошибка добавления записи в историю: {e}")
            return False

    def add_project_template(self, contract_id: int, template_url: str) -> Optional[int]:
        """Добавить ссылку на шаблон проекта"""
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/project-templates",
                json={'contract_id': contract_id, 'template_url': template_url}
            )
            result = self._handle_response(response)
            return result.get('id')
        except Exception as e:
            print(f"[API] Ошибка добавления шаблона: {e}")
            return None

    def get_project_templates(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получить все шаблоны для договора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/project-templates/{contract_id}"
        )
        return self._handle_response(response)

    def delete_project_template(self, template_id: int) -> bool:
        """Удалить шаблон проекта"""
        try:
            response = self._request(
                'DELETE',
                f"{self.base_url}/api/project-templates/{template_id}"
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка удаления шаблона: {e}")
            return False

    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Получить список всех агентов"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/agents"
            )
            return self._handle_response(response)
        except Exception:
            # Fallback: получаем через сотрудников с фильтром по должности
            employees = self.get_employees(limit=500)
            return [emp for emp in employees if emp.get('position') == 'Агент' or emp.get('secondary_position') == 'Агент']

    def add_agent(self, name: str, color: str) -> bool:
        """Добавить нового агента"""
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/agents",
                json={'name': name, 'color': color}
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка добавления агента: {e}")
            return False

    def update_agent_color(self, name: str, color: str) -> bool:
        """Обновить цвет агента"""
        try:
            response = self._request(
                'PATCH',
                f"{self.base_url}/api/agents/{name}/color",
                json={'color': color}
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка обновления цвета агента: {e}")
            return False

    def get_agent_color(self, name: str) -> Optional[str]:
        """Получить цвет агента по имени"""
        try:
            agents = self.get_all_agents()
            for agent in agents:
                if agent.get('name') == name:
                    return agent.get('color')
            return None
        except Exception as e:
            print(f"[API] Ошибка получения цвета агента: {e}")
            return None

    def get_agents(self) -> List[Dict[str, Any]]:
        """Получить список агентов"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/agents"
        )
        return self._handle_response(response)

    def get_agent(self, agent_id: int) -> Dict[str, Any]:
        """Получить агента по ID"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/agents/{agent_id}"
        )
        return self._handle_response(response)

    def search(self, query: str, limit: int = 50, entity_types: str = None) -> Dict[str, Any]:
        """Полнотекстовый поиск по клиентам, договорам, CRM карточкам"""
        params = {"q": query, "limit": limit}
        if entity_types:
            params["entity_types"] = entity_types
        response = self._request(
            'GET',
            f"{self.base_url}/api/search",
            params=params
        )
        return self._handle_response(response)

    def get_norm_days_template(self, project_type: str, project_subtype: str, agent_type: str = 'Все агенты') -> Dict[str, Any]:
        """Получить шаблон нормо-дней для типа/подтипа/агента"""
        params = {"project_type": project_type, "project_subtype": project_subtype, "agent_type": agent_type}
        response = self._request('GET', f"{self.base_url}/api/norm-days/templates", params=params)
        return self._handle_response(response)

    def save_norm_days_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Сохранить кастомный шаблон нормо-дней"""
        response = self._request('PUT', f"{self.base_url}/api/norm-days/templates", json=data)
        return self._handle_response(response)

    def preview_norm_days_template(self, project_type: str, project_subtype: str, area: float, agent_type: str = 'Все агенты') -> Dict[str, Any]:
        """Предпросмотр расчёта нормо-дней для указанной площади"""
        response = self._request('POST', f"{self.base_url}/api/norm-days/templates/preview",
                                 json={"project_type": project_type, "project_subtype": project_subtype,
                                        "area": area, "agent_type": agent_type})
        return self._handle_response(response)

    def reset_norm_days_template(self, project_type: str, project_subtype: str, agent_type: str = 'Все агенты') -> Dict[str, Any]:
        """Сбросить кастомный шаблон нормо-дней (возврат к формулам)"""
        response = self._request('POST', f"{self.base_url}/api/norm-days/templates/reset",
                                 json={"project_type": project_type, "project_subtype": project_subtype,
                                        "agent_type": agent_type})
        return self._handle_response(response)

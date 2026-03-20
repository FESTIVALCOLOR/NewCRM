from typing import Optional, List, Dict, Any


class MessengerMixin:

    def create_messenger_chat(self, crm_card_id: int, messenger_type: str = "telegram",
                               members: list = None, chat_title: str = None) -> Dict[str, Any]:
        """Создать чат автоматически (MTProto)"""
        payload = {
            "crm_card_id": crm_card_id,
            "messenger_type": messenger_type,
            "members": members or []
        }
        if chat_title:
            payload["chat_title"] = chat_title
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/messenger/chats",
            json=payload,
            timeout=60  # Создание TG-группы + миграция в supergroup — долгая операция
        )
        return self._handle_response(response)

    def bind_messenger_chat(self, crm_card_id: int, invite_link: str,
                             messenger_type: str = "telegram", members: list = None) -> Dict[str, Any]:
        """Привязать существующий чат по invite-ссылке"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/messenger/chats/bind",
            json={
                "crm_card_id": crm_card_id,
                "invite_link": invite_link,
                "messenger_type": messenger_type,
                "members": members or []
            },
            timeout=60  # MTProto join + добавление бота + promote — долгая операция
        )
        return self._handle_response(response)

    def get_messenger_chat_by_card(self, card_id: int) -> Optional[Dict[str, Any]]:
        """Получить чат по CRM-карточке"""
        try:
            response = self._request('GET', f"{self.base_url}/api/v1/messenger/chats/by-card/{card_id}")
            return self._handle_response(response)
        except Exception:
            return None

    def get_supervision_chat(self, supervision_card_id: int) -> Optional[Dict[str, Any]]:
        """Получить чат по карточке надзора"""
        try:
            response = self._request('GET', f"{self.base_url}/api/v1/messenger/chats/by-supervision/{supervision_card_id}")
            return self._handle_response(response)
        except Exception:
            return None

    def create_supervision_chat(self, supervision_card_id: int, messenger_type: str = "telegram",
                                 members: list = None, chat_title: str = None) -> Dict[str, Any]:
        """Создать чат для карточки надзора"""
        payload = {
            "supervision_card_id": supervision_card_id,
            "messenger_type": messenger_type,
            "members": members or []
        }
        if chat_title:
            payload["chat_title"] = chat_title
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/messenger/chats/supervision",
            json=payload
        )
        return self._handle_response(response)

    def delete_messenger_chat(self, chat_id: int) -> Dict[str, Any]:
        """Удалить/отвязать чат"""
        response = self._request('DELETE', f"{self.base_url}/api/v1/messenger/chats/{chat_id}")
        return self._handle_response(response)

    def send_messenger_message(self, chat_id: int, text: str, deadline_date: str = None) -> Dict[str, Any]:
        """Отправить сообщение в чат"""
        payload = {"text": text}
        if deadline_date:
            payload["deadline_date"] = deadline_date
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/messenger/chats/{chat_id}/message",
            json=payload
        )
        return self._handle_response(response)

    def send_messenger_files(self, chat_id: int, file_ids: list = None,
                              yandex_paths: list = None, caption: str = None,
                              as_gallery: bool = False) -> Dict[str, Any]:
        """Отправить файлы в чат"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/messenger/chats/{chat_id}/files",
            json={
                "file_ids": file_ids or [],
                "yandex_paths": yandex_paths or [],
                "caption": caption,
                "as_gallery": as_gallery,
            }
        )
        return self._handle_response(response)

    def send_messenger_invites(self, chat_id: int, member_ids: list = None) -> Dict[str, Any]:
        """Разослать invite-ссылки"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/messenger/chats/{chat_id}/send-invites",
            json={"member_ids": member_ids or []}
        )
        return self._handle_response(response)

    def trigger_script(self, card_id: int, script_type: str, entity_type: str = 'crm') -> bool:
        """Отправить скрипт мессенджера"""
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/v1/messenger/trigger-script",
                json={
                    'card_id': card_id,
                    'script_type': script_type,
                    'entity_type': entity_type
                }
            )
            return response is not None and response.status_code == 200
        except Exception:
            return False

    def preview_script(self, card_id: int, script_type: str = 'stage_complete',
                       stage_name: str = None) -> Dict[str, Any]:
        """Предпросмотр скрипта с рендерингом переменных"""
        payload = {'card_id': card_id, 'script_type': script_type}
        if stage_name:
            payload['stage_name'] = stage_name
        response = self._request(
            'POST', f"{self.base_url}/api/v1/messenger/preview-script", json=payload
        )
        return self._handle_response(response)

    def preview_act(self, card_id: int) -> Dict[str, Any]:
        """Предпросмотр скрипта отправки акта клиенту"""
        response = self._request(
            'POST', f"{self.base_url}/api/v1/messenger/preview-act",
            json={'card_id': card_id}
        )
        return self._handle_response(response)

    def send_act(self, card_id: int, text: str, act_prefixes: list = None) -> Dict[str, Any]:
        """Отправить акт в групповой чат"""
        response = self._request(
            'POST', f"{self.base_url}/api/v1/messenger/send-act",
            timeout=60,
            json={
                'card_id': card_id,
                'text': text,
                'act_prefixes': act_prefixes or [],
            }
        )
        return self._handle_response(response)

    def send_edited_script(self, card_id: int, text: str, file_ids: list = None,
                           deadline_date: str = None, custom_deadline: bool = False) -> Dict[str, Any]:
        """Отправить отредактированный скрипт в групповой чат"""
        response = self._request(
            'POST', f"{self.base_url}/api/v1/messenger/send-edited-script",
            timeout=120,  # Скачивание с ЯД + отправка в Telegram — долгая операция
            json={
                'card_id': card_id,
                'text': text,
                'file_ids': file_ids or [],
                'deadline_date': deadline_date,
                'custom_deadline': custom_deadline,
            }
        )
        return self._handle_response(response)

    # --- Скрипты ---

    def get_messenger_scripts(self, project_type: str = None, script_type: str = None) -> List[Dict[str, Any]]:
        """Получить скрипты"""
        params = {}
        if project_type:
            params['project_type'] = project_type
        if script_type:
            params['script_type'] = script_type
        response = self._request('GET', f"{self.base_url}/api/v1/messenger/scripts", params=params)
        return self._handle_response(response)

    def create_messenger_script(self, data: Dict) -> Dict[str, Any]:
        """Создать скрипт"""
        response = self._request('POST', f"{self.base_url}/api/v1/messenger/scripts", json=data)
        return self._handle_response(response)

    def update_messenger_script(self, script_id: int, data: Dict) -> Dict[str, Any]:
        """Обновить скрипт"""
        response = self._request('PUT', f"{self.base_url}/api/v1/messenger/scripts/{script_id}", json=data)
        return self._handle_response(response)

    def delete_messenger_script(self, script_id: int) -> Dict[str, Any]:
        """Удалить скрипт"""
        response = self._request('DELETE', f"{self.base_url}/api/v1/messenger/scripts/{script_id}")
        return self._handle_response(response)

    def toggle_messenger_script(self, script_id: int) -> Dict[str, Any]:
        """Вкл/выкл скрипт"""
        response = self._request('PATCH', f"{self.base_url}/api/v1/messenger/scripts/{script_id}/toggle")
        return self._handle_response(response)

    # --- Настройки ---

    def get_messenger_settings(self) -> List[Dict[str, Any]]:
        """Получить настройки мессенджера"""
        response = self._request('GET', f"{self.base_url}/api/v1/messenger/settings")
        return self._handle_response(response)

    def update_messenger_settings(self, settings: list) -> Dict[str, Any]:
        """Обновить настройки (массовое)"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/v1/messenger/settings",
            json={"settings": settings}
        )
        return self._handle_response(response)

    def get_messenger_status(self) -> Dict[str, Any]:
        """Статус сервисов мессенджера"""
        try:
            response = self._request('GET', f"{self.base_url}/api/v1/messenger/status")
            return self._handle_response(response)
        except Exception:
            return {"telegram_bot_available": False, "telegram_mtproto_available": False, "email_available": False}

    def mtproto_send_code(self) -> Dict[str, Any]:
        """Шаг 1: Отправить код подтверждения для MTProto"""
        response = self._request('POST', f"{self.base_url}/api/v1/messenger/mtproto/send-code")
        return self._handle_response(response)

    def mtproto_resend_sms(self) -> Dict[str, Any]:
        """Переотправить код по SMS"""
        response = self._request('POST', f"{self.base_url}/api/v1/messenger/mtproto/resend-sms")
        return self._handle_response(response)

    def mtproto_verify_code(self, code: str) -> Dict[str, Any]:
        """Шаг 2: Подтвердить код MTProto"""
        response = self._request('POST', f"{self.base_url}/api/v1/messenger/mtproto/verify-code", json={"code": code})
        return self._handle_response(response)

    def mtproto_session_status(self) -> Dict[str, Any]:
        """Проверить статус MTProto сессии"""
        try:
            response = self._request('GET', f"{self.base_url}/api/v1/messenger/mtproto/session-status")
            return self._handle_response(response)
        except Exception:
            return {"valid": False}

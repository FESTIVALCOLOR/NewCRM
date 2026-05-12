"""
Миксин API клиента: внутренний чат.
"""

from typing import Any, Dict, List, Optional


class ChatMixin:
    # ----------------------------------------------------------
    # Чаты
    # ----------------------------------------------------------

    def create_internal_chat(self, chat_type: str, crm_card_id: int = None, supervision_card_id: int = None) -> dict[str, Any]:
        """Создать чат (employee / client)."""
        payload = {"chat_type": chat_type}
        if crm_card_id:
            payload["crm_card_id"] = crm_card_id
        if supervision_card_id:
            payload["supervision_card_id"] = supervision_card_id
        r = self._request("POST", f"{self.base_url}/api/v1/chats/", json=payload)
        return self._handle_response(r)

    def get_internal_chats(self, chat_type: str = None, crm_card_id: int = None) -> list[dict[str, Any]]:
        """Список чатов текущего сотрудника."""
        params = {}
        if chat_type:
            params["chat_type"] = chat_type
        if crm_card_id:
            params["crm_card_id"] = crm_card_id
        try:
            r = self._request("GET", f"{self.base_url}/api/v1/chats/", params=params)
            return self._handle_response(r) or []
        except Exception:
            return []

    def get_internal_chat(self, chat_id: int) -> Optional[dict[str, Any]]:
        """Детали чата с участниками и последними сообщениями."""
        try:
            r = self._request("GET", f"{self.base_url}/api/v1/chats/{chat_id}")
            return self._handle_response(r)
        except Exception:
            return None

    def delete_internal_chat(self, chat_id: int) -> bool:
        try:
            r = self._request("DELETE", f"{self.base_url}/api/v1/chats/{chat_id}")
            self._handle_response(r)
            return True
        except Exception:
            return False

    # ----------------------------------------------------------
    # Сообщения
    # ----------------------------------------------------------

    def get_chat_messages(self, chat_id: int, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        try:
            r = self._request("GET", f"{self.base_url}/api/v1/chats/{chat_id}/messages", params={"limit": limit, "offset": offset})
            return self._handle_response(r) or []
        except Exception:
            return []

    def send_chat_message(self, chat_id: int, content: str, reply_to_id: int = None) -> Optional[dict[str, Any]]:
        try:
            payload = {"content": content, "message_type": "text"}
            if reply_to_id:
                payload["reply_to_id"] = reply_to_id
            r = self._request("POST", f"{self.base_url}/api/v1/chats/{chat_id}/messages", json=payload)
            return self._handle_response(r)
        except Exception:
            return None

    def edit_chat_message(self, chat_id: int, msg_id: int, content: str) -> Optional[dict[str, Any]]:
        try:
            r = self._request("PATCH", f"{self.base_url}/api/v1/chats/{chat_id}/messages/{msg_id}", json={"content": content})
            return self._handle_response(r)
        except Exception:
            return None

    def delete_chat_message(self, chat_id: int, msg_id: int) -> bool:
        try:
            r = self._request("DELETE", f"{self.base_url}/api/v1/chats/{chat_id}/messages/{msg_id}")
            self._handle_response(r)
            return True
        except Exception:
            return False

    def pin_chat_message(self, chat_id: int, msg_id: int) -> bool:
        """Закрепить / открепить сообщение (toggle)."""
        try:
            r = self._request("POST", f"{self.base_url}/api/v1/chats/{chat_id}/messages/{msg_id}/pin")
            self._handle_response(r)
            return True
        except Exception:
            return False

    def mark_chat_read(self, chat_id: int, last_message_id: int) -> bool:
        try:
            r = self._request("POST", f"{self.base_url}/api/v1/chats/{chat_id}/messages/{last_message_id}/read")
            self._handle_response(r)
            return True
        except Exception:
            return False

    def search_chat_messages(self, chat_id: int, q: str, limit: int = 20) -> list[dict[str, Any]]:
        """Полнотекстовый поиск по сообщениям чата."""
        try:
            r = self._request("GET", f"{self.base_url}/api/v1/chats/{chat_id}/messages/search", params={"q": q, "limit": limit})
            return self._handle_response(r) or []
        except Exception:
            return []

    # ----------------------------------------------------------
    # Файлы
    # ----------------------------------------------------------

    def upload_chat_file(self, chat_id: int, file_bytes: bytes, filename: str, message_type: str = "file", group_id: str = None) -> Optional[dict[str, Any]]:
        """Загрузить файл/голос/изображение в чат."""
        try:
            data = {"message_type": message_type}
            if group_id:
                data["group_id"] = group_id
            r = self._request(
                "POST",
                f"{self.base_url}/api/v1/chats/{chat_id}/files",
                files={"file": (filename, file_bytes)},
                data=data,
            )
            return self._handle_response(r)
        except Exception:
            return None

    def link_project_file_to_chat(self, chat_id: int, yandex_path: str, file_name: str, public_link: str = "", message_type: str = "file") -> Optional[dict[str, Any]]:
        """Прикрепить существующий файл проекта к чату (без загрузки байт)."""
        try:
            r = self._request(
                "POST",
                f"{self.base_url}/api/v1/chats/{chat_id}/messages/from-project-file",
                json={"yandex_path": yandex_path, "file_name": file_name, "public_link": public_link, "message_type": message_type},
            )
            return self._handle_response(r)
        except Exception:
            return None

    # ----------------------------------------------------------
    # Участники
    # ----------------------------------------------------------

    def add_chat_member(self, chat_id: int, employee_id: int) -> bool:
        try:
            r = self._request("POST", f"{self.base_url}/api/v1/chats/{chat_id}/members", json={"employee_id": employee_id})
            self._handle_response(r)
            return True
        except Exception:
            return False

    def remove_chat_member(self, chat_id: int, member_id: int) -> bool:
        try:
            r = self._request("DELETE", f"{self.base_url}/api/v1/chats/{chat_id}/members/{member_id}")
            self._handle_response(r)
            return True
        except Exception:
            return False

    # ----------------------------------------------------------
    # Ссылки для клиентов
    # ----------------------------------------------------------

    def create_client_invite_link(self, chat_id: int) -> Optional[dict[str, Any]]:
        try:
            r = self._request("POST", f"{self.base_url}/api/v1/chats/{chat_id}/invite-links")
            return self._handle_response(r)
        except Exception:
            return None

    def get_client_invite_links(self, chat_id: int) -> list[dict[str, Any]]:
        try:
            r = self._request("GET", f"{self.base_url}/api/v1/chats/{chat_id}/invite-links")
            return self._handle_response(r) or []
        except Exception:
            return []

    def revoke_client_access(self, chat_id: int, member_id: int) -> bool:
        try:
            r = self._request("DELETE", f"{self.base_url}/api/v1/chats/{chat_id}/invite-links/{member_id}")
            self._handle_response(r)
            return True
        except Exception:
            return False

    # ----------------------------------------------------------
    # Пересылка
    # ----------------------------------------------------------

    def forward_chat_message(self, chat_id: int, msg_id: int, target_chat_id: int) -> bool:
        try:
            r = self._request(
                "POST",
                f"{self.base_url}/api/v1/chats/{chat_id}/forward/{target_chat_id}",
                json={"msg_id": msg_id},
            )
            self._handle_response(r)
            return True
        except Exception:
            return False

    def get_gallery_public_link(self, chat_id: int, msg_id: int) -> Optional[str]:
        """Получить публичную ссылку на папку галереи (Яндекс.Диск)."""
        try:
            r = self._request("POST", f"{self.base_url}/api/v1/chats/{chat_id}/messages/{msg_id}/gallery-link")
            result = self._handle_response(r)
            return result.get("public_url") if result else None
        except Exception:
            return None

    def get_card_stage_variations(self, chat_id: int, crm_card_id: int, destination: str) -> dict:
        """Получить вариации стадии карточки для копирования файла."""
        try:
            r = self._request(
                "GET",
                f"{self.base_url}/api/v1/chats/{chat_id}/card-stage-variations",
                params={"crm_card_id": crm_card_id, "destination": destination},
            )
            return self._handle_response(r) or {"variations": [], "next_variation": 1}
        except Exception:
            return {"variations": [], "next_variation": 1}

    def copy_message_to_card(self, chat_id: int, msg_id: int, crm_card_id: int, destination: str, variation: int = None) -> Optional[dict]:
        """Скопировать файл из сообщения в поле/стадию CRM-карточки."""
        try:
            payload = {"crm_card_id": crm_card_id, "destination": destination}
            if variation is not None:
                payload["variation"] = variation
            r = self._request(
                "POST",
                f"{self.base_url}/api/v1/chats/{chat_id}/messages/{msg_id}/copy-to-card",
                json=payload,
            )
            return self._handle_response(r)
        except Exception:
            return None

    def forward_chat_message_group(self, chat_id: int, target_chat_id: int, msg_ids: list) -> bool:
        """Переслать группу сообщений (галерею) как единую медиа-группу."""
        try:
            r = self._request(
                "POST",
                f"{self.base_url}/api/v1/chats/{chat_id}/forward-group/{target_chat_id}",
                json={"msg_ids": msg_ids},
            )
            self._handle_response(r)
            return True
        except Exception:
            return False

    # ----------------------------------------------------------
    # WebSocket URL
    # ----------------------------------------------------------

    def get_chat_ws_url(self, chat_id: int) -> str:
        """Вернуть URL для WebSocket подключения сотрудника."""
        base = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        token = getattr(self, "token", "") or ""
        return f"{base}/api/v1/ws/chat/{chat_id}?token={token}"

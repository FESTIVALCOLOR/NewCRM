"""
Pydantic-схемы для системы мессенджер-чатов
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# =========================
# ЧАТЫ
# =========================

class ChatMemberInput(BaseModel):
    """Участник чата при создании"""
    member_type: str  # 'employee' / 'client'
    member_id: int
    role_in_project: Optional[str] = None
    is_mandatory: bool = False


class MessengerChatCreate(BaseModel):
    """Создание чата (автоматическое)"""
    crm_card_id: int
    messenger_type: str = "telegram"
    members: List[ChatMemberInput] = []


class MessengerChatBind(BaseModel):
    """Привязка существующего чата"""
    crm_card_id: int
    invite_link: str
    messenger_type: str = "telegram"
    members: List[ChatMemberInput] = []


class MessengerChatResponse(BaseModel):
    """Ответ с данными чата"""
    id: int
    contract_id: Optional[int] = None
    crm_card_id: Optional[int] = None
    supervision_card_id: Optional[int] = None
    messenger_type: str
    telegram_chat_id: Optional[int] = None
    chat_title: Optional[str] = None
    invite_link: Optional[str] = None
    avatar_type: Optional[str] = None
    creation_method: str
    created_by: Optional[int] = None
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


# =========================
# УЧАСТНИКИ ЧАТА
# =========================

class ChatMemberResponse(BaseModel):
    """Ответ с данными участника"""
    id: int
    messenger_chat_id: int
    member_type: str
    member_id: int
    role_in_project: Optional[str] = None
    is_mandatory: bool
    phone: Optional[str] = None
    email: Optional[str] = None
    telegram_user_id: Optional[int] = None
    invite_status: str
    invited_at: Optional[datetime] = None
    joined_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessengerChatDetailResponse(BaseModel):
    """Расширенный ответ с участниками"""
    chat: MessengerChatResponse
    members: List[ChatMemberResponse] = []


# =========================
# СКРИПТЫ
# =========================

class MessengerScriptCreate(BaseModel):
    """Создание скрипта"""
    script_type: str  # project_start / stage_complete / project_end
    project_type: Optional[str] = None
    stage_name: Optional[str] = None
    message_template: str = Field(..., min_length=1)
    use_auto_deadline: bool = True
    is_enabled: bool = True
    sort_order: int = 0


class MessengerScriptUpdate(BaseModel):
    """Обновление скрипта"""
    script_type: Optional[str] = None
    project_type: Optional[str] = None
    stage_name: Optional[str] = None
    message_template: Optional[str] = None
    use_auto_deadline: Optional[bool] = None
    is_enabled: Optional[bool] = None
    sort_order: Optional[int] = None


class MessengerScriptResponse(BaseModel):
    """Ответ с данными скрипта"""
    id: int
    script_type: str
    project_type: Optional[str] = None
    stage_name: Optional[str] = None
    message_template: str
    use_auto_deadline: bool
    is_enabled: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =========================
# НАСТРОЙКИ
# =========================

class MessengerSettingUpdate(BaseModel):
    """Обновление настройки"""
    setting_key: str
    setting_value: Optional[str] = None


class MessengerSettingResponse(BaseModel):
    """Ответ с настройкой"""
    id: int
    setting_key: str
    setting_value: Optional[str] = None
    updated_at: datetime
    updated_by: Optional[int] = None

    class Config:
        from_attributes = True


class MessengerSettingsBulkUpdate(BaseModel):
    """Массовое обновление настроек"""
    settings: List[MessengerSettingUpdate]


# =========================
# СООБЩЕНИЯ
# =========================

class SendMessageRequest(BaseModel):
    """Отправка сообщения в чат"""
    text: str
    deadline_date: Optional[str] = None  # для подстановки в {deadline}


class SendFilesRequest(BaseModel):
    """Отправка файлов в чат"""
    file_ids: List[int] = []  # ID из project_files
    yandex_paths: List[str] = []  # Прямые пути на Яндекс.Диске
    caption: Optional[str] = None
    as_gallery: bool = False  # Отправить изображения галереей


class SendScriptMessageRequest(BaseModel):
    """Отправка скрипт-сообщения"""
    script_id: int
    deadline_date: Optional[str] = None  # Ручная дата, если use_auto_deadline=False


class MessageLogResponse(BaseModel):
    """Ответ с логом сообщения"""
    id: int
    messenger_chat_id: int
    message_type: Optional[str] = None
    message_text: Optional[str] = None
    file_links: Optional[str] = None
    sent_by: Optional[int] = None
    sent_at: datetime
    telegram_message_id: Optional[int] = None
    delivery_status: str

    class Config:
        from_attributes = True


# =========================
# INVITE
# =========================

class SendInvitesRequest(BaseModel):
    """Рассылка invite-ссылок участникам"""
    member_ids: List[int] = []  # ID из messenger_chat_members, пусто = всем

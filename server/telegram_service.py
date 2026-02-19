"""
Telegram сервис для CRM мессенджер-чатов.
Поддерживает два режима:
1. MTProto (Pyrogram) — автоматическое создание групп
2. Bot API — управление, сообщения, файлы, уведомления
"""
import os
import json
import asyncio
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Флаг доступности Pyrogram (MTProto)
PYROGRAM_AVAILABLE = False
try:
    from pyrogram import Client as PyrogramClient
    from pyrogram.types import ChatPhoto
    from pyrogram.errors import (
        FloodWait, UserNotParticipant, ChatAdminRequired,
        PeerIdInvalid, PhoneNumberInvalid, SessionPasswordNeeded
    )
    PYROGRAM_AVAILABLE = True
except ImportError:
    logger.info("Pyrogram не установлен — автосоздание групп недоступно")

# Флаг доступности aiogram (Bot API)
AIOGRAM_AVAILABLE = False
try:
    from aiogram import Bot
    from aiogram.types import (
        InputMediaPhoto, InputMediaDocument,
        FSInputFile, BufferedInputFile
    )
    from aiogram.enums import ParseMode
    AIOGRAM_AVAILABLE = True
except ImportError:
    logger.warning("aiogram не установлен — Telegram Bot API недоступен")


class TelegramService:
    """Единый сервис для работы с Telegram"""

    def __init__(self):
        self._bot: Optional[Any] = None
        self._pyrogram_client: Optional[Any] = None
        self._bot_token: Optional[str] = None
        self._api_id: Optional[int] = None
        self._api_hash: Optional[str] = None
        self._phone: Optional[str] = None
        self._initialized = False

    def configure(self, settings: Dict[str, str]):
        """Конфигурация из настроек БД"""
        self._bot_token = settings.get("telegram_bot_token", "")
        api_id = settings.get("telegram_api_id", "")
        self._api_id = int(api_id) if api_id else None
        self._api_hash = settings.get("telegram_api_hash", "")
        self._phone = settings.get("telegram_phone", "")

        # Инициализация Bot API
        if self._bot_token and AIOGRAM_AVAILABLE:
            self._bot = Bot(token=self._bot_token)
            logger.info("Telegram Bot API инициализирован")

        self._initialized = True

    @property
    def bot_available(self) -> bool:
        """Bot API доступен"""
        return self._bot is not None

    @property
    def mtproto_available(self) -> bool:
        """MTProto (Pyrogram) доступен"""
        return (
            PYROGRAM_AVAILABLE
            and self._api_id is not None
            and bool(self._api_hash)
            and bool(self._phone)
        )

    # ========================================
    # MTProto — авторизация (Pyrogram)
    # ========================================

    async def send_auth_code(self) -> str:
        """Отправить код подтверждения для MTProto авторизации.
        Клиент остаётся подключённым до verify/resend.
        Сессия сохраняется на диск для доступа с другого воркера.
        Возвращает phone_code_hash.
        """
        if not PYROGRAM_AVAILABLE:
            raise RuntimeError("Pyrogram не установлен")
        if not self._api_id or not self._api_hash or not self._phone:
            raise RuntimeError("API ID, API Hash и телефон должны быть заполнены")

        # Закрыть предыдущий auth-клиент если был
        if hasattr(self, '_auth_client') and self._auth_client:
            try:
                if self._auth_client.is_connected:
                    await self._auth_client.disconnect()
            except Exception:
                pass
            self._auth_client = None

        session_path = os.path.join(os.path.dirname(__file__), "telegram_session")
        # Удаляем старый невалидный файл сессии если есть
        session_file = session_path + ".session"
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
                logger.info("Удалён старый файл сессии")
            except Exception:
                pass

        client = PyrogramClient(
            session_path,
            api_id=self._api_id,
            api_hash=self._api_hash,
        )
        await client.connect()
        sent_code = await client.send_code(self._phone)
        logger.info(f"Код подтверждения отправлен на {self._phone}, тип: {sent_code.type}")

        # Сохраняем сессию на диск (для доступа другим воркером)
        try:
            await client.storage.save()
            logger.info("Сессия сохранена на диск")
        except Exception as e:
            logger.warning(f"Не удалось сохранить сессию: {e}")

        # Сохраняем клиент живым — нужен для verify_auth_code / resend
        self._auth_client = client
        self._auth_phone_code_hash = sent_code.phone_code_hash
        return sent_code.phone_code_hash

    async def _get_or_restore_auth_client(self, phone_code_hash: str):
        """Получить живой auth-клиент или восстановить из файла сессии."""
        client = getattr(self, '_auth_client', None)
        if client and client.is_connected:
            return client

        # Восстановление: другой воркер — загружаем сессию с диска
        session_path = os.path.join(os.path.dirname(__file__), "telegram_session")
        session_file = session_path + ".session"
        if not os.path.exists(session_file):
            raise RuntimeError("Нет файла сессии. Нажмите «Запросить код» заново.")

        logger.info("Восстановление auth-клиента из файла сессии (другой воркер)")
        client = PyrogramClient(
            session_path,
            api_id=self._api_id,
            api_hash=self._api_hash,
        )
        await client.connect()
        self._auth_client = client
        self._auth_phone_code_hash = phone_code_hash
        return client

    async def send_auth_code_sms(self) -> str:
        """Отправить код сразу по SMS (send_code + resend_code в одном вызове).
        Создаёт свежий клиент, отправляет код, моментально переключает на SMS.
        """
        if not PYROGRAM_AVAILABLE:
            raise RuntimeError("Pyrogram не установлен")
        if not self._api_id or not self._api_hash or not self._phone:
            raise RuntimeError("API ID, API Hash и телефон должны быть заполнены")

        # Закрыть предыдущий auth-клиент
        if hasattr(self, '_auth_client') and self._auth_client:
            try:
                if self._auth_client.is_connected:
                    await self._auth_client.disconnect()
            except Exception:
                pass
            self._auth_client = None

        session_path = os.path.join(os.path.dirname(__file__), "telegram_session")
        session_file = session_path + ".session"
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
            except Exception:
                pass

        client = PyrogramClient(
            session_path,
            api_id=self._api_id,
            api_hash=self._api_hash,
        )
        await client.connect()

        # Шаг 1: send_code — Telegram отправит код в приложение
        sent_code = await client.send_code(self._phone)
        logger.info(f"send_code: тип={sent_code.type}, next_type={getattr(sent_code, 'next_type', 'N/A')}")

        # Шаг 2: сразу resend_code — переключить на SMS
        try:
            resent = await client.resend_code(self._phone, sent_code.phone_code_hash)
            final_hash = resent.phone_code_hash
            logger.info(f"resend_code (SMS): тип={resent.type}")
        except Exception as e:
            logger.warning(f"resend_code не удался ({e}), используем код из приложения")
            final_hash = sent_code.phone_code_hash

        # Сохраняем сессию на диск
        try:
            await client.storage.save()
        except Exception:
            pass

        self._auth_client = client
        self._auth_phone_code_hash = final_hash
        return final_hash

    async def verify_auth_code(self, phone_code_hash: str, code: str) -> Dict[str, Any]:
        """Подтвердить код и завершить авторизацию MTProto.
        Использует живой клиент или восстанавливает из файла сессии.
        """
        if not PYROGRAM_AVAILABLE:
            raise RuntimeError("Pyrogram не установлен")

        client = await self._get_or_restore_auth_client(phone_code_hash)

        try:
            await client.sign_in(self._phone, phone_code_hash, code)
            me = await client.get_me()
            logger.info(f"MTProto авторизация успешна: {me.first_name} (@{me.username or 'N/A'})")
            # stop() сохраняет сессию на диск
            await client.stop()
            self._auth_client = None
            # Сбросить кэшированный рабочий клиент
            self._pyrogram_client = None
            return {
                "first_name": me.first_name or "",
                "last_name": me.last_name or "",
                "username": me.username or "",
            }
        except SessionPasswordNeeded:
            try:
                await client.disconnect()
            except Exception:
                pass
            self._auth_client = None
            raise RuntimeError("Аккаунт защищён двухфакторной аутентификацией (2FA). "
                               "Отключите облачный пароль в Telegram и повторите.")
        except Exception:
            # Не закрываем клиент — пусть пользователь попробует другой код
            raise

    async def check_session_valid(self) -> Dict[str, Any]:
        """Проверить, есть ли валидная Pyrogram-сессия.
        Возвращает info о пользователе или None.
        """
        if not PYROGRAM_AVAILABLE or not self._api_id or not self._api_hash:
            return {"valid": False}

        session_path = os.path.join(os.path.dirname(__file__), "telegram_session")
        session_file = session_path + ".session"
        if not os.path.exists(session_file):
            return {"valid": False}

        client = PyrogramClient(
            session_path,
            api_id=self._api_id,
            api_hash=self._api_hash,
        )
        try:
            await client.connect()
            me = await client.get_me()
            await client.disconnect()
            return {
                "valid": True,
                "first_name": me.first_name or "",
                "last_name": me.last_name or "",
                "username": me.username or "",
            }
        except Exception as e:
            logger.warning(f"Сессия невалидна: {e}")
            try:
                await client.disconnect()
            except Exception:
                pass
            return {"valid": False}

    # ========================================
    # MTProto — создание групп (Pyrogram)
    # ========================================

    async def _get_pyrogram_client(self) -> Any:
        """Получить или создать Pyrogram клиент"""
        if not self.mtproto_available:
            raise RuntimeError("MTProto не настроен")

        if self._pyrogram_client is None:
            session_path = os.path.join(
                os.path.dirname(__file__), "telegram_session"
            )
            self._pyrogram_client = PyrogramClient(
                session_path,
                api_id=self._api_id,
                api_hash=self._api_hash,
                phone_number=self._phone,
            )

        if not self._pyrogram_client.is_connected:
            await self._pyrogram_client.start()

        return self._pyrogram_client

    async def create_group(
        self,
        title: str,
        photo_path: Optional[str] = None,
        bot_username: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Создать группу через MTProto.
        Возвращает: {chat_id, title, invite_link}
        """
        client = await self._get_pyrogram_client()

        try:
            # Создаём группу (нужен хотя бы один участник — бот)
            users = []
            if bot_username:
                users.append(bot_username)

            group = await client.create_group(title, users or ["me"])
            chat_id = group.id

            # Устанавливаем фото
            if photo_path and os.path.exists(photo_path):
                try:
                    await client.set_chat_photo(
                        chat_id=chat_id, photo=photo_path
                    )
                except Exception as e:
                    logger.warning(f"Не удалось установить фото группы: {e}")

            # Генерируем invite-ссылку
            invite_link = await client.export_chat_invite_link(chat_id)

            logger.info(f"Группа создана: {title} (chat_id={chat_id})")
            return {
                "chat_id": chat_id,
                "title": title,
                "invite_link": invite_link,
            }

        except FloodWait as e:
            logger.error(f"Telegram FloodWait: ожидание {e.value} сек")
            raise RuntimeError(
                f"Telegram ограничил запросы. Повторите через {e.value} сек."
            )
        except Exception as e:
            logger.error(f"Ошибка создания группы: {e}")
            raise

    async def delete_group(self, chat_id: int) -> bool:
        """Удалить группу через MTProto"""
        try:
            client = await self._get_pyrogram_client()
            await client.delete_supergroup(chat_id)
            logger.info(f"Группа {chat_id} удалена")
            return True
        except Exception as e:
            logger.warning(f"Не удалось удалить группу {chat_id}: {e}")
            # Пробуем через бота покинуть чат
            if self.bot_available:
                try:
                    await self._bot.leave_chat(chat_id)
                    return True
                except Exception:
                    pass
            return False

    # ========================================
    # Bot API — привязка и управление
    # ========================================

    async def verify_bot_in_chat(self, chat_id: int) -> bool:
        """Проверить, что бот есть в чате"""
        if not self.bot_available:
            return False
        try:
            chat = await self._bot.get_chat(chat_id)
            return chat is not None
        except Exception:
            return False

    async def get_chat_info(self, chat_id: int) -> Optional[Dict]:
        """Получить информацию о чате"""
        if not self.bot_available:
            return None
        try:
            chat = await self._bot.get_chat(chat_id)
            return {
                "id": chat.id,
                "title": chat.title,
                "type": chat.type,
                "invite_link": chat.invite_link,
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о чате {chat_id}: {e}")
            return None

    async def set_chat_photo(self, chat_id: int, photo_path: str) -> bool:
        """Установить фото чата через Bot API"""
        if not self.bot_available:
            return False
        try:
            photo = FSInputFile(photo_path)
            await self._bot.set_chat_photo(chat_id=chat_id, photo=photo)
            return True
        except Exception as e:
            logger.warning(f"Не удалось установить фото чата: {e}")
            return False

    async def get_invite_link(self, chat_id: int) -> Optional[str]:
        """Получить или создать invite-ссылку"""
        if not self.bot_available:
            return None
        try:
            link = await self._bot.export_chat_invite_link(chat_id)
            return link
        except Exception as e:
            logger.error(f"Ошибка получения invite-ссылки: {e}")
            return None

    async def leave_chat(self, chat_id: int) -> bool:
        """Бот покидает чат"""
        if not self.bot_available:
            return False
        try:
            await self._bot.leave_chat(chat_id)
            return True
        except Exception as e:
            logger.warning(f"Ошибка выхода из чата: {e}")
            return False

    # ========================================
    # Bot API — сообщения
    # ========================================

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
    ) -> Optional[int]:
        """
        Отправить текстовое сообщение.
        Возвращает telegram_message_id или None.
        """
        if not self.bot_available:
            logger.warning("Bot API недоступен")
            return None
        try:
            pm = ParseMode.HTML if parse_mode == "HTML" else ParseMode.MARKDOWN
            msg = await self._bot.send_message(
                chat_id=chat_id, text=text, parse_mode=pm
            )
            return msg.message_id
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в {chat_id}: {e}")
            return None

    async def send_document(
        self,
        chat_id: int,
        file_path: str,
        caption: Optional[str] = None,
    ) -> Optional[int]:
        """Отправить документ (файл)"""
        if not self.bot_available:
            return None
        try:
            document = FSInputFile(file_path)
            msg = await self._bot.send_document(
                chat_id=chat_id, document=document, caption=caption
            )
            return msg.message_id
        except Exception as e:
            logger.error(f"Ошибка отправки документа: {e}")
            return None

    async def send_document_from_bytes(
        self,
        chat_id: int,
        file_bytes: bytes,
        filename: str,
        caption: Optional[str] = None,
    ) -> Optional[int]:
        """Отправить документ из байтов"""
        if not self.bot_available:
            return None
        try:
            document = BufferedInputFile(file_bytes, filename=filename)
            msg = await self._bot.send_document(
                chat_id=chat_id, document=document, caption=caption
            )
            return msg.message_id
        except Exception as e:
            logger.error(f"Ошибка отправки документа из байтов: {e}")
            return None

    async def send_media_group(
        self,
        chat_id: int,
        photos: List[str],
        caption: Optional[str] = None,
    ) -> Optional[List[int]]:
        """
        Отправить галерею фото (до 10 штук).
        photos — список путей к файлам.
        """
        if not self.bot_available:
            return None
        if not photos:
            return None

        try:
            media = []
            for i, photo_path in enumerate(photos[:10]):
                file = FSInputFile(photo_path)
                media.append(
                    InputMediaPhoto(
                        media=file,
                        caption=caption if i == 0 else None,
                        parse_mode=ParseMode.HTML if caption else None,
                    )
                )

            messages = await self._bot.send_media_group(
                chat_id=chat_id, media=media
            )
            return [m.message_id for m in messages]
        except Exception as e:
            logger.error(f"Ошибка отправки галереи: {e}")
            return None

    async def send_media_group_from_bytes(
        self,
        chat_id: int,
        photos: List[Dict[str, Any]],
        caption: Optional[str] = None,
    ) -> Optional[List[int]]:
        """
        Отправить галерею из байтов.
        photos — список {'bytes': bytes, 'filename': str}
        """
        if not self.bot_available:
            return None
        if not photos:
            return None

        try:
            media = []
            for i, photo_data in enumerate(photos[:10]):
                file = BufferedInputFile(
                    photo_data["bytes"], filename=photo_data["filename"]
                )
                media.append(
                    InputMediaPhoto(
                        media=file,
                        caption=caption if i == 0 else None,
                        parse_mode=ParseMode.HTML if caption else None,
                    )
                )

            messages = await self._bot.send_media_group(
                chat_id=chat_id, media=media
            )
            return [m.message_id for m in messages]
        except Exception as e:
            logger.error(f"Ошибка отправки галереи из байтов: {e}")
            return None

    # ========================================
    # Скрипт-сообщения
    # ========================================

    def render_template(
        self, template: str, context: Dict[str, str]
    ) -> str:
        """Подставить переменные в шаблон скрипта"""
        result = template
        for key, value in context.items():
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, str(value) if value else "")
        return result

    async def send_script_message(
        self,
        chat_id: int,
        template: str,
        context: Dict[str, str],
    ) -> Optional[int]:
        """Отправить сообщение по скрипту с подстановкой переменных"""
        text = self.render_template(template, context)
        return await self.send_message(chat_id, text, parse_mode="HTML")

    # ========================================
    # Привязка чата по invite-ссылке
    # ========================================

    async def resolve_invite_link(self, invite_link: str) -> Optional[int]:
        """
        Извлечь chat_id из invite-ссылки.
        Бот должен быть уже добавлен в чат.
        """
        if not self.bot_available:
            return None

        # Если это числовой ID
        try:
            return int(invite_link)
        except ValueError:
            pass

        # Пробуем получить чат напрямую
        # (работает только если бот уже в чате)
        # Для t.me/+hash ссылок бот не может resolve без вступления
        logger.info(
            f"Для привязки чата бот должен быть добавлен вручную. "
            f"Ссылка: {invite_link}"
        )
        return None

    # ========================================
    # Очистка
    # ========================================

    async def close(self):
        """Закрыть соединения"""
        if self._bot:
            await self._bot.session.close()
            self._bot = None

        if self._pyrogram_client and self._pyrogram_client.is_connected:
            await self._pyrogram_client.stop()
            self._pyrogram_client = None

        self._initialized = False


# Синглтон сервиса
_telegram_service: Optional[TelegramService] = None


def get_telegram_service() -> TelegramService:
    """Получить экземпляр TelegramService"""
    global _telegram_service
    if _telegram_service is None:
        _telegram_service = TelegramService()
    return _telegram_service

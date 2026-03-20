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
import sqlite3 as _sqlite3
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Флаг доступности Pyrogram (MTProto)
PYROGRAM_AVAILABLE = False
try:
    from pyrogram import Client as PyrogramClient, raw
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
        self._mtproto_lock = asyncio.Lock()

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
        Использует основной клиент (под _mtproto_lock), не создавая отдельного.
        """
        if not PYROGRAM_AVAILABLE or not self._api_id or not self._api_hash:
            return {"valid": False}

        session_file = self._get_session_path() + ".session"
        if not os.path.exists(session_file):
            return {"valid": False}

        async with self._mtproto_lock:
            try:
                client = await self._ensure_pyrogram_client()
                me = await client.get_me()
                return {
                    "valid": True,
                    "first_name": me.first_name or "",
                    "last_name": me.last_name or "",
                    "username": me.username or "",
                }
            except Exception as e:
                logger.warning(f"Сессия невалидна: {e}")
                # Принудительно очистить клиент, чтобы не оставлять stale connection
                self._force_close_client()
                return {"valid": False}

    # ========================================
    # MTProto — создание групп (Pyrogram)
    # ========================================

    def _get_session_path(self) -> str:
        """Путь к файлу сессии Pyrogram (без расширения .session)."""
        return os.path.join(os.path.dirname(__file__), "telegram_session")

    def _prepare_session_db(self) -> None:
        """Подготовить SQLite session DB: снять stale locks, переключить на WAL.
        Вызывать ПЕРЕД созданием PyrogramClient.
        """
        db_path = self._get_session_path() + ".session"
        if not os.path.exists(db_path):
            return

        try:
            conn = _sqlite3.connect(db_path, timeout=30)
            conn.execute("PRAGMA busy_timeout = 30000")
            # WAL mode — намного устойчивее к блокировкам
            conn.execute("PRAGMA journal_mode = WAL")
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
            conn.close()
            logger.debug("Session DB подготовлена: WAL mode, checkpoint OK")
        except Exception as e:
            logger.warning(f"Не удалось подготовить session DB: {e}")
            # Крайняя мера — удаляем stale journal/wal/shm файлы
            self._cleanup_session_locks()

    def _cleanup_session_locks(self) -> None:
        """Удалить stale lock-файлы SQLite сессии."""
        db_path = self._get_session_path() + ".session"
        for ext in ("-wal", "-shm", "-journal"):
            lock_file = db_path + ext
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                    logger.info(f"Удалён stale lock: {lock_file}")
                except Exception as rm_err:
                    logger.warning(f"Не удалось удалить {lock_file}: {rm_err}")

    def _force_close_client(self) -> None:
        """Принудительно закрыть Pyrogram клиент и его SQLite-соединение."""
        client = self._pyrogram_client
        if client is None:
            return
        # Закрыть SQLite storage напрямую (синхронный метод)
        try:
            if hasattr(client, 'storage') and client.storage:
                if hasattr(client.storage, 'conn') and client.storage.conn:
                    client.storage.conn.close()
                    logger.debug("SQLite storage connection закрыта принудительно")
        except Exception:
            pass
        self._pyrogram_client = None

    async def _ensure_pyrogram_client(self) -> Any:
        """Получить или создать Pyrogram клиент.
        ВАЖНО: вызывать только под self._mtproto_lock!
        При ошибке 'database is locked' — подготавливает DB и пересоздаёт клиент.
        """
        if not self.mtproto_available:
            raise RuntimeError("MTProto не настроен")

        max_attempts = 3
        for attempt in range(max_attempts):
            if self._pyrogram_client is None:
                # Подготовка session DB перед созданием клиента
                self._prepare_session_db()
                session_path = self._get_session_path()
                self._pyrogram_client = PyrogramClient(
                    session_path,
                    api_id=self._api_id,
                    api_hash=self._api_hash,
                    phone_number=self._phone,
                )

            if not self._pyrogram_client.is_connected:
                try:
                    await self._pyrogram_client.start()
                except Exception as e:
                    err_msg = str(e)
                    logger.error(
                        f"Pyrogram start() failed (попытка {attempt+1}/{max_attempts}): {err_msg}"
                    )
                    if "database is locked" in err_msg and attempt < max_attempts - 1:
                        delay = 2.0 + attempt * 2.0  # 2с, 4с
                        logger.warning(
                            f"SQLite locked — cleanup + retry через {delay}с"
                        )
                        # Агрессивный cleanup: закрыть storage напрямую
                        try:
                            if self._pyrogram_client.is_connected:
                                await self._pyrogram_client.disconnect()
                        except Exception:
                            pass
                        self._force_close_client()
                        # Подчистить lock-файлы
                        self._cleanup_session_locks()
                        await asyncio.sleep(delay)
                        continue
                    raise
            break

        return self._pyrogram_client

    async def create_group(
        self,
        title: str,
        photo_path: Optional[str] = None,
        bot_username: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Создать группу через MTProto.
        Порядок: создать basic group → мигрировать в supergroup → настроить.
        Возвращает: {chat_id, title, invite_link}
        """
        async with self._mtproto_lock:
            client = await self._ensure_pyrogram_client()

            try:
                # 1. Создаём базовую группу (нужен хотя бы один участник — бот)
                users = [bot_username] if bot_username else ["me"]
                group = await client.create_group(title, users)
                chat_id = group.id
                logger.info(f"Базовая группа создана: {title} (chat_id={chat_id})")

                # 2. Принудительная миграция в supergroup СРАЗУ
                #    (чтобы все последующие операции работали с единым chat_id)
                try:
                    updates = await client.invoke(
                        raw.functions.messages.MigrateChat(chat_id=-chat_id)
                    )
                    for ch in getattr(updates, 'chats', []):
                        if getattr(ch, 'megagroup', False):
                            old_id = chat_id
                            chat_id = -int(f"100{ch.id}")
                            logger.info(
                                f"Мигрирована в supergroup: {old_id} → {chat_id}"
                            )
                            break
                except Exception as mig_err:
                    logger.warning(f"Миграция в supergroup: {mig_err}")

                # 3. Повышаем бота до админа (уже на supergroup)
                if bot_username:
                    try:
                        from pyrogram.types import ChatPrivileges
                        await client.promote_chat_member(
                            chat_id, bot_username,
                            privileges=ChatPrivileges(
                                can_manage_chat=True,
                                can_delete_messages=True,
                                can_restrict_members=True,
                                can_invite_users=True,
                                can_pin_messages=True,
                            )
                        )
                        logger.info(f"Бот {bot_username} повышен до админа в {chat_id}")
                    except Exception as e:
                        logger.warning(f"Не удалось повысить бота до админа: {e}")

                # 4. Устанавливаем фото
                if photo_path and os.path.exists(photo_path):
                    try:
                        await client.set_chat_photo(
                            chat_id=chat_id, photo=photo_path
                        )
                    except Exception as e:
                        logger.warning(f"Не удалось установить фото группы: {e}")

                # 5. Генерируем invite-ссылку
                try:
                    invite_link = await client.export_chat_invite_link(chat_id)
                except Exception as e:
                    logger.warning(f"export_chat_invite_link({chat_id}) ошибка: {e}")
                    invite_link = None

                # 6. Включаем видимость истории для новых участников
                try:
                    peer = await client.resolve_peer(chat_id)
                    if hasattr(peer, 'channel_id'):
                        channel = raw.types.InputChannel(
                            channel_id=peer.channel_id,
                            access_hash=peer.access_hash
                        )
                        await client.invoke(
                            raw.functions.channels.TogglePreHistoryHidden(
                                channel=channel,
                                enabled=False  # False = история ВИДНА новым участникам
                            )
                        )
                        logger.info(f"История чата {chat_id} открыта для новых участников")
                except Exception as e:
                    logger.warning(f"Не удалось открыть историю чата {chat_id}: {e}")

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

    async def delete_group(self, chat_id: int, member_tg_ids: list = None) -> bool:
        """Удалить группу через MTProto: кикнуть всех участников, потом удалить группу.
        Если MTProto недоступен — fallback на бота (кик по member_tg_ids + leave).
        member_tg_ids — telegram_user_id участников из БД (для fallback через бота).
        """
        mtproto_success = False

        # Сначала пробуем через MTProto (полное удаление)
        if self.mtproto_available:
            try:
                async with self._mtproto_lock:
                    client = await self._ensure_pyrogram_client()

                    # Кикаем всех участников перед удалением
                    try:
                        me = await client.get_me()
                        my_id = me.id
                        kicked_count = 0
                        async for member in client.get_chat_members(chat_id):
                            if member.user.id == my_id:
                                continue
                            try:
                                await client.ban_chat_member(chat_id, member.user.id)
                                kicked_count += 1
                            except Exception as kick_err:
                                logger.warning(f"Не удалось кикнуть {member.user.id}: {kick_err}")
                        logger.info(f"Исключено {kicked_count} участников из {chat_id}")
                        mtproto_success = True
                    except Exception as members_err:
                        logger.warning(f"Не удалось получить участников {chat_id}: {members_err}")

                    # Пробуем удалить группу целиком
                    try:
                        await client.delete_supergroup(chat_id)
                        logger.info(f"Группа {chat_id} удалена через MTProto")
                        return True
                    except Exception as del_err:
                        logger.warning(f"delete_supergroup({chat_id}): {del_err}")
                        try:
                            await client.leave_chat(chat_id)
                            mtproto_success = True
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"MTProto ошибка удаления группы {chat_id}: {e}")

        # Если MTProto полностью справился — не нужен fallback
        if mtproto_success:
            return True

        # Fallback: бот кикает участников по списку из БД и покидает чат
        if self.bot_available:
            kicked_any = False
            try:
                if member_tg_ids:
                    bot_me = await self._bot.get_me()
                    for tg_id in member_tg_ids:
                        if tg_id == bot_me.id:
                            continue
                        try:
                            await self._bot.ban_chat_member(chat_id, tg_id)
                            kicked_any = True
                            logger.debug(f"Бот кикнул {tg_id} из {chat_id}")
                        except Exception as kick_err:
                            logger.warning(f"Бот не смог кикнуть {tg_id}: {kick_err}")
            except Exception as e:
                logger.warning(f"Бот: ошибка кика участников {chat_id}: {e}")

            try:
                await self._bot.leave_chat(chat_id)
                logger.info(f"Бот покинул чат {chat_id} (fallback)")
                return True
            except Exception as bot_err:
                logger.warning(f"Бот не смог покинуть чат {chat_id}: {bot_err}")
                return kicked_any

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

    async def join_chat_by_link(self, invite_link: str) -> Optional[Dict[str, Any]]:
        """
        Вступить в чат по invite-ссылке через MTProto и добавить бота.
        Возвращает {chat_id, title, invite_link} или None.
        """
        # Если это числовой ID — бот просто пробует получить чат
        try:
            numeric_id = int(invite_link)
            if self.bot_available:
                try:
                    chat = await self._bot.get_chat(numeric_id)
                    return {
                        "chat_id": chat.id,
                        "title": chat.title or "",
                        "invite_link": invite_link,
                    }
                except Exception:
                    pass
            return {"chat_id": numeric_id, "title": "", "invite_link": invite_link}
        except ValueError:
            pass

        # Вступаем через MTProto (user-аккаунт может join по invite-ссылке)
        if not self.mtproto_available:
            logger.warning("MTProto недоступен — не могу вступить в чат по ссылке")
            return None

        try:
            async with self._mtproto_lock:
                client = await self._ensure_pyrogram_client()

                # Пробуем вступить; если уже участник — получаем чат по ссылке
                try:
                    chat = await client.join_chat(invite_link)
                    chat_id = chat.id
                    title = chat.title or ""
                    logger.info(f"MTProto вступил в чат: {title} (chat_id={chat_id})")
                except Exception as join_err:
                    err_msg = str(join_err)
                    if "USER_ALREADY_PARTICIPANT" in err_msg or "INVITE_REQUEST_SENT" in err_msg:
                        # Уже в чате — получаем info через get_chat по ссылке
                        logger.info(f"Уже участник чата, получаем данные: {invite_link}")
                        try:
                            chat = await client.get_chat(invite_link)
                            chat_id = chat.id
                            title = chat.title or ""
                        except Exception:
                            # Пробуем извлечь hash из ссылки и получить info через API
                            import re
                            hash_match = re.search(r't\.me/\+([A-Za-z0-9_-]+)', invite_link)
                            if hash_match:
                                try:
                                    from pyrogram import raw
                                    invite_info = await client.invoke(
                                        raw.functions.messages.CheckChatInvite(
                                            hash=hash_match.group(1)
                                        )
                                    )
                                    # ChatInviteAlready — мы уже в чате
                                    ch = getattr(invite_info, 'chat', None)
                                    if ch:
                                        chat_id = -int(f"100{ch.id}") if getattr(ch, 'megagroup', False) or getattr(ch, 'broadcast', False) else -ch.id
                                        title = getattr(ch, 'title', '') or ""
                                        logger.info(f"CheckChatInvite → chat_id={chat_id}, title={title}")
                                    else:
                                        raise RuntimeError("CheckChatInvite не вернул chat")
                                except Exception as check_err:
                                    logger.error(f"CheckChatInvite ошибка: {check_err}")
                                    raise join_err
                            else:
                                raise join_err
                    else:
                        raise

                # Добавляем бота в чат и повышаем до админа
                if self.bot_available:
                    try:
                        bot_me = await self._bot.get_me()
                        bot_username = bot_me.username
                        if bot_username:
                            # Проверяем, не в чате ли уже бот
                            bot_already_in = False
                            try:
                                member = await client.get_chat_member(chat_id, bot_username)
                                if member and member.status.value in ("member", "administrator", "owner"):
                                    bot_already_in = True
                                    logger.info(f"Бот @{bot_username} уже в чате {chat_id}")
                            except Exception:
                                pass

                            if not bot_already_in:
                                await client.add_chat_members(chat_id, bot_username)
                                logger.info(f"Бот @{bot_username} добавлен в чат {chat_id}")

                            # Повышаем бота до админа (даже если уже в чате — возможно без прав)
                            try:
                                from pyrogram.types import ChatPrivileges as _CP
                                await client.promote_chat_member(
                                    chat_id, bot_username,
                                    privileges=_CP(
                                        can_manage_chat=True,
                                        can_post_messages=True,
                                        can_edit_messages=True,
                                        can_delete_messages=True,
                                        can_invite_users=True,
                                        can_restrict_members=True,
                                        can_pin_messages=True,
                                        can_manage_video_chats=True,
                                    )
                                )
                                logger.info(f"Бот повышен до админа в чате {chat_id}")
                            except Exception as promo_err:
                                logger.warning(f"Не удалось повысить бота: {promo_err}")
                    except Exception as bot_err:
                        logger.warning(f"Не удалось добавить бота в чат: {bot_err}")

                # Экспортируем invite-ссылку (если есть права)
                final_link = invite_link
                try:
                    exported = await client.export_chat_invite_link(chat_id)
                    if exported:
                        final_link = exported
                except Exception:
                    pass

                return {
                    "chat_id": chat_id,
                    "title": title,
                    "invite_link": final_link,
                }
        except Exception as e:
            logger.error(f"Ошибка вступления в чат по ссылке {invite_link}: {e}")
            return None

    async def resolve_invite_link(self, invite_link: str) -> Optional[int]:
        """
        Извлечь chat_id из invite-ссылки (legacy, вызывает join_chat_by_link).
        """
        result = await self.join_chat_by_link(invite_link)
        return result["chat_id"] if result else None

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

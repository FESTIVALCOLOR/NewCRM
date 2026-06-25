"""
Telegram Bot handlers — обработчики команд бота для CRM.
Обрабатывает привязку Telegram аккаунта сотрудника через /start TOKEN.
"""

from datetime import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Флаг доступности aiogram
AIOGRAM_AVAILABLE = False
try:
    from aiogram import Router
    from aiogram.filters import CommandStart
    from aiogram.types import Message

    AIOGRAM_AVAILABLE = True
except ImportError:
    logger.warning("aiogram не установлен — Telegram bot handlers недоступны")

if AIOGRAM_AVAILABLE:
    router = Router()

    @router.message(CommandStart())
    async def handle_start(message: Message):
        """Обработчик команды /start для привязки Telegram аккаунта сотрудника"""
        from database import Employee, SessionLocal

        args = message.text.split(maxsplit=1)
        token = args[1] if len(args) > 1 else None

        if not token:
            await message.answer("Добро пожаловать в CRM Festival Color!\n\nДля подключения уведомлений используйте ссылку из приветственного письма.")
            return

        db = SessionLocal()
        try:
            employee = db.query(Employee).filter(Employee.telegram_link_token == token, Employee.telegram_link_token_expires > datetime.utcnow()).first()

            if not employee:
                await message.answer("Ссылка недействительна или устарела.\n\nПопросите администратора выслать приглашение повторно.")
                return

            # Привязываем Telegram ID к сотруднику
            employee.telegram_user_id = message.from_user.id
            employee.telegram_link_token = None
            employee.telegram_link_token_expires = None
            db.commit()

            # Загружаем аватар из Telegram, если фото ещё не задано
            if not employee.photo_url:
                try:
                    import io
                    import os

                    photos = await message.bot.get_user_profile_photos(user_id=message.from_user.id, limit=1)
                    if photos.total_count > 0:
                        file_id = photos.photos[0][-1].file_id
                        buf = io.BytesIO()
                        await message.bot.download(file_id, destination=buf)
                        buf.seek(0)
                        os.makedirs("uploads/avatars", exist_ok=True)
                        filename = f"employee_{employee.id}.jpg"
                        with open(os.path.join("uploads", "avatars", filename), "wb") as f:
                            f.write(buf.read())
                        base_url = os.environ.get("BASE_URL", "https://crm.festivalcolor.ru")
                        employee.photo_url = f"{base_url}/api/v1/avatars/{filename}"
                        db.commit()
                        logger.info(f"Telegram аватар сохранён: employee_id={employee.id}")
                except Exception as tg_err:
                    logger.warning(f"Не удалось загрузить Telegram аватар employee {employee.id}: {tg_err}")

            # Определяем имя для обращения
            parts = employee.full_name.split()
            first_name = parts[1] if len(parts) > 1 else employee.full_name

            await message.answer(
                f"Отлично, {first_name}!\n\n"
                f"Ваш аккаунт привязан к CRM Festival Color.\n"
                f"Теперь вы будете получать уведомления:\n\n"
                f"• Назначение на стадии\n"
                f"• Напоминания о дедлайнах\n"
                f"• Изменения по проектам"
            )
            logger.info(f"Telegram привязан: employee_id={employee.id}, telegram_user_id={message.from_user.id}")

        except Exception as e:
            logger.error(f"Ошибка привязки Telegram для токена {token}: {e}")
            await message.answer("Произошла ошибка. Попробуйте позже.")
        finally:
            db.close()

else:
    # Заглушка если aiogram не установлен
    router = None


async def sync_employee_telegram_avatars():
    """При старте сервера: загружает аватары из Telegram для уже привязанных
    сотрудников у которых нет фото (photo_url IS NULL, telegram_user_id IS NOT NULL).
    Использует MTProto (Pyrogram) — Bot API заблокирован на сервере хостинга.
    Запускается однократно в фоне.
    """
    import asyncio
    import io
    import os

    await asyncio.sleep(25)  # Ждём полной инициализации Pyrogram-клиента

    from telegram_service import get_telegram_service

    tg = get_telegram_service()
    if not tg.mtproto_available:
        logger.info("Telegram avatar sync: MTProto недоступен, пропуск")
        return

    from database import Employee, SessionLocal

    db = SessionLocal()
    try:
        employees = db.query(Employee).filter(Employee.telegram_user_id.isnot(None), Employee.photo_url.is_(None)).all()
        if not employees:
            logger.info("Telegram avatar sync: нет сотрудников для синхронизации")
            return

        logger.info(f"Telegram avatar sync: начало, {len(employees)} сотрудников")
        base_url = os.environ.get("BASE_URL", "https://crm.festivalcolor.ru")

        # Получение аватаров через MTProto (Pyrogram). DC может быть заблокирован хостингом.
        try:
            async with tg._mtproto_lock:
                client = await tg._ensure_pyrogram_client()
                for emp in employees:
                    try:
                        downloaded = False
                        async for photo in client.get_chat_photos(emp.telegram_user_id, limit=1):
                            buf = await client.download_media(photo, in_memory=True)
                            if buf:
                                buf.seek(0)
                                os.makedirs("uploads/avatars", exist_ok=True)
                                filename = f"employee_{emp.id}.jpg"
                                with open(os.path.join("uploads", "avatars", filename), "wb") as f:
                                    f.write(buf.read())
                                emp.photo_url = f"{base_url}/api/v1/avatars/{filename}"
                                db.commit()
                                logger.info(f"Telegram avatar sync: сохранён employee_id={emp.id}")
                                downloaded = True
                            break
                        if not downloaded:
                            logger.info(f"Telegram avatar sync: нет фото у employee {emp.id}")
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.warning(f"Telegram avatar sync: ошибка для employee {emp.id}: {e}")
        except RuntimeError as e:
            logger.warning(f"Telegram avatar sync: MTProto недоступен — {e}")
            return
        finally:
            # Останавливаем Pyrogram после задачи — иначе internal NetworkTask/PingTask
            # уходит в бесконечный reconnect-loop при нестабильном DC (Timeweb блокирует)
            await tg.stop_pyrogram()

        logger.info("Telegram avatar sync: завершено")
    finally:
        db.close()

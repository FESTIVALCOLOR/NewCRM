"""
Telegram Bot handlers — обработчики команд бота для CRM.
Обрабатывает привязку Telegram аккаунта сотрудника через /start TOKEN.
"""
import logging
from datetime import datetime
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
        from database import SessionLocal, Employee

        args = message.text.split(maxsplit=1)
        token = args[1] if len(args) > 1 else None

        if not token:
            await message.answer(
                "Добро пожаловать в CRM Festival Color!\n\n"
                "Для подключения уведомлений используйте ссылку из приветственного письма."
            )
            return

        db = SessionLocal()
        try:
            employee = db.query(Employee).filter(
                Employee.telegram_link_token == token,
                Employee.telegram_link_token_expires > datetime.utcnow()
            ).first()

            if not employee:
                await message.answer(
                    "Ссылка недействительна или устарела.\n\n"
                    "Попросите администратора выслать приглашение повторно."
                )
                return

            # Привязываем Telegram ID к сотруднику
            employee.telegram_user_id = message.from_user.id
            employee.telegram_link_token = None
            employee.telegram_link_token_expires = None
            db.commit()

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
            logger.info(
                f"Telegram привязан: employee_id={employee.id}, "
                f"telegram_user_id={message.from_user.id}"
            )

        except Exception as e:
            logger.error(f"Ошибка привязки Telegram для токена {token}: {e}")
            await message.answer("Произошла ошибка. Попробуйте позже.")
        finally:
            db.close()

else:
    # Заглушка если aiogram не установлен
    router = None

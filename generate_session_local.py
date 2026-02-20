# -*- coding: utf-8 -*-
"""Локальная генерация Pyrogram-сессии (чистая попытка)."""
import asyncio
import os
# Фикс для Python 3.14+
asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client


API_ID = 31917427
API_HASH = "426df2dea97e625afe0f90708ef89689"
PHONE = "+79062003365"


async def main():
    print()
    print("=" * 50)
    print("  Генерация Pyrogram-сессии")
    print("=" * 50)

    # Удаляем старую сессию
    if os.path.exists("telegram_session.session"):
        os.remove("telegram_session.session")
        print("\n  Старая сессия удалена")

    client = Client(
        "telegram_session",
        api_id=API_ID,
        api_hash=API_HASH,
    )

    print(f"\n  Подключение к Telegram...")
    await client.connect()
    print(f"  Подключено!")

    # Одна чистая попытка send_code (без resend, чтобы не тратить лимит)
    print(f"\n  Отправка кода на {PHONE}...")
    print(f"  (код придёт в приложение Telegram)")
    try:
        sent = await client.send_code(PHONE)
        print(f"  Код отправлен! Тип: {sent.type}")
        final_hash = sent.phone_code_hash
    except Exception as e:
        print(f"\n  ОШИБКА: {e}")
        await client.disconnect()
        return

    # Спрашиваем: хотите переключить на SMS?
    print(f"\n  Если код НЕ пришёл в Telegram, введите 'sms' для SMS.")
    print(f"  Если код пришёл — введите его сразу.")
    user_input = input("\n  Код или 'sms': ").strip()

    if user_input.lower() == "sms":
        print(f"\n  Переключаю на SMS...")
        try:
            resent = await client.resend_code(PHONE, sent.phone_code_hash)
            print(f"  SMS отправлена! Тип: {resent.type}")
            final_hash = resent.phone_code_hash
        except Exception as e:
            print(f"  Ошибка SMS: {e}")
            print(f"  Попробуйте ввести код из Telegram-приложения")

        user_input = input("\n  Введите код: ").strip()

    if not user_input or user_input.lower() == "sms":
        print("  Код не введён. Выход.")
        await client.disconnect()
        return

    code = user_input

    try:
        await client.sign_in(PHONE, final_hash, code)
        me = await client.get_me()
        print(f"\n  УСПЕХ! Авторизован: {me.first_name} {me.last_name or ''}")
        await client.stop()
        print(f"\n  Файл сессии сохранён: telegram_session.session")
        print(f"  Теперь загрузите его на сервер.")
    except Exception as e:
        print(f"\n  ОШИБКА sign_in: {e}")
        if "PASSWORD" in str(e).upper():
            pwd = input("  Введите пароль 2FA: ").strip()
            try:
                await client.check_password(pwd)
                me = await client.get_me()
                print(f"\n  УСПЕХ! Авторизован: {me.first_name}")
                await client.stop()
                print(f"\n  Файл сессии сохранён: telegram_session.session")
            except Exception as e2:
                print(f"  Ошибка 2FA: {e2}")
                await client.disconnect()
        else:
            await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

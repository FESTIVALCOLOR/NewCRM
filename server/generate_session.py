#!/usr/bin/env python3
"""
Скрипт для интерактивной генерации Pyrogram-сессии.
Запускать ВНУТРИ Docker контейнера (или на сервере):

    docker-compose exec api python generate_session.py

При запуске:
1. Читает api_id, api_hash, phone из БД (messenger_settings)
2. Создаёт Pyrogram-клиент → он запросит код из Telegram
3. Сохраняет session-файл (telegram_session.session)

После этого MTProto станет доступен для автосоздания групп.
"""
import asyncio
import os
import sys

# Настройка пути
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from pyrogram import Client as PyrogramClient


def get_settings_from_db():
    """Прочитать настройки из PostgreSQL"""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ОШИБКА: DATABASE_URL не задан")
        sys.exit(1)

    engine = create_engine(db_url)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT setting_key, setting_value FROM messenger_settings"))
        settings = {}
        for row in rows:
            settings[row[0]] = row[1] or ""
    return settings


async def main():
    print("=" * 50)
    print("Генерация Pyrogram-сессии для MTProto")
    print("=" * 50)

    settings = get_settings_from_db()

    api_id = settings.get("telegram_api_id", "")
    api_hash = settings.get("telegram_api_hash", "")
    phone = settings.get("telegram_phone", "")

    if not api_id or not api_hash:
        print("\nОШИБКА: api_id или api_hash не заданы в настройках.")
        print("Сначала заполните их через CRM → Администрирование чатов → Telegram")
        sys.exit(1)

    if not phone:
        phone = input("\nВведите номер телефона (формат +79XXXXXXXXX): ").strip()
        if not phone:
            print("Телефон не указан.")
            sys.exit(1)

    print(f"\nAPI ID: {api_id}")
    print(f"API Hash: {api_hash[:8]}...")
    print(f"Телефон: {phone}")
    print(f"\nСоздание сессии...")

    session_path = os.path.join(os.path.dirname(__file__), "telegram_session")

    client = PyrogramClient(
        session_path,
        api_id=int(api_id),
        api_hash=api_hash,
        phone_number=phone,
    )

    await client.start()
    me = await client.get_me()
    print(f"\nУспешно! Авторизован как: {me.first_name} {me.last_name or ''} (@{me.username or 'N/A'})")

    # Сохраняем телефон в БД если его не было
    if not settings.get("telegram_phone"):
        from sqlalchemy import create_engine
        engine = create_engine(os.environ["DATABASE_URL"])
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO messenger_settings (setting_key, setting_value) VALUES (:k, :v) ON CONFLICT (setting_key) DO UPDATE SET setting_value = :v"),
                {"k": "telegram_phone", "v": phone}
            )
            conn.commit()
        print(f"Телефон {phone} сохранён в настройки.")

    await client.stop()
    print(f"\nФайл сессии: {session_path}.session")
    print("MTProto теперь доступен. Перезапустите api-контейнер:")
    print("  docker-compose restart api")


if __name__ == "__main__":
    asyncio.run(main())

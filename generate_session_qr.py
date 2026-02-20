# -*- coding: utf-8 -*-
"""QR-код авторизация для Pyrogram (без ввода кода)."""
import asyncio
import os
import sys
import base64

# Фикс для Python 3.14+
asyncio.set_event_loop(asyncio.new_event_loop())

import qrcode
from pyrogram import Client
from pyrogram.raw.functions.auth import ExportLoginToken, ImportLoginToken
from pyrogram.raw.types.auth import LoginToken, LoginTokenSuccess, LoginTokenMigrateTo


API_ID = 31917427
API_HASH = "426df2dea97e625afe0f90708ef89689"


async def main():
    print()
    print("=" * 55)
    print("  QR-код авторизация Telegram (без SMS/кода)")
    print("=" * 55)

    # Удаляем старую сессию
    if os.path.exists("telegram_session.session"):
        os.remove("telegram_session.session")
        print("\n  Старая сессия удалена")

    client = Client(
        "telegram_session",
        api_id=API_ID,
        api_hash=API_HASH,
    )

    print("\n  Подключение к Telegram...")
    await client.connect()
    print("  Подключено!")

    print()
    print("  " + "-" * 50)
    print("  ИНСТРУКЦИЯ:")
    print("  1. Откройте Telegram на телефоне")
    print("  2. Настройки -> Устройства -> Подключить устройство")
    print("  3. Отсканируйте QR-код ниже камерой")
    print("  " + "-" * 50)

    attempt = 0
    max_attempts = 60  # 5 минут (5 сек * 60)

    while attempt < max_attempts:
        try:
            result = await client.invoke(
                ExportLoginToken(
                    api_id=API_ID,
                    api_hash=API_HASH,
                    except_ids=[],
                )
            )
        except Exception as e:
            print(f"\n  Ошибка ExportLoginToken: {e}")
            await asyncio.sleep(3)
            attempt += 1
            continue

        if isinstance(result, LoginToken):
            # Генерируем QR-код
            token_b64 = base64.urlsafe_b64encode(result.token).decode().rstrip("=")
            url = f"tg://login?token={token_b64}"

            # Очистка экрана и вывод QR
            if os.name == "nt":
                os.system("cls")
            else:
                os.system("clear")

            print()
            print("  Отсканируйте QR в Telegram:")
            print("  Настройки -> Устройства -> Подключить устройство")
            print()

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            qr.print_ascii(invert=True)

            remaining = (max_attempts - attempt) * 5
            print(f"\n  Ожидание сканирования... ({remaining} сек осталось)")

            await asyncio.sleep(5)
            attempt += 1

        elif isinstance(result, LoginTokenSuccess):
            # Успех!
            user = result.authorization.user
            first_name = getattr(user, "first_name", "") or ""
            last_name = getattr(user, "last_name", "") or ""
            print(f"\n  УСПЕХ! Авторизован: {first_name} {last_name}")

            # Сохраняем сессию вручную (user_id обязателен!)
            try:
                await client.storage.user_id(user.id)
                await client.storage.is_bot(False)
            except Exception:
                pass
            try:
                await client.storage.save()
                print(f"  Сессия сохранена в файл.")
            except Exception as e:
                print(f"  Предупреждение при сохранении: {e}")

            # Закрываем соединение
            try:
                await client.disconnect()
            except Exception:
                pass

            print(f"  Файл сессии: telegram_session.session")
            print(f"\n  Готово! Можно закрывать окно.")
            input("\n  Нажмите Enter для выхода...")
            return

        elif isinstance(result, LoginTokenMigrateTo):
            # DC миграция — нужно подключиться к другому дата-центру
            print(f"\n  Миграция на DC {result.dc_id}...")
            try:
                result2 = await client.invoke(
                    ImportLoginToken(token=result.token)
                )
                if isinstance(result2, LoginTokenSuccess):
                    user = result2.authorization.user
                    first_name = getattr(user, "first_name", "") or ""
                    last_name = getattr(user, "last_name", "") or ""
                    print(f"\n  УСПЕХ! Авторизован: {first_name} {last_name}")
                    try:
                        await client.storage.user_id(user.id)
                        await client.storage.is_bot(False)
                        await client.storage.save()
                    except Exception:
                        pass
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
                    print(f"  Файл сессии: telegram_session.session")
                    input("\n  Нажмите Enter для выхода...")
                    return
            except Exception as e:
                print(f"  Ошибка миграции: {e}")
                await asyncio.sleep(3)
                attempt += 1

    print("\n  Время вышло. Запустите скрипт заново.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

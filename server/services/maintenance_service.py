"""
Сервис технического обслуживания внутренних чатов.

Задачи:
1. Перемещение в корзину ЯД файлов из чатов старше 6 месяцев (по created_at сообщения).
2. Деактивация/удаление записей об удалённых чатах.

Запускается через APScheduler или вручную при необходимости.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Пороговый возраст файлов чата для удаления с ЯД — 6 месяцев
_FILE_RETENTION_DAYS = 180

# Срок хранения удалённых договоров в корзине — 30 дней
_TRASH_CONTRACT_RETENTION_DAYS = 30


def _get_yd():
    """Получить YandexDiskService с проверкой токена."""
    try:
        from yandex_disk_service import get_yandex_disk_service

        yd = get_yandex_disk_service()
        if yd and yd.token:
            return yd
    except Exception as e:
        logger.warning(f"[maintenance] YD недоступен: {e}")
    return None


def cleanup_old_chat_files(db: Session, dry_run: bool = False) -> dict:
    """
    Переместить в корзину ЯД файлы из сообщений чата, которым > 6 месяцев.

    Параметры:
        db      — сессия SQLAlchemy
        dry_run — если True, только считает файлы, не удаляет

    Возвращает dict с количеством обработанных/удалённых файлов.
    """
    from database import InternalChatMessage

    cutoff = datetime.now(timezone.utc) - timedelta(days=_FILE_RETENTION_DAYS)
    # Сообщения с файлами старше порога
    old_messages = (
        db.query(InternalChatMessage)
        .filter(
            InternalChatMessage.message_type.in_(["file", "image", "voice"]),
            InternalChatMessage.yandex_path.isnot(None),
            InternalChatMessage.created_at < cutoff,
        )
        .all()
    )

    stats = {"checked": len(old_messages), "deleted": 0, "errors": 0, "dry_run": dry_run}

    if not old_messages:
        logger.info("[maintenance] Нет файлов для очистки")
        return stats

    yd = _get_yd() if not dry_run else None

    for msg in old_messages:
        yd_path = msg.yandex_path
        if not yd_path:
            continue

        if dry_run:
            logger.info(f"[maintenance DRY] Будет удалён: {yd_path}")
            stats["deleted"] += 1
            continue

        try:
            if yd:
                yd.delete_file(yd_path, permanently=False)  # В корзину, не навсегда
            # Очищаем путь в БД чтобы не пытаться удалить повторно
            msg.yandex_path = None
            stats["deleted"] += 1
            logger.info(f"[maintenance] Перемещён в корзину: {yd_path}")
        except Exception as e:
            stats["errors"] += 1
            logger.error(f"[maintenance] Ошибка удаления {yd_path}: {e}")

    if not dry_run:
        try:
            db.commit()
        except Exception as e:
            logger.error(f"[maintenance] Ошибка commit: {e}")
            db.rollback()

    logger.info(f"[maintenance] Итог: {stats}")
    return stats


def cleanup_deleted_chat_folders(db: Session, dry_run: bool = False) -> dict:
    """
    Переместить в корзину ЯД папки неактивных чатов
    (чат деактивирован И не было сообщений > 30 дней).

    Параметры:
        db      — сессия SQLAlchemy
        dry_run — если True, только логирует

    Возвращает dict со статистикой.
    """
    from sqlalchemy import func

    from database import InternalChat, InternalChatMessage

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    # Неактивные чаты с папкой ЯД
    inactive_chats = (
        db.query(InternalChat)
        .filter(
            InternalChat.is_active == False,  # noqa: E712
            InternalChat.yandex_folder_path.isnot(None),
        )
        .all()
    )

    stats = {"checked": len(inactive_chats), "deleted": 0, "errors": 0, "dry_run": dry_run}
    yd = _get_yd() if not dry_run else None

    for chat in inactive_chats:
        # Проверяем что последнее сообщение было > 30 дней назад
        last_msg = db.query(func.max(InternalChatMessage.created_at)).filter(InternalChatMessage.chat_id == chat.id).scalar()
        if last_msg and last_msg.replace(tzinfo=timezone.utc) > cutoff:
            continue  # Ещё свежий — не трогаем

        folder_path = chat.yandex_folder_path
        if not folder_path:
            continue

        if dry_run:
            logger.info(f"[maintenance DRY] Папка в корзину: {folder_path}")
            stats["deleted"] += 1
            continue

        try:
            if yd:
                yd.delete_file(folder_path, permanently=False)
            chat.yandex_folder_path = None
            stats["deleted"] += 1
            logger.info(f"[maintenance] Папка в корзину: {folder_path}")
        except Exception as e:
            stats["errors"] += 1
            logger.error(f"[maintenance] Ошибка удаления папки {folder_path}: {e}")

    if not dry_run:
        try:
            db.commit()
        except Exception as e:
            logger.error(f"[maintenance] Ошибка commit: {e}")
            db.rollback()

    logger.info(f"[maintenance] Папки итог: {stats}")
    return stats


def cleanup_trash_contracts(db: Session, dry_run: bool = False) -> dict:
    """
    Безвозвратно удалить из корзины договоры старше 30 дней:
    — запись DeletedContract из БД
    — папку договора из корзины Яндекс.Диска (permanently=True)
    """
    from database import DeletedContract

    # deleted_at хранится как UTC naive (datetime.utcnow), используем тот же тип
    cutoff = datetime.utcnow() - timedelta(days=_TRASH_CONTRACT_RETENTION_DAYS)
    old_records = db.query(DeletedContract).filter(DeletedContract.deleted_at < cutoff).all()

    stats = {"checked": len(old_records), "deleted": 0, "errors": 0, "dry_run": dry_run}

    if not old_records:
        logger.info("[maintenance] Корзина договоров: нечего чистить")
        return stats

    yd = _get_yd() if not dry_run else None

    for rec in old_records:
        if dry_run:
            logger.info(f"[maintenance DRY] Корзина договоров: удалить #{rec.id} ({rec.contract_number})")
            stats["deleted"] += 1
            continue

        # Безвозвратное удаление папки ЯД из корзины
        yd_path = rec.yandex_folder_path
        if yd and yd_path:
            try:
                # Путь в корзине ЯД: "disk:/..." → после удаления хранится в trash:/...
                trash_path = yd_path.replace("disk:", "trash:", 1) if yd_path.startswith("disk:") else yd_path
                yd.delete_file(trash_path, permanently=True)
                logger.info(f"[maintenance] ЯД корзина очищена: {trash_path}")
            except Exception as e:
                logger.warning(f"[maintenance] ЯД корзина, не удалось удалить {yd_path}: {e}")

        try:
            db.delete(rec)
            stats["deleted"] += 1
            logger.info(f"[maintenance] Корзина договоров: удалён #{rec.id} ({rec.contract_number})")
        except Exception as e:
            stats["errors"] += 1
            logger.error(f"[maintenance] Ошибка удаления записи #{rec.id}: {e}")

    if not dry_run:
        try:
            db.commit()
        except Exception as e:
            logger.error(f"[maintenance] Ошибка commit корзины договоров: {e}")
            db.rollback()

    logger.info(f"[maintenance] Корзина договоров итог: {stats}")
    return stats


def run_all_maintenance(db: Session, dry_run: bool = False) -> dict:
    """Запустить все задачи технического обслуживания."""
    logger.info("[maintenance] Запуск технического обслуживания чатов...")
    files_stats = cleanup_old_chat_files(db, dry_run=dry_run)
    folders_stats = cleanup_deleted_chat_folders(db, dry_run=dry_run)
    trash_stats = cleanup_trash_contracts(db, dry_run=dry_run)
    return {
        "files": files_stats,
        "folders": folders_stats,
        "trash_contracts": trash_stats,
    }


async def chat_maintenance_loop() -> None:
    """Фоновая задача: обслуживание чатов раз в сутки в 03:00 UTC."""
    import asyncio
    from datetime import datetime as _dt
    from datetime import timedelta as _td
    from datetime import timezone as _tz

    from database import SessionLocal

    while True:
        now = _dt.now(_tz.utc)
        target = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if target <= now:
            target += _td(days=1)
        await asyncio.sleep((target - now).total_seconds())
        db = SessionLocal()
        try:
            run_all_maintenance(db)
        except Exception as e:
            logger.warning(f"[maintenance] Ошибка: {e}")
        finally:
            db.close()

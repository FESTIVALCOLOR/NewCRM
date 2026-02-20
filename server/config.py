"""
Конфигурация приложения
Загружает переменные окружения и настройки
"""
import secrets
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения из .env файла"""

    # База данных
    database_url: str = "sqlite:///./test.db"

    # JWT
    secret_key: str = secrets.token_hex(32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60  # 60 минут (auto-refresh на клиенте)
    refresh_token_expire_days: int = 7  # 7 дней

    # Яндекс.Диск
    yandex_disk_token: str = ""

    # Приложение
    app_name: str = "Interior Studio CRM API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Файлы
    max_file_size_mb: int = 50
    file_storage_path: str = "./uploads"
    preview_cache_path: str = "./previews"

    # Синхронизация
    sync_interval_seconds: int = 5  # Интервал обновления для клиентов

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Получить настройки (кэшированные)"""
    import os
    settings = Settings()
    # В production (Docker) SECRET_KEY ОБЯЗАТЕЛЕН через .env
    env_secret = os.getenv("SECRET_KEY", "")
    if os.getenv("DATABASE_URL", "").startswith("postgresql"):
        if not env_secret:
            raise RuntimeError(
                "CRITICAL: SECRET_KEY не задан! "
                "Установите переменную окружения SECRET_KEY (openssl rand -hex 32)"
            )
    elif not env_secret:
        import logging
        logging.warning("SECURITY WARNING: SECRET_KEY не задан в .env — используется случайный ключ (сессии сбросятся при рестарте)")
    return settings

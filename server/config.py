"""
Конфигурация приложения
Загружает переменные окружения и настройки
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения из .env файла"""

    # База данных
    database_url: str = "sqlite:///./test.db"

    # JWT
    secret_key: str = "your-secret-key-change-this"
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
    # В production (Docker) SECRET_KEY ОБЯЗАТЕЛЕН
    if os.getenv("DATABASE_URL", "").startswith("postgresql"):
        if "change-this" in settings.secret_key or settings.secret_key == "your-secret-key-change-this":
            raise RuntimeError(
                "CRITICAL: SECRET_KEY не задан! "
                "Установите переменную окружения SECRET_KEY (openssl rand -hex 32)"
            )
    elif "change-this" in settings.secret_key:
        import logging
        logging.warning("SECURITY WARNING: JWT secret_key использует значение по умолчанию! Установите SECRET_KEY в .env")
    return settings

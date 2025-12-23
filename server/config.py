"""
Конфигурация приложения
Загружает переменные окружения и настройки
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Настройки приложения из .env файла"""

    # База данных
    database_url: str = "sqlite:///./test.db"

    # JWT
    secret_key: str = "your-secret-key-change-this"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Яндекс.Диск
    yandex_disk_token: str = ""

    # Приложение
    app_name: str = "Interior Studio CRM API"
    app_version: str = "1.0.0"
    debug: bool = False
    allowed_origins: list = ["http://localhost:3000"]

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
    return Settings()

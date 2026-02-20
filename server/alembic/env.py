"""
Alembic env.py — конфигурация миграций для Interior Studio CRM.
Использует database.py для MetaData и config.py для DATABASE_URL.
"""
import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Добавить server/ в sys.path для импорта database, config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_settings
from database import Base

# Alembic Config object
config = context.config

# Логирование
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData для autogenerate
target_metadata = Base.metadata

# Устанавливаем URL из config.py (переопределяет alembic.ini)
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Offline миграции (генерация SQL без подключения к БД)"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online миграции (подключение к БД и применение)"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # Обнаруживать изменения типов колонок
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

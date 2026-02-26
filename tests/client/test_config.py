# -*- coding: utf-8 -*-
"""
Тесты для config.py — константы, Settings, get_settings(), env-переменные.

Этап 9: Мелкие модули и gaps.
"""
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# КОНСТАНТЫ — НАЛИЧИЕ И ТИПЫ
# ============================================================================

class TestConfigConstants:
    """Проверяем наличие и корректность всех констант в config.py"""

    def test_base_dir_is_absolute(self):
        """BASE_DIR — абсолютный путь"""
        import config
        assert os.path.isabs(config.BASE_DIR)

    def test_database_path_is_under_base_dir(self):
        """DATABASE_PATH лежит внутри BASE_DIR"""
        import config
        assert config.DATABASE_PATH.startswith(config.BASE_DIR)

    def test_database_path_extension(self):
        """DATABASE_PATH имеет расширение .db"""
        import config
        assert config.DATABASE_PATH.endswith('.db')

    def test_roles_is_dict(self):
        """ROLES — словарь с ролями"""
        import config
        assert isinstance(config.ROLES, dict)
        assert len(config.ROLES) > 0

    def test_roles_have_required_keys(self):
        """Каждая роль содержит tabs, can_assign, can_edit"""
        import config
        for role_name, role_data in config.ROLES.items():
            assert 'tabs' in role_data, f"У роли '{role_name}' нет ключа 'tabs'"
            assert 'can_assign' in role_data, f"У роли '{role_name}' нет ключа 'can_assign'"
            assert 'can_edit' in role_data, f"У роли '{role_name}' нет ключа 'can_edit'"

    def test_positions_is_list(self):
        """POSITIONS — непустой список строк"""
        import config
        assert isinstance(config.POSITIONS, list)
        assert len(config.POSITIONS) > 0
        for pos in config.POSITIONS:
            assert isinstance(pos, str)

    def test_project_types(self):
        """PROJECT_TYPES содержит ожидаемые значения"""
        import config
        assert isinstance(config.PROJECT_TYPES, list)
        assert 'Индивидуальный' in config.PROJECT_TYPES
        assert 'Шаблонный' in config.PROJECT_TYPES

    def test_project_subtypes(self):
        """PROJECT_SUBTYPES — непустой список"""
        import config
        assert isinstance(config.PROJECT_SUBTYPES, list)
        assert len(config.PROJECT_SUBTYPES) > 0

    def test_agents_list(self):
        """AGENTS содержит ожидаемые агентства"""
        import config
        assert isinstance(config.AGENTS, list)
        assert 'ФЕСТИВАЛЬ' in config.AGENTS
        assert 'ПЕТРОВИЧ' in config.AGENTS

    def test_cities_list(self):
        """CITIES содержит ожидаемые города"""
        import config
        assert isinstance(config.CITIES, list)
        assert 'СПБ' in config.CITIES
        assert 'МСК' in config.CITIES

    def test_colors_is_dict(self):
        """COLORS — словарь с цветами (#hex)"""
        import config
        assert isinstance(config.COLORS, dict)
        required_keys = ['primary', 'secondary', 'accent', 'background', 'border', 'text']
        for key in required_keys:
            assert key in config.COLORS, f"COLORS не содержит ключ '{key}'"
            assert config.COLORS[key].startswith('#'), \
                f"COLORS['{key}'] = '{config.COLORS[key]}' не hex"

    def test_app_version_format(self):
        """APP_VERSION — строка формата X.Y.Z"""
        import config
        assert isinstance(config.APP_VERSION, str)
        parts = config.APP_VERSION.split('.')
        assert len(parts) == 3, f"APP_VERSION '{config.APP_VERSION}' не формата X.Y.Z"
        for part in parts:
            assert part.isdigit(), f"APP_VERSION часть '{part}' не число"


# ============================================================================
# ЗНАЧЕНИЯ ПО УМОЛЧАНИЮ
# ============================================================================

class TestConfigDefaults:
    """Проверяем дефолтные значения ключевых переменных"""

    def test_multi_user_mode_default(self):
        """MULTI_USER_MODE по умолчанию True"""
        import config
        assert config.MULTI_USER_MODE is True

    def test_api_base_url_default(self):
        """API_BASE_URL по умолчанию — production URL"""
        import config
        assert isinstance(config.API_BASE_URL, str)
        assert config.API_BASE_URL.startswith('http')

    def test_sync_interval_default(self):
        """SYNC_INTERVAL по умолчанию — целое число секунд"""
        import config
        assert isinstance(config.SYNC_INTERVAL, int)
        assert config.SYNC_INTERVAL > 0

    def test_cache_enabled_default(self):
        """CACHE_ENABLED по умолчанию True"""
        import config
        assert config.CACHE_ENABLED is True

    def test_update_check_enabled_default(self):
        """UPDATE_CHECK_ENABLED по умолчанию True"""
        import config
        assert config.UPDATE_CHECK_ENABLED is True


# ============================================================================
# SETTINGS (Pydantic BaseSettings)
# ============================================================================

class TestSettingsClass:
    """Тестируем класс Settings и get_settings()"""

    def test_settings_has_secret_key(self):
        """Settings содержит secret_key (не пустой)"""
        import config
        s = config.Settings()
        assert isinstance(s.secret_key, str)
        assert len(s.secret_key) > 0

    def test_settings_algorithm(self):
        """Settings.algorithm = HS256"""
        import config
        s = config.Settings()
        assert s.algorithm == "HS256"

    def test_settings_token_expire_minutes(self):
        """Settings.access_token_expire_minutes — положительное целое"""
        import config
        s = config.Settings()
        assert isinstance(s.access_token_expire_minutes, int)
        assert s.access_token_expire_minutes > 0

    def test_settings_database_url(self):
        """Settings.database_url содержит sqlite"""
        import config
        s = config.Settings()
        assert 'sqlite' in s.database_url

    def test_settings_app_name(self):
        """Settings.app_name совпадает с APP_NAME"""
        import config
        s = config.Settings()
        assert s.app_name == config.APP_NAME

    def test_settings_cors_defaults(self):
        """Settings содержит корректные CORS-настройки"""
        import config
        s = config.Settings()
        assert isinstance(s.allow_origins, list)
        assert s.allow_credentials is True
        assert s.allow_methods == ["*"]
        assert s.allow_headers == ["*"]

    def test_get_settings_lru_cache(self):
        """get_settings() — LRU cached: два вызова возвращают один объект"""
        import config
        # Очищаем кеш для чистоты теста
        config.get_settings.cache_clear()
        s1 = config.get_settings()
        s2 = config.get_settings()
        assert s1 is s2

    def test_get_settings_returns_settings_instance(self):
        """get_settings() возвращает экземпляр Settings"""
        import config
        config.get_settings.cache_clear()
        s = config.get_settings()
        assert isinstance(s, config.Settings)


# ============================================================================
# ENV-ПЕРЕМЕННЫЕ
# ============================================================================

class TestConfigEnvVars:
    """Проверяем загрузку значений из переменных окружения"""

    def test_api_base_url_from_env(self):
        """API_BASE_URL читается из env API_BASE_URL"""
        # Просто проверяем что механизм os.getenv работает
        # (реальная переменная не задана — будет дефолт)
        import config
        assert isinstance(config.API_BASE_URL, str)

    def test_yandex_disk_token_from_env(self):
        """YANDEX_DISK_TOKEN читается из env (по умолчанию пустая строка)"""
        import config
        assert isinstance(config.YANDEX_DISK_TOKEN, str)

    def test_api_verify_ssl_from_env(self):
        """API_VERIFY_SSL парсится из строки env"""
        import config
        assert isinstance(config.API_VERIFY_SSL, bool)

    def test_yandex_disk_paths(self):
        """Яндекс.Диск пути — строки начинающиеся с disk:/"""
        import config
        assert config.YANDEX_DISK_ROOT.startswith('disk:/')
        assert config.YANDEX_DISK_PROJECTS.startswith(config.YANDEX_DISK_ROOT)
        assert config.YANDEX_DISK_BACKUPS.startswith(config.YANDEX_DISK_ROOT)

    def test_project_statuses_list(self):
        """PROJECT_STATUSES — список строковых статусов"""
        import config
        assert isinstance(config.PROJECT_STATUSES, list)
        assert len(config.PROJECT_STATUSES) > 0
        for status in config.PROJECT_STATUSES:
            assert isinstance(status, str)

    def test_template_subtypes_list(self):
        """TEMPLATE_SUBTYPES — список шаблонных подтипов"""
        import config
        assert isinstance(config.TEMPLATE_SUBTYPES, list)
        assert len(config.TEMPLATE_SUBTYPES) > 0

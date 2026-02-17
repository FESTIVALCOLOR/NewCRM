import os

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'interior_studio.db')
YANDEX_DISK_LINK = "https://disk.yandex.ru/d/SMKt9A7JGjzSEw"

# Яндекс.Диск OAuth токен (получить на https://oauth.yandex.ru/)
# ВАЖНО: Для работы требуются права: cloud_api:disk.app_folder или cloud_api:disk.write
YANDEX_DISK_TOKEN = os.getenv('YANDEX_DISK_TOKEN', '')

# ========== ЯНДЕКС.ДИСК ПУТИ ==========
# Единая корневая папка для всех данных CRM на Яндекс.Диске
YANDEX_DISK_ROOT = 'disk:/CRM'
YANDEX_DISK_PROJECTS = f'{YANDEX_DISK_ROOT}/Проекты'
YANDEX_DISK_BACKUPS = f'{YANDEX_DISK_ROOT}/Бэкапы'
YANDEX_DISK_UPDATES = f'{YANDEX_DISK_ROOT}/Обновления'
# =======================================

# Роли пользователей
ROLES = {
    'Руководитель студии': {
        'tabs': ['Клиенты', 'Договора', 'СРМ', 'СРМ надзора', 
                 'Отчеты и Статистика', 'Сотрудники', 'Зарплаты', 
                 'Отчеты по сотрудникам'],
        'can_assign': ['all'],
        'can_edit': True
    },
    'Старший менеджер проектов': {
        'tabs': ['Клиенты', 'Договора', 'СРМ', 'СРМ надзора', 
                 'Отчеты и Статистика', 'Сотрудники', 'Зарплаты', 
                 'Отчеты по сотрудникам'],
        'can_assign': ['Проектный отдел', 'Исполнительный отдел'],
        'can_edit': True
    },
    'СДП': {
        'tabs': ['СРМ', 'Отчеты и Статистика', 'Сотрудники'],
        'can_assign': [],
        'can_edit': True
    },
    'ГАП': {
        'tabs': ['СРМ', 'Отчеты и Статистика', 'Сотрудники'],
        'can_assign': [],
        'can_edit': True
    },
    'Дизайнер': {
        'tabs': ['СРМ'],
        'can_assign': [],
        'can_edit': True  # доступ к просмотру данных по проекту
    },
    'Чертёжник': {
        'tabs': ['СРМ'],
        'can_assign': [],
        'can_edit': True  # доступ к просмотру данных по проекту
    },
    'Менеджер': {
        'tabs': ['СРМ', 'СРМ надзора', 'Отчеты и Статистика', 'Сотрудники'],
        'can_assign': [],
        'can_edit': True
    },
    'ДАН': {
        'tabs': ['СРМ надзора'],
        'can_assign': [],
        'can_edit': True  # только свои проекты
    },
    'Замерщик': {
        'tabs': ['СРМ'],
        'can_assign': [],
        'can_edit': False
    }
}
# Должности сотрудников
POSITIONS = [
    'Руководитель студии',
    'Старший менеджер проектов',
    'СДП',
    'ГАП',
    'Менеджер',
    'Дизайнер',
    'Чертёжник',
    'Замерщик',
    'ДАН'
]
# Типы проектов
PROJECT_TYPES = ['Индивидуальный', 'Шаблонный']
PROJECT_SUBTYPES = ['Полный (с 3д визуализацией)', 'Эскизный (с коллажами)', 'Планировочный']
TEMPLATE_SUBTYPES = [
    'Стандарт',
    'Стандарт с визуализацией',
    'Проект ванной комнаты',
    'Проект ванной комнаты с визуализацией'
]
AGENTS = ['ФЕСТИВАЛЬ', 'ПЕТРОВИЧ']
CITIES = ['СПБ', 'МСК', 'ВН']
PROJECT_STATUSES = ['СДАН', 'АВТОРСКИЙ НАДЗОР', 'РАСТОРГНУТ']

# Цветовая схема (пастельная)
COLORS = {
    'primary': '#E8F4F8',
    'secondary': '#F5E6D3',
    'accent': '#D4E4BC',
    'background': '#FFFFFF',
    'border': '#CCCCCC',
    'text': '#333333'
}

# ========== ВЕРСИОНИРОВАНИЕ И ОБНОВЛЕНИЯ ==========
APP_VERSION = "1.0.0"
APP_NAME = "Interior Studio CRM"

# Настройки обновлений через Яндекс Диск
UPDATE_CHECK_ENABLED = True  # Включить/выключить проверку обновлений
UPDATE_CHECK_INTERVAL = 3600  # Проверка каждый час (в секундах)
UPDATE_YANDEX_PUBLIC_KEY = "SmxiWfUUEt8oEA"  # Публичный ключ папки с обновлениями (будет настроен позже)
UPDATE_CHECK_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"
# ===================================================

# ========== МНОГОПОЛЬЗОВАТЕЛЬСКИЙ РЕЖИМ ==========
# Включить многопользовательский режим (работа через API сервер)
MULTI_USER_MODE = True

# URL API сервера (задать через переменную окружения API_BASE_URL)
API_BASE_URL = os.getenv('API_BASE_URL', "https://crm.festivalcolor.ru")

# Проверять SSL сертификат сервера (Let's Encrypt = валидный сертификат)
API_VERIFY_SSL = os.getenv('API_VERIFY_SSL', 'true').lower() in ('true', '1', 'yes')

# Интервал синхронизации с сервером (секунды)
SYNC_INTERVAL = 5

# Локальный кэш данных
CACHE_ENABLED = True
CACHE_PATH = os.path.join(BASE_DIR, 'cache')
# ===================================================

# ========== FASTAPI SETTINGS ==========
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

class Settings(BaseSettings):
    """Настройки для FastAPI сервера"""
    # Настройки API
    app_name: str = APP_NAME
    app_version: str = APP_VERSION
    api_title: str = "Interior Studio CRM API"
    api_version: str = APP_VERSION
    api_description: str = "REST API для многопользовательской CRM системы"

    # Безопасность (на сервере задаётся через SECRET_KEY в .env)
    secret_key: str = os.getenv('SECRET_KEY', "local-dev-key-not-for-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60  # 60 минут (auto-refresh на клиенте)

    # База данных
    database_url: str = f"sqlite:///{DATABASE_PATH}"

    # CORS
    allow_origins: list = ["*"]  # В продакшене указать конкретные домены
    allow_credentials: bool = True
    allow_methods: list = ["*"]
    allow_headers: list = ["*"]

    class Config:
        case_sensitive = False

@lru_cache()
def get_settings():
    """Получить настройки приложения"""
    return Settings()
# ===================================================

# -*- coding: utf-8 -*-
"""
Централизованная система логирования для CRM
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


# Создаём папку для логов если её нет
LOGS_DIR = 'logs'
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)


def setup_logger(name='crm', level=logging.INFO):
    """
    Настраивает и возвращает logger

    Args:
        name: Имя logger'а
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Настроенный logger
    """
    logger = logging.getLogger(name)

    # Если logger уже настроен, возвращаем его
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler 1: Файл для всех логов (ротация при 10MB, хранить 5 файлов)
    all_logs_file = os.path.join(LOGS_DIR, 'crm_all.log')
    file_handler = RotatingFileHandler(
        all_logs_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler 2: Файл только для ошибок
    error_logs_file = os.path.join(LOGS_DIR, 'crm_errors.log')
    error_handler = RotatingFileHandler(
        error_logs_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    # Handler 3: Консоль (опционально, можно отключить в продакшене)
    # Отключаем консольный вывод для Windows, чтобы избежать проблем с emoji
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.WARNING)  # В консоль только WARNING и выше
    # console_handler.setFormatter(formatter)
    # logger.addHandler(console_handler)

    return logger


# Глобальный logger для всего приложения
app_logger = setup_logger('crm', logging.INFO)


def log_database_operation(operation: str, table: str, record_id=None, user=None):
    """
    Логирует операцию с базой данных (аудит)

    Args:
        operation: Тип операции (CREATE, READ, UPDATE, DELETE)
        table: Название таблицы
        record_id: ID записи (опционально)
        user: Пользователь, выполнивший операцию (опционально)
    """
    user_str = f" by {user}" if user else ""
    record_str = f" #{record_id}" if record_id else ""

    app_logger.info(f"DB {operation}: {table}{record_str}{user_str}")


def log_auth_attempt(login: str, success: bool, ip: str = None):
    """
    Логирует попытку входа в систему

    Args:
        login: Логин пользователя
        success: Успешна ли попытка
        ip: IP адрес (опционально)
    """
    status = "SUCCESS" if success else "FAILED"
    ip_str = f" from {ip}" if ip else ""

    if success:
        app_logger.info(f"AUTH {status}: User '{login}'{ip_str}")
    else:
        app_logger.warning(f"AUTH {status}: User '{login}'{ip_str}")


def log_error(error: Exception, context: str = None):
    """
    Логирует ошибку с полным traceback

    Args:
        error: Исключение
        context: Контекст ошибки (опционально)
    """
    import traceback

    context_str = f" [{context}]" if context else ""
    app_logger.error(f"ERROR{context_str}: {str(error)}")
    app_logger.debug(f"Traceback:\n{traceback.format_exc()}")


def log_file_operation(operation: str, filename: str, user=None):
    """
    Логирует операцию с файлом

    Args:
        operation: Тип операции (EXPORT, IMPORT, UPLOAD, DOWNLOAD, DELETE)
        filename: Имя файла
        user: Пользователь (опционально)
    """
    user_str = f" by {user}" if user else ""
    app_logger.info(f"FILE {operation}: {filename}{user_str}")


def log_business_event(event: str, details: dict = None):
    """
    Логирует бизнес-событие

    Args:
        event: Описание события
        details: Дополнительные детали (опционально)
    """
    details_str = f" | Details: {details}" if details else ""
    app_logger.info(f"EVENT: {event}{details_str}")


# Специализированные логгеры для разных модулей
db_logger = setup_logger('crm.database', logging.DEBUG)
ui_logger = setup_logger('crm.ui', logging.INFO)
auth_logger = setup_logger('crm.auth', logging.INFO)
api_logger = setup_logger('crm.api', logging.INFO)


# Пример использования
if __name__ == '__main__':
    print("=== Тест системы логирования ===\n")

    # Тест 1: Обычные логи
    app_logger.debug("Это DEBUG сообщение")
    app_logger.info("Это INFO сообщение")
    app_logger.warning("Это WARNING сообщение")
    app_logger.error("Это ERROR сообщение")
    app_logger.critical("Это CRITICAL сообщение")

    # Тест 2: Операции с БД
    log_database_operation("CREATE", "clients", record_id=123, user="admin")
    log_database_operation("UPDATE", "contracts", record_id=456, user="manager")
    log_database_operation("DELETE", "employees", record_id=789, user="admin")

    # Тест 3: Попытки входа
    log_auth_attempt("admin", success=True, ip="192.168.1.1")
    log_auth_attempt("hacker", success=False, ip="1.2.3.4")

    # Тест 4: Ошибки
    try:
        1 / 0
    except Exception as e:
        log_error(e, context="Деление на ноль в тесте")

    # Тест 5: Файловые операции
    log_file_operation("EXPORT", "report_2024.pdf", user="admin")
    log_file_operation("UPLOAD", "contract_scan.jpg", user="manager")

    # Тест 6: Бизнес-события
    log_business_event("Договор подписан", {"contract_id": 123, "amount": 500000})
    log_business_event("Проект завершён", {"project_id": 456, "duration": "45 дней"})

    print(f"\nЛоги записаны в папку: {os.path.abspath(LOGS_DIR)}")
    print(f"  - Все логи: {os.path.join(LOGS_DIR, 'crm_all.log')}")
    print(f"  - Только ошибки: {os.path.join(LOGS_DIR, 'crm_errors.log')}")

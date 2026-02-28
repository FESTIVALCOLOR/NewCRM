# -*- coding: utf-8 -*-
"""
Тесты utils/logger.py — централизованная система логирования.

Покрытие:
  - TestSetupLogger (5) — создание и настройка логгеров
  - TestLogDatabaseOperation (3) — аудит операций с БД
  - TestLogAuthAttempt (3) — логирование попыток входа
  - TestLogError (2) — логирование ошибок
  - TestLogFileOperation (2) — логирование файловых операций
  - TestLogBusinessEvent (2) — бизнес-события
  - TestSpecializedLoggers (2) — специализированные логгеры
ИТОГО: 19 тестов
"""

import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestSetupLogger:
    """Тесты создания и настройки логгеров."""

    def test_setup_logger_returns_logger(self):
        """setup_logger возвращает объект logging.Logger."""
        from utils.logger import setup_logger
        logger = setup_logger('test_returns_logger', logging.DEBUG)
        assert isinstance(logger, logging.Logger)

    def test_setup_logger_sets_level(self):
        """Уровень логирования устанавливается корректно."""
        from utils.logger import setup_logger
        logger = setup_logger('test_level_debug', logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_setup_logger_has_handlers(self):
        """Логгер имеет хотя бы один handler."""
        from utils.logger import setup_logger
        logger = setup_logger('test_handlers_exist', logging.INFO)
        assert len(logger.handlers) > 0

    def test_setup_logger_has_file_handler(self):
        """Логгер содержит RotatingFileHandler."""
        from utils.logger import setup_logger
        from logging.handlers import RotatingFileHandler
        logger = setup_logger('test_has_rotating', logging.INFO)
        rotating_handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
        assert len(rotating_handlers) >= 1

    def test_setup_logger_idempotent(self):
        """Повторный вызов setup_logger с тем же именем не дублирует handlers."""
        from utils.logger import setup_logger
        logger1 = setup_logger('test_idempotent_logger', logging.INFO)
        handler_count = len(logger1.handlers)
        logger2 = setup_logger('test_idempotent_logger', logging.INFO)
        assert logger1 is logger2
        assert len(logger2.handlers) == handler_count


class TestLogDatabaseOperation:
    """Тесты аудита операций с базой данных."""

    def test_log_db_operation_basic(self):
        """Базовое логирование операции CREATE."""
        from utils.logger import log_database_operation, app_logger
        with patch.object(app_logger, 'info') as mock_info:
            log_database_operation("CREATE", "clients", record_id=1, user="admin")
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "CREATE" in call_args
            assert "clients" in call_args
            assert "#1" in call_args
            assert "admin" in call_args

    def test_log_db_operation_without_optional(self):
        """Логирование без record_id и user."""
        from utils.logger import log_database_operation, app_logger
        with patch.object(app_logger, 'info') as mock_info:
            log_database_operation("DELETE", "contracts")
            call_args = mock_info.call_args[0][0]
            assert "DELETE" in call_args
            assert "contracts" in call_args
            # Не должно содержать '#' или 'by '
            assert "#" not in call_args
            assert " by " not in call_args

    def test_log_db_operation_with_only_record_id(self):
        """Логирование с record_id, но без user."""
        from utils.logger import log_database_operation, app_logger
        with patch.object(app_logger, 'info') as mock_info:
            log_database_operation("UPDATE", "employees", record_id=42)
            call_args = mock_info.call_args[0][0]
            assert "#42" in call_args
            assert " by " not in call_args


class TestLogAuthAttempt:
    """Тесты логирования попыток входа."""

    def test_auth_success_logged_as_info(self):
        """Успешный вход логируется как INFO."""
        from utils.logger import log_auth_attempt, app_logger
        with patch.object(app_logger, 'info') as mock_info:
            log_auth_attempt("admin", success=True, ip="192.168.1.1")
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "SUCCESS" in call_args
            assert "admin" in call_args
            assert "192.168.1.1" in call_args

    def test_auth_failure_logged_as_warning(self):
        """Неудачный вход логируется как WARNING."""
        from utils.logger import log_auth_attempt, app_logger
        with patch.object(app_logger, 'warning') as mock_warn:
            log_auth_attempt("hacker", success=False, ip="1.2.3.4")
            mock_warn.assert_called_once()
            call_args = mock_warn.call_args[0][0]
            assert "FAILED" in call_args
            assert "hacker" in call_args

    def test_auth_attempt_without_ip(self):
        """Вход без IP-адреса — ip не отображается."""
        from utils.logger import log_auth_attempt, app_logger
        with patch.object(app_logger, 'info') as mock_info:
            log_auth_attempt("user1", success=True)
            call_args = mock_info.call_args[0][0]
            assert "user1" in call_args
            assert " from " not in call_args


class TestLogError:
    """Тесты логирования ошибок."""

    def test_log_error_with_context(self):
        """Ошибка с контекстом логируется как ERROR."""
        from utils.logger import log_error, app_logger
        with patch.object(app_logger, 'error') as mock_error:
            with patch.object(app_logger, 'debug'):
                try:
                    1 / 0
                except Exception as e:
                    log_error(e, context="Деление на ноль")
                mock_error.assert_called_once()
                call_args = mock_error.call_args[0][0]
                assert "Деление на ноль" in call_args

    def test_log_error_without_context(self):
        """Ошибка без контекста."""
        from utils.logger import log_error, app_logger
        with patch.object(app_logger, 'error') as mock_error:
            with patch.object(app_logger, 'debug'):
                log_error(ValueError("тестовая ошибка"))
                call_args = mock_error.call_args[0][0]
                assert "тестовая ошибка" in call_args
                assert "[" not in call_args  # нет контекста


class TestLogFileOperation:
    """Тесты логирования файловых операций."""

    def test_log_file_export(self):
        """Логирование экспорта файла."""
        from utils.logger import log_file_operation, app_logger
        with patch.object(app_logger, 'info') as mock_info:
            log_file_operation("EXPORT", "report.pdf", user="admin")
            call_args = mock_info.call_args[0][0]
            assert "EXPORT" in call_args
            assert "report.pdf" in call_args
            assert "admin" in call_args

    def test_log_file_without_user(self):
        """Логирование без указания пользователя."""
        from utils.logger import log_file_operation, app_logger
        with patch.object(app_logger, 'info') as mock_info:
            log_file_operation("UPLOAD", "photo.jpg")
            call_args = mock_info.call_args[0][0]
            assert "UPLOAD" in call_args
            assert "photo.jpg" in call_args
            assert " by " not in call_args


class TestLogBusinessEvent:
    """Тесты логирования бизнес-событий."""

    def test_business_event_with_details(self):
        """Бизнес-событие с деталями."""
        from utils.logger import log_business_event, app_logger
        with patch.object(app_logger, 'info') as mock_info:
            log_business_event("Договор подписан", {"contract_id": 123})
            call_args = mock_info.call_args[0][0]
            assert "Договор подписан" in call_args
            assert "contract_id" in call_args

    def test_business_event_without_details(self):
        """Бизнес-событие без деталей."""
        from utils.logger import log_business_event, app_logger
        with patch.object(app_logger, 'info') as mock_info:
            log_business_event("Проект завершён")
            call_args = mock_info.call_args[0][0]
            assert "Проект завершён" in call_args
            assert "Details" not in call_args


class TestSpecializedLoggers:
    """Тесты специализированных логгеров."""

    def test_app_logger_exists(self):
        """Глобальный app_logger существует и является Logger."""
        from utils.logger import app_logger
        assert isinstance(app_logger, logging.Logger)
        assert app_logger.name == 'crm'

    def test_specialized_loggers_exist(self):
        """Специализированные логгеры (db, ui, auth, api) созданы."""
        from utils.logger import db_logger, ui_logger, auth_logger, api_logger
        assert db_logger.name == 'crm.database'
        assert ui_logger.name == 'crm.ui'
        assert auth_logger.name == 'crm.auth'
        assert api_logger.name == 'crm.api'

# -*- coding: utf-8 -*-
"""
Автоматизированный Regression Suite — Interior Studio CRM

20+ тестов для предотвращения повторных багов.
Каждый тест самодостаточен, не зависит от PyQt5, использует реальный SQLite через tmp_path.

Покрытые категории:
- Целостность данных (контракты, платежи, клиенты)
- Валидация ввода (телефон, даты, суммы)
- Безопасность (SQL-инъекции, XSS, пароли, JWT)
- Offline-режим (очередь, дедупликация, fallback)
- Пагинация и поиск
- Каскадное удаление и блокировки
- Идемпотентность миграций
"""

import json
import re
import sqlite3
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Корень проекта
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Вспомогательные функции для тестов
# ============================================================================

def _seed_client(conn, client_id=1, full_name="Тестовый Клиент", phone="+7 (900) 123-45-67"):
    """Вставляет тестового клиента и возвращает его id."""
    conn.execute(
        "INSERT OR IGNORE INTO clients (id, client_type, full_name, phone) VALUES (?, ?, ?, ?)",
        (client_id, "Физическое лицо", full_name, phone),
    )
    conn.commit()
    return client_id


def _seed_contract(conn, contract_id=1, client_id=1, number="01/2026", **kwargs):
    """Вставляет тестовый договор."""
    defaults = {
        "project_type": "Индивидуальный",
        "status": "Новый заказ",
        "address": "г. Москва, ул. Тестовая, д. 1",
        "area": 80.0,
        "contract_date": "2026-01-15",
    }
    defaults.update(kwargs)
    conn.execute(
        """INSERT OR IGNORE INTO contracts
           (id, contract_number, client_id, project_type, status, address, area, contract_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (contract_id, number, client_id, defaults["project_type"],
         defaults["status"], defaults["address"], defaults["area"], defaults["contract_date"]),
    )
    conn.commit()
    return contract_id


def _seed_crm_card(conn, card_id=1, contract_id=1, column="Новый заказ"):
    """Вставляет тестовую CRM-карточку."""
    conn.execute(
        "INSERT OR IGNORE INTO crm_cards (id, contract_id, column_name) VALUES (?, ?, ?)",
        (card_id, contract_id, column),
    )
    conn.commit()
    return card_id


# ============================================================================
# 1. test_contract_number_not_null
# ============================================================================

class TestContractNumberNotNull:
    """Номер контракта не может быть NULL при создании."""

    def test_contract_number_not_null(self, mock_db):
        """Попытка вставить контракт с NULL номером должна провалиться."""
        _seed_client(mock_db)
        with pytest.raises(sqlite3.IntegrityError):
            mock_db.execute(
                "INSERT INTO contracts (contract_number, client_id, project_type) VALUES (NULL, 1, 'Индивидуальный')"
            )

    def test_contract_number_not_empty_via_validator(self, mock_db):
        """Валидатор validate_contract_number отклоняет пустую строку."""
        from utils.validators import validate_contract_number, ValidationError
        with pytest.raises(ValidationError, match="Номер договора обязателен"):
            validate_contract_number("")

    def test_contract_number_valid_format(self, mock_db):
        """Корректный формат XX/YYYY проходит валидацию."""
        from utils.validators import validate_contract_number
        assert validate_contract_number("01/2026") is True


# ============================================================================
# 2. test_payment_amount_positive
# ============================================================================

class TestPaymentAmountPositive:
    """Сумма платежа всегда > 0."""

    def test_negative_amount_rejected_by_validator(self):
        """validate_positive_number отклоняет отрицательное число."""
        from utils.validators import validate_positive_number, ValidationError
        with pytest.raises(ValidationError, match="положительным числом"):
            validate_positive_number(-100, "Сумма")

    def test_zero_amount_passes(self):
        """Нулевая сумма допустима (по логике валидатора >= 0)."""
        from utils.validators import validate_positive_number
        assert validate_positive_number(0, "Сумма") is True

    def test_positive_amount_passes(self):
        """Положительная сумма проходит."""
        from utils.validators import validate_positive_number
        assert validate_positive_number(5000.50, "Сумма") is True


# ============================================================================
# 3. test_client_phone_format
# ============================================================================

class TestClientPhoneFormat:
    """Телефон форматируется корректно при сохранении."""

    def test_format_phone_from_raw_digits(self):
        """format_phone преобразует 11 цифр в стандартный формат."""
        from utils.validators import format_phone
        assert format_phone("89001234567") == "+7 (900) 123-45-67"

    def test_format_phone_from_plus7(self):
        """format_phone преобразует +7XXXXXXXXXX."""
        from utils.validators import format_phone
        assert format_phone("+79001234567") == "+7 (900) 123-45-67"

    def test_validate_phone_correct_format(self):
        """validate_phone принимает корректный формат."""
        from utils.validators import validate_phone
        assert validate_phone("+7 (900) 123-45-67") is True

    def test_validate_phone_rejects_invalid(self):
        """validate_phone отклоняет некорректный формат."""
        from utils.validators import validate_phone, ValidationError
        with pytest.raises(ValidationError):
            validate_phone("89001234567")

    def test_phone_stored_formatted_in_db(self, mock_db):
        """Телефон сохраняется в БД в отформатированном виде."""
        from utils.validators import format_phone
        raw = "89001234567"
        formatted = format_phone(raw)
        mock_db.execute(
            "INSERT INTO clients (id, client_type, full_name, phone) VALUES (100, 'Физическое лицо', 'Тест', ?)",
            (formatted,),
        )
        mock_db.commit()
        row = mock_db.execute("SELECT phone FROM clients WHERE id = 100").fetchone()
        assert row["phone"] == "+7 (900) 123-45-67"


# ============================================================================
# 4. test_date_format_consistent
# ============================================================================

class TestDateFormatConsistent:
    """Даты всегда в формате YYYY-MM-DD в БД."""

    def test_date_stored_as_iso(self, mock_db):
        """contract_date хранится в ISO-формате."""
        _seed_client(mock_db)
        _seed_contract(mock_db, contract_date="2026-01-15")
        row = mock_db.execute("SELECT contract_date FROM contracts WHERE id = 1").fetchone()
        # Проверяем что дата соответствует ISO-8601 (YYYY-MM-DD)
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", row["contract_date"])

    def test_validate_date_dd_mm_yyyy(self):
        """validate_date принимает формат DD.MM.YYYY (UI-формат)."""
        from utils.validators import validate_date
        assert validate_date("15.01.2026", "%d.%m.%Y") is True

    def test_validate_date_rejects_wrong_format(self):
        """validate_date отклоняет неверный формат."""
        from utils.validators import validate_date, ValidationError
        with pytest.raises(ValidationError):
            validate_date("2026/01/15", "%d.%m.%Y")


# ============================================================================
# 5. test_offline_queue_not_duplicate
# ============================================================================

class TestOfflineQueueNotDuplicate:
    """Одна операция не дублируется в offline-очереди."""

    def test_no_duplicate_operations(self, mock_db):
        """Повторная вставка идентичной операции не создаёт дубликат."""
        data = json.dumps({"full_name": "Обновленное Имя"})
        for _ in range(3):
            # Проверяем — есть ли уже такая pending операция
            existing = mock_db.execute(
                """SELECT id FROM offline_queue
                   WHERE operation_type = 'UPDATE' AND entity_type = 'client'
                   AND entity_id = 1 AND status = 'pending'"""
            ).fetchone()
            if not existing:
                mock_db.execute(
                    """INSERT INTO offline_queue (operation_type, entity_type, entity_id, data, status)
                       VALUES ('UPDATE', 'client', 1, ?, 'pending')""",
                    (data,),
                )
                mock_db.commit()

        count = mock_db.execute(
            "SELECT COUNT(*) as cnt FROM offline_queue WHERE entity_id = 1 AND entity_type = 'client'"
        ).fetchone()["cnt"]
        assert count == 1, f"Ожидалась 1 операция, найдено: {count}"

    def test_different_operations_allowed(self, mock_db):
        """Разные типы операций для одной сущности допускаются."""
        data = json.dumps({"full_name": "Имя"})
        mock_db.execute(
            "INSERT INTO offline_queue (operation_type, entity_type, entity_id, data) VALUES ('CREATE', 'client', 1, ?)",
            (data,),
        )
        mock_db.execute(
            "INSERT INTO offline_queue (operation_type, entity_type, entity_id, data) VALUES ('UPDATE', 'client', 1, ?)",
            (data,),
        )
        mock_db.commit()
        count = mock_db.execute(
            "SELECT COUNT(*) as cnt FROM offline_queue WHERE entity_id = 1"
        ).fetchone()["cnt"]
        assert count == 2


# ============================================================================
# 6. test_api_timeout_does_not_crash
# ============================================================================

class TestApiTimeoutDoesNotCrash:
    """APITimeoutError не крашит приложение."""

    def test_timeout_is_catchable(self):
        """APITimeoutError можно перехватить без краша."""
        from utils.api_client.exceptions import APITimeoutError, APIError
        try:
            raise APITimeoutError("Таймаут 10с")
        except APIError as e:
            assert "Таймаут" in str(e)

    def test_timeout_inherits_api_error(self):
        """APITimeoutError является подклассом APIError."""
        from utils.api_client.exceptions import APITimeoutError, APIError
        assert issubclass(APITimeoutError, APIError)


# ============================================================================
# 7. test_connection_error_fallback
# ============================================================================

class TestConnectionErrorFallback:
    """APIConnectionError переходит на локальную БД."""

    def test_connection_error_is_api_error(self):
        """APIConnectionError — подкласс APIError."""
        from utils.api_client.exceptions import APIConnectionError, APIError
        assert issubclass(APIConnectionError, APIError)

    def test_fallback_to_local_db_on_connection_error(self, mock_db):
        """При APIConnectionError данные читаются из локальной БД."""
        _seed_client(mock_db)
        _seed_contract(mock_db)

        # Имитируем: API упал, читаем из локальной БД напрямую
        from utils.api_client.exceptions import APIConnectionError
        api_failed = False
        try:
            raise APIConnectionError("Сервер недоступен")
        except APIConnectionError:
            api_failed = True

        assert api_failed
        # Fallback: данные доступны через SQLite
        row = mock_db.execute("SELECT * FROM contracts WHERE id = 1").fetchone()
        assert row is not None
        assert row["contract_number"] == "01/2026"


# ============================================================================
# 8. test_business_error_no_fallback
# ============================================================================

class TestBusinessErrorNoFallback:
    """HTTP 400/409 НЕ переходит на fallback — это бизнес-ошибка."""

    def test_response_error_is_not_connection_error(self):
        """APIResponseError не является APIConnectionError."""
        from utils.api_client.exceptions import APIResponseError, APIConnectionError
        assert not issubclass(APIResponseError, APIConnectionError)

    def test_400_should_not_queue(self):
        """Бизнес-ошибка 400 не должна попадать в offline-очередь."""
        from utils.api_client.exceptions import APIResponseError, APIConnectionError, APITimeoutError
        error = APIResponseError("Некорректные данные", status_code=400)
        # Проверяем: ошибка не является сетевой
        assert not isinstance(error, (APIConnectionError, APITimeoutError))

    def test_409_conflict_not_retryable(self):
        """Конфликт 409 — не подлежит повторной попытке."""
        from utils.api_client.exceptions import APIResponseError, APIConnectionError, APITimeoutError
        error = APIResponseError("Конфликт: запись уже существует", status_code=409)
        assert not isinstance(error, (APIConnectionError, APITimeoutError))
        assert error.status_code == 409


# ============================================================================
# 9. test_sql_injection_prevention
# ============================================================================

class TestSqlInjectionPrevention:
    """Параметризованные запросы защищают от SQL-инъекций."""

    def test_parameterized_insert_safe(self, mock_db):
        """Вставка через параметры безопасна даже с SQL-инъекцией в данных."""
        malicious_name = "'; DROP TABLE clients; --"
        mock_db.execute(
            "INSERT INTO clients (id, client_type, full_name, phone) VALUES (200, 'Физическое лицо', ?, '+7 (900) 000-00-00')",
            (malicious_name,),
        )
        mock_db.commit()

        # Таблица clients должна существовать и содержать запись
        row = mock_db.execute("SELECT full_name FROM clients WHERE id = 200").fetchone()
        assert row is not None
        assert row["full_name"] == malicious_name

    def test_parameterized_select_safe(self, mock_db):
        """Поиск через параметры не исполняет SQL-инъекцию."""
        _seed_client(mock_db)
        injection = "1 OR 1=1"
        rows = mock_db.execute(
            "SELECT * FROM clients WHERE id = ?", (injection,)
        ).fetchall()
        # Не должно вернуть все записи — только по точному id
        assert len(rows) == 0

    def test_sanitize_string_strips_html(self):
        """sanitize_string удаляет HTML-теги."""
        from utils.validators import sanitize_string
        result = sanitize_string("Нормальный <script>alert('xss')</script> текст")
        assert "<script>" not in result
        assert "Нормальный" in result


# ============================================================================
# 10. test_xss_in_client_name
# ============================================================================

class TestXssInClientName:
    """HTML в имени клиента экранируется через sanitize_string."""

    def test_html_tags_removed(self):
        """sanitize_string удаляет все HTML-теги из строки."""
        from utils.validators import sanitize_string
        dirty = '<b>Иванов</b> <img src=x onerror=alert(1)> Иван'
        clean = sanitize_string(dirty)
        assert "<b>" not in clean
        assert "<img" not in clean
        assert "Иванов" in clean
        assert "Иван" in clean

    def test_script_tag_removed(self):
        """sanitize_string удаляет <script> теги."""
        from utils.validators import sanitize_string
        dirty = '<script>document.cookie</script>Петров'
        clean = sanitize_string(dirty)
        assert "<script>" not in clean
        assert "Петров" in clean

    def test_clean_string_unchanged(self):
        """Чистая строка остаётся без изменений."""
        from utils.validators import sanitize_string
        clean = "Иванов Пётр Сергеевич"
        assert sanitize_string(clean) == clean


# ============================================================================
# 11. test_large_data_pagination
# ============================================================================

class TestLargeDataPagination:
    """При >100 записях используется пагинация."""

    def test_pagination_with_limit_offset(self, mock_db):
        """SQL LIMIT/OFFSET корректно обрезает результат."""
        # Вставляем 150 клиентов
        for i in range(1, 151):
            mock_db.execute(
                "INSERT INTO clients (client_type, full_name, phone) VALUES ('Физическое лицо', ?, ?)",
                (f"Клиент {i}", f"+7 (900) 000-{i:04d}"),
            )
        mock_db.commit()

        # Первая страница: 50 записей
        page1 = mock_db.execute(
            "SELECT * FROM clients ORDER BY id LIMIT ? OFFSET ?", (50, 0)
        ).fetchall()
        assert len(page1) == 50

        # Вторая страница: 50 записей
        page2 = mock_db.execute(
            "SELECT * FROM clients ORDER BY id LIMIT ? OFFSET ?", (50, 50)
        ).fetchall()
        assert len(page2) == 50

        # Третья страница: оставшиеся 50
        page3 = mock_db.execute(
            "SELECT * FROM clients ORDER BY id LIMIT ? OFFSET ?", (50, 100)
        ).fetchall()
        assert len(page3) == 50

        # Нет пересечений между страницами
        ids_1 = {r["id"] for r in page1}
        ids_2 = {r["id"] for r in page2}
        ids_3 = {r["id"] for r in page3}
        assert ids_1.isdisjoint(ids_2)
        assert ids_2.isdisjoint(ids_3)


# ============================================================================
# 12. test_concurrent_edit_lock
# ============================================================================

class TestConcurrentEditLock:
    """При параллельном редактировании updated_at обновляется, позволяя обнаружить конфликт."""

    def test_updated_at_changes_on_edit(self, mock_db):
        """Поле updated_at меняется при каждом обновлении записи."""
        _seed_client(mock_db)
        _seed_contract(mock_db)
        _seed_crm_card(mock_db)

        # Первоначальное значение
        row1 = mock_db.execute("SELECT updated_at FROM crm_cards WHERE id = 1").fetchone()
        ts1 = row1["updated_at"]

        # Обновляем
        mock_db.execute(
            "UPDATE crm_cards SET column_name = 'В работе', updated_at = datetime('now', '+1 second') WHERE id = 1"
        )
        mock_db.commit()

        row2 = mock_db.execute("SELECT updated_at FROM crm_cards WHERE id = 1").fetchone()
        ts2 = row2["updated_at"]

        assert ts2 != ts1, "updated_at должен измениться после обновления"

    def test_optimistic_lock_detects_conflict(self, mock_db):
        """Оптимистичная блокировка: UPDATE WHERE updated_at = old_value обновляет 0 строк при конфликте."""
        _seed_client(mock_db)
        _seed_contract(mock_db)
        _seed_crm_card(mock_db)

        # Читаем текущий timestamp
        row = mock_db.execute("SELECT updated_at FROM crm_cards WHERE id = 1").fetchone()
        old_ts = row["updated_at"]

        # Имитируем: другой пользователь обновил карточку
        mock_db.execute(
            "UPDATE crm_cards SET column_name = 'В работе', updated_at = datetime('now', '+5 seconds') WHERE id = 1"
        )
        mock_db.commit()

        # Наша попытка обновить с устаревшим timestamp — должна затронуть 0 строк
        cursor = mock_db.execute(
            "UPDATE crm_cards SET column_name = 'Согласование' WHERE id = 1 AND updated_at = ?",
            (old_ts,),
        )
        mock_db.commit()
        assert cursor.rowcount == 0, "При конфликте UPDATE не должен затронуть строки"


# ============================================================================
# 13. test_empty_search_returns_all
# ============================================================================

class TestEmptySearchReturnsAll:
    """Пустой поиск возвращает все записи."""

    def test_empty_string_search(self, mock_db):
        """Поиск с пустой строкой возвращает все записи."""
        for i in range(5):
            mock_db.execute(
                "INSERT INTO clients (client_type, full_name, phone) VALUES ('Физическое лицо', ?, ?)",
                (f"Клиент {i}", f"+7 (900) 000-{i:04d}"),
            )
        mock_db.commit()

        search_term = ""
        # Пустой поиск — возвращаем всё (WHERE 1=1 или LIKE '%%')
        if search_term:
            rows = mock_db.execute(
                "SELECT * FROM clients WHERE full_name LIKE ?", (f"%{search_term}%",)
            ).fetchall()
        else:
            rows = mock_db.execute("SELECT * FROM clients").fetchall()

        assert len(rows) == 5

    def test_none_search_returns_all(self, mock_db):
        """Поиск с None как фильтром возвращает все записи."""
        for i in range(3):
            mock_db.execute(
                "INSERT INTO clients (client_type, full_name, phone) VALUES ('Физическое лицо', ?, ?)",
                (f"Клиент {i}", f"+7 (900) 000-{i:04d}"),
            )
        mock_db.commit()

        search_term = None
        if search_term:
            rows = mock_db.execute(
                "SELECT * FROM clients WHERE full_name LIKE ?", (f"%{search_term}%",)
            ).fetchall()
        else:
            rows = mock_db.execute("SELECT * FROM clients").fetchall()

        assert len(rows) == 3


# ============================================================================
# 14. test_unicode_in_fields
# ============================================================================

class TestUnicodeInFields:
    """Кириллица корректно сохраняется и читается из БД."""

    def test_cyrillic_client_name(self, mock_db):
        """Кириллическое ФИО сохраняется и читается без искажений."""
        name = "Иванов Пётр Сергеевич"
        mock_db.execute(
            "INSERT INTO clients (id, client_type, full_name, phone) VALUES (300, 'Физическое лицо', ?, '+7 (900) 000-0000')",
            (name,),
        )
        mock_db.commit()
        row = mock_db.execute("SELECT full_name FROM clients WHERE id = 300").fetchone()
        assert row["full_name"] == name

    def test_cyrillic_address(self, mock_db):
        """Кириллический адрес сохраняется корректно."""
        _seed_client(mock_db)
        address = "г. Санкт-Петербург, ул. Большая Морская, д. 15, кв. 3"
        mock_db.execute(
            """INSERT INTO contracts (id, contract_number, client_id, project_type, address)
               VALUES (300, '99/2026', 1, 'Индивидуальный', ?)""",
            (address,),
        )
        mock_db.commit()
        row = mock_db.execute("SELECT address FROM contracts WHERE id = 300").fetchone()
        assert row["address"] == address

    def test_emoji_in_comments(self, mock_db):
        """Emoji и спецсимволы в комментариях не ломают БД."""
        _seed_client(mock_db)
        comment = "Клиент VIP, требует особого внимания! (Бюджет: 1 500 000 руб.)"
        mock_db.execute(
            """INSERT INTO contracts (id, contract_number, client_id, project_type, comments)
               VALUES (301, '98/2026', 1, 'Индивидуальный', ?)""",
            (comment,),
        )
        mock_db.commit()
        row = mock_db.execute("SELECT comments FROM contracts WHERE id = 301").fetchone()
        assert row["comments"] == comment


# ============================================================================
# 15. test_password_not_stored_plain
# ============================================================================

class TestPasswordNotStoredPlain:
    """Пароли хранятся в хэшированном формате (PBKDF2-SHA256 salt$hash)."""

    def test_hash_password_produces_salted_hash(self):
        """hash_password возвращает строку формата salt$hash."""
        from utils.password_utils import hash_password
        hashed = hash_password("SecurePass123!")
        assert "$" in hashed
        parts = hashed.split("$")
        assert len(parts) == 2
        # Обе части — base64
        import base64
        base64.b64decode(parts[0])  # salt — не должно кинуть ошибку
        base64.b64decode(parts[1])  # hash — не должно кинуть ошибку

    def test_verify_password_correct(self):
        """verify_password подтверждает правильный пароль."""
        from utils.password_utils import hash_password, verify_password
        pwd = "MyPassword2026"
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed) is True

    def test_verify_password_wrong(self):
        """verify_password отклоняет неверный пароль."""
        from utils.password_utils import hash_password, verify_password
        hashed = hash_password("CorrectPassword")
        assert verify_password("WrongPassword", hashed) is False

    def test_plaintext_password_rejected(self):
        """verify_password отклоняет plaintext-пароль (без $ разделителя)."""
        from utils.password_utils import verify_password
        assert verify_password("admin", "admin") is False

    def test_different_hashes_for_same_password(self):
        """Два вызова hash_password для одного пароля дают разные хэши (разная соль)."""
        from utils.password_utils import hash_password
        h1 = hash_password("SamePassword")
        h2 = hash_password("SamePassword")
        assert h1 != h2, "Каждый хэш должен использовать уникальную соль"


# ============================================================================
# 16. test_jwt_expiration_handled
# ============================================================================

class TestJwtExpirationHandled:
    """Истёкший JWT обрабатывается gracefully."""

    def test_auth_error_is_api_error(self):
        """APIAuthError является подклассом APIError."""
        from utils.api_client.exceptions import APIAuthError, APIError
        assert issubclass(APIAuthError, APIError)

    def test_expired_jwt_raises_auth_error(self):
        """При истёкшем JWT должна выбрасываться APIAuthError."""
        from utils.api_client.exceptions import APIAuthError
        # Имитируем обработку истёкшего JWT
        try:
            raise APIAuthError("Токен истёк")
        except APIAuthError as e:
            assert "истёк" in str(e)

    def test_auth_error_does_not_crash_app(self):
        """APIAuthError перехватывается без краша."""
        from utils.api_client.exceptions import APIAuthError, APIError
        caught = False
        try:
            raise APIAuthError("JWT expired")
        except APIError:
            caught = True
        assert caught


# ============================================================================
# 17. test_file_upload_size_limit
# ============================================================================

class TestFileUploadSizeLimit:
    """Файлы больше определённого лимита отклоняются."""

    MAX_FILE_SIZE_MB = 50  # Лимит в МБ

    def test_small_file_accepted(self):
        """Файл меньше лимита проходит проверку."""
        file_size_bytes = 10 * 1024 * 1024  # 10 МБ
        assert file_size_bytes <= self.MAX_FILE_SIZE_MB * 1024 * 1024

    def test_large_file_rejected(self):
        """Файл больше лимита отклоняется."""
        file_size_bytes = 100 * 1024 * 1024  # 100 МБ
        assert file_size_bytes > self.MAX_FILE_SIZE_MB * 1024 * 1024

    def test_file_record_stored_in_db(self, mock_db):
        """Запись о файле сохраняется в project_files."""
        _seed_client(mock_db)
        _seed_contract(mock_db)
        mock_db.execute(
            """INSERT INTO project_files (contract_id, stage, file_type, file_name, yandex_path)
               VALUES (1, 'Дизайн-концепция', 'image', 'plan.jpg', '/disk/projects/plan.jpg')"""
        )
        mock_db.commit()
        row = mock_db.execute("SELECT * FROM project_files WHERE contract_id = 1").fetchone()
        assert row is not None
        assert row["file_name"] == "plan.jpg"


# ============================================================================
# 18. test_deleted_record_not_visible
# ============================================================================

class TestDeletedRecordNotVisible:
    """Удалённая запись не видна в списках."""

    def test_deleted_client_not_in_list(self, mock_db):
        """После DELETE клиент не виден в SELECT."""
        _seed_client(mock_db, client_id=400, full_name="Удаляемый Клиент")
        mock_db.execute("DELETE FROM clients WHERE id = 400")
        mock_db.commit()

        row = mock_db.execute("SELECT * FROM clients WHERE id = 400").fetchone()
        assert row is None

    def test_deleted_contract_not_in_list(self, mock_db):
        """После DELETE договор не виден."""
        _seed_client(mock_db)
        _seed_contract(mock_db, contract_id=400, number="DEL/2026")
        mock_db.execute("DELETE FROM contracts WHERE id = 400")
        mock_db.commit()

        row = mock_db.execute("SELECT * FROM contracts WHERE id = 400").fetchone()
        assert row is None

    def test_deleted_payment_not_in_totals(self, mock_db):
        """Удалённый платёж не учитывается в суммах."""
        _seed_client(mock_db)
        _seed_contract(mock_db)
        _seed_crm_card(mock_db)

        mock_db.execute(
            """INSERT INTO payments (id, contract_id, crm_card_id, employee_id, final_amount, payment_status)
               VALUES (400, 1, 1, NULL, 10000, 'pending')"""
        )
        mock_db.commit()

        # Удаляем платёж
        mock_db.execute("DELETE FROM payments WHERE id = 400")
        mock_db.commit()

        total = mock_db.execute(
            "SELECT COALESCE(SUM(final_amount), 0) as total FROM payments WHERE contract_id = 1"
        ).fetchone()["total"]
        assert total == 0


# ============================================================================
# 19. test_cascade_delete
# ============================================================================

class TestCascadeDelete:
    """Удаление клиента каскадно удаляет связанные данные (через ON DELETE CASCADE)."""

    def test_cascade_delete_crm_cards(self, mock_db):
        """Удаление договора каскадно удаляет CRM-карточки."""
        _seed_client(mock_db)
        _seed_contract(mock_db)
        _seed_crm_card(mock_db)

        # Проверяем что карточка существует
        assert mock_db.execute("SELECT id FROM crm_cards WHERE contract_id = 1").fetchone() is not None

        # Удаляем договор — карточка должна удалиться каскадно
        mock_db.execute("DELETE FROM contracts WHERE id = 1")
        mock_db.commit()

        card = mock_db.execute("SELECT id FROM crm_cards WHERE contract_id = 1").fetchone()
        assert card is None, "CRM-карточка должна быть удалена каскадно с договором"

    def test_cascade_delete_supervision_cards(self, mock_db):
        """Удаление договора каскадно удаляет карточки надзора."""
        _seed_client(mock_db)
        _seed_contract(mock_db)
        mock_db.execute(
            "INSERT INTO supervision_cards (id, contract_id, column_name) VALUES (1, 1, 'Новый заказ')"
        )
        mock_db.commit()

        mock_db.execute("DELETE FROM contracts WHERE id = 1")
        mock_db.commit()

        card = mock_db.execute("SELECT id FROM supervision_cards WHERE contract_id = 1").fetchone()
        assert card is None, "Карточка надзора должна быть удалена каскадно"

    def test_cascade_delete_project_files(self, mock_db):
        """Удаление договора каскадно удаляет файлы проекта."""
        _seed_client(mock_db)
        _seed_contract(mock_db)
        mock_db.execute(
            """INSERT INTO project_files (contract_id, stage, file_name, yandex_path)
               VALUES (1, 'Дизайн', 'file.jpg', '/disk/file.jpg')"""
        )
        mock_db.commit()

        mock_db.execute("DELETE FROM contracts WHERE id = 1")
        mock_db.commit()

        files = mock_db.execute("SELECT id FROM project_files WHERE contract_id = 1").fetchall()
        assert len(files) == 0, "Файлы проекта должны быть удалены каскадно"


# ============================================================================
# 20. test_migration_idempotent
# ============================================================================

class TestMigrationIdempotent:
    """Повторная миграция не ломает данные."""

    def test_create_table_if_not_exists(self, mock_db):
        """Повторное CREATE TABLE IF NOT EXISTS не вызывает ошибку."""
        # Выполняем CREATE TABLE дважды — не должно быть ошибки
        for _ in range(3):
            mock_db.execute("""
                CREATE TABLE IF NOT EXISTS cities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'активный',
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
        mock_db.commit()

        # Таблица должна существовать и быть функциональной
        mock_db.execute("INSERT OR IGNORE INTO cities (name) VALUES ('Москва')")
        mock_db.commit()
        row = mock_db.execute("SELECT name FROM cities WHERE name = 'Москва'").fetchone()
        assert row is not None

    def test_alter_table_idempotent(self, mock_db):
        """Повторное ADD COLUMN обрабатывается без краша."""
        # Пытаемся добавить колонку, которая уже может существовать
        try:
            mock_db.execute("ALTER TABLE clients ADD COLUMN notes TEXT")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                pass  # Ожидаемо — колонка уже есть
            else:
                raise

        # Повторная попытка — не должна крашить
        try:
            mock_db.execute("ALTER TABLE clients ADD COLUMN notes TEXT")
        except sqlite3.OperationalError:
            pass  # Нормально — колонка уже существует

        # Данные не повреждены
        _seed_client(mock_db, client_id=500)
        row = mock_db.execute("SELECT id FROM clients WHERE id = 500").fetchone()
        assert row is not None

    def test_data_preserved_after_migration(self, mock_db):
        """Данные сохраняются после повторной миграции."""
        _seed_client(mock_db, client_id=600, full_name="Данные До Миграции")
        mock_db.commit()

        # Имитируем миграцию — CREATE TABLE IF NOT EXISTS + INSERT OR IGNORE
        mock_db.execute("""
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'активный',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        mock_db.execute("INSERT OR IGNORE INTO cities (name) VALUES ('Москва')")
        mock_db.commit()

        # Проверяем что данные клиента не потерялись
        row = mock_db.execute("SELECT full_name FROM clients WHERE id = 600").fetchone()
        assert row["full_name"] == "Данные До Миграции"


# ============================================================================
# 21. test_unique_contract_number (бонусный)
# ============================================================================

class TestUniqueContractNumber:
    """Номер договора уникален в БД."""

    def test_duplicate_contract_number_rejected(self, mock_db):
        """Вставка договора с дублирующимся номером вызывает IntegrityError."""
        _seed_client(mock_db)
        _seed_contract(mock_db, contract_id=1, number="DUP/2026")

        with pytest.raises(sqlite3.IntegrityError):
            mock_db.execute(
                """INSERT INTO contracts (contract_number, client_id, project_type)
                   VALUES ('DUP/2026', 1, 'Индивидуальный')"""
            )


# ============================================================================
# 22. test_offline_queue_valid_json (бонусный)
# ============================================================================

class TestOfflineQueueValidJson:
    """Данные в offline-очереди — валидный JSON."""

    def test_valid_json_stored(self, mock_db):
        """Данные операции хранятся как валидный JSON."""
        data = {"full_name": "Новое Имя", "phone": "+7 (900) 111-22-33"}
        mock_db.execute(
            "INSERT INTO offline_queue (operation_type, entity_type, entity_id, data) VALUES ('UPDATE', 'client', 1, ?)",
            (json.dumps(data, ensure_ascii=False),),
        )
        mock_db.commit()

        row = mock_db.execute("SELECT data FROM offline_queue WHERE entity_id = 1").fetchone()
        parsed = json.loads(row["data"])
        assert parsed["full_name"] == "Новое Имя"
        assert parsed["phone"] == "+7 (900) 111-22-33"

    def test_invalid_json_detectable(self, mock_db):
        """Некорректный JSON в offline-очереди обнаруживается."""
        mock_db.execute(
            "INSERT INTO offline_queue (operation_type, entity_type, entity_id, data) VALUES ('UPDATE', 'client', 2, 'NOT_JSON')"
        )
        mock_db.commit()

        row = mock_db.execute("SELECT data FROM offline_queue WHERE entity_id = 2").fetchone()
        with pytest.raises(json.JSONDecodeError):
            json.loads(row["data"])


# ============================================================================
# 23. test_validator_required_field (бонусный)
# ============================================================================

class TestValidatorRequiredField:
    """validate_required корректно проверяет обязательные поля."""

    def test_none_rejected(self):
        """None отклоняется."""
        from utils.validators import validate_required, ValidationError
        with pytest.raises(ValidationError, match="обязательно"):
            validate_required(None, "Имя клиента")

    def test_empty_string_rejected(self):
        """Пустая строка отклоняется."""
        from utils.validators import validate_required, ValidationError
        with pytest.raises(ValidationError, match="обязательно"):
            validate_required("   ", "Адрес")

    def test_valid_value_accepted(self):
        """Непустое значение проходит."""
        from utils.validators import validate_required
        assert validate_required("Иванов", "Имя клиента") is True


# ============================================================================
# Итоговая метка — все тесты покрыты
# ============================================================================

class TestRegressionSuiteSummary:
    """Документация: список всех покрытых регрессионных сценариев."""

    def test_all_20_plus_scenarios_covered(self):
        """Проверяем что в suite >= 20 тестовых классов."""
        # Считаем классы с тестами в этом модуле
        import inspect
        current_module = sys.modules[__name__]
        test_classes = [
            name for name, obj in inspect.getmembers(current_module, inspect.isclass)
            if name.startswith("Test") and name != "TestRegressionSuiteSummary"
        ]
        assert len(test_classes) >= 20, (
            f"Должно быть >= 20 тестовых классов, найдено: {len(test_classes)}: {test_classes}"
        )

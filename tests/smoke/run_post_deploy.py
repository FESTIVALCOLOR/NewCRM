#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoke-тест после деплоя (Уровень 2).

Запускается ПОСЛЕ Docker rebuild для проверки работоспособности.
Можно вызвать вручную или из CI/CD pipeline.

Использование:
    python tests/smoke/run_post_deploy.py                    # production
    python tests/smoke/run_post_deploy.py --url http://...   # кастомный URL
    python tests/smoke/run_post_deploy.py --wait 30          # ждать 30 сек до старта
    python tests/smoke/run_post_deploy.py --retries 5        # 5 попыток при недоступности

Возвращает:
    exit code 0 — все проверки прошли
    exit code 1 — есть ошибки
"""

import sys
import os
import time
import argparse
import requests

# Добавляем путь проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import API_BASE_URL

# Критические endpoint-ы для проверки после деплоя
HEALTH_CHECKS = [
    # (метод, путь, описание, нужна_авторизация, допустимые_коды)
    ("GET", "/", "Корневой endpoint", False, [200]),
    ("GET", "/health", "Health check", False, [200]),
    ("GET", "/api/crm/cards?project_type=Индивидуальный", "CRM карточки", True, [200]),
    ("GET", "/api/contracts", "Договоры", True, [200]),
    ("GET", "/api/clients", "Клиенты", True, [200]),
    ("GET", "/api/employees", "Сотрудники", True, [200]),
    ("GET", "/api/payments", "Платежи", True, [200]),
    ("GET", "/api/supervision/cards", "Авторский надзор", True, [200]),
    ("GET", "/api/statistics/projects?project_type=Индивидуальный", "Статистика проектов", True, [200]),
    ("GET", "/api/statistics/supervision", "Статистика надзора", True, [200]),
    ("GET", "/api/v1/agents", "Агенты", True, [200]),
    ("GET", "/api/v1/cities", "Города", True, [200]),
    ("GET", "/api/rates", "Тарифы", True, [200]),
]


def get_auth_token(base_url: str) -> str | None:
    """Получить JWT токен для авторизованных запросов."""
    try:
        resp = requests.post(
            f"{base_url}/api/auth/login",
            data={"username": "admin", "password": "admin123"},
            timeout=10,
            verify=False,
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception as e:
        print(f"  [AUTH] Ошибка авторизации: {e}")
    return None


def wait_for_server(base_url: str, retries: int = 10, delay: float = 5.0) -> bool:
    """Подождать пока сервер станет доступен."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(f"{base_url}/", timeout=5, verify=False)
            if resp.status_code == 200:
                print(f"  Сервер доступен (попытка {attempt}/{retries})")
                return True
        except Exception:
            pass
        if attempt < retries:
            print(f"  Сервер недоступен, ждём {delay}с... (попытка {attempt}/{retries})")
            time.sleep(delay)

    print(f"  Сервер не стал доступен после {retries} попыток")
    return False


def run_checks(base_url: str) -> tuple[int, int, list[str]]:
    """Запустить все проверки. Возвращает (passed, failed, errors)."""
    passed = 0
    failed = 0
    errors = []

    # Авторизация
    token = get_auth_token(base_url)
    auth_headers = {"Authorization": f"Bearer {token}"} if token else {}

    for method, path, desc, needs_auth, ok_codes in HEALTH_CHECKS:
        headers = auth_headers if needs_auth else {}
        if needs_auth and not token:
            print(f"  SKIP  {desc} (нет токена)")
            continue

        try:
            start = time.time()
            resp = requests.request(
                method,
                f"{base_url}{path}",
                headers=headers,
                timeout=15,
                verify=False,
            )
            elapsed = time.time() - start

            if resp.status_code in ok_codes:
                passed += 1
                status = "OK"
                timing = f"{elapsed:.1f}с"
                if elapsed > 5:
                    timing += " (МЕДЛЕННО!)"
                print(f"  OK    {desc} [{resp.status_code}] {timing}")
            else:
                failed += 1
                error_msg = f"{desc}: HTTP {resp.status_code}"
                errors.append(error_msg)
                print(f"  FAIL  {desc} [{resp.status_code}] ожидался {ok_codes}")
        except requests.exceptions.Timeout:
            failed += 1
            error_msg = f"{desc}: TIMEOUT"
            errors.append(error_msg)
            print(f"  FAIL  {desc} [TIMEOUT]")
        except requests.exceptions.ConnectionError as e:
            failed += 1
            error_msg = f"{desc}: CONNECTION ERROR"
            errors.append(error_msg)
            print(f"  FAIL  {desc} [CONNECTION ERROR] {e}")

    return passed, failed, errors


def main():
    parser = argparse.ArgumentParser(description="Smoke-тест после деплоя")
    parser.add_argument("--url", default=None, help="URL API сервера")
    parser.add_argument("--wait", type=int, default=0, help="Секунд ожидания перед стартом")
    parser.add_argument("--retries", type=int, default=10, help="Попытки ожидания сервера")
    args = parser.parse_args()

    base_url = (args.url or API_BASE_URL).rstrip("/")

    print(f"\n{'='*60}")
    print(f"  SMOKE-ТЕСТ ПОСЛЕ ДЕПЛОЯ")
    print(f"  URL: {base_url}")
    print(f"{'='*60}\n")

    # Ожидание перед стартом (после Docker rebuild)
    if args.wait > 0:
        print(f"  Ожидание {args.wait} секунд...")
        time.sleep(args.wait)

    # Ожидание доступности сервера
    print("  Проверка доступности сервера...")
    if not wait_for_server(base_url, retries=args.retries):
        print(f"\n{'='*60}")
        print(f"  РЕЗУЛЬТАТ: FAIL — сервер недоступен")
        print(f"{'='*60}\n")
        return 1

    # Запуск проверок
    print(f"\n  Запуск {len(HEALTH_CHECKS)} проверок...\n")
    passed, failed, errors = run_checks(base_url)

    # Итог
    total = passed + failed
    print(f"\n{'='*60}")
    if failed == 0:
        print(f"  РЕЗУЛЬТАТ: OK — {passed}/{total} проверок пройдено")
    else:
        print(f"  РЕЗУЛЬТАТ: FAIL — {failed}/{total} проверок не прошли")
        for err in errors:
            print(f"    - {err}")
    print(f"{'='*60}\n")

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    # Подавить InsecureRequestWarning
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    sys.exit(main())

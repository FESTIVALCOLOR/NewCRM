# -*- coding: utf-8 -*-
"""
Smoke Tests conftest — auto-skip если сервер недоступен + общие хелперы.
"""
import pytest
import requests
import urllib3
import sys
import os
from datetime import datetime

# Подавляем InsecureRequestWarning (сотни warnings при запуске smoke-тестов)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import API_BASE_URL

TEST_PREFIX = "__SMOKE__"
TIMEOUT = 15


def _check_server():
    try:
        return requests.get(f"{API_BASE_URL}/health", timeout=5, verify=False).status_code == 200
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    # Проверяем только если есть smoke-тесты в сессии
    smoke_items = [i for i in items if "smoke" in str(i.fspath)]
    if not smoke_items:
        return

    if _check_server():
        return

    skip = pytest.mark.skip(reason="API сервер недоступен — Smoke тесты пропущены")
    for item in smoke_items:
        item.add_marker(skip)


# ════════════════════════════════════════════════════════════
# Общая HTTP-сессия и хелперы (для новых файлов)
# ════════════════════════════════════════════════════════════

_session = requests.Session()
_session.verify = False


def _get(path, headers, params=None):
    return _session.get(f"{API_BASE_URL}{path}", headers=headers,
                        params=params, timeout=TIMEOUT)


def _post(path, headers, json=None, data=None):
    return _session.post(f"{API_BASE_URL}{path}", headers=headers,
                         json=json, data=data, timeout=TIMEOUT)


def _put(path, headers, json=None):
    return _session.put(f"{API_BASE_URL}{path}", headers=headers,
                        json=json, timeout=TIMEOUT)


def _patch(path, headers, json=None):
    return _session.patch(f"{API_BASE_URL}{path}", headers=headers,
                          json=json, timeout=TIMEOUT)


def _delete(path, headers, params=None):
    return _session.delete(f"{API_BASE_URL}{path}", headers=headers,
                           params=params, timeout=TIMEOUT)


@pytest.fixture(scope="session")
def admin_headers():
    """Авторизация admin (session-scope, переиспользуется всеми файлами)."""
    resp = _post("/api/auth/login", {}, data={"username": "admin", "password": "admin123"})
    if resp.status_code != 200:
        pytest.skip(f"Не удалось авторизоваться: {resp.status_code}")
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def create_test_client(headers, suffix=""):
    """Создать тестового клиента. Возвращает client_id."""
    ts = datetime.now().strftime('%H%M%S%f')[:10]
    resp = _post("/api/clients", headers, json={
        "client_type": "Физическое лицо",
        "full_name": f"{TEST_PREFIX}{suffix}_{ts}",
        "phone": f"+7999{ts[:7]}",
    })
    assert resp.status_code == 200, f"Создание клиента: {resp.status_code} {resp.text}"
    return resp.json()["id"]


def create_test_contract(headers, client_id, suffix="", project_type="Индивидуальный"):
    """Создать тестовой договор. Возвращает contract_id."""
    ts = datetime.now().strftime('%H%M%S%f')[:10]
    resp = _post("/api/contracts", headers, json={
        "client_id": client_id,
        "project_type": project_type,
        "agent_type": "ФЕСТИВАЛЬ",
        "city": "МСК",
        "contract_number": f"{TEST_PREFIX}{suffix}{ts}",
        "contract_date": datetime.now().strftime("%Y-%m-%d"),
        "address": f"{TEST_PREFIX}Адрес {suffix} {ts}",
        "area": 100.0,
        "total_amount": 500000.0,
        "advance_payment": 250000.0,
        "additional_payment": 250000.0,
        "contract_period": 60,
        "status": "Новый заказ",
    })
    assert resp.status_code == 200, f"Создание договора: {resp.status_code} {resp.text}"
    return resp.json()["id"]


def find_crm_card_by_contract(headers, contract_id, project_type="Индивидуальный"):
    """Найти CRM карточку по contract_id. Возвращает card_id."""
    resp = _get("/api/crm/cards", headers, params={"project_type": project_type})
    assert resp.status_code == 200
    card = next((c for c in resp.json() if c["contract_id"] == contract_id), None)
    assert card, f"CRM карточка не найдена для договора {contract_id}"
    return card["id"]


def create_test_card(headers, suffix="", project_type="Индивидуальный"):
    """Создать клиент + договор + найти CRM карточку.
    Возвращает (client_id, contract_id, card_id).
    """
    client_id = create_test_client(headers, suffix)
    contract_id = create_test_contract(headers, client_id, suffix, project_type)
    card_id = find_crm_card_by_contract(headers, contract_id, project_type)
    return client_id, contract_id, card_id


def cleanup_test_card(headers, client_id, contract_id):
    """Удалить договор и клиента (каскадно удалит карточки/платежи)."""
    try:
        _delete(f"/api/contracts/{contract_id}", headers)
    except Exception:
        pass
    try:
        _delete(f"/api/clients/{client_id}", headers)
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def cleanup_smoke_data_after_all(admin_headers):
    """Глобальная очистка __SMOKE__ данных ПОСЛЕ всех тестов.

    Порядок: платежи → CRM карточки → supervision карточки → договоры → клиенты.
    Это гарантирует удаление даже если per-test cleanup не сработал.
    """
    yield  # Тесты выполняются

    import logging
    log = logging.getLogger("smoke_cleanup")

    # 1. Удаляем тестовые договоры (каскадно удалит CRM/supervision карточки и платежи)
    try:
        contracts = _get("/api/contracts", admin_headers).json()
        smoke_contracts = [c for c in contracts if TEST_PREFIX in str(c.get("contract_number", ""))]
        for c in smoke_contracts:
            try:
                _delete(f"/api/contracts/{c['id']}", admin_headers)
            except Exception:
                pass
        if smoke_contracts:
            log.info(f"Cleanup: удалено {len(smoke_contracts)} тестовых договоров")
    except Exception:
        pass

    # 2. Удаляем тестовых клиентов (теперь без договоров)
    try:
        clients = _get("/api/clients", admin_headers).json()
        smoke_clients = [c for c in clients if TEST_PREFIX in str(c.get("full_name", ""))]
        for c in smoke_clients:
            try:
                _delete(f"/api/clients/{c['id']}", admin_headers)
            except Exception:
                pass
        if smoke_clients:
            log.info(f"Cleanup: удалено {len(smoke_clients)} тестовых клиентов")
    except Exception:
        pass

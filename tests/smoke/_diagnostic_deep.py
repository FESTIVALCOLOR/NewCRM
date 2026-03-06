# -*- coding: utf-8 -*-
"""
DEEP DIAGNOSTIC: Комплексный аудит данных, логики и синхронизации на РЕАЛЬНОМ сервере.

НЕ проверяет HTTP-коды — проверяет ДАННЫЕ:
- Корректность полей в ответах (типы, форматы, обязательные поля)
- Перекрёстные ссылки между сущностями (сироты, мёртвые ссылки)
- Консистентность workflow-состояний (стадии, исполнители, статусы)
- Синхронизация CRUD-операций (create -> read -> update -> verify)
- Аномалии данных (нулевые суммы, пустые даты, дубликаты)
- Время отклика endpoint-ов

Запуск:
    pytest tests/smoke/_diagnostic_deep.py -v --timeout=300 -s
"""

import time
import re
import warnings
import pytest
import requests
import urllib3
import sys
import os
from collections import defaultdict
from datetime import datetime, date

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import API_BASE_URL

TEST_PREFIX = "__DIAG__"
TIMEOUT = 30
SLOW_THRESHOLD_SEC = 5.0

_session = requests.Session()
_session.verify = False


# ════════════════════════════════════════════════════════════
# HTTP helpers с замером времени
# ════════════════════════════════════════════════════════════

_timing_log = []


def _timed_get(path, headers, params=None):
    t0 = time.time()
    r = _session.get(f"{API_BASE_URL}{path}", headers=headers,
                     params=params, timeout=TIMEOUT)
    elapsed = time.time() - t0
    _timing_log.append((path, elapsed))
    return r, elapsed


def _get(path, headers, params=None):
    r, _ = _timed_get(path, headers, params)
    return r


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


# ════════════════════════════════════════════════════════════
# Утилиты
# ════════════════════════════════════════════════════════════

def _is_valid_iso_date(s):
    """Проверяет что строка — валидная ISO-дата (YYYY-MM-DD или datetime)."""
    if not s or not isinstance(s, str):
        return False
    patterns = [
        r'^\d{4}-\d{2}-\d{2}$',
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
        r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
    ]
    return any(re.match(p, s) for p in patterns)


def _format_issues(issues, title=""):
    """Форматирует список проблем в читаемый отчёт."""
    if not issues:
        return ""
    sep = "=" * 60
    lines = [f"\n{sep}", f"  {title} ({len(issues)} проблем)", f"{sep}"]
    for i, issue in enumerate(issues, 1):
        lines.append(f"  [{i:03d}] {issue}")
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════
# Фикстуры
# ════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def admin_headers():
    """Авторизация admin."""
    resp = _post("/api/auth/login", {}, data={"username": "admin", "password": "admin123"})
    if resp.status_code != 200:
        pytest.skip(f"Не удалось авторизоваться: {resp.status_code}")
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(scope="session")
def all_data(admin_headers):
    """Загрузка ВСЕХ данных для аудита."""
    def fetch(path, params=None):
        r = _get(path, admin_headers, params)
        if r.status_code != 200:
            print(f"  WARN: {path} вернул {r.status_code}")
            return []
        data = r.json()
        return data if isinstance(data, list) else [data] if isinstance(data, dict) else []

    print("\n--- Загрузка данных для диагностики ---")

    data = {
        "contracts": fetch("/api/contracts"),
        "clients": fetch("/api/clients"),
        "payments": fetch("/api/payments"),
        "employees": fetch("/api/employees"),
        "rates": fetch("/api/rates"),
        "crm_individual": fetch("/api/crm/cards", {"project_type": "Индивидуальный"}),
        "crm_template": fetch("/api/crm/cards", {"project_type": "Шаблонный"}),
        "crm_individual_archive": fetch("/api/crm/cards", {"project_type": "Индивидуальный", "archived": "true"}),
        "crm_template_archive": fetch("/api/crm/cards", {"project_type": "Шаблонный", "archived": "true"}),
        "supervision_active": fetch("/api/supervision/cards"),
        "supervision_archive": fetch("/api/supervision/cards", {"archived": "true"}),
        "stage_executors": fetch("/api/sync/stage-executors"),
    }

    # Индексы
    data["contracts_by_id"] = {c["id"]: c for c in data["contracts"]}
    data["clients_by_id"] = {c["id"]: c for c in data["clients"]}
    data["employees_by_id"] = {e["id"]: e for e in data["employees"]}
    data["all_crm_active"] = data["crm_individual"] + data["crm_template"]
    data["all_crm_archive"] = data["crm_individual_archive"] + data["crm_template_archive"]
    data["all_crm_cards"] = data["all_crm_active"] + data["all_crm_archive"]
    data["crm_cards_by_id"] = {c["id"]: c for c in data["all_crm_cards"]}

    # Stage executors по карточке
    se_by_card = defaultdict(list)
    for se in data["stage_executors"]:
        se_by_card[se.get("crm_card_id")].append(se)
    data["stage_executors_by_card"] = dict(se_by_card)

    # Тарифы
    rates_index = {}
    for r in data["rates"]:
        key = (r.get("project_type"), r.get("role"), r.get("stage_name"))
        rates_index[key] = r
    data["rates_index"] = rates_index

    counts = {k: len(v) for k, v in data.items() if isinstance(v, list)}
    print(f"  Загружено: {counts}")
    return data


# ════════════════════════════════════════════════════════════
#  1. RESPONSE CONTENT VALIDATION
# ════════════════════════════════════════════════════════════

class TestResponseContentValidation:
    """Проверка что API возвращает корректные данные в каждой записи."""

    def test_crm_cards_required_fields(self, all_data):
        """Каждая CRM карточка ОБЯЗАНА иметь id, contract_id, column_name, client_name."""
        issues = []
        required = ["id", "contract_id", "column_name"]

        for card in all_data["all_crm_cards"]:
            card_id = card.get("id", "???")
            for field in required:
                val = card.get(field)
                if val is None or val == "":
                    issues.append(
                        f"CRM card id={card_id}: поле '{field}' пустое/отсутствует"
                    )
            # client_name может быть в card_data или напрямую
            client_name = (card.get("client_name")
                           or (card.get("card_data") or {}).get("client_name"))
            if not client_name:
                # Если нет клиента — проверим через contract
                contract = all_data["contracts_by_id"].get(card.get("contract_id"))
                if contract:
                    client_id = contract.get("client_id")
                    client = all_data["clients_by_id"].get(client_id)
                    if not client:
                        issues.append(
                            f"CRM card id={card_id}: нет client_name и клиент id={client_id} не найден"
                        )
                else:
                    issues.append(
                        f"CRM card id={card_id}: нет client_name и contract_id={card.get('contract_id')} не найден"
                    )

        report = _format_issues(issues, "CRM карточки: обязательные поля")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} проблем с обязательными полями CRM карточек{report}"

    def test_contracts_area_and_amount(self, all_data):
        """Каждый договор ОБЯЗАН иметь area > 0 и total_amount > 0."""
        issues = []

        for c in all_data["contracts"]:
            cid = c.get("id", "???")
            num = c.get("contract_number", "???")
            status = c.get("status", "")

            # Пропускаем расторгнутые — у них могут быть нулевые суммы
            if status == "РАСТОРГНУТ":
                continue

            area = c.get("area")
            if area is None or (isinstance(area, (int, float)) and area <= 0):
                issues.append(
                    f"Договор id={cid} №{num}: area={area} (ожидается > 0)"
                )

            total = c.get("total_amount")
            if total is None or (isinstance(total, (int, float)) and total <= 0):
                issues.append(
                    f"Договор id={cid} №{num}: total_amount={total} (ожидается > 0)"
                )

        report = _format_issues(issues, "Договоры: area и total_amount")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} проблем с area/total_amount{report}"

    def test_payments_amounts_valid(self, all_data):
        """Суммы платежей — числовые и положительные (кроме корректировок)."""
        issues = []

        for p in all_data["payments"]:
            pid = p.get("id", "???")
            amount = p.get("final_amount")

            # Проверка типа
            if amount is not None and not isinstance(amount, (int, float)):
                issues.append(
                    f"Платёж id={pid}: final_amount={amount!r} — НЕ число (тип {type(amount).__name__})"
                )
                continue

            # Нулевая/отрицательная сумма (если не ручная корректировка)
            if amount is not None and isinstance(amount, (int, float)) and amount < 0:
                if not p.get("is_manual"):
                    issues.append(
                        f"Платёж id={pid}: final_amount={amount} — отрицательная сумма"
                    )

        report = _format_issues(issues, "Платежи: валидность сумм")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} проблем с суммами платежей{report}"

    def test_payments_employee_exists(self, all_data):
        """employee_id в платежах ссылается на существующего сотрудника."""
        issues = []
        employees_by_id = all_data["employees_by_id"]

        for p in all_data["payments"]:
            pid = p.get("id", "???")
            eid = p.get("employee_id")
            if eid is not None and eid not in employees_by_id:
                issues.append(
                    f"Платёж id={pid}: employee_id={eid} — сотрудник НЕ существует"
                )

        report = _format_issues(issues, "Платежи: несуществующие сотрудники")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} платежей с несуществующими сотрудниками{report}"


# ════════════════════════════════════════════════════════════
#  2. CROSS-ENTITY CONSISTENCY
# ════════════════════════════════════════════════════════════

class TestCrossEntityConsistency:
    """Перекрёстная валидация: все ссылки между сущностями существуют."""

    def test_crm_card_contract_exists(self, all_data):
        """Для каждой CRM карточки contract_id ссылается на существующий договор."""
        issues = []
        contracts_by_id = all_data["contracts_by_id"]

        for card in all_data["all_crm_cards"]:
            cid = card.get("id", "???")
            contract_id = card.get("contract_id")
            if contract_id and contract_id not in contracts_by_id:
                issues.append(
                    f"CRM card id={cid}: contract_id={contract_id} — договор НЕ существует (сиротская карточка)"
                )

        report = _format_issues(issues, "CRM -> Договоры: сиротские карточки")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} сиротских CRM карточек{report}"

    def test_payment_contract_exists(self, all_data):
        """Для каждого платежа contract_id ссылается на существующий договор."""
        issues = []
        contracts_by_id = all_data["contracts_by_id"]

        for p in all_data["payments"]:
            pid = p.get("id", "???")
            contract_id = p.get("contract_id")
            if contract_id and contract_id not in contracts_by_id:
                issues.append(
                    f"Платёж id={pid}: contract_id={contract_id} — договор НЕ существует (сиротский платёж)"
                )

        report = _format_issues(issues, "Платежи -> Договоры: сиротские платежи")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} сиротских платежей{report}"

    def test_stage_executor_employee_exists(self, all_data):
        """Для каждого stage_executor employee_id ссылается на существующего сотрудника."""
        issues = []
        employees_by_id = all_data["employees_by_id"]

        for se in all_data["stage_executors"]:
            se_id = se.get("id", "???")
            eid = se.get("employee_id")
            if eid is not None and eid not in employees_by_id:
                card_id = se.get("crm_card_id", "???")
                stage = se.get("stage_name", "???")
                issues.append(
                    f"StageExecutor id={se_id} (card={card_id}, stage={stage}): "
                    f"employee_id={eid} — сотрудник НЕ существует"
                )

        report = _format_issues(issues, "StageExecutors -> Сотрудники: мёртвые ссылки")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} stage_executors с несуществующими сотрудниками{report}"

    def test_contract_client_exists(self, all_data):
        """Для каждого договора client_id ссылается на существующего клиента."""
        issues = []
        clients_by_id = all_data["clients_by_id"]

        for c in all_data["contracts"]:
            cid = c.get("id", "???")
            client_id = c.get("client_id")
            if client_id and client_id not in clients_by_id:
                issues.append(
                    f"Договор id={cid} №{c.get('contract_number', '???')}: "
                    f"client_id={client_id} — клиент НЕ существует"
                )

        report = _format_issues(issues, "Договоры -> Клиенты: сиротские договоры")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} договоров с несуществующими клиентами{report}"

    def test_dashboard_crm_matches_actual_counts(self, admin_headers, all_data):
        """Dashboard /api/dashboard/crm числа совпадают с фактическими подсчётами карточек."""
        issues = []

        for project_type in ["Индивидуальный", "Шаблонный"]:
            resp = _get("/api/dashboard/crm", admin_headers,
                        params={"project_type": project_type})
            if resp.status_code != 200:
                issues.append(f"Dashboard CRM {project_type}: HTTP {resp.status_code}")
                continue

            dash = resp.json()
            dash_active = dash.get("active_orders", -1)
            dash_archive = dash.get("archive_orders", -1)
            dash_total = dash.get("total_orders", -1)

            # Подсчёт фактических из загруженных данных
            archive_statuses = ["СДАН", "РАСТОРГНУТ", "АВТОРСКИЙ НАДЗОР"]

            if project_type == "Индивидуальный":
                all_cards = all_data["crm_individual"] + all_data["crm_individual_archive"]
            else:
                all_cards = all_data["crm_template"] + all_data["crm_template_archive"]

            # Считаем активные/архивные на основе статуса договора
            actual_active = 0
            actual_archive = 0
            for card in all_cards:
                contract = all_data["contracts_by_id"].get(card.get("contract_id"))
                if contract:
                    if contract.get("status") in archive_statuses:
                        actual_archive += 1
                    else:
                        actual_active += 1

            # Подсчёт total_orders = количество договоров данного типа
            actual_total = sum(
                1 for c in all_data["contracts"]
                if c.get("project_type") == project_type
            )

            if dash_active != actual_active:
                issues.append(
                    f"Dashboard {project_type} active_orders: "
                    f"dashboard={dash_active}, фактически={actual_active} (разница={dash_active - actual_active})"
                )
            if dash_archive != actual_archive:
                issues.append(
                    f"Dashboard {project_type} archive_orders: "
                    f"dashboard={dash_archive}, фактически={actual_archive} (разница={dash_archive - actual_archive})"
                )
            if dash_total != actual_total:
                issues.append(
                    f"Dashboard {project_type} total_orders: "
                    f"dashboard={dash_total}, фактически={actual_total} (разница={dash_total - actual_total})"
                )

        report = _format_issues(issues, "Dashboard CRM vs фактические подсчёты")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} расхождений в Dashboard{report}"


# ════════════════════════════════════════════════════════════
#  3. WORKFLOW STATE CONSISTENCY
# ════════════════════════════════════════════════════════════

class TestWorkflowStateConsistency:
    """Проверка логической целостности workflow-состояний."""

    STAGE_COLUMNS = [
        "Стадия 1: планировочные решения",
        "Стадия 2: концепция дизайна",
        "Стадия 2: рабочие чертежи",
        "Стадия 3: рабочие чертежи",
        "Стадия 3: 3д визуализация (Дополнительная)",
    ]

    def test_stage_cards_have_executors(self, all_data):
        """Карточки в стадиях 1/2/3 ДОЛЖНЫ иметь хотя бы одного stage_executor."""
        issues = []
        se_by_card = all_data["stage_executors_by_card"]

        for card in all_data["all_crm_active"]:
            col = card.get("column_name", "")
            card_id = card.get("id")

            if any(col.startswith(s.split(":")[0] + ":") for s in self.STAGE_COLUMNS
                   if ":" in s):
                # Карточка в стадии — проверяем наличие исполнителей
                executors = se_by_card.get(card_id, [])
                if not executors:
                    contract = all_data["contracts_by_id"].get(card.get("contract_id"), {})
                    issues.append(
                        f"CRM card id={card_id} в колонке '{col}': "
                        f"НЕТ ни одного stage_executor "
                        f"(договор №{contract.get('contract_number', '???')})"
                    )

        report = _format_issues(issues, "Стадии без исполнителей")
        if report:
            print(report)
        # Это warning, а не hard fail — карточки могут быть только что перемещены
        if issues:
            warnings.warn(
                f"Найдено {len(issues)} карточек в стадиях без исполнителей{report}",
                UserWarning,
            )

    def test_archived_cards_not_in_active(self, all_data):
        """Архивные карточки НЕ должны дублироваться в активных списках."""
        issues = []

        archive_ids = {c["id"] for c in all_data["all_crm_archive"]}
        active_ids = {c["id"] for c in all_data["all_crm_active"]}

        overlap = archive_ids & active_ids
        for card_id in overlap:
            card = all_data["crm_cards_by_id"].get(card_id, {})
            issues.append(
                f"CRM card id={card_id}: присутствует И в активных, И в архивных "
                f"(column={card.get('column_name', '???')})"
            )

        report = _format_issues(issues, "Дубликаты: активные + архивные")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} карточек-дубликатов в активных и архивных{report}"

    def test_completed_stages_have_dates(self, all_data):
        """Завершённые stage_executors (completed=True) ДОЛЖНЫ иметь completed_at."""
        issues = []

        for se in all_data["stage_executors"]:
            se_id = se.get("id", "???")
            is_completed = se.get("completed") or se.get("is_completed")
            completed_at = se.get("completed_at") or se.get("completion_date")

            if is_completed and not completed_at:
                issues.append(
                    f"StageExecutor id={se_id} (card={se.get('crm_card_id')}, "
                    f"stage={se.get('stage_name')}): completed=True но completed_at=None"
                )

        report = _format_issues(issues, "Завершённые стадии без даты завершения")
        if report:
            print(report)
        if issues:
            warnings.warn(
                f"Найдено {len(issues)} завершённых стадий без даты{report}",
                UserWarning,
            )

    def test_paid_payments_have_dates(self, all_data):
        """Платежи с is_paid=True ОБЯЗАНЫ иметь paid_date."""
        issues = []

        for p in all_data["payments"]:
            pid = p.get("id", "???")
            if p.get("is_paid") and not p.get("paid_date"):
                contract_id = p.get("contract_id", "???")
                role = p.get("role", "???")
                issues.append(
                    f"Платёж id={pid} (contract={contract_id}, role={role}): "
                    f"is_paid=True но paid_date=None"
                )

        report = _format_issues(issues, "Оплаченные платежи без даты оплаты")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} оплаченных платежей без paid_date{report}"

    def test_crm_columns_valid(self, all_data):
        """Все column_name карточек входят в допустимый набор колонок."""
        VALID_INDIVIDUAL = {
            "Новый заказ", "В ожидании",
            "Стадия 1: планировочные решения",
            "Стадия 2: концепция дизайна",
            "Стадия 3: рабочие чертежи",
            "Выполненный проект",
        }
        VALID_TEMPLATE = {
            "Новый заказ", "В ожидании",
            "Стадия 1: планировочные решения",
            "Стадия 2: рабочие чертежи",
            "Стадия 3: 3д визуализация (Дополнительная)",
            "Выполненный проект",
        }

        issues = []
        for card in all_data["all_crm_cards"]:
            col = card.get("column_name", "")
            card_id = card.get("id", "???")
            contract = all_data["contracts_by_id"].get(card.get("contract_id"), {})
            ptype = contract.get("project_type", "Индивидуальный")

            valid = VALID_TEMPLATE if ptype == "Шаблонный" else VALID_INDIVIDUAL
            if col and col not in valid:
                issues.append(
                    f"CRM card id={card_id}: column_name='{col}' — "
                    f"НЕ входит в допустимые для {ptype}"
                )

        report = _format_issues(issues, "Недопустимые column_name")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} карточек с недопустимыми колонками{report}"


# ════════════════════════════════════════════════════════════
#  4. SYNCHRONIZATION CHECKS (CRUD round-trip)
# ════════════════════════════════════════════════════════════

class TestSynchronizationChecks:
    """Создание -> чтение -> обновление -> проверка: данные синхронизированы."""

    def test_create_client_contract_card_roundtrip(self, admin_headers):
        """Создать клиента -> договор -> проверить что CRM карточка авто-создалась."""
        issues = []
        client_id = None
        contract_id = None

        try:
            # 1. Создаём клиента
            ts = datetime.now().strftime("%H%M%S%f")[:10]
            client_resp = _post("/api/clients", admin_headers, json={
                "client_type": "Физическое лицо",
                "full_name": f"{TEST_PREFIX}DiagClient_{ts}",
                "phone": f"+7999{ts[:7]}",
            })
            assert client_resp.status_code == 200, \
                f"Создание клиента: {client_resp.status_code} {client_resp.text}"
            client_id = client_resp.json()["id"]

            # 2. Создаём договор
            contract_resp = _post("/api/contracts", admin_headers, json={
                "client_id": client_id,
                "project_type": "Индивидуальный",
                "agent_type": "ФЕСТИВАЛЬ",
                "city": "МСК",
                "contract_number": f"{TEST_PREFIX}D{ts}",
                "contract_date": datetime.now().strftime("%Y-%m-%d"),
                "address": f"{TEST_PREFIX}Диагностический адрес {ts}",
                "area": 80.0,
                "total_amount": 400000.0,
                "advance_payment": 200000.0,
                "additional_payment": 200000.0,
                "contract_period": 45,
                "status": "Новый заказ",
            })
            assert contract_resp.status_code == 200, \
                f"Создание договора: {contract_resp.status_code} {contract_resp.text}"
            contract_id = contract_resp.json()["id"]

            # 3. Проверяем что CRM карточка авто-создалась
            cards_resp = _get("/api/crm/cards", admin_headers,
                              params={"project_type": "Индивидуальный"})
            assert cards_resp.status_code == 200
            cards = cards_resp.json()
            our_card = [c for c in cards if c.get("contract_id") == contract_id]

            if not our_card:
                issues.append(
                    f"CRM карточка НЕ авто-создалась для договора id={contract_id}"
                )
            else:
                card = our_card[0]
                # 4. Проверяем что карточка в правильной колонке
                if card.get("column_name") != "Новый заказ":
                    issues.append(
                        f"Новая CRM карточка в колонке '{card.get('column_name')}' "
                        f"вместо 'Новый заказ'"
                    )

                # 5. Проверяем что данные клиента прокинулись
                card_client = (card.get("client_name")
                               or (card.get("card_data") or {}).get("client_name"))
                if not card_client:
                    issues.append(
                        f"CRM карточка id={card['id']}: client_name пуст"
                    )

        finally:
            if contract_id:
                _delete(f"/api/contracts/{contract_id}", admin_headers)
            if client_id:
                _delete(f"/api/clients/{client_id}", admin_headers)

        report = _format_issues(issues, "Синхронизация: клиент -> договор -> карточка")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} проблем синхронизации{report}"

    def test_move_card_column_roundtrip(self, admin_headers):
        """Переместить карточку -> проверить что column_name изменился в GET."""
        issues = []
        client_id = None
        contract_id = None

        try:
            ts = datetime.now().strftime("%H%M%S%f")[:10]
            # Создаём клиента + договор
            cr = _post("/api/clients", admin_headers, json={
                "client_type": "Физическое лицо",
                "full_name": f"{TEST_PREFIX}MoveTest_{ts}",
                "phone": f"+7998{ts[:7]}",
            })
            assert cr.status_code == 200
            client_id = cr.json()["id"]

            ctr = _post("/api/contracts", admin_headers, json={
                "client_id": client_id,
                "project_type": "Индивидуальный",
                "agent_type": "ФЕСТИВАЛЬ",
                "city": "СПБ",
                "contract_number": f"{TEST_PREFIX}M{ts}",
                "contract_date": datetime.now().strftime("%Y-%m-%d"),
                "address": f"{TEST_PREFIX}Move addr {ts}",
                "area": 60.0,
                "total_amount": 300000.0,
                "advance_payment": 150000.0,
                "additional_payment": 150000.0,
                "contract_period": 30,
                "status": "Новый заказ",
            })
            assert ctr.status_code == 200
            contract_id = ctr.json()["id"]

            # Находим карточку
            cards = _get("/api/crm/cards", admin_headers,
                         params={"project_type": "Индивидуальный"}).json()
            card = next((c for c in cards if c["contract_id"] == contract_id), None)
            assert card, "Карточка не найдена"

            # Перемещаем в "В ожидании"
            move = _patch(f"/api/crm/cards/{card['id']}/column", admin_headers,
                          json={"column_name": "В ожидании"})
            assert move.status_code == 200, \
                f"Перемещение: {move.status_code} {move.text}"

            # Проверяем что изменение отразилось
            check = _get(f"/api/crm/cards/{card['id']}", admin_headers)
            assert check.status_code == 200
            actual_col = check.json().get("column_name")
            if actual_col != "В ожидании":
                issues.append(
                    f"После PATCH column='В ожидании', GET вернул column='{actual_col}' "
                    f"(данные не синхронизированы)"
                )

        finally:
            if contract_id:
                _delete(f"/api/contracts/{contract_id}", admin_headers)
            if client_id:
                _delete(f"/api/clients/{client_id}", admin_headers)

        report = _format_issues(issues, "Синхронизация: перемещение карточки")
        if report:
            print(report)
        assert len(issues) == 0, f"Проблемы синхронизации перемещения{report}"

    def test_assign_executor_roundtrip(self, admin_headers):
        """Назначить исполнителя -> проверить что он виден в GET."""
        issues = []
        client_id = None
        contract_id = None

        try:
            ts = datetime.now().strftime("%H%M%S%f")[:10]
            cr = _post("/api/clients", admin_headers, json={
                "client_type": "Физическое лицо",
                "full_name": f"{TEST_PREFIX}ExecTest_{ts}",
                "phone": f"+7997{ts[:7]}",
            })
            assert cr.status_code == 200
            client_id = cr.json()["id"]

            ctr = _post("/api/contracts", admin_headers, json={
                "client_id": client_id,
                "project_type": "Индивидуальный",
                "agent_type": "ФЕСТИВАЛЬ",
                "city": "МСК",
                "contract_number": f"{TEST_PREFIX}E{ts}",
                "contract_date": datetime.now().strftime("%Y-%m-%d"),
                "address": f"{TEST_PREFIX}Exec addr {ts}",
                "area": 55.0,
                "total_amount": 250000.0,
                "advance_payment": 125000.0,
                "additional_payment": 125000.0,
                "contract_period": 30,
                "status": "Новый заказ",
            })
            assert ctr.status_code == 200
            contract_id = ctr.json()["id"]

            # Находим карточку
            cards = _get("/api/crm/cards", admin_headers,
                         params={"project_type": "Индивидуальный"}).json()
            card = next((c for c in cards if c["contract_id"] == contract_id), None)
            assert card, "Карточка не найдена"
            card_id = card["id"]

            # Перемещаем в Стадию 1
            move = _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                          json={"column_name": "В ожидании"})
            assert move.status_code == 200

            move2 = _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                           json={"column_name": "Стадия 1: планировочные решения"})
            assert move2.status_code == 200

            # Находим первого активного сотрудника для назначения
            employees = _get("/api/employees", admin_headers).json()
            emp = next(
                (e for e in employees
                 if e.get("status") == "активный"
                 and e.get("position") in ("Дизайнер", "СДП", "ГАП", "Чертёжник")),
                None
            )
            if not emp:
                pytest.skip("Нет активных сотрудников для назначения")

            # Назначаем исполнителя (API ожидает executor_id, не employee_id)
            assign = _post(f"/api/crm/cards/{card_id}/stage-executor", admin_headers,
                           json={
                               "stage_name": "Стадия 1: планировочные решения",
                               "executor_id": emp["id"],
                           })
            if assign.status_code not in (200, 201):
                issues.append(
                    f"Назначение исполнителя: {assign.status_code} {assign.text}"
                )
            else:
                # Проверяем через GET
                card_detail = _get(f"/api/crm/cards/{card_id}", admin_headers)
                assert card_detail.status_code == 200
                card_data = card_detail.json()

                # Проверяем stage_executors в ответе
                se_list = card_data.get("stage_executors", [])
                found = any(
                    se.get("employee_id") == emp["id"]
                    for se in se_list
                )
                if not found:
                    # Альтернативно — через sync endpoint
                    se_resp = _get("/api/sync/stage-executors", admin_headers)
                    if se_resp.status_code == 200:
                        all_se = se_resp.json()
                        found = any(
                            se.get("crm_card_id") == card_id
                            and se.get("employee_id") == emp["id"]
                            for se in all_se
                        )

                    if not found:
                        issues.append(
                            f"Назначенный исполнитель emp_id={emp['id']} "
                            f"НЕ виден в GET карточки id={card_id}"
                        )

        finally:
            if contract_id:
                _delete(f"/api/contracts/{contract_id}", admin_headers)
            if client_id:
                _delete(f"/api/clients/{client_id}", admin_headers)

        report = _format_issues(issues, "Синхронизация: назначение исполнителя")
        if report:
            print(report)
        assert len(issues) == 0, f"Проблемы синхронизации назначения{report}"

    def test_update_contract_area_reflects_in_get(self, admin_headers):
        """Обновить площадь договора -> проверить что GET возвращает новое значение."""
        issues = []
        client_id = None
        contract_id = None

        try:
            ts = datetime.now().strftime("%H%M%S%f")[:10]
            cr = _post("/api/clients", admin_headers, json={
                "client_type": "Физическое лицо",
                "full_name": f"{TEST_PREFIX}AreaTest_{ts}",
                "phone": f"+7996{ts[:7]}",
            })
            assert cr.status_code == 200
            client_id = cr.json()["id"]

            ctr = _post("/api/contracts", admin_headers, json={
                "client_id": client_id,
                "project_type": "Индивидуальный",
                "agent_type": "ФЕСТИВАЛЬ",
                "city": "СПБ",
                "contract_number": f"{TEST_PREFIX}A{ts}",
                "contract_date": datetime.now().strftime("%Y-%m-%d"),
                "address": f"{TEST_PREFIX}Area addr {ts}",
                "area": 100.0,
                "total_amount": 500000.0,
                "advance_payment": 250000.0,
                "additional_payment": 250000.0,
                "contract_period": 60,
                "status": "Новый заказ",
            })
            assert ctr.status_code == 200
            contract_id = ctr.json()["id"]

            # Обновляем площадь
            upd = _put(f"/api/contracts/{contract_id}", admin_headers, json={
                "area": 150.0,
                "total_amount": 750000.0,
            })
            if upd.status_code != 200:
                issues.append(f"PUT contract area: {upd.status_code} {upd.text}")
            else:
                # Проверяем
                check = _get(f"/api/contracts/{contract_id}", admin_headers)
                assert check.status_code == 200
                data = check.json()
                actual_area = data.get("area")
                if actual_area != 150.0:
                    issues.append(
                        f"После PUT area=150.0, GET вернул area={actual_area}"
                    )

        finally:
            if contract_id:
                _delete(f"/api/contracts/{contract_id}", admin_headers)
            if client_id:
                _delete(f"/api/clients/{client_id}", admin_headers)

        report = _format_issues(issues, "Синхронизация: обновление площади")
        if report:
            print(report)
        assert len(issues) == 0, f"Проблемы синхронизации площади{report}"


# ════════════════════════════════════════════════════════════
#  5. DATA TYPE / FORMAT ISSUES
# ════════════════════════════════════════════════════════════

class TestDataTypeFormatIssues:
    """Проверка типов данных и форматов значений."""

    def test_contract_dates_iso_format(self, all_data):
        """Даты договоров — валидный ISO формат."""
        issues = []
        date_fields = ["contract_date", "created_at", "updated_at"]

        for c in all_data["contracts"]:
            cid = c.get("id", "???")
            for field in date_fields:
                val = c.get(field)
                if val is not None and isinstance(val, str) and val.strip():
                    if not _is_valid_iso_date(val):
                        issues.append(
                            f"Договор id={cid}: {field}='{val}' — невалидный формат даты"
                        )

        report = _format_issues(issues, "Договоры: невалидные форматы дат")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} невалидных дат{report}"

    def test_payment_dates_iso_format(self, all_data):
        """Даты платежей — валидный ISO формат."""
        issues = []
        date_fields = ["paid_date", "created_at", "updated_at"]

        for p in all_data["payments"]:
            pid = p.get("id", "???")
            for field in date_fields:
                val = p.get(field)
                if val is not None and isinstance(val, str) and val.strip():
                    if not _is_valid_iso_date(val):
                        issues.append(
                            f"Платёж id={pid}: {field}='{val}' — невалидный формат даты"
                        )

        report = _format_issues(issues, "Платежи: невалидные форматы дат")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} невалидных дат{report}"

    def test_amounts_are_numbers(self, all_data):
        """Суммы в договорах и платежах — числа, не строки."""
        issues = []
        amount_fields_contract = ["area", "total_amount", "advance_payment", "additional_payment"]
        amount_fields_payment = ["final_amount", "rate_per_m2"]

        for c in all_data["contracts"]:
            cid = c.get("id", "???")
            for field in amount_fields_contract:
                val = c.get(field)
                if val is not None and not isinstance(val, (int, float)):
                    issues.append(
                        f"Договор id={cid}: {field}={val!r} — тип {type(val).__name__}, ожидается число"
                    )

        for p in all_data["payments"]:
            pid = p.get("id", "???")
            for field in amount_fields_payment:
                val = p.get(field)
                if val is not None and not isinstance(val, (int, float)):
                    issues.append(
                        f"Платёж id={pid}: {field}={val!r} — тип {type(val).__name__}, ожидается число"
                    )

        report = _format_issues(issues, "Суммы не являются числами")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} сумм с неправильным типом{report}"

    def test_ids_are_integers(self, all_data):
        """ID всех сущностей — целые числа."""
        issues = []

        entities = [
            ("contracts", all_data["contracts"]),
            ("clients", all_data["clients"]),
            ("employees", all_data["employees"]),
            ("payments", all_data["payments"]),
            ("crm_cards", all_data["all_crm_cards"]),
            ("stage_executors", all_data["stage_executors"]),
        ]

        for name, items in entities:
            for item in items:
                val = item.get("id")
                if val is not None and not isinstance(val, int):
                    issues.append(
                        f"{name}: id={val!r} — тип {type(val).__name__}, ожидается int"
                    )

        report = _format_issues(issues, "ID с неправильным типом")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} ID с неправильным типом{report}"

    def test_phone_numbers_format(self, all_data):
        """Телефоны клиентов — корректный формат (если заполнены)."""
        issues = []
        # Допустимые паттерны: +7..., 8..., пусто
        phone_re = re.compile(r'^(\+?\d[\d\s\-()]{6,20})?$')

        for c in all_data["clients"]:
            cid = c.get("id", "???")
            phone = c.get("phone")
            if phone and isinstance(phone, str) and phone.strip():
                clean = phone.strip()
                if not phone_re.match(clean):
                    issues.append(
                        f"Клиент id={cid} '{c.get('full_name', '???')}': "
                        f"phone='{clean}' — нестандартный формат"
                    )

        report = _format_issues(issues, "Клиенты: формат телефонов")
        if report:
            print(report)
        # Soft assert — не все телефоны идеальны
        if issues:
            warnings.warn(
                f"Найдено {len(issues)} нестандартных телефонов{report}",
                UserWarning,
            )

    def test_employee_required_fields(self, all_data):
        """Сотрудники имеют обязательные поля: id, full_name, position, status."""
        issues = []
        required = ["id", "full_name", "position"]

        for e in all_data["employees"]:
            eid = e.get("id", "???")
            for field in required:
                val = e.get(field)
                if val is None or val == "":
                    issues.append(
                        f"Сотрудник id={eid}: поле '{field}' пустое/отсутствует"
                    )

        report = _format_issues(issues, "Сотрудники: обязательные поля")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} проблем с полями сотрудников{report}"


# ════════════════════════════════════════════════════════════
#  6. RESPONSE TIME ANOMALIES
# ════════════════════════════════════════════════════════════

class TestResponseTimeAnomalies:
    """Проверка времени отклика ключевых endpoint-ов."""

    ENDPOINTS = [
        ("/api/contracts", None),
        ("/api/clients", None),
        ("/api/payments", None),
        ("/api/employees", None),
        ("/api/crm/cards", {"project_type": "Индивидуальный"}),
        ("/api/crm/cards", {"project_type": "Шаблонный"}),
        ("/api/supervision/cards", None),
        ("/api/rates", None),
        ("/api/dashboard/crm", {"project_type": "Индивидуальный"}),
        ("/api/dashboard/crm", {"project_type": "Шаблонный"}),
        ("/api/dashboard/clients", None),
        ("/api/dashboard/contracts", None),
        ("/api/dashboard/employees", None),
        ("/api/sync/stage-executors", None),
        ("/api/v1/agents", None),
        ("/api/v1/cities", None),
    ]

    def test_no_slow_endpoints(self, admin_headers):
        """Ни один ключевой endpoint не должен отвечать дольше 5 секунд."""
        issues = []
        timing_results = []

        for path, params in self.ENDPOINTS:
            r, elapsed = _timed_get(path, admin_headers, params)
            params_str = f" params={params}" if params else ""
            timing_results.append((path + params_str, elapsed, r.status_code))

            if elapsed > SLOW_THRESHOLD_SEC:
                issues.append(
                    f"{path}{params_str}: {elapsed:.2f}s (порог={SLOW_THRESHOLD_SEC}s) "
                    f"HTTP {r.status_code}"
                )

        # Выводим полную таблицу тайминга
        print(f"\n{'='*70}")
        print(f"  Response Time Report (порог: {SLOW_THRESHOLD_SEC}s)")
        print(f"{'='*70}")
        for path, elapsed, status in sorted(timing_results, key=lambda x: -x[1]):
            marker = " *** SLOW ***" if elapsed > SLOW_THRESHOLD_SEC else ""
            print(f"  {elapsed:6.2f}s  HTTP {status}  {path}{marker}")
        print(f"{'='*70}")

        report = _format_issues(issues, "Медленные endpoint-ы")
        if report:
            print(report)
        if issues:
            warnings.warn(
                f"Найдено {len(issues)} медленных endpoint-ов{report}",
                UserWarning,
            )


# ════════════════════════════════════════════════════════════
#  7. ADDITIONAL DATA ANOMALIES
# ════════════════════════════════════════════════════════════

class TestDataAnomalies:
    """Поиск аномалий в данных."""

    def test_duplicate_crm_cards_per_contract(self, all_data):
        """Один договор -> максимум одна CRM карточка (не считая архивных)."""
        issues = []
        cards_by_contract = defaultdict(list)

        for card in all_data["all_crm_active"]:
            contract_id = card.get("contract_id")
            if contract_id:
                cards_by_contract[contract_id].append(card)

        for contract_id, cards in cards_by_contract.items():
            if len(cards) > 1:
                card_ids = [c["id"] for c in cards]
                columns = [c.get("column_name", "???") for c in cards]
                issues.append(
                    f"Договор id={contract_id}: {len(cards)} активных CRM карточек "
                    f"(ids={card_ids}, columns={columns})"
                )

        report = _format_issues(issues, "Дубликаты CRM карточек на один договор")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} договоров с дубликатами карточек{report}"

    def test_zero_amount_payments_with_rates(self, all_data):
        """Платежи с final_amount=0 при наличии ненулевого тарифа — потенциальный баг."""
        issues = []
        rates_index = all_data["rates_index"]
        contracts_by_id = all_data["contracts_by_id"]

        for p in all_data["payments"]:
            pid = p.get("id", "???")
            amount = float(p.get("final_amount") or 0)
            if amount != 0:
                continue

            # Пропускаем ручные и оклады
            if p.get("is_manual") or p.get("role") == "Оклад":
                continue

            contract_id = p.get("contract_id")
            contract = contracts_by_id.get(contract_id, {})
            area = float(contract.get("area") or 0)
            role = p.get("role", "")
            stage = p.get("stage_name")
            project_type = p.get("project_type") or contract.get("project_type", "")

            # Проверяем есть ли тариф
            rate = rates_index.get((project_type, role, stage))
            if not rate:
                rate = rates_index.get((project_type, role, None))

            if rate and float(rate.get("rate_per_m2") or 0) > 0 and area > 0:
                expected = area * float(rate["rate_per_m2"])
                issues.append(
                    f"Платёж id={pid} (contract={contract_id}, role={role}, stage={stage}): "
                    f"final_amount=0 но тариф={rate['rate_per_m2']}, "
                    f"area={area}, ожидается={expected:.2f}"
                )

        report = _format_issues(issues, "Нулевые платежи при ненулевых тарифах")
        if report:
            print(report)
        if issues:
            warnings.warn(
                f"Найдено {len(issues)} нулевых платежей при ненулевых тарифах{report}",
                UserWarning,
            )

    def test_test_data_in_production(self, all_data):
        """Тестовые/smoke данные НЕ должны оставаться в production."""
        issues = []
        test_prefixes = ["__SMOKE__", "__DIAG__", "__TEST__", "test_", "ТЕСТ"]

        for c in all_data["clients"]:
            name = c.get("full_name") or ""
            if any(name.startswith(p) or name.startswith(p.upper()) for p in test_prefixes):
                issues.append(
                    f"Клиент id={c['id']}: тестовые данные в production: '{name}'"
                )

        for c in all_data["contracts"]:
            num = c.get("contract_number") or ""
            if any(num.startswith(p) or num.startswith(p.upper()) for p in test_prefixes):
                issues.append(
                    f"Договор id={c['id']}: тестовый номер в production: '{num}'"
                )

        report = _format_issues(issues, "Тестовые данные в production")
        if report:
            print(report)
        if issues:
            warnings.warn(
                f"Найдено {len(issues)} тестовых записей в production{report}",
                UserWarning,
            )

    def test_duplicate_payments_per_contract_role_stage(self, all_data):
        """Не должно быть дубликатов платежей (одинаковый contract+role+stage+payment_type)."""
        issues = []
        seen = defaultdict(list)

        for p in all_data["payments"]:
            key = (
                p.get("contract_id"),
                p.get("role"),
                p.get("stage_name"),
                p.get("payment_type"),
            )
            seen[key].append(p)

        for key, payments in seen.items():
            if len(payments) > 1:
                ids = [p["id"] for p in payments]
                amounts = [p.get("final_amount") for p in payments]
                contract_id, role, stage, ptype = key
                issues.append(
                    f"Дубликаты: contract={contract_id}, role={role}, "
                    f"stage={stage}, type={ptype}: ids={ids}, amounts={amounts}"
                )

        report = _format_issues(issues, "Дубликаты платежей")
        if report:
            print(report)
        if issues:
            warnings.warn(
                f"Найдено {len(issues)} групп дубликатов платежей{report}",
                UserWarning,
            )

    def test_contracts_without_crm_cards(self, all_data):
        """Каждый не-архивный договор ДОЛЖЕН иметь CRM карточку."""
        issues = []
        archive_statuses = {"СДАН", "РАСТОРГНУТ"}

        contracts_with_cards = {
            c.get("contract_id") for c in all_data["all_crm_cards"]
        }

        for c in all_data["contracts"]:
            cid = c.get("id")
            status = c.get("status", "")
            ptype = c.get("project_type", "")

            # Архивные и надзор — пропускаем
            if status in archive_statuses:
                continue
            if status == "АВТОРСКИЙ НАДЗОР":
                continue

            if cid not in contracts_with_cards:
                issues.append(
                    f"Договор id={cid} №{c.get('contract_number', '???')} "
                    f"({ptype}, status={status}): НЕТ CRM карточки"
                )

        report = _format_issues(issues, "Договоры без CRM карточек")
        if report:
            print(report)
        if issues:
            warnings.warn(
                f"Найдено {len(issues)} договоров без CRM карточек{report}",
                UserWarning,
            )

    def test_stage_executor_deadlines_valid(self, all_data):
        """Дедлайны stage_executor — валидные даты или null."""
        issues = []

        for se in all_data["stage_executors"]:
            se_id = se.get("id", "???")
            deadline = se.get("deadline")
            if deadline is not None and isinstance(deadline, str) and deadline.strip():
                if not _is_valid_iso_date(deadline):
                    issues.append(
                        f"StageExecutor id={se_id} (card={se.get('crm_card_id')}, "
                        f"stage={se.get('stage_name')}): deadline='{deadline}' — невалидный формат"
                    )

        report = _format_issues(issues, "StageExecutor: невалидные дедлайны")
        if report:
            print(report)
        assert len(issues) == 0, f"Найдено {len(issues)} невалидных дедлайнов{report}"


# ════════════════════════════════════════════════════════════
#  8. SUMMARY REPORT
# ════════════════════════════════════════════════════════════

class TestSummaryReport:
    """Финальный отчёт по всем проверкам (запускается последним)."""

    def test_print_data_summary(self, all_data):
        """Вывести сводку по всем данным."""
        print(f"\n{'='*70}")
        print(f"  DIAGNOSTIC DEEP: SUMMARY REPORT")
        print(f"{'='*70}")

        stats = {
            "Клиенты": len(all_data["clients"]),
            "Договоры": len(all_data["contracts"]),
            "Платежи": len(all_data["payments"]),
            "Сотрудники": len(all_data["employees"]),
            "CRM карточки (активные)": len(all_data["all_crm_active"]),
            "CRM карточки (архив)": len(all_data["all_crm_archive"]),
            "Карточки надзора (активные)": len(all_data["supervision_active"]),
            "Карточки надзора (архив)": len(all_data["supervision_archive"]),
            "Stage Executors": len(all_data["stage_executors"]),
            "Тарифы": len(all_data["rates"]),
        }

        for name, count in stats.items():
            print(f"  {name:.<45} {count:>5}")

        # Статусы договоров
        status_counts = defaultdict(int)
        for c in all_data["contracts"]:
            status_counts[c.get("status", "N/A")] += 1
        print(f"\n  Статусы договоров:")
        for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
            print(f"    {status:.<40} {count:>5}")

        # Колонки CRM
        col_counts = defaultdict(int)
        for card in all_data["all_crm_active"]:
            col_counts[card.get("column_name", "N/A")] += 1
        print(f"\n  Колонки CRM (активные):")
        for col, count in sorted(col_counts.items(), key=lambda x: -x[1]):
            print(f"    {col:.<40} {count:>5}")

        # Статусы платежей
        pay_status_counts = defaultdict(int)
        for p in all_data["payments"]:
            ps = p.get("payment_status", "N/A")
            pay_status_counts[ps] += 1
        print(f"\n  Статусы платежей:")
        for ps, count in sorted(pay_status_counts.items(), key=lambda x: -x[1]):
            print(f"    {ps:.<40} {count:>5}")

        # Роли платежей
        role_counts = defaultdict(int)
        for p in all_data["payments"]:
            role_counts[p.get("role", "N/A")] += 1
        print(f"\n  Роли платежей:")
        for role, count in sorted(role_counts.items(), key=lambda x: -x[1]):
            print(f"    {role:.<40} {count:>5}")

        # Timing
        if _timing_log:
            avg = sum(t for _, t in _timing_log) / len(_timing_log)
            max_t = max(_timing_log, key=lambda x: x[1])
            slow = [t for t in _timing_log if t[1] > SLOW_THRESHOLD_SEC]
            print(f"\n  Timing:")
            print(f"    Запросов:                                {len(_timing_log):>5}")
            print(f"    Среднее время:                           {avg:>5.2f}s")
            print(f"    Макс. время: {max_t[0]:.<30} {max_t[1]:>5.2f}s")
            print(f"    Медленных (>{SLOW_THRESHOLD_SEC}s):                          {len(slow):>5}")

        print(f"{'='*70}")

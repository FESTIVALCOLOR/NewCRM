# -*- coding: utf-8 -*-
"""
Data Consistency Tests: ПОЛНЫЙ АУДИТ бизнес-данных на реальном сервере.

Каждый тест скачивает реальные данные и ищет ВСЕ аномалии:
- Пересчёт каждого платежа по формуле (area × rate)
- Перекрёстные связи (сироты, мертвые ссылки)
- Противоречия в статусах
- Мусорные/тестовые данные в production
- Пробелы в покрытии тарифами
- Просроченные дедлайны

Запуск: pytest tests/smoke/test_data_consistency.py -v --timeout=120
"""

import pytest
import requests
import sys
import os
from collections import defaultdict
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import API_BASE_URL

TIMEOUT = 15

_session = requests.Session()
_session.verify = False


def _get(path, headers, params=None):
    return _session.get(f"{API_BASE_URL}{path}", headers=headers,
                        params=params, timeout=TIMEOUT)


def _post(path, headers, json=None, data=None):
    return _session.post(f"{API_BASE_URL}{path}", headers=headers,
                         json=json, data=data, timeout=TIMEOUT)


# ════════════════════════════════════════════════════════════
# Фикстуры — загрузка ВСЕХ данных один раз
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
    """Скачать ВСЕ данные с сервера для аудита."""
    def fetch(path, params=None):
        r = _get(path, admin_headers, params)
        if r.status_code != 200:
            return []
        data = r.json()
        return data if isinstance(data, list) else [data] if isinstance(data, dict) else []

    data = {
        "contracts": fetch("/api/contracts"),
        "clients": fetch("/api/clients"),
        "payments": fetch("/api/payments"),
        "employees": fetch("/api/employees"),
        "rates": fetch("/api/rates"),
        "crm_individual": fetch("/api/crm/cards", {"project_type": "Индивидуальный"}),
        "crm_template": fetch("/api/crm/cards", {"project_type": "Шаблонный"}),
        "supervision_active": fetch("/api/supervision/cards"),
        "supervision_archive": fetch("/api/supervision/cards", {"archived": "true"}),
        "agents": fetch("/api/v1/agents"),
        "cities": fetch("/api/v1/cities"),
    }

    # Индексы для быстрого поиска
    data["contracts_by_id"] = {c["id"]: c for c in data["contracts"]}
    data["clients_by_id"] = {c["id"]: c for c in data["clients"]}
    data["employees_by_id"] = {e["id"]: e for e in data["employees"]}
    data["all_crm_cards"] = data["crm_individual"] + data["crm_template"]
    data["crm_cards_by_id"] = {c["id"]: c for c in data["all_crm_cards"]}
    data["supervision_by_id"] = {c["id"]: c for c in data["supervision_active"]}

    # Индекс тарифов: (project_type, role, stage_name) → rate
    rates_index = {}
    for r in data["rates"]:
        key = (r.get("project_type"), r.get("role"), r.get("stage_name"))
        rates_index[key] = r
    data["rates_index"] = rates_index

    return data


# ════════════════════════════════════════════════════════════
# 1. ПЕРЕСЧЁТ КАЖДОГО ПЛАТЕЖА: stored vs expected
# ════════════════════════════════════════════════════════════

@pytest.mark.data_consistency
class TestPaymentRecalculation:
    """Пересчитать КАЖДЫЙ платёж по формуле и сравнить с хранимым значением."""

    def test_every_payment_amount_matches_formula(self, all_data):
        """Для каждого не-ручного платежа: stored amount == area × rate_per_m2."""
        payments = all_data["payments"]
        contracts = all_data["contracts_by_id"]
        rates_index = all_data["rates_index"]

        if not payments:
            pytest.skip("Нет платежей")

        bugs = []
        for pay in payments:
            # Пропускаем оклады и ручные корректировки
            if pay.get("role") == "Оклад":
                continue
            if pay.get("is_manual"):
                continue

            contract_id = pay.get("contract_id")
            if not contract_id:
                continue

            contract = contracts.get(contract_id)
            if not contract:
                continue  # Сиротский — поймаем в другом тесте

            area = float(contract.get("area") or 0)
            role = pay.get("role", "")
            stage = pay.get("stage_name")
            source = pay.get("source", "")
            stored = float(pay.get("final_amount") or 0)
            project_type = pay.get("project_type") or contract.get("project_type", "")

            # Определяем ожидаемую сумму по тарифу
            expected = None

            if source == "CRM Надзор" or pay.get("supervision_card_id"):
                # Надзор: area × rate_per_m2
                rate = rates_index.get(("Авторский надзор", role, stage))
                if not rate:
                    rate = rates_index.get(("Авторский надзор", role, None))
                if rate and rate.get("rate_per_m2"):
                    expected = area * float(rate["rate_per_m2"])

            elif project_type == "Индивидуальный":
                # Индивидуальный: area × rate_per_m2
                rate = rates_index.get(("Индивидуальный", role, stage))
                if not rate:
                    rate = rates_index.get(("Индивидуальный", role, None))
                if rate and rate.get("rate_per_m2"):
                    expected = area * float(rate["rate_per_m2"])

            elif project_type == "Шаблонный":
                # Шаблонный: fixed_price по диапазону площади
                for r in all_data["rates"]:
                    if (r.get("project_type") == "Шаблонный" and
                            r.get("role") == role and
                            r.get("area_from") is not None and
                            r.get("area_to") is not None):
                        if float(r["area_from"]) <= area <= float(r["area_to"]):
                            expected = float(r.get("fixed_price") or 0)
                            break

            if role == "Замерщик":
                # Замерщик: фиксированная цена по городу, но может быть
                # индивидуальная сумма — пропускаем проверку формулы
                continue

            # Сравниваем
            if expected is not None and abs(stored - expected) > 0.01:
                bugs.append(
                    f"Оплата id={pay['id']} договор={contract_id} "
                    f"роль='{role}' стадия='{stage}': "
                    f"хранится={stored:.2f}₽, ожидается={expected:.2f}₽ "
                    f"(area={area}, project={project_type}, source={source})"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(
                f"НАЙДЕНО {len(bugs)} платежей с неверной суммой:\n{report}"
            )

    def test_no_zero_payments_with_existing_rates(self, all_data):
        """Платежи = 0₽ при наличии тарифа и площади > 0 — это баг."""
        payments = all_data["payments"]
        contracts = all_data["contracts_by_id"]
        rates_index = all_data["rates_index"]

        bugs = []
        for pay in payments:
            if pay.get("role") == "Оклад" or pay.get("is_manual"):
                continue

            stored = float(pay.get("final_amount") or 0)
            if stored != 0:
                continue  # Только нулевые

            contract_id = pay.get("contract_id")
            contract = contracts.get(contract_id, {})
            area = float(contract.get("area") or 0)
            if area == 0:
                continue  # Ноль закономерен, поймаем в тесте area

            role = pay.get("role", "")
            stage = pay.get("stage_name")
            source = pay.get("source", "")

            # Ищем тариф
            rate_found = False
            if source == "CRM Надзор" or pay.get("supervision_card_id"):
                rate = rates_index.get(("Авторский надзор", role, stage))
                if not rate:
                    rate = rates_index.get(("Авторский надзор", role, None))
                rate_found = bool(rate and rate.get("rate_per_m2"))
            else:
                pt = pay.get("project_type", "")
                rate = rates_index.get((pt, role, stage))
                if not rate:
                    rate = rates_index.get((pt, role, None))
                rate_found = bool(rate and (rate.get("rate_per_m2") or rate.get("fixed_price")))

            if rate_found:
                bugs.append(
                    f"Оплата id={pay['id']} = 0₽ при area={area}м² "
                    f"роль='{role}' стадия='{stage}' source='{source}' "
                    f"договор={contract_id} ({contract.get('contract_number', '?')})"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(
                f"НАЙДЕНО {len(bugs)} нулевых платежей при наличии тарифа и площади:\n{report}"
            )


# ════════════════════════════════════════════════════════════
# 2. ПРОТИВОРЕЧИЯ В СТАТУСАХ
# ════════════════════════════════════════════════════════════

@pytest.mark.data_consistency
class TestStatusContradictions:
    """Статусы не должны противоречить друг другу."""

    def test_payment_status_vs_is_paid(self, all_data):
        """payment_status='paid' → is_paid=True (и наоборот)."""
        contracts = all_data["contracts_by_id"]
        bugs = []
        for pay in all_data["payments"]:
            status = pay.get("payment_status", "")
            is_paid = pay.get("is_paid", False)

            if status == "paid" and not is_paid:
                cid = pay.get("contract_id")
                contract = contracts.get(cid, {})
                bugs.append(
                    f"Оплата id={pay['id']}: {pay.get('employee_name')} "
                    f"({pay.get('role')}), {pay.get('final_amount')}₽, "
                    f"договор {contract.get('contract_number', '?')} "
                    f"({contract.get('address', '?')}): "
                    f"payment_status='paid' НО is_paid=False"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(
                f"НАЙДЕНО {len(bugs)} противоречий status vs is_paid:\n{report}"
            )

    def test_contract_status_vs_cards(self, all_data):
        """Договор 'АВТОРСКИЙ НАДЗОР' → должна быть карточка надзора.
           Договор в работе (не АВТОРСКИЙ НАДЗОР/СДАН/РАСТОРГНУТ) → CRM карточка."""
        contracts = all_data["contracts"]
        sup_contract_ids = {c["contract_id"] for c in all_data["supervision_active"]}
        # Договор с АВТОРСКИЙ НАДЗОР уходит из активных CRM в архив —
        # поэтому его НЕТ в активных CRM и это нормально.
        crm_contract_ids = {c["contract_id"] for c in all_data["all_crm_cards"]}

        bugs = []
        for c in contracts:
            cid = c["id"]
            status = c.get("status", "")

            # Статус АВТОРСКИЙ НАДЗОР → обязательно карточка надзора
            if status == "АВТОРСКИЙ НАДЗОР" and cid not in sup_contract_ids:
                bugs.append(
                    f"Договор {c.get('contract_number')} "
                    f"({c.get('address', '?')}): "
                    f"статус='АВТОРСКИЙ НАДЗОР' но карточки надзора НЕТ"
                )

            # Активный договор (не АВТОРСКИЙ НАДЗОР, не СДАН, не РАСТОРГНУТ) → CRM карточка
            if status not in ("АВТОРСКИЙ НАДЗОР", "РАСТОРГНУТ", "СДАН") and \
               cid not in crm_contract_ids:
                bugs.append(
                    f"Договор {c.get('contract_number')} "
                    f"({c.get('address', '?')}): "
                    f"статус='{status}' но CRM карточки НЕТ"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(
                f"НАЙДЕНО {len(bugs)} рассогласований договор↔карточка:\n{report}"
            )

    def test_supervision_archive_not_in_active_crm(self, all_data):
        """Договор с АВТОРСКИЙ НАДЗОР → CRM карточка должна быть в архиве, не в активных."""
        # Карточка надзора — это ОТДЕЛЬНАЯ сущность от CRM карточки.
        # Когда договор переходит в АВТОРСКИЙ НАДЗОР:
        # - CRM карточка → архив основного CRM
        # - Создаётся новая карточка надзора (активная)
        sup_contract_ids = {c["contract_id"] for c in all_data["supervision_active"]}
        active_crm_contract_ids = {c["contract_id"] for c in all_data["all_crm_cards"]}

        bugs = []
        for cid in sup_contract_ids:
            if cid in active_crm_contract_ids:
                contract = all_data["contracts_by_id"].get(cid, {})
                bugs.append(
                    f"Договор {contract.get('contract_number', '?')} "
                    f"({contract.get('address', '?')}): "
                    f"есть активная карточка надзора И активная CRM карточка одновременно. "
                    f"CRM карточка должна быть в архиве."
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(
                f"Карточки с АВТОРСКИЙ НАДЗОР ещё в активном CRM:\n{report}"
            )


# ════════════════════════════════════════════════════════════
# 3. СИРОТСКИЕ ЗАПИСИ (мёртвые ссылки)
# ════════════════════════════════════════════════════════════

@pytest.mark.data_consistency
class TestOrphanRecords:
    """Все ссылки между сущностями должны быть валидны."""

    def test_payments_reference_valid_contracts(self, all_data):
        """Каждый платёж ссылается на существующий договор."""
        contracts = all_data["contracts_by_id"]
        bugs = []
        for pay in all_data["payments"]:
            cid = pay.get("contract_id")
            if cid and cid not in contracts:
                bugs.append(
                    f"Оплата id={pay['id']} ({pay.get('role')}, "
                    f"{pay.get('final_amount')}₽): "
                    f"contract_id={cid} НЕ СУЩЕСТВУЕТ"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(f"Сиротские платежи:\n{report}")

    def test_payments_reference_valid_employees(self, all_data):
        """Каждый платёж ссылается на существующего сотрудника."""
        employees = all_data["employees_by_id"]
        bugs = []
        for pay in all_data["payments"]:
            eid = pay.get("employee_id")
            if eid and eid not in employees:
                bugs.append(
                    f"Оплата id={pay['id']} ({pay.get('role')}, "
                    f"{pay.get('employee_name')}): "
                    f"employee_id={eid} НЕ СУЩЕСТВУЕТ"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(f"Платежи с несуществующими сотрудниками:\n{report}")

    def test_contracts_reference_valid_clients(self, all_data):
        """Каждый договор ссылается на существующего клиента."""
        clients = all_data["clients_by_id"]
        bugs = []
        for c in all_data["contracts"]:
            client_id = c.get("client_id")
            if client_id and client_id not in clients:
                bugs.append(
                    f"Договор {c['id']} ({c.get('contract_number')}): "
                    f"client_id={client_id} НЕ СУЩЕСТВУЕТ"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(f"Договоры-сироты:\n{report}")

    def test_crm_cards_reference_valid_contracts(self, all_data):
        """Каждая CRM карточка привязана к существующему договору."""
        contracts = all_data["contracts_by_id"]
        bugs = []
        for card in all_data["all_crm_cards"]:
            cid = card.get("contract_id")
            if cid and cid not in contracts:
                bugs.append(
                    f"CRM карточка {card['id']}: contract_id={cid} НЕ СУЩЕСТВУЕТ"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(f"CRM карточки-сироты:\n{report}")

    def test_supervision_cards_reference_valid_contracts(self, all_data):
        """Каждая карточка надзора привязана к существующему договору."""
        contracts = all_data["contracts_by_id"]
        bugs = []
        for card in all_data["supervision_active"]:
            cid = card.get("contract_id")
            if cid and cid not in contracts:
                bugs.append(
                    f"Карточка надзора {card['id']}: contract_id={cid} НЕ СУЩЕСТВУЕТ"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(f"Карточки надзора-сироты:\n{report}")


# ════════════════════════════════════════════════════════════
# 4. МУСОР В PRODUCTION
# ════════════════════════════════════════════════════════════

@pytest.mark.data_consistency
class TestProductionDataCleanliness:
    """В production НЕ должно быть тестовых данных."""

    def test_no_test_rates(self, all_data):
        """Тарифы с __TEST__ или __SMOKE__ в stage_name — мусор от тестов."""
        bugs = []
        for r in all_data["rates"]:
            stage = r.get("stage_name") or ""
            role = r.get("role") or ""
            if "__TEST__" in stage or "__SMOKE__" in stage or \
               "__TEST__" in role or "__SMOKE__" in role:
                bugs.append(
                    f"Тариф id={r['id']}: project={r.get('project_type')}, "
                    f"role='{role}', stage='{stage}' — тестовый мусор!"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(
                f"НАЙДЕНО {len(bugs)} тестовых тарифов в production:\n{report}\n"
                f"Их нужно удалить — они могут влиять на расчёт!"
            )

    def test_no_test_contracts(self, all_data):
        """Договоры с __TEST__ или __SMOKE__ в номере — мусор от тестов."""
        bugs = []
        for c in all_data["contracts"]:
            num = c.get("contract_number") or ""
            if "__TEST__" in num or "__SMOKE__" in num:
                bugs.append(
                    f"Договор {c['id']}: номер='{num}' — тестовый мусор!"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(f"Тестовые договоры в production:\n{report}")

    def test_no_test_clients(self, all_data):
        """Клиенты с __TEST__ или __SMOKE__ в имени — мусор от тестов."""
        bugs = []
        for c in all_data["clients"]:
            name = c.get("full_name") or c.get("organization_name") or ""
            if "__TEST__" in name or "__SMOKE__" in name:
                bugs.append(
                    f"Клиент {c['id']}: имя='{name}' — тестовый мусор!"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(f"Тестовые клиенты в production:\n{report}")


# ════════════════════════════════════════════════════════════
# 5. ПОКРЫТИЕ ТАРИФАМИ
# ════════════════════════════════════════════════════════════

@pytest.mark.data_consistency
class TestRateCoverage:
    """Тарифы должны покрывать все используемые комбинации role × project_type."""

    def test_all_payment_roles_have_rates(self, all_data):
        """Каждая комбинация (project_type, role) из платежей — покрыта тарифом."""
        rates_index = all_data["rates_index"]
        rates = all_data["rates"]
        contracts = all_data["contracts_by_id"]

        # Собираем все комбинации из тарифов
        rate_combos = set()
        for r in rates:
            rate_combos.add((r.get("project_type"), r.get("role")))

        # Тарифы замерщика привязаны к городу, а не к project_type
        surveyor_cities = set()
        for r in rates:
            if r.get("role") == "Замерщик" and r.get("city"):
                surveyor_cities.add(r["city"])

        # Проверяем каждый платёж
        missing = defaultdict(list)
        for pay in all_data["payments"]:
            if pay.get("role") == "Оклад":
                continue

            pt = pay.get("project_type", "")
            role = pay.get("role", "")
            stage = pay.get("stage_name")

            if not pt or not role:
                continue

            # Замерщик — тариф по городу, не по project_type
            if role == "Замерщик":
                contract = contracts.get(pay.get("contract_id"), {})
                city = contract.get("city") or pay.get("city", "")
                if city and city not in surveyor_cities:
                    missing[("Замерщик", city)].append(pay["id"])
                continue

            # Ищем точный тариф (с stage) или общий (без stage)
            has_rate = (
                (pt, role, stage) in rates_index or
                (pt, role, None) in rates_index or
                (pt, role) in rate_combos
            )

            if not has_rate:
                missing[(pt, role)].append(pay["id"])

        if missing:
            bugs = []
            for key, pay_ids in missing.items():
                bugs.append(
                    f"НЕТ тарифа: {key} "
                    f"— затронуто {len(pay_ids)} платежей (id: {pay_ids[:5]})"
                )
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(
                f"НАЙДЕНО {len(missing)} комбинаций без тарифа:\n{report}"
            )

    def test_supervision_stages_have_rates(self, all_data):
        """Все стадии надзора, используемые в платежах, покрыты тарифами."""
        rates_index = all_data["rates_index"]

        missing = defaultdict(list)
        for pay in all_data["payments"]:
            if pay.get("source") != "CRM Надзор":
                continue

            role = pay.get("role", "")
            stage = pay.get("stage_name")
            if not stage:
                continue

            # Ищем тариф для конкретной стадии
            has_stage_rate = ("Авторский надзор", role, stage) in rates_index
            has_general_rate = ("Авторский надзор", role, None) in rates_index

            if not has_stage_rate and not has_general_rate:
                missing[(role, stage)].append(pay["id"])

        if missing:
            bugs = []
            for (role, stage), pay_ids in missing.items():
                bugs.append(
                    f"НЕТ тарифа надзора: role='{role}', stage='{stage}' "
                    f"— затронуто {len(pay_ids)} платежей"
                )
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(
                f"Стадии надзора без тарифов:\n{report}"
            )


# ════════════════════════════════════════════════════════════
# 6. ДЕДЛАЙНЫ И СРОКИ
# ════════════════════════════════════════════════════════════

@pytest.mark.data_consistency
class TestDeadlines:
    """Дедлайны должны быть адекватными."""

    def test_overdue_crm_cards(self, all_data):
        """Обнаружение CRM карточек с просроченным дедлайном (warning, не fail)."""
        today = date.today()
        overdue = []

        for card in all_data["all_crm_cards"]:
            deadline_str = card.get("deadline")
            if not deadline_str:
                continue
            try:
                dl = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

            col = card.get("column_name", "")
            # Пропускаем завершённые
            if col in ("Выполненный проект", "СДАН"):
                continue

            if dl < today:
                days = (today - dl).days
                overdue.append(
                    f"CRM #{card['id']} ({card.get('contract_number', '?')}) "
                    f"колонка='{col}': дедлайн {deadline_str} "
                    f"просрочен на {days} дн."
                )

        # Это warning, не fail — просроченные карточки не всегда баг
        if overdue:
            report = "\n".join(f"  - {o}" for o in overdue)
            print(f"\n⚠ ПРОСРОЧЕННЫЕ CRM карточки ({len(overdue)}):\n{report}")

    def test_overdue_supervision_cards(self, all_data):
        """Карточки надзора с просроченным дедлайном."""
        today = date.today()
        overdue = []

        for card in all_data["supervision_active"]:
            deadline_str = card.get("deadline")
            if not deadline_str:
                continue
            try:
                dl = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

            col = card.get("column_name", "")
            if col == "СДАН":
                continue

            if dl < today:
                days = (today - dl).days
                overdue.append(
                    f"Надзор #{card['id']} ({card.get('contract_number', '?')}) "
                    f"колонка='{col}': дедлайн {deadline_str} "
                    f"просрочен на {days} дн."
                )

        if overdue:
            report = "\n".join(f"  - {o}" for o in overdue)
            print(f"\n⚠ ПРОСРОЧЕННЫЕ карточки надзора ({len(overdue)}):\n{report}")


# ════════════════════════════════════════════════════════════
# 7. CRM КАРТОЧКИ: полнота данных
# ════════════════════════════════════════════════════════════

@pytest.mark.data_consistency
class TestCrmCardCompleteness:
    """CRM карточки должны иметь назначенных ответственных."""

    def test_cards_in_work_have_managers(self, all_data):
        """Карточки за пределами 'Новый заказ' должны иметь менеджеров."""
        bugs = []
        no_manager_columns = {"Новый заказ"}

        for card in all_data["all_crm_cards"]:
            col = card.get("column_name", "")
            if col in no_manager_columns:
                continue  # Для новых — допустимо без менеджера

            missing = []
            if not card.get("senior_manager_id"):
                missing.append("senior_manager")
            if not card.get("sdp_id"):
                missing.append("sdp")
            if not card.get("gap_id"):
                missing.append("gap")

            if len(missing) == 3:  # Вообще никого нет
                bugs.append(
                    f"CRM #{card['id']} ({card.get('contract_number', '?')}) "
                    f"колонка='{col}': нет ни одного ответственного! "
                    f"Отсутствуют: {', '.join(missing)}"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(
                f"НАЙДЕНО {len(bugs)} карточек в работе без ответственных:\n{report}"
            )

    def test_cards_have_valid_columns(self, all_data):
        """Все CRM карточки находятся в допустимых колонках."""
        VALID = {
            'Новый заказ', 'В ожидании', 'Готово к выезду',
            'Стадия 1: планировочные решения',
            'Стадия 2: концепция дизайна',
            'Стадия 2: рабочие чертежи',
            'Стадия 3: рабочие чертежи',
            'Стадия 3: 3д визуализация (Дополнительная)',
            'Выполненный проект', 'СДАН',
        }
        bugs = []
        for card in all_data["all_crm_cards"]:
            col = card.get("column_name", "")
            if col and col not in VALID:
                bugs.append(
                    f"CRM #{card['id']}: колонка '{col}' — неизвестна!"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(
                f"НАЙДЕНО {len(bugs)} карточек в неизвестных колонках:\n{report}"
            )


# ════════════════════════════════════════════════════════════
# 8. ДОГОВОРЫ: финансовая валидность
# ════════════════════════════════════════════════════════════

@pytest.mark.data_consistency
class TestContractFinancials:
    """Финансовые данные договоров должны быть валидны."""

    def test_contracts_have_area_and_amount(self, all_data):
        """Все договоры (кроме тестовых) должны иметь area > 0 и total > 0."""
        bugs = []
        for c in all_data["contracts"]:
            num = c.get("contract_number") or ""
            if "__TEST__" in num or "__SMOKE__" in num:
                continue

            issues = []
            area = float(c.get("area") or 0)
            total = float(c.get("total_amount") or 0)

            if area == 0:
                issues.append(f"area=0")
            if total == 0:
                issues.append(f"total_amount=0")

            if issues:
                bugs.append(
                    f"Договор {c['id']} ({num}): {', '.join(issues)} "
                    f"тип='{c.get('project_type')}'"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(
                f"НАЙДЕНО {len(bugs)} договоров с нулевыми данными:\n{report}"
            )

    def test_advance_not_exceeds_total(self, all_data):
        """Аванс не должен превышать общую сумму договора."""
        bugs = []
        for c in all_data["contracts"]:
            total = float(c.get("total_amount") or 0)
            advance = float(c.get("advance_payment") or 0)
            additional = float(c.get("additional_payment") or 0)
            third = float(c.get("third_payment") or 0)

            if total == 0:
                continue

            payments_sum = advance + additional + third
            if payments_sum > total * 1.01:  # 1% допуск на округление
                bugs.append(
                    f"Договор {c['id']} ({c.get('contract_number')}): "
                    f"аванс+доплаты={payments_sum:.2f}₽ > "
                    f"total_amount={total:.2f}₽"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(
                f"Договоры где оплаты > суммы:\n{report}"
            )


# ════════════════════════════════════════════════════════════
# 9. СОТРУДНИКИ: полнота данных
# ════════════════════════════════════════════════════════════

@pytest.mark.data_consistency
class TestEmployeeData:
    """Сотрудники должны иметь полные и корректные данные."""

    def test_active_employees_have_required_fields(self, all_data):
        """Активные сотрудники: ФИО, должность, логин."""
        bugs = []
        for emp in all_data["employees"]:
            if emp.get("status") != "активный":
                continue

            missing = []
            if not emp.get("full_name"):
                missing.append("full_name")
            if not emp.get("position"):
                missing.append("position")
            if not emp.get("login"):
                missing.append("login")

            if missing:
                bugs.append(
                    f"Сотрудник {emp['id']} "
                    f"'{emp.get('full_name', '???')}': "
                    f"нет {', '.join(missing)}"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(
                f"Сотрудники с неполными данными:\n{report}"
            )

    def test_payment_employees_are_active(self, all_data):
        """Сотрудники в непогашенных платежах должны быть активными."""
        employees = all_data["employees_by_id"]
        bugs = []
        for pay in all_data["payments"]:
            if pay.get("is_paid"):
                continue  # Уже оплаченные — не критично

            eid = pay.get("employee_id")
            emp = employees.get(eid)
            if emp and emp.get("status") != "активный":
                bugs.append(
                    f"Оплата id={pay['id']} ({pay.get('role')}, "
                    f"{pay.get('final_amount')}₽): "
                    f"сотрудник '{emp.get('full_name')}' — "
                    f"статус '{emp.get('status')}' (не активный!)"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(
                f"Неоплаченные платежи с неактивными сотрудниками:\n{report}"
            )


# ════════════════════════════════════════════════════════════
# 10. СПРАВОЧНИКИ
# ════════════════════════════════════════════════════════════

@pytest.mark.data_consistency
class TestReferenceData:
    """Справочники (агенты, города) должны быть заполнены."""

    def test_agents_not_empty(self, all_data):
        """Агенты существуют и имеют имена."""
        agents = all_data["agents"]
        assert len(agents) > 0, "Список агентов ПУСТ!"
        for a in agents:
            assert a.get("name"), f"Агент id={a.get('id')} без имени!"

    def test_cities_not_empty(self, all_data):
        """Города существуют и имеют имена."""
        cities = all_data["cities"]
        assert len(cities) > 0, "Список городов ПУСТ!"
        for c in cities:
            name = c.get("name") if isinstance(c, dict) else c
            assert name, f"Город без имени: {c}"

    def test_contract_agents_exist_in_reference(self, all_data):
        """agent_type в договорах совпадает с реальными агентами."""
        agent_names = {a.get("name") for a in all_data["agents"]}
        bugs = []
        for c in all_data["contracts"]:
            at = c.get("agent_type")
            if at and at not in agent_names:
                bugs.append(
                    f"Договор {c['id']} ({c.get('contract_number')}): "
                    f"agent_type='{at}' НЕТ в справочнике {agent_names}"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(f"Договоры с несуществующим агентом:\n{report}")

    def test_contract_cities_exist_in_reference(self, all_data):
        """city в договорах совпадает с реальными городами."""
        city_names = set()
        for c in all_data["cities"]:
            city_names.add(c.get("name") if isinstance(c, dict) else c)

        bugs = []
        for c in all_data["contracts"]:
            city = c.get("city")
            if city and city not in city_names:
                bugs.append(
                    f"Договор {c['id']} ({c.get('contract_number')}): "
                    f"city='{city}' НЕТ в справочнике {city_names}"
                )

        if bugs:
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(f"Договоры с несуществующим городом:\n{report}")


# ════════════════════════════════════════════════════════════
# 11. ДУБЛИКАТЫ
# ════════════════════════════════════════════════════════════

@pytest.mark.data_consistency
class TestDuplicates:
    """В данных не должно быть дубликатов."""

    def test_no_duplicate_contract_numbers(self, all_data):
        """Номера договоров уникальны."""
        nums = defaultdict(list)
        for c in all_data["contracts"]:
            num = c.get("contract_number", "")
            if num:
                nums[num].append(c["id"])

        dupes = {n: ids for n, ids in nums.items() if len(ids) > 1}
        if dupes:
            bugs = [f"Номер '{n}': договоры {ids}" for n, ids in dupes.items()]
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(f"Дубликаты номеров договоров:\n{report}")

    def test_no_duplicate_employee_logins(self, all_data):
        """Логины сотрудников уникальны."""
        logins = defaultdict(list)
        for e in all_data["employees"]:
            login = e.get("login", "")
            if login:
                logins[login].append(e["id"])

        dupes = {l: ids for l, ids in logins.items() if len(ids) > 1}
        if dupes:
            bugs = [f"Логин '{l}': сотрудники {ids}" for l, ids in dupes.items()]
            report = "\n".join(f"  - {b}" for b in bugs)
            pytest.fail(f"Дубликаты логинов:\n{report}")

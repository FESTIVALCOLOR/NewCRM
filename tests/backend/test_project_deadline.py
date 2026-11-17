"""
Backend Tests — единые правила сроков проекта (server/services/project_deadline.py):
вне объёма и ожидание после START не считаются просрочкой и сдвигают дедлайн.
Даты подобраны без праздников: 07.09.2026 — понедельник.
"""

from datetime import date
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "server"))

from services.project_deadline import compute_project_metrics  # noqa: E402

START = "2026-09-07"


def entry(order, code, date_str="", days=0, in_scope=True, role="Чертёжник", status=""):
    return SimpleNamespace(
        sort_order=order,
        stage_code=code,
        actual_date=date_str,
        actual_days=days,
        is_in_contract_scope=in_scope,
        executor_role=role,
        status=status,
    )


def card(column="Выполненный проект", deadline="2026-09-14", total_pause=0, post_wait=0, paused_at=None):
    return SimpleNamespace(column_name=column, deadline=deadline, paused_at=paused_at, total_pause_days=total_pause, post_start_wait_days=post_wait)


CONTRACT = SimpleNamespace(contract_period=5, status="СДАН")


def closed_entries():
    return [
        entry(1, "START", START, role="Менеджер"),
        entry(2, "S1", "2026-09-14", 5),
        entry(3, "CLIENT", "2026-09-17", 3, in_scope=False, role="Клиент"),
        entry(4, "S2", "2026-09-18", 1),
    ]


def test_out_of_scope_not_counted_as_overdue():
    m = compute_project_metrics(card(), CONTRACT, closed_entries())
    assert m["fact_days_all"] == 9
    assert m["out_of_scope_days"] == 3
    assert m["fact_days"] == 6
    assert m["deadline"] == "2026-09-17"
    assert m["closure_date"] == "2026-09-18"
    assert m["overdue_days"] == 1  # факт по договору 6 − норма 5


def test_post_start_wait_shifts_deadline():
    m = compute_project_metrics(card(total_pause=1, post_wait=1), CONTRACT, closed_entries())
    assert m["deadline"] == "2026-09-18"
    assert m["overdue_days"] == 0
    assert m["fact_days_all"] == 8
    assert m["fact_days"] == 5
    assert m["wait_days_pre_start"] == 0


def test_pre_start_wait_does_not_shift_deadline():
    m = compute_project_metrics(card(total_pause=2, post_wait=0), CONTRACT, closed_entries())
    assert m["deadline"] == "2026-09-17"
    assert m["wait_days_total"] == 2
    assert m["wait_days_pre_start"] == 2
    assert m["overdue_days"] == 1


def test_running_out_of_scope_stage_shifts_deadline_for_open_project():
    entries = [
        entry(1, "START", START, role="Менеджер"),
        entry(2, "S1", "2026-09-14", 5),
        entry(3, "CLIENT", in_scope=False, role="Клиент"),
        entry(4, "S2"),
    ]
    open_contract = SimpleNamespace(contract_period=5, status="Новый заказ")
    m = compute_project_metrics(card(column="Стадия 1: планировочные решения"), open_contract, entries, today=date(2026, 9, 18))
    assert m["is_closed"] is False
    assert m["out_of_scope_days"] == 4  # ждём клиента с 14.09
    assert m["deadline"] == "2026-09-18"
    assert m["overdue_days"] == 0
    assert m["fact_days"] == 5


def test_skipped_and_header_entries_ignored():
    entries = closed_entries() + [
        entry(5, "S1_HDR", "2026-09-18", 7, role="header"),
        entry(6, "SKIP", "2026-09-18", 9, in_scope=False, status="skipped"),
    ]
    m = compute_project_metrics(card(), CONTRACT, entries)
    assert m["out_of_scope_days"] == 3
    assert m["overdue_days"] == 1


def test_manual_base_deadline_respected():
    m = compute_project_metrics(card(deadline="2026-09-16"), CONTRACT, closed_entries())
    assert m["deadline"] == "2026-09-21"  # 16.09 + 3 р.д. вне объёма
    assert m["overdue_days"] == 0


def test_no_start_date_gives_empty_metrics():
    m = compute_project_metrics(card(deadline=None), CONTRACT, [entry(1, "START", role="Менеджер")])
    assert m["deadline"] is None
    assert m["fact_days"] == 0
    assert m["overdue_days"] == 0

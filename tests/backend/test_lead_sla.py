"""
Backend Tests — таймер на принятие заявки с сайта (server/services/lead_sla.py).
Отсчёт только в рабочее время (будни 10:00–19:00 МСК); точки: 12 ч, +3 ч ×3, +1 ч ×6 → просрочка на 27-м часу.
Даты без праздников: 07.09.2026 — понедельник. В БД время в UTC (МСК − 3 ч).
"""

from datetime import datetime, timedelta
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "server"))

lead_sla_module = pytest.importorskip("services.lead_sla")
lead_sla = lead_sla_module.lead_sla


def msk(day, hour, minute=0):
    """Московское время → наивное UTC, как хранится в БД."""
    return datetime(2026, 9, day, hour, minute) - timedelta(hours=3)


def lead(created, status="new", sla_start=None):
    return SimpleNamespace(status=status, created_at=created, sla_start=sla_start)


def test_processed_lead_has_no_timer():
    assert lead_sla(lead(msk(7, 10), status="done"), now=msk(7, 12)) is None


def test_counts_only_working_hours_and_next_at():
    state = lead_sla(lead(msk(7, 10)), now=msk(7, 19))
    assert state["elapsed_seconds"] == 9 * 3600
    assert state["passed"] == 0 and state["phase"] == "first"
    assert state["remaining_seconds"] == 3 * 3600
    assert state["working_now"] is False
    # 12 рабочих часов от пн 10:00 — вторник 13:00 МСК
    assert state["next_at"] == "2026-09-08T10:00:00Z"


def test_night_and_weekend_lead_starts_at_next_working_morning():
    state = lead_sla(lead(msk(12, 15)), now=msk(13, 12))  # пришла в субботу, сейчас воскресенье
    assert state["started"] is False
    assert state["starts_at"] == "2026-09-14T07:00:00Z"  # пн 10:00 МСК
    assert state["elapsed_seconds"] == 0 and state["remaining_seconds"] == 12 * 3600

    evening = lead_sla(lead(msk(7, 18)), now=msk(8, 11))  # 1 ч в пн + 1 ч во вт
    assert evening["elapsed_seconds"] == 2 * 3600


@pytest.mark.parametrize(
    "now, passed, phase, remaining",
    [
        (msk(8, 13), 1, "three", 3 * 3600),  # 12 ч — первое напоминание, дальше интервал 3 ч
        (msk(8, 19), 3, "three", 3 * 3600),  # 18 ч
        (msk(9, 13), 4, "hour", 3600),  # 21 ч — дальше по часу
        (msk(9, 18, 59), 9, "hour", 60),
    ],
)
def test_checkpoint_phases(now, passed, phase, remaining):
    state = lead_sla(lead(msk(7, 10)), now=now)
    assert (state["passed"], state["phase"], state["remaining_seconds"]) == (passed, phase, remaining)
    assert state["overdue"] is False


def test_overdue_after_27_working_hours():
    state = lead_sla(lead(msk(7, 10)), now=msk(10, 10))
    assert state["overdue"] is True and state["passed"] == 10 and state["remaining_seconds"] == 0


def test_reopened_lead_counts_from_sla_start():
    state = lead_sla(lead(msk(1, 10), sla_start=msk(7, 10)), now=msk(7, 11))
    assert state["elapsed_seconds"] == 3600

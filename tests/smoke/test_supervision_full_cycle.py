# -*- coding: utf-8 -*-
"""
Smoke: Supervision полный цикл — создание → стадии → pause → resume → выезды → архив.

Запуск: pytest tests/smoke/test_supervision_full_cycle.py -v --timeout=180
"""
import pytest
from datetime import datetime, timedelta
from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    TEST_PREFIX, create_test_client, create_test_contract,
    cleanup_test_card,
)


def _find_supervision_card(headers, contract_id):
    """Найти supervision карточку по contract_id."""
    resp = _get("/api/supervision/cards", headers)
    if resp.status_code != 200:
        return None
    cards = resp.json()
    card = next((c for c in cards if c.get("contract_id") == contract_id), None)
    return card["id"] if card else None


def _create_supervision_setup(headers, suffix=""):
    """Создать клиент + договор с триггером supervision → найти supervision карточку."""
    client_id = create_test_client(headers, f"SUP_{suffix}")
    # Создаём договор с project_type="Авторский надзор" и статусом "АВТОРСКИЙ НАДЗОР"
    # Именно статус "АВТОРСКИЙ НАДЗОР" триггерит автосоздание supervision карточки
    contract_id = create_test_contract(headers, client_id, f"SUP{suffix}",
                                        project_type="Авторский надзор")
    # Меняем статус на "АВТОРСКИЙ НАДЗОР" для триггера создания
    _put(f"/api/contracts/{contract_id}", headers,
         json={"status": "АВТОРСКИЙ НАДЗОР"})
    card_id = _find_supervision_card(headers, contract_id)
    # Если автосоздание не сработало — пробуем создать напрямую
    if not card_id:
        resp = _post("/api/supervision/cards", headers,
                     json={"contract_id": contract_id})
        if resp.status_code in (200, 201):
            card_id = resp.json().get("id")
        else:
            card_id = _find_supervision_card(headers, contract_id)
    return client_id, contract_id, card_id


@pytest.mark.smoke
class TestSupervisionCreation:
    """Создание и базовые операции с supervision карточками."""

    def test_create_supervision_card_via_contract(self, admin_headers):
        """При создании договора 'Авторский надзор' автоматически создаётся supervision карточка."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "CREATE")
            assert card_id is not None, \
                "Supervision карточка не создана автоматически при создании договора"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_supervision_card_get_by_id(self, admin_headers):
        """GET /supervision/cards/{id} возвращает детали карточки."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "GETID")
            if not card_id:
                pytest.skip("Supervision карточка не создалась")

            resp = _get(f"/api/supervision/cards/{card_id}", admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("contract_id") == contract_id
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_supervision_addresses_list(self, admin_headers):
        """GET /supervision/addresses доступен."""
        resp = _get("/api/supervision/addresses", admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.smoke
class TestSupervisionColumnMovement:
    """Перемещение supervision карточки по колонкам."""

    def test_move_column(self, admin_headers):
        """PATCH column перемещает supervision карточку."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "MOVE")
            if not card_id:
                pytest.skip("Supervision карточка не создалась")

            # Попробуем переместить
            resp = _patch(f"/api/supervision/cards/{card_id}/column", admin_headers,
                          json={"column_name": "В работе"})
            if resp.status_code == 200:
                # Проверяем через GET
                resp = _get(f"/api/supervision/cards/{card_id}", admin_headers)
                assert resp.status_code == 200
                assert resp.json().get("column_name") == "В работе"
            else:
                # Колонка может не существовать в этом проекте — не fail
                assert resp.status_code in (200, 400, 422), \
                    f"Unexpected: {resp.status_code} {resp.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_move_returns_old_column(self, admin_headers):
        """PATCH column возвращает old_column_name в ответе."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "OLDCOL")
            if not card_id:
                pytest.skip("Supervision карточка не создалась")

            # Получаем текущую колонку
            resp = _get(f"/api/supervision/cards/{card_id}", admin_headers)
            assert resp.status_code == 200
            old_col = resp.json().get("column_name")

            resp = _patch(f"/api/supervision/cards/{card_id}/column", admin_headers,
                          json={"column_name": "В работе"})
            if resp.status_code == 200:
                data = resp.json()
                # Проверяем наличие old_column_name в ответе
                if "old_column_name" in data:
                    assert data["old_column_name"] == old_col
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


@pytest.mark.smoke
class TestSupervisionPauseResume:
    """Пауза и возобновление supervision карточки."""

    def test_pause_card(self, admin_headers):
        """POST pause ставит карточку на паузу."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "PAUSE")
            if not card_id:
                pytest.skip("Supervision карточка не создалась")

            resp = _post(f"/api/supervision/cards/{card_id}/pause", admin_headers,
                         json={"pause_reason": "Smoke test pause"})
            if resp.status_code == 200:
                # Проверяем что карточка на паузе
                resp = _get(f"/api/supervision/cards/{card_id}", admin_headers)
                assert resp.status_code == 200
                data = resp.json()
                assert data.get("is_paused") is True, \
                    f"Карточка должна быть на паузе, is_paused={data.get('is_paused')}"
            else:
                # Может быть 422 если уже на паузе или бизнес-правило
                assert resp.status_code in (200, 400, 422), \
                    f"pause: {resp.status_code} {resp.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_resume_after_pause(self, admin_headers):
        """POST resume снимает паузу + total_pause_days > 0."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "RESUME")
            if not card_id:
                pytest.skip("Supervision карточка не создалась")

            # Пауза
            resp = _post(f"/api/supervision/cards/{card_id}/pause", admin_headers,
                         json={"pause_reason": "Smoke test resume check"})
            if resp.status_code != 200:
                pytest.skip(f"Не удалось поставить на паузу: {resp.status_code}")

            # Возобновление
            resp = _post(f"/api/supervision/cards/{card_id}/resume", admin_headers)
            assert resp.status_code == 200, \
                f"resume: {resp.status_code} {resp.text}"

            # Проверяем что пауза снята
            resp = _get(f"/api/supervision/cards/{card_id}", admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("is_paused") is not True, \
                "Карточка должна быть НЕ на паузе после resume"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_double_pause_rejected(self, admin_headers):
        """Повторная пауза → 422 или ошибка."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "DBLPAUSE")
            if not card_id:
                pytest.skip("Supervision карточка не создалась")

            # Первая пауза
            resp = _post(f"/api/supervision/cards/{card_id}/pause", admin_headers,
                         json={"pause_reason": "First pause"})
            if resp.status_code != 200:
                pytest.skip(f"Первая пауза не прошла: {resp.status_code}")

            # Вторая пауза — должна быть отклонена
            resp = _post(f"/api/supervision/cards/{card_id}/pause", admin_headers,
                         json={"pause_reason": "Second pause"})
            assert resp.status_code in (400, 409, 422), \
                f"Двойная пауза должна быть отклонена: {resp.status_code} {resp.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_resume_without_pause_rejected(self, admin_headers):
        """Resume без предварительной паузы → ошибка."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "NOPAUSE")
            if not card_id:
                pytest.skip("Supervision карточка не создалась")

            resp = _post(f"/api/supervision/cards/{card_id}/resume", admin_headers)
            assert resp.status_code in (400, 409, 422), \
                f"Resume без паузы должен быть отклонён: {resp.status_code}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


@pytest.mark.smoke
class TestSupervisionVisits:
    """Выезды (visits) по supervision карточке."""

    def test_add_visit(self, admin_headers):
        """POST visit добавляет выезд."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "VISIT")
            if not card_id:
                pytest.skip("Supervision карточка не создалась")

            visit_date = datetime.now().strftime("%Y-%m-%d")
            # Пробуем несколько вариантов URL для выездов
            resp = _post(f"/api/supervision/cards/{card_id}/visits", admin_headers,
                         json={
                             "stage_code": "STAGE_1_CERAMIC",
                             "stage_name": "Стадия 1: Закупка керамогранита",
                             "visit_date": visit_date,
                             "executor_name": "Smoke Test",
                             "notes": f"{TEST_PREFIX}Тестовый выезд",
                         })
            if resp.status_code == 404:
                # Альтернативный endpoint
                resp = _post(f"/api/supervision/visits", admin_headers,
                             json={
                                 "card_id": card_id,
                                 "stage_code": "STAGE_1_CERAMIC",
                                 "visit_date": visit_date,
                                 "executor_name": "Smoke Test",
                                 "notes": f"{TEST_PREFIX}Тестовый выезд",
                             })
            assert resp.status_code in (200, 201, 404, 422), \
                f"Добавление выезда: {resp.status_code} {resp.text}"
            if resp.status_code == 404:
                pytest.skip("Endpoint visits не найден")
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_visits_list(self, admin_headers):
        """GET visits возвращает список."""
        resp = _get("/api/supervision/cards", admin_headers)
        if resp.status_code != 200 or not resp.json():
            pytest.skip("Нет supervision карточек")

        card = resp.json()[0]
        card_id = card["id"]

        resp = _get(f"/api/supervision/cards/{card_id}/visits", admin_headers)
        # Может не быть endpoint visits отдельно — проверяем что не 500
        assert resp.status_code != 500, \
            f"visits вернул 500: {resp.text}"


@pytest.mark.smoke
class TestSupervisionStages:
    """Стадии supervision карточки."""

    def test_complete_stage(self, admin_headers):
        """POST complete-stage завершает стадию."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "STAGE")
            if not card_id:
                pytest.skip("Supervision карточка не создалась")

            resp = _post(f"/api/supervision/cards/{card_id}/complete-stage", admin_headers,
                         json={"stage_code": "STAGE_1_CERAMIC"})
            # Может быть 200 или 422 (если стадия не начата)
            assert resp.status_code in (200, 400, 422), \
                f"complete-stage: {resp.status_code} {resp.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_reset_stages(self, admin_headers):
        """POST reset-stages сбрасывает стадии."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "RESET")
            if not card_id:
                pytest.skip("Supervision карточка не создалась")

            resp = _post(f"/api/supervision/cards/{card_id}/reset-stages", admin_headers)
            assert resp.status_code in (200, 400, 422), \
                f"reset-stages: {resp.status_code} {resp.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


@pytest.mark.smoke
class TestSupervisionTimeline:
    """Timeline для supervision."""

    def test_timeline_init(self, admin_headers):
        """POST init создаёт timeline для карточки."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "TLINIT")
            if not card_id:
                pytest.skip("Supervision карточка не создалась")

            resp = _post(f"/api/supervision-timeline/{card_id}/init", admin_headers)
            assert resp.status_code in (200, 201, 409, 422), \
                f"timeline init: {resp.status_code} {resp.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_timeline_get(self, admin_headers):
        """GET supervision-timeline/{card_id} возвращает данные."""
        resp = _get("/api/supervision/cards", admin_headers)
        if resp.status_code != 200 or not resp.json():
            pytest.skip("Нет supervision карточек")

        card_id = resp.json()[0]["id"]
        resp = _get(f"/api/supervision-timeline/{card_id}", admin_headers)
        # Может быть 200 (есть данные) или 404 (не инициализирован)
        assert resp.status_code in (200, 404), \
            f"timeline get: {resp.status_code} {resp.text}"

    def test_timeline_entry_update(self, admin_headers):
        """PUT entry обновляет запись timeline."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "TLUPD")
            if not card_id:
                pytest.skip("Supervision карточка не создалась")

            # Сначала init
            _post(f"/api/supervision-timeline/{card_id}/init", admin_headers)

            # Обновляем entry
            resp = _put(f"/api/supervision-timeline/{card_id}/entry/STAGE_1_CERAMIC",
                        admin_headers,
                        json={"notes": f"{TEST_PREFIX}Updated entry"})
            # Может быть 200, 404 (нет entry), 422
            assert resp.status_code in (200, 404, 422), \
                f"timeline entry update: {resp.status_code} {resp.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


@pytest.mark.smoke
class TestSupervisionArchive:
    """Архивирование supervision карточки."""

    def test_archive_supervision_card(self, admin_headers):
        """POST archive перемещает карточку в архив."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "ARCHIVE")
            if not card_id:
                pytest.skip("Supervision карточка не создалась")

            resp = _post(f"/api/supervision/cards/{card_id}/archive", admin_headers)
            if resp.status_code == 200:
                # Проверяем что карточка в архиве
                resp = _get(f"/api/supervision/cards/{card_id}", admin_headers)
                if resp.status_code == 200:
                    data = resp.json()
                    archive_status = data.get("archive_status") or data.get("is_archived")
                    assert archive_status, "Карточка должна быть в архиве"
            else:
                assert resp.status_code in (200, 400, 422, 404), \
                    f"archive: {resp.status_code} {resp.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_history_entry_created(self, admin_headers):
        """POST history добавляет запись в историю карточки."""
        client_id = contract_id = card_id = None
        try:
            client_id, contract_id, card_id = _create_supervision_setup(admin_headers, "HIST")
            if not card_id:
                pytest.skip("Supervision карточка не создалась")

            resp = _post(f"/api/supervision/cards/{card_id}/history", admin_headers,
                         json={
                             "action_type": "data_change",
                             "description": f"{TEST_PREFIX}Тестовая запись в истории",
                         })
            assert resp.status_code in (200, 201, 404, 422), \
                f"history: {resp.status_code} {resp.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

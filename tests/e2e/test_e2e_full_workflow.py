# -*- coding: utf-8 -*-
"""
E2E Tests: Полный бизнес-цикл — 16 шагов
Сквозной тест: весь жизненный цикл проекта от клиента до надзора.

ВАЖНО: тесты выполняются в строгом порядке, используется class-level state.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from urllib.parse import quote

from tests.e2e.conftest import (
    TEST_PREFIX, api_get, api_post, api_put, api_patch, api_delete
)


@pytest.mark.critical
class TestFullBusinessWorkflow:
    """
    Сквозной тест: весь жизненный цикл проекта.

    1. Создание клиента
    2. Создание индивидуального договора
    3. Создание CRM карточки
    4. Установка дедлайна
    5. Назначение замерщика + дата замера
    6. Перемещение в стадию 1, назначение дизайнера
    7. Дизайнер подаёт работу
    8. Менеджер принимает стадию 1
    9. Загрузка файлов стадии 1
    10. Перемещение в стадию 2, назначение чертёжника
    11. Завершение всех стадий
    12. Перемещение в выполненный проект
    13. Создание карточки надзора
    14. Загрузка файла надзора (stage='supervision')
    15. Проверка всех платежей
    16. Очистка тестовых данных
    """

    # Class-level state для передачи данных между тестами
    _state = {}

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, test_employees):
        self.__class__._api_base = api_base
        self.__class__._headers = admin_headers
        self.__class__._employees = test_employees

    @pytest.mark.order(1)
    def test_01_create_client(self):
        """Шаг 1: Создание тестового клиента"""
        resp = api_post(self._api_base, "/api/clients", self._headers, json={
            "client_type": "Физическое лицо",
            "full_name": f"{TEST_PREFIX}WORKFLOW Клиент",
            "phone": "+79990000100",
            "email": "workflow@test.com",
        })
        assert resp.status_code == 200
        client = resp.json()
        self._state['client_id'] = client["id"]
        assert client["id"] > 0

    @pytest.mark.order(2)
    def test_02_create_individual_contract(self):
        """Шаг 2: Создание индивидуального договора"""
        resp = api_post(self._api_base, "/api/contracts", self._headers, json={
            "client_id": self._state['client_id'],
            "project_type": "Индивидуальный",
            "agent_type": "ФЕСТИВАЛЬ",
            "city": "СПБ",
            "contract_number": f"{TEST_PREFIX}WF001",
            "contract_date": "2026-02-01",
            "address": "Тестовый адрес Workflow",
            "area": 80.0,
            "total_amount": 400000.0,
            "advance_payment": 200000.0,
            "additional_payment": 200000.0,
            "contract_period": 45,
            "status": "Новый заказ",
        })
        assert resp.status_code == 200
        contract = resp.json()
        self._state['contract_id'] = contract["id"]

    @pytest.mark.order(3)
    def test_03_create_crm_card(self):
        """Шаг 3: Создание CRM карточки"""
        resp = api_post(self._api_base, "/api/crm/cards", self._headers, json={
            "contract_id": self._state['contract_id'],
            "column_name": "Новый заказ",
            "order_position": 0,
        })
        assert resp.status_code == 200
        card = resp.json()
        self._state['crm_card_id'] = card["id"]
        assert card["column_name"] == "Новый заказ"

    @pytest.mark.order(4)
    def test_04_set_card_deadline(self):
        """Шаг 4: Установка дедлайна"""
        resp = api_patch(
            self._api_base,
            f"/api/crm/cards/{self._state['crm_card_id']}",
            self._headers,
            json={"deadline": "2026-04-15"}
        )
        assert resp.status_code == 200
        assert resp.json()["deadline"] == "2026-04-15"

    @pytest.mark.order(5)
    def test_05_assign_surveyor_and_measurement(self):
        """Шаг 5: Назначение замерщика и дата замера"""
        surveyor = self._employees.get('surveyor')
        if surveyor:
            api_patch(
                self._api_base,
                f"/api/crm/cards/{self._state['crm_card_id']}",
                self._headers,
                json={"surveyor_id": surveyor["id"]}
            )

        resp = api_patch(
            self._api_base,
            f"/api/contracts/{self._state['contract_id']}/files",
            self._headers,
            json={"measurement_date": "2026-02-10"}
        )
        assert resp.status_code == 200

    @pytest.mark.order(6)
    def test_06_move_to_stage1_assign_designer(self):
        """Шаг 6: Перемещение в Стадию 1, назначение дизайнера"""
        card_id = self._state['crm_card_id']

        # В ожидании
        resp = api_patch(self._api_base, f"/api/crm/cards/{card_id}/column",
                         self._headers, json={"column_name": "В ожидании"})
        assert resp.status_code == 200

        # Стадия 1
        resp = api_patch(self._api_base, f"/api/crm/cards/{card_id}/column",
                         self._headers, json={"column_name": "Стадия 1: планировочные решения"})
        assert resp.status_code == 200

        # Назначаем дизайнера
        designer = self._employees.get('designer')
        if designer:
            resp = api_post(
                self._api_base,
                f"/api/crm/cards/{card_id}/stage-executor",
                self._headers,
                json={
                    "stage_name": "Стадия 1: планировочные решения",
                    "executor_id": designer["id"],
                    "deadline": "2026-03-01",
                }
            )
            assert resp.status_code == 200

    @pytest.mark.order(7)
    def test_07_designer_submits_work(self):
        """Шаг 7: Дизайнер подаёт работу"""
        card_id = self._state['crm_card_id']
        stage = "Стадия 1: планировочные решения"
        stage_encoded = quote(stage, safe='')

        designer = self._employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        resp = api_patch(
            self._api_base,
            f"/api/crm/cards/{card_id}/stage-executor/{stage_encoded}/complete",
            self._headers,
            json={"executor_id": designer['id']}
        )
        assert resp.status_code == 200

    @pytest.mark.order(8)
    def test_08_manager_accepts_stage1(self):
        """Шаг 8: Менеджер принимает стадию 1"""
        card_id = self._state['crm_card_id']

        manager = self._employees.get('manager')
        designer = self._employees.get('designer')
        manager_id = manager["id"] if manager else 1
        executor_name = designer["full_name"] if designer else "Test"

        resp = api_post(
            self._api_base,
            f"/api/crm/cards/{card_id}/manager-acceptance",
            self._headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_name": executor_name,
                "manager_id": manager_id,
            }
        )
        assert resp.status_code == 200

    @pytest.mark.order(9)
    def test_09_upload_stage1_files(self):
        """Шаг 9: Добавление файлов стадии 1"""
        resp = api_post(self._api_base, "/api/files", self._headers, json={
            "contract_id": self._state['contract_id'],
            "stage": "Стадия 1",
            "file_type": "Чертёж планировки",
            "file_name": f"{TEST_PREFIX}stage1_plan.pdf",
            "yandex_path": f"/{TEST_PREFIX}/stage1/plan.pdf",
            "public_link": "",
            "file_order": 0,
            "variation": 1,
        })
        assert resp.status_code == 200
        self._state['stage1_file_id'] = resp.json()["id"]

    @pytest.mark.order(10)
    def test_10_move_to_stage2_assign_draftsman(self):
        """Шаг 10: Перемещение в Стадию 2, назначение чертёжника"""
        card_id = self._state['crm_card_id']

        resp = api_patch(self._api_base, f"/api/crm/cards/{card_id}/column",
                         self._headers,
                         json={"column_name": "Стадия 2: концепция дизайна"})
        assert resp.status_code == 200

        draftsman = self._employees.get('draftsman')
        if draftsman:
            resp = api_post(
                self._api_base,
                f"/api/crm/cards/{card_id}/stage-executor",
                self._headers,
                json={
                    "stage_name": "Стадия 2: концепция дизайна",
                    "executor_id": draftsman["id"],
                }
            )
            assert resp.status_code == 200

    @pytest.mark.order(11)
    def test_11_complete_all_stages(self):
        """Шаг 11: Завершение всех стадий"""
        card_id = self._state['crm_card_id']

        # Стадия 3
        resp = api_patch(self._api_base, f"/api/crm/cards/{card_id}/column",
                         self._headers,
                         json={"column_name": "Стадия 3: рабочие чертежи"})
        assert resp.status_code == 200

    @pytest.mark.order(12)
    def test_12_move_to_completed(self):
        """Шаг 12: Перемещение в выполненный проект"""
        card_id = self._state['crm_card_id']

        resp = api_patch(self._api_base, f"/api/crm/cards/{card_id}/column",
                         self._headers,
                         json={"column_name": "Выполненный проект"})
        assert resp.status_code == 200
        assert resp.json()["column_name"] == "Выполненный проект"

    @pytest.mark.order(13)
    def test_13_create_supervision_card(self):
        """Шаг 13: Создание карточки надзора"""
        contract_id = self._state['contract_id']

        resp = api_post(self._api_base, "/api/supervision/cards", self._headers, json={
            "contract_id": contract_id,
            "column_name": "Новый заказ",
        })
        assert resp.status_code == 200
        sv_card = resp.json()
        self._state['supervision_card_id'] = sv_card["id"]
        assert sv_card["contract_id"] == contract_id

    @pytest.mark.order(14)
    def test_14_upload_supervision_file_correct_stage(self):
        """Шаг 14: Файл надзора с stage='supervision' (НЕ с именем стадии!)"""
        resp = api_post(self._api_base, "/api/files", self._headers, json={
            "contract_id": self._state['contract_id'],
            "stage": "supervision",
            "file_type": "Стадия 1: Закупка керамогранита",
            "file_name": f"{TEST_PREFIX}supervision_file.pdf",
            "yandex_path": f"/{TEST_PREFIX}/supervision/file.pdf",
            "public_link": "",
            "file_order": 0,
            "variation": 1,
        })
        assert resp.status_code == 200
        sv_file = resp.json()
        self._state['supervision_file_id'] = sv_file["id"]
        assert sv_file["stage"] == "supervision", \
            f"Файл надзора должен иметь stage='supervision', а не '{sv_file['stage']}'"

    @pytest.mark.order(15)
    def test_15_verify_all_data_exists(self):
        """Шаг 15: Проверка всех созданных данных"""
        # Клиент
        resp = api_get(self._api_base,
                       f"/api/clients/{self._state['client_id']}", self._headers)
        assert resp.status_code == 200

        # Договор
        resp = api_get(self._api_base,
                       f"/api/contracts/{self._state['contract_id']}", self._headers)
        assert resp.status_code == 200

        # CRM карточка
        resp = api_get(self._api_base,
                       f"/api/crm/cards/{self._state['crm_card_id']}", self._headers)
        assert resp.status_code == 200
        assert resp.json()["column_name"] == "Выполненный проект"

        # Карточка надзора
        resp = api_get(self._api_base,
                       f"/api/supervision/cards/{self._state['supervision_card_id']}",
                       self._headers)
        assert resp.status_code == 200

        # Файлы
        resp = api_get(self._api_base,
                       f"/api/files/contract/{self._state['contract_id']}",
                       self._headers)
        assert resp.status_code == 200
        files = resp.json()
        assert len(files) >= 2  # stage1 + supervision
        # Проверяем что supervision файл имеет правильный stage
        sv_files = [f for f in files if f['stage'] == 'supervision']
        assert len(sv_files) >= 1, "Нет файлов с stage='supervision'"

    @pytest.mark.order(16)
    def test_16_cleanup_all_test_data(self):
        """Шаг 16: Очистка всех тестовых данных"""
        # Файлы
        for file_key in ['stage1_file_id', 'supervision_file_id']:
            fid = self._state.get(file_key)
            if fid:
                api_delete(self._api_base, f"/api/files/{fid}", self._headers)

        # Карточка надзора
        sv_id = self._state.get('supervision_card_id')
        if sv_id:
            api_delete(self._api_base, f"/api/supervision/orders/{sv_id}", self._headers)

        # CRM карточка
        crm_id = self._state.get('crm_card_id')
        if crm_id:
            api_delete(self._api_base, f"/api/crm/cards/{crm_id}", self._headers)

        # Договор
        con_id = self._state.get('contract_id')
        if con_id:
            api_delete(self._api_base, f"/api/contracts/{con_id}", self._headers)

        # Клиент (каскадно удалит оставшееся)
        cl_id = self._state.get('client_id')
        if cl_id:
            resp = api_delete(self._api_base, f"/api/clients/{cl_id}", self._headers)
            assert resp.status_code == 200

        self._state.clear()

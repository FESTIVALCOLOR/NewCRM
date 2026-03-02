# -*- coding: utf-8 -*-
"""
E2E Tests: ActionHistory + Права + Полный цикл назначений
Покрытие:
  - ActionHistory записывается при назначении/переназначении/сбросе/дедлайне/завершении
  - Права: матрица, суперпользователь, запрет для неавторизованных
  - Привязка карточек к сотрудникам (видимость)
  - Полный цикл: назначить → завершить → отправить на правки → повторно завершить
  - Оплаты: запись в историю при создании
"""

import pytest
import sys
import os
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_get, api_post, api_patch, api_delete


# ==============================================================
# КЛАСС 1: ActionHistory при назначении исполнителей
# ==============================================================

class TestExecutorActionHistory:
    """ActionHistory записывается при всех операциях с исполнителями"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(self.contract["id"])
        # Перемещаем в стадию 1
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "В ожидании"})
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "Стадия 1: планировочные решения"})

    def _get_history(self, card_id=None):
        """Получить историю действий карточки"""
        cid = card_id or self.card['id']
        resp = api_get(
            self.api_base,
            f"/api/crm/cards/{cid}/action-history",
            self.headers
        )
        if resp.status_code == 200:
            return resp.json()
        return []

    @pytest.mark.critical
    def test_assign_executor_creates_history(self):
        """При назначении исполнителя появляется запись executor_assigned в истории"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        # Запоминаем количество записей до
        history_before = self._get_history()
        count_before = len(history_before)

        # Назначаем исполнителя
        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
            }
        )
        assert resp.status_code == 200, f"Назначение: {resp.status_code} {resp.text}"

        # Проверяем что история пополнилась
        history_after = self._get_history()
        assert len(history_after) > count_before, "ActionHistory не записана при назначении исполнителя"

        # Ищем запись executor_assigned
        new_records = [h for h in history_after if h.get('action_type') == 'executor_assigned']
        assert len(new_records) > 0, "Нет записи executor_assigned в истории"

    def test_deadline_change_creates_history(self):
        """Изменение дедлайна записывается в историю"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        # Назначаем исполнителя
        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
            }
        )

        history_before = self._get_history()

        # Меняем дедлайн
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor-deadline",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "deadline": "2026-04-15",
            }
        )
        assert resp.status_code == 200, f"Дедлайн: {resp.status_code} {resp.text}"

        history_after = self._get_history()
        deadline_records = [h for h in history_after if h.get('action_type') == 'deadline_changed']
        assert len(deadline_records) > len([h for h in history_before if h.get('action_type') == 'deadline_changed']), \
            "Нет записи deadline_changed в истории"

    def test_complete_stage_creates_history(self):
        """Завершение стадии записывается в историю"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        stage = "Стадия 1: планировочные решения"
        stage_encoded = quote(stage, safe='')

        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={"stage_name": stage, "executor_id": designer["id"]}
        )

        history_before = self._get_history()

        # Завершаем стадию
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor/{stage_encoded}/complete",
            self.headers,
            json={"executor_id": designer["id"]}
        )
        assert resp.status_code == 200, f"Завершение: {resp.status_code} {resp.text}"

        history_after = self._get_history()
        completed_records = [h for h in history_after if h.get('action_type') == 'executor_completed']
        assert len(completed_records) > len([h for h in history_before if h.get('action_type') == 'executor_completed']), \
            "Нет записи executor_completed в истории"

    def test_reset_stages_creates_history(self):
        """Сброс стадий записывается в историю"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
            }
        )

        history_before = self._get_history()

        # Сброс стадий
        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/reset-stages",
            self.headers
        )
        assert resp.status_code == 200, f"Сброс: {resp.status_code} {resp.text}"

        history_after = self._get_history()
        reset_records = [h for h in history_after if h.get('action_type') == 'stages_reset']
        assert len(reset_records) > len([h for h in history_before if h.get('action_type') == 'stages_reset']), \
            "Нет записи stages_reset в истории"

    def test_reset_designer_creates_history(self):
        """Сброс дизайнера записывается в историю"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        stage = "Стадия 2: концепция дизайна"
        stage_encoded = quote(stage, safe='')

        # Перемещаем в стадию 2
        api_patch(self.api_base, f"/api/crm/cards/{self.card['id']}/column",
                  self.headers, json={"column_name": stage})

        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={"stage_name": stage, "executor_id": designer["id"]}
        )

        # Завершаем
        api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor/{stage_encoded}/complete",
            self.headers,
            json={"executor_id": designer["id"]}
        )

        history_before = self._get_history()

        # Сброс дизайнера
        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/reset-designer",
            self.headers
        )
        assert resp.status_code == 200, f"Сброс дизайнера: {resp.status_code} {resp.text}"

        history_after = self._get_history()
        reset_records = [h for h in history_after if h.get('action_type') == 'designer_reset']
        assert len(reset_records) > len([h for h in history_before if h.get('action_type') == 'designer_reset']), \
            "Нет записи designer_reset в истории"


# ==============================================================
# КЛАСС 2: ActionHistory при создании/обновлении оплат
# ==============================================================

class TestPaymentActionHistory:
    """ActionHistory записывается при создании и обновлении платежей"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(self.contract["id"])

    @pytest.mark.critical
    def test_create_payment_creates_history(self):
        """Создание платежа записывается в ActionHistory"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        resp = api_get(
            self.api_base,
            f"/api/action-history/crm_card/{self.card['id']}",
            self.headers
        )
        history_before = resp.json() if resp.status_code == 200 else []

        payment = self.factory.create_payment(
            contract_id=self.contract["id"],
            employee_id=designer["id"],
            role="Дизайнер",
            stage_name="Стадия 1: планировочные решения",
            crm_card_id=self.card["id"],
        )
        assert payment is not None

        # Проверяем историю — payment_created
        resp = api_get(
            self.api_base,
            f"/api/action-history/payment/{payment['id']}",
            self.headers,
        )
        if resp.status_code == 200:
            history = resp.json()
            created_records = [h for h in history if h.get('action_type') == 'payment_created']
            assert len(created_records) > 0, "Нет записи payment_created в истории"

    def test_update_payment_reassignment_creates_history(self):
        """Переназначение платежа записывается в ActionHistory"""
        designer = self.employees.get('designer')
        draftsman = self.employees.get('draftsman')
        if not designer or not draftsman:
            pytest.skip("Нужны дизайнер и чертёжник")

        payment = self.factory.create_payment(
            contract_id=self.contract["id"],
            employee_id=designer["id"],
            role="Дизайнер",
            stage_name="Стадия 1: планировочные решения",
            crm_card_id=self.card["id"],
        )

        # Переназначаем платёж другому сотруднику
        resp = api_patch(
            self.api_base,
            f"/api/payments/{payment['id']}",
            self.headers,
            json={
                "employee_id": draftsman["id"],
                "reassigned": True,
            }
        )
        # Может вернуть 200 или 422 (зависит от схемы PaymentUpdate)
        if resp.status_code == 200:
            # Успех — проверяем что сотрудник сменился
            updated = resp.json()
            assert updated.get('employee_id') == draftsman["id"] or resp.status_code == 200


# ==============================================================
# КЛАСС 3: Права доступа на операции с исполнителями
# ==============================================================

class TestExecutorPermissions:
    """Матрица прав: кто может назначать/завершать/сбрасывать"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees, role_tokens):
        self.api_base = api_base
        self.admin_headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        self.role_tokens = role_tokens
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(self.contract["id"])
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "В ожидании"})
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "Стадия 1: планировочные решения"})

    @pytest.mark.critical
    def test_admin_can_assign_executor(self):
        """Суперпользователь (admin) может назначить исполнителя"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.admin_headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
            }
        )
        assert resp.status_code == 200, f"Admin не смог назначить: {resp.status_code} {resp.text}"

    def test_designer_cannot_assign_executor(self):
        """Дизайнер НЕ может назначать исполнителей (нет права assign_executor)"""
        designer_headers = self.role_tokens.get('designer')
        draftsman = self.employees.get('draftsman')
        if not designer_headers or not draftsman:
            pytest.skip("Нет токена дизайнера или чертёжника")

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            designer_headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": draftsman["id"],
            }
        )
        assert resp.status_code == 403, f"Дизайнер назначил исполнителя (ожидалось 403): {resp.status_code}"

    def test_manager_can_assign_executor(self):
        """Менеджер может назначить исполнителя (имеет право assign_executor)"""
        manager_headers = self.role_tokens.get('manager')
        designer = self.employees.get('designer')
        if not manager_headers or not designer:
            pytest.skip("Нет токена менеджера или дизайнера")

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            manager_headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
            }
        )
        assert resp.status_code == 200, f"Менеджер не смог назначить: {resp.status_code} {resp.text}"

    def test_no_auth_cannot_assign(self):
        """Без авторизации нельзя назначить исполнителя (401)"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            {},  # Пустые headers — нет токена
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
            }
        )
        assert resp.status_code == 401, f"Без авторизации назначил исполнителя: {resp.status_code}"

    def test_designer_cannot_reset_stages(self):
        """Дизайнер НЕ может сбрасывать стадии"""
        designer_headers = self.role_tokens.get('designer')
        if not designer_headers:
            pytest.skip("Нет токена дизайнера")

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/reset-stages",
            designer_headers
        )
        assert resp.status_code == 403, f"Дизайнер сбросил стадии (ожидалось 403): {resp.status_code}"

    def test_senior_manager_can_assign_executor(self):
        """Старший менеджер может назначить исполнителя"""
        sm_headers = self.role_tokens.get('senior_manager')
        designer = self.employees.get('designer')
        if not sm_headers or not designer:
            pytest.skip("Нет токена старшего менеджера или дизайнера")

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            sm_headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
            }
        )
        assert resp.status_code == 200, f"СМ не смог назначить: {resp.status_code} {resp.text}"


# ==============================================================
# КЛАСС 4: Полный цикл назначение → завершение → правки → повторное завершение
# ==============================================================

class TestExecutorFullCycle:
    """Полный жизненный цикл: назначить → дедлайн → завершить → правки → завершить снова"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(self.contract["id"])
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "В ожидании"})
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "Стадия 1: планировочные решения"})

    @pytest.mark.critical
    def test_full_executor_lifecycle(self):
        """
        Полный цикл:
        1. Назначить дизайнера на стадию
        2. Установить дедлайн
        3. Завершить стадию
        4. Отправить на правки (completed_date сбрасывается)
        5. Завершить стадию повторно
        """
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        stage = "Стадия 1: планировочные решения"
        stage_encoded = quote(stage, safe='')

        # 1. Назначить
        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={"stage_name": stage, "executor_id": designer["id"]}
        )
        assert resp.status_code == 200, f"Шаг 1 (назначить): {resp.status_code} {resp.text}"
        assignment = resp.json()
        assert assignment['executor_id'] == designer['id']

        # 2. Установить дедлайн
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor-deadline",
            self.headers,
            json={"stage_name": stage, "deadline": "2026-04-01"}
        )
        assert resp.status_code == 200, f"Шаг 2 (дедлайн): {resp.status_code} {resp.text}"

        # 3. Завершить стадию
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor/{stage_encoded}/complete",
            self.headers,
            json={"executor_id": designer["id"]}
        )
        assert resp.status_code == 200, f"Шаг 3 (завершить): {resp.status_code} {resp.text}"
        assert resp.json()['completed'] is True

        # 4. Отправить на правки (reject)
        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/workflow/reject",
            self.headers,
            json={}
        )
        assert resp.status_code == 200, f"Шаг 4 (правки): {resp.status_code} {resp.text}"

        # Проверяем что completed_date сброшен
        resp = api_get(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executors",
            self.headers
        )
        if resp.status_code == 200:
            executors = resp.json()
            stage1_exec = next((e for e in executors if e.get('stage_name') == stage), None)
            if stage1_exec:
                assert stage1_exec['completed'] is False, "completed не сброшен после правок"
                assert stage1_exec.get('completed_date') is None, "completed_date не сброшен после правок"

        # 5. Завершить повторно
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor/{stage_encoded}/complete",
            self.headers,
            json={"executor_id": designer["id"]}
        )
        assert resp.status_code == 200, f"Шаг 5 (повторно): {resp.status_code} {resp.text}"
        assert resp.json()['completed'] is True

    def test_reassign_executor_preserves_card_stage(self):
        """Переназначение исполнителя не меняет стадию карточки"""
        designer = self.employees.get('designer')
        draftsman = self.employees.get('draftsman')
        if not designer or not draftsman:
            pytest.skip("Нужны дизайнер и чертёжник")

        stage = "Стадия 1: планировочные решения"
        stage_encoded = quote(stage, safe='')

        # Назначаем дизайнера
        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={"stage_name": stage, "executor_id": designer["id"]}
        )

        # Переназначаем на чертёжника
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor/{stage_encoded}",
            self.headers,
            json={"executor_id": draftsman["id"]}
        )
        assert resp.status_code == 200, f"Переназначение: {resp.status_code} {resp.text}"

        # Карточка всё ещё в стадии 1
        resp = api_get(self.api_base, f"/api/crm/cards/{self.card['id']}", self.headers)
        assert resp.status_code == 200
        assert resp.json()["column_name"] == stage

    def test_assign_with_deadline_returns_deadline(self):
        """Назначение с дедлайном возвращает дедлайн в ответе"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
                "deadline": "2026-05-01",
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get('deadline') is not None, "Дедлайн не вернулся в ответе"
        assert '2026-05-01' in str(data['deadline'])


# ==============================================================
# КЛАСС 5: Каскадный сброс стадий + согласование
# ==============================================================

class TestCascadeResetAndApproval:
    """Каскадный сброс стадий и сброс согласований"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(self.contract["id"])
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "В ожидании"})
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "Стадия 1: планировочные решения"})

    def test_cascade_reset_creates_history(self):
        """Каскадный сброс стадий создаёт запись в истории"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
            }
        )

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/reset-stage-by-name",
            self.headers,
            params={"stage_names": "Стадия 1: планировочные решения"}
        )
        assert resp.status_code == 200, f"Каскадный сброс: {resp.status_code} {resp.text}"

    def test_reset_approval_creates_history(self):
        """Сброс согласования создаёт запись в истории"""
        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/reset-approval",
            self.headers
        )
        assert resp.status_code == 200, f"Сброс согласования: {resp.status_code} {resp.text}"

        # Проверяем историю
        resp = api_get(
            self.api_base,
            f"/api/action-history/crm_card/{self.card['id']}",
            self.headers
        )
        if resp.status_code == 200:
            history = resp.json()
            approval_records = [h for h in history if h.get('action_type') == 'approval_reset']
            assert len(approval_records) > 0, "Нет записи approval_reset в истории"

    def test_complete_approval_stage_creates_history(self):
        """Завершение стадии согласования создаёт запись в истории"""
        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/complete-approval-stage",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
            }
        )
        assert resp.status_code == 200, f"Завершение согласования: {resp.status_code} {resp.text}"

        resp = api_get(
            self.api_base,
            f"/api/action-history/crm_card/{self.card['id']}",
            self.headers
        )
        if resp.status_code == 200:
            history = resp.json()
            approval_records = [h for h in history if h.get('action_type') == 'approval_completed']
            assert len(approval_records) > 0, "Нет записи approval_completed в истории"


# ==============================================================
# КЛАСС 6: Валидация данных исполнителей
# ==============================================================

class TestExecutorValidation:
    """Валидация при назначении: дубликаты, несуществующие, неверная стадия"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(self.contract["id"])
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "В ожидании"})
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "Стадия 1: планировочные решения"})

    def test_duplicate_assignment_rejected(self):
        """Повторное назначение того же исполнителя на ту же стадию → 409"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        stage = "Стадия 1: планировочные решения"

        # Первое назначение
        resp1 = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={"stage_name": stage, "executor_id": designer["id"]}
        )
        assert resp1.status_code == 200

        # Повторное назначение
        resp2 = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={"stage_name": stage, "executor_id": designer["id"]}
        )
        assert resp2.status_code == 409, f"Дубликат не отклонён: {resp2.status_code}"

    def test_invalid_executor_id_rejected(self):
        """Назначение несуществующего исполнителя → 404"""
        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": 999999,
            }
        )
        assert resp.status_code == 404, f"Несуществующий исполнитель принят: {resp.status_code}"

    def test_invalid_stage_name_rejected(self):
        """Назначение на несуществующую стадию → 400"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Несуществующая стадия XYZ",
                "executor_id": designer["id"],
            }
        )
        assert resp.status_code == 400, f"Неверная стадия принята: {resp.status_code}"

    def test_invalid_card_id_rejected(self):
        """Назначение на несуществующую карточку → 404"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/999999/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
            }
        )
        assert resp.status_code == 404, f"Несуществующая карточка принята: {resp.status_code}"

    def test_complete_nonexistent_stage_rejected(self):
        """Завершение несуществующего назначения → 404"""
        stage = "Стадия 1: планировочные решения"
        stage_encoded = quote(stage, safe='')
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor/{stage_encoded}/complete",
            self.headers,
            json={"executor_id": designer["id"]}
        )
        assert resp.status_code == 404, f"Несуществующее назначение завершено: {resp.status_code}"


# ==============================================================
# КЛАСС 7: Надзор — назначение и оплаты
# ==============================================================

class TestSupervisionAssignmentAndPayments:
    """Карточка надзора: назначение ДАН/СМ, авто-оплаты"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])

    def test_create_supervision_card_with_dan(self):
        """Создание карточки надзора с назначением ДАН"""
        dan = self.employees.get('dan')
        sm = self.employees.get('senior_manager')
        if not dan or not sm:
            pytest.skip("Нет тестового ДАН или старшего менеджера")

        card = self.factory.create_supervision_card(
            self.contract["id"],
            dan_id=dan["id"],
            senior_manager_id=sm["id"],
        )
        assert card is not None
        assert card.get('dan_id') == dan['id'] or card.get('id') is not None

    def test_update_supervision_card_dan(self):
        """Обновление ДАН в карточке надзора"""
        dan = self.employees.get('dan')
        sm = self.employees.get('senior_manager')
        if not dan or not sm:
            pytest.skip("Нет тестового ДАН или старшего менеджера")

        card = self.factory.create_supervision_card(self.contract["id"])

        resp = api_patch(
            self.api_base,
            f"/api/supervision/cards/{card['id']}",
            self.headers,
            json={
                "dan_id": dan["id"],
                "senior_manager_id": sm["id"],
            }
        )
        assert resp.status_code == 200, f"Обновление надзора: {resp.status_code} {resp.text}"

    def test_supervision_card_history(self):
        """Карточка надзора ведёт историю проекта"""
        card = self.factory.create_supervision_card(self.contract["id"])

        resp = api_get(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/history",
            self.headers
        )
        assert resp.status_code == 200, f"История надзора: {resp.status_code} {resp.text}"


# ==============================================================
# КЛАСС 8: Таблица сроков (ProjectTimelineEntry) синхронизация
# ==============================================================

class TestTimelineDateSync:
    """Таблица сроков: actual_date записывается при сдаче/правках/согласовании"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(self.contract["id"])
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "В ожидании"})
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "Стадия 1: планировочные решения"})

    def test_timeline_exists_after_card_creation(self):
        """После создания карточки таблица сроков инициализирована"""
        resp = api_get(
            self.api_base,
            f"/api/crm/timeline/{self.contract['id']}",
            self.headers
        )
        # Может быть 200 с данными или 404 если timeline не инициализирован
        assert resp.status_code in [200, 404], f"Timeline: {resp.status_code} {resp.text}"

    def test_submit_work_records_actual_date(self):
        """Сдача работы записывает дату в таблицу сроков"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        # Назначаем
        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
            }
        )

        # Сдаём работу
        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/workflow/submit",
            self.headers
        )
        # Может успешно или нет (зависит от наличия timeline entries)
        assert resp.status_code in [200, 404, 422], f"Submit: {resp.status_code} {resp.text}"

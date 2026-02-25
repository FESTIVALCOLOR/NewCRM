# -*- coding: utf-8 -*-
"""
E2E Tests: Синхронизация данных
7 тестов — GET endpoints синхронизации с проверкой структуры ответов.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get, api_post


class TestSyncData:
    """Тесты синхронизации данных"""

    def test_sync_stage_executors(self, api_base, admin_headers):
        """GET /api/sync/stage-executors — исполнители стадий"""
        resp = api_get(api_base, "/api/sync/stage-executors", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            required_keys = {"id", "crm_card_id", "stage_name", "executor_id",
                             "assigned_date", "assigned_by", "deadline",
                             "completed", "completed_date", "submitted_date"}
            for item in data[:5]:
                assert required_keys.issubset(item.keys()), (
                    f"Отсутствуют ключи: {required_keys - item.keys()}"
                )
                assert isinstance(item["id"], int), "id должен быть int"
                assert isinstance(item["crm_card_id"], int), "crm_card_id должен быть int"
                assert isinstance(item["completed"], bool), "completed должен быть bool"
                # executor_id — int или None
                if item["executor_id"] is not None:
                    assert isinstance(item["executor_id"], int), "executor_id должен быть int или None"

    def test_sync_stage_executors_deadline_fields(self, api_base, admin_headers):
        """GET /api/sync/stage-executors — проверка полей deadline и completed"""
        resp = api_get(api_base, "/api/sync/stage-executors", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            for item in data[:5]:
                # deadline — строка-дата или None
                if item.get("deadline") is not None:
                    assert isinstance(item["deadline"], str), (
                        f"deadline должен быть строкой (ISO дата), получили: {type(item['deadline'])}"
                    )
                # completed_date только если completed=True (мягкая проверка)
                if item.get("completed_date") is not None:
                    assert isinstance(item["completed_date"], str), "completed_date должен быть строкой"
                # submitted_date — строка или None
                if item.get("submitted_date") is not None:
                    assert isinstance(item["submitted_date"], str), "submitted_date должен быть строкой"

    def test_sync_approval_deadlines(self, api_base, admin_headers):
        """GET /api/sync/approval-deadlines — дедлайны согласования"""
        resp = api_get(api_base, "/api/sync/approval-deadlines", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            required_keys = {"id", "crm_card_id", "stage_name", "deadline",
                             "is_completed", "completed_date", "created_at"}
            for item in data[:5]:
                assert required_keys.issubset(item.keys()), (
                    f"Отсутствуют ключи: {required_keys - item.keys()}"
                )
                assert isinstance(item["id"], int), "id должен быть int"
                assert isinstance(item["crm_card_id"], int), "crm_card_id должен быть int"
                assert isinstance(item["is_completed"], bool), "is_completed должен быть bool"
                # deadline — строка или None
                if item["deadline"] is not None:
                    assert isinstance(item["deadline"], str), "deadline должен быть строкой"

    def test_sync_action_history(self, api_base, admin_headers):
        """GET /api/sync/action-history — история действий"""
        resp = api_get(api_base, "/api/sync/action-history", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            required_keys = {"id", "user_id", "action_type", "entity_type",
                             "entity_id", "description", "action_date"}
            for item in data[:5]:
                assert required_keys.issubset(item.keys()), (
                    f"Отсутствуют ключи: {required_keys - item.keys()}"
                )
                assert isinstance(item["id"], int), "id должен быть int"
                # user_id — int или None
                if item["user_id"] is not None:
                    assert isinstance(item["user_id"], int), "user_id должен быть int или None"
                # action_type и entity_type — строки или None
                if item["action_type"] is not None:
                    assert isinstance(item["action_type"], str), "action_type должен быть строкой"
                if item["entity_type"] is not None:
                    assert isinstance(item["entity_type"], str), "entity_type должен быть строкой"

    def test_sync_supervision_history(self, api_base, admin_headers):
        """GET /api/sync/supervision-history — история надзора"""
        resp = api_get(api_base, "/api/sync/supervision-history", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            required_keys = {"id", "supervision_card_id", "entry_type",
                             "message", "created_by", "created_at"}
            for item in data[:5]:
                assert required_keys.issubset(item.keys()), (
                    f"Отсутствуют ключи: {required_keys - item.keys()}"
                )
                assert isinstance(item["id"], int), "id должен быть int"
                # supervision_card_id — int или None
                if item["supervision_card_id"] is not None:
                    assert isinstance(item["supervision_card_id"], int), (
                        "supervision_card_id должен быть int или None"
                    )
                # created_at — строка или None
                if item["created_at"] is not None:
                    assert isinstance(item["created_at"], str), "created_at должен быть строкой"

    def test_sync_all_endpoints_return_list(self, api_base, admin_headers):
        """Одновременный GET всех 4 endpoint-ов синхронизации — все возвращают list"""
        endpoints = [
            "/api/sync/stage-executors",
            "/api/sync/approval-deadlines",
            "/api/sync/action-history",
            "/api/sync/supervision-history",
        ]
        for endpoint in endpoints:
            resp = api_get(api_base, endpoint, admin_headers)
            assert resp.status_code == 200, (
                f"Endpoint {endpoint} вернул {resp.status_code}"
            )
            data = resp.json()
            assert isinstance(data, list), (
                f"Endpoint {endpoint} должен возвращать list, получили {type(data)}"
            )

    def test_sync_requires_auth(self, api_base):
        """GET /api/sync/stage-executors без токена — 401"""
        resp = api_get(api_base, "/api/sync/stage-executors", {})
        assert resp.status_code in (401, 403)

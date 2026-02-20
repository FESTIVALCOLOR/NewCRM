# -*- coding: utf-8 -*-
"""
Тесты CacheManager — файловый кэш превью
"""
import sys
import os
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.cache_manager import CacheManager


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Переопределяем cache_dir на временную директорию"""
    cache_path = str(tmp_path / "interior_studio_cache" / "previews")
    monkeypatch.setattr(CacheManager, 'get_cache_dir', staticmethod(lambda: cache_path))
    return cache_path


class TestCacheManagerBasic:
    def test_get_cache_dir_returns_string(self):
        path = CacheManager.get_cache_dir()
        assert isinstance(path, str)
        assert "interior_studio_cache" in path

    def test_ensure_cache_dir_creates(self, cache_dir):
        assert not os.path.exists(cache_dir)
        result = CacheManager.ensure_cache_dir()
        assert os.path.exists(result)

    def test_ensure_cache_dir_idempotent(self, cache_dir):
        CacheManager.ensure_cache_dir()
        CacheManager.ensure_cache_dir()
        assert os.path.exists(cache_dir)


class TestCacheManagerSize:
    def test_empty_cache_size_zero(self, cache_dir):
        assert CacheManager.get_cache_size() == 0

    def test_cache_size_with_files(self, cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
        # Создаём файл 1KB
        with open(os.path.join(cache_dir, "test.png"), "wb") as f:
            f.write(b"x" * 1024)
        assert CacheManager.get_cache_size() == 1024

    def test_cache_size_mb(self, cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
        with open(os.path.join(cache_dir, "big.png"), "wb") as f:
            f.write(b"x" * (1024 * 1024))  # 1 MB
        assert CacheManager.get_cache_size_mb() == 1.0

    def test_cache_files_count(self, cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
        for i in range(5):
            with open(os.path.join(cache_dir, f"file_{i}.png"), "w") as f:
                f.write("x")
        assert CacheManager.get_cache_files_count() == 5

    def test_empty_dir_count_zero(self, cache_dir):
        assert CacheManager.get_cache_files_count() == 0


class TestCacheManagerClear:
    def test_clear_cache_removes_all(self, cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
        for i in range(3):
            with open(os.path.join(cache_dir, f"file_{i}.png"), "w") as f:
                f.write("x")
        result = CacheManager.clear_cache()
        assert result is True
        assert not os.path.exists(cache_dir)

    def test_clear_nonexistent_returns_false(self, cache_dir):
        assert CacheManager.clear_cache() is False

    def test_clear_contract_cache(self, cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
        # Файлы для contract_id=42
        for i in range(3):
            with open(os.path.join(cache_dir, f"42_preview_{i}.png"), "w") as f:
                f.write("x")
        # Файлы для другого контракта
        with open(os.path.join(cache_dir, "99_preview_0.png"), "w") as f:
            f.write("x")

        deleted = CacheManager.clear_contract_cache(42)
        assert deleted == 3
        # Файл другого контракта остался
        assert os.path.exists(os.path.join(cache_dir, "99_preview_0.png"))

    def test_clear_contract_nonexistent_dir(self, cache_dir):
        assert CacheManager.clear_contract_cache(42) == 0

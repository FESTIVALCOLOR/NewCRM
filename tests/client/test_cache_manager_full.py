# -*- coding: utf-8 -*-
"""
Полное покрытие utils/cache_manager.py — ~15 тестов.
"""

import pytest
import os
import tempfile
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.cache_manager import CacheManager


@pytest.fixture
def cache_dir():
    """Создать и очистить кэш-директорию."""
    d = CacheManager.get_cache_dir()
    os.makedirs(d, exist_ok=True)
    yield d
    # cleanup
    import shutil
    if os.path.exists(d):
        shutil.rmtree(d)


class TestGetCacheDir:
    def test_returns_string(self):
        result = CacheManager.get_cache_dir()
        assert isinstance(result, str)

    def test_contains_interior_studio(self):
        result = CacheManager.get_cache_dir()
        assert 'interior_studio_cache' in result

    def test_contains_previews(self):
        result = CacheManager.get_cache_dir()
        assert 'previews' in result


class TestEnsureCacheDir:
    def test_creates_directory(self):
        result = CacheManager.ensure_cache_dir()
        assert os.path.isdir(result)
        # cleanup
        import shutil
        parent = os.path.dirname(result)
        if os.path.exists(parent):
            shutil.rmtree(parent)


class TestClearCache:
    def test_clears_existing_cache(self, cache_dir):
        # Создаём тестовый файл
        test_file = os.path.join(cache_dir, 'test.png')
        with open(test_file, 'w') as f:
            f.write('test')
        assert CacheManager.clear_cache() is True
        assert not os.path.exists(cache_dir)

    def test_nonexistent_cache_returns_false(self):
        import shutil
        d = CacheManager.get_cache_dir()
        if os.path.exists(d):
            shutil.rmtree(d)
        assert CacheManager.clear_cache() is False


class TestClearContractCache:
    def test_clears_contract_files(self, cache_dir):
        # Создаём файлы для контракта
        for i in range(3):
            with open(os.path.join(cache_dir, f'100_file{i}.png'), 'w') as f:
                f.write('x')
        # Файл другого контракта
        with open(os.path.join(cache_dir, '200_other.png'), 'w') as f:
            f.write('x')

        deleted = CacheManager.clear_contract_cache(100)
        assert deleted == 3
        assert os.path.exists(os.path.join(cache_dir, '200_other.png'))

    def test_nonexistent_dir_returns_zero(self):
        import shutil
        d = CacheManager.get_cache_dir()
        if os.path.exists(d):
            shutil.rmtree(d)
        assert CacheManager.clear_contract_cache(999) == 0


class TestGetCacheSize:
    def test_empty_cache_returns_zero(self):
        import shutil
        d = CacheManager.get_cache_dir()
        if os.path.exists(d):
            shutil.rmtree(d)
        assert CacheManager.get_cache_size() == 0

    def test_with_files(self, cache_dir):
        with open(os.path.join(cache_dir, 'file.txt'), 'w') as f:
            f.write('A' * 100)
        size = CacheManager.get_cache_size()
        assert size >= 100


class TestGetCacheSizeMb:
    def test_returns_float(self):
        result = CacheManager.get_cache_size_mb()
        assert isinstance(result, float)


class TestGetCacheFilesCount:
    def test_empty_returns_zero(self):
        import shutil
        d = CacheManager.get_cache_dir()
        if os.path.exists(d):
            shutil.rmtree(d)
        assert CacheManager.get_cache_files_count() == 0

    def test_with_files(self, cache_dir):
        for i in range(5):
            with open(os.path.join(cache_dir, f'f{i}.txt'), 'w') as f:
                f.write('x')
        assert CacheManager.get_cache_files_count() == 5

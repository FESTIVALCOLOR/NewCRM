# -*- coding: utf-8 -*-
"""
Утилита управления кэшем превью файлов
"""
import os
import shutil
import tempfile


class CacheManager:
    """Управление кэшем превью"""

    @staticmethod
    def get_cache_dir():
        """Получение директории кэша

        Returns:
            Путь к директории кэша
        """
        return os.path.join(tempfile.gettempdir(), 'interior_studio_cache', 'previews')

    @staticmethod
    def clear_cache():
        """Очистка всего кэша превью

        Returns:
            True при успехе, False при ошибке
        """
        try:
            cache_dir = CacheManager.get_cache_dir()
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                print("[OK] Кэш превью очищен")
                return True
            return False
        except Exception as e:
            print(f"[ERROR] Ошибка очистки кэша: {e}")
            return False

    @staticmethod
    def clear_contract_cache(contract_id):
        """Очистка кэша для конкретного договора

        Args:
            contract_id: ID договора

        Returns:
            Количество удаленных файлов
        """
        try:
            cache_dir = CacheManager.get_cache_dir()
            if not os.path.exists(cache_dir):
                return 0

            deleted_count = 0
            # Удаляем все файлы, начинающиеся с contract_id
            for filename in os.listdir(cache_dir):
                if filename.startswith(f"{contract_id}_"):
                    try:
                        file_path = os.path.join(cache_dir, filename)
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        print(f"[WARN] Не удалось удалить файл {filename}: {e}")

            print(f"[OK] Очищен кэш договора {contract_id}: {deleted_count} файлов")
            return deleted_count

        except Exception as e:
            print(f"[ERROR] Ошибка очистки кэша договора: {e}")
            return 0

    @staticmethod
    def get_cache_size():
        """Получение размера кэша в байтах

        Returns:
            Размер кэша в байтах
        """
        try:
            cache_dir = CacheManager.get_cache_dir()
            if not os.path.exists(cache_dir):
                return 0

            total_size = 0
            for dirpath, dirnames, filenames in os.walk(cache_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)

            return total_size

        except Exception as e:
            print(f"[ERROR] Ошибка получения размера кэша: {e}")
            return 0

    @staticmethod
    def get_cache_size_mb():
        """Получение размера кэша в мегабайтах

        Returns:
            Размер кэша в МБ (округленный до 2 знаков)
        """
        size_bytes = CacheManager.get_cache_size()
        size_mb = size_bytes / (1024 * 1024)
        return round(size_mb, 2)

    @staticmethod
    def get_cache_files_count():
        """Получение количества файлов в кэше

        Returns:
            Количество файлов
        """
        try:
            cache_dir = CacheManager.get_cache_dir()
            if not os.path.exists(cache_dir):
                return 0

            return len([f for f in os.listdir(cache_dir) if os.path.isfile(os.path.join(cache_dir, f))])

        except Exception as e:
            print(f"[ERROR] Ошибка подсчета файлов кэша: {e}")
            return 0

    @staticmethod
    def ensure_cache_dir():
        """Создание директории кэша если её нет

        Returns:
            Путь к директории кэша
        """
        cache_dir = CacheManager.get_cache_dir()
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

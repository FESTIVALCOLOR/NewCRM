"""
Интеграция с Яндекс.Диском
Загрузка, скачивание и управление файлами
"""

import os
from typing import BinaryIO, Optional

import requests

from config import get_settings

settings = get_settings()


class YandexDiskService:
    """Сервис для работы с Яндекс.Диском"""

    def __init__(self):
        self.token = settings.yandex_disk_token
        self.base_url = "https://cloud-api.yandex.net/v1/disk"
        self.headers = {"Authorization": f"OAuth {self.token}", "Content-Type": "application/json"}

    def upload_file(self, local_path: str, yandex_path: str) -> dict:
        """
        Загрузка файла на Яндекс.Диск

        Args:
            local_path: Путь к локальному файлу
            yandex_path: Путь на Яндекс.Диске (например: "/CRM/contracts/file.pdf")

        Returns:
            dict с информацией о загруженном файле
        """
        # Получаем ссылку для загрузки
        upload_url_response = requests.get(f"{self.base_url}/resources/upload", headers=self.headers, params={"path": yandex_path, "overwrite": "true"})

        if upload_url_response.status_code != 200:
            raise Exception(f"Ошибка получения ссылки: {upload_url_response.json()}")

        upload_url = upload_url_response.json().get("href")

        # Загружаем файл
        with open(local_path, "rb") as f:
            upload_response = requests.put(upload_url, files={"file": f})

        if upload_response.status_code not in [200, 201]:
            raise Exception(f"Ошибка загрузки файла: {upload_response.text}")

        # Получаем информацию о файле
        return self.get_file_info(yandex_path)

    def upload_file_from_bytes(self, file_bytes: bytes, yandex_path: str) -> dict:
        """
        Загрузка файла из байтов на Яндекс.Диск

        Args:
            file_bytes: Байты файла
            yandex_path: Путь на Яндекс.Диске

        Returns:
            dict с информацией о загруженном файле
        """
        # Автоматически создаём родительскую папку если не существует
        parent_dir = "/".join(yandex_path.split("/")[:-1])
        if parent_dir and parent_dir != "/":
            self.create_folder(parent_dir)

        # Получаем ссылку для загрузки
        upload_url_response = requests.get(
            f"{self.base_url}/resources/upload",
            headers=self.headers,
            params={"path": yandex_path, "overwrite": "true"},
            timeout=30,
        )

        if upload_url_response.status_code != 200:
            raise Exception(f"Ошибка получения ссылки: {upload_url_response.json()}")

        upload_url = upload_url_response.json().get("href")

        # Загружаем файл (таймаут 600с — файлы до 600 МБ на медленном канале)
        upload_response = requests.put(upload_url, data=file_bytes, timeout=600)

        if upload_response.status_code not in [200, 201]:
            raise Exception(f"Ошибка загрузки файла: {upload_response.text}")

        return self.get_file_info(yandex_path)

    def download_file(self, yandex_path: str, local_path: str) -> str:
        """
        Скачивание файла с Яндекс.Диска

        Args:
            yandex_path: Путь на Яндекс.Диске
            local_path: Куда сохранить файл локально

        Returns:
            Путь к скачанному файлу
        """
        # Получаем ссылку для скачивания
        download_url_response = requests.get(f"{self.base_url}/resources/download", headers=self.headers, params={"path": yandex_path})

        if download_url_response.status_code != 200:
            raise Exception(f"Ошибка получения ссылки: {download_url_response.json()}")

        download_url = download_url_response.json().get("href")

        # Скачиваем файл
        file_response = requests.get(download_url)

        if file_response.status_code != 200:
            raise Exception(f"Ошибка скачивания файла")

        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # Сохраняем файл
        with open(local_path, "wb") as f:
            f.write(file_response.content)

        return local_path

    def get_file_info(self, yandex_path: str) -> dict:
        """
        Получить информацию о файле

        Args:
            yandex_path: Путь на Яндекс.Диске

        Returns:
            dict с информацией о файле
        """
        response = requests.get(f"{self.base_url}/resources", headers=self.headers, params={"path": yandex_path})

        if response.status_code != 200:
            raise Exception(f"Ошибка получения информации: {response.json()}")

        return response.json()

    def create_folder(self, yandex_path: str) -> dict:
        """
        Создать папку на Яндекс.Диске (рекурсивно создаёт промежуточные)

        Args:
            yandex_path: Путь к папке

        Returns:
            dict с информацией о папке
        """
        response = requests.put(f"{self.base_url}/resources", headers=self.headers, params={"path": yandex_path})

        if response.status_code in [200, 201]:
            # Папка создана
            try:
                return self.get_file_info(yandex_path)
            except Exception:
                return {"path": yandex_path, "type": "dir"}
        elif response.status_code == 409:
            # 409 может быть: папка уже существует ИЛИ родительская не существует
            try:
                err_data = response.json()
                err_code = err_data.get("error", "")
            except Exception:
                err_code = ""

            if "DiskPathDoesntExistsError" in err_code or "DoesntExist" in err_code:
                # Родительская папка не существует — создаём рекурсивно
                parts = yandex_path.replace("disk:/", "").split("/")
                current = "disk:"
                for part in parts:
                    if not part:
                        continue
                    current = current + "/" + part
                    requests.put(f"{self.base_url}/resources", headers=self.headers, params={"path": current})
                try:
                    return self.get_file_info(yandex_path)
                except Exception:
                    return {"path": yandex_path, "type": "dir"}
            else:
                # Папка уже существует
                try:
                    return self.get_file_info(yandex_path)
                except Exception:
                    return {"path": yandex_path, "type": "dir"}
        else:
            raise Exception(f"Ошибка создания папки: {response.json()}")

    def copy_file(self, src_path: str, dst_path: str, overwrite: bool = False) -> dict:
        """Копировать файл на Яндекс.Диске (src → dst)."""
        response = requests.post(
            f"{self.base_url}/resources/copy",
            headers=self.headers,
            params={"from": src_path, "path": dst_path, "overwrite": str(overwrite).lower()},
        )
        if response.status_code in [200, 201, 202]:
            return {"status": "ok", "path": dst_path}
        raise Exception(f"Ошибка копирования: {response.text}")

    def delete_file(self, yandex_path: str, permanently: bool = True) -> dict:
        """
        Удалить файл с Яндекс.Диска

        Args:
            yandex_path: Путь к файлу
            permanently: Удалить навсегда (True) или в корзину (False)

        Returns:
            dict с результатом операции
        """
        response = requests.delete(f"{self.base_url}/resources", headers=self.headers, params={"path": yandex_path, "permanently": str(permanently).lower()})

        if response.status_code not in [200, 202, 204]:
            raise Exception(f"Ошибка удаления: {response.json()}")

        return {"status": "deleted", "path": yandex_path}

    def restore_from_trash(self, trash_path: str, name: str = None, overwrite: bool = False) -> dict:
        """Восстановить файл/папку из корзины Яндекс.Диска."""
        params = {"path": trash_path, "overwrite": str(overwrite).lower()}
        if name:
            params["name"] = name
        response = requests.put(
            "https://cloud-api.yandex.net/v1/disk/trash/resources/restore",
            headers=self.headers,
            params=params,
        )
        if response.status_code in (201, 202):
            return {"status": "restored", "path": trash_path}
        raise Exception(f"Ошибка восстановления из корзины: {response.text}")

    def file_exists(self, yandex_path: str) -> bool:
        """
        Проверить существование файла на Яндекс.Диске

        Args:
            yandex_path: Путь к файлу

        Returns:
            True если файл существует, False если нет

        Raises:
            Exception: если токен не настроен (нельзя определить существование)
        """
        if not self.token:
            raise Exception("Yandex Disk token not configured on server")

        response = requests.get(f"{self.base_url}/resources", headers=self.headers, params={"path": yandex_path, "fields": "type"}, timeout=10)
        if response.status_code == 401:
            raise Exception("Yandex Disk token is invalid or expired")
        return response.status_code == 200

    def get_public_link(self, yandex_path: str) -> str:
        """
        Получить публичную ссылку на файл

        Args:
            yandex_path: Путь к файлу

        Returns:
            Публичная ссылка
        """
        import time as _time

        # Публикуем файл
        response = requests.put(f"{self.base_url}/resources/publish", headers=self.headers, params={"path": yandex_path}, timeout=15)

        # 200 = опубликован, 409 = уже опубликован — оба OK
        if response.status_code not in [200, 409]:
            raise Exception(f"Ошибка публикации: {response.status_code} {response.text}")

        # Задержка для обработки на стороне ЯД
        _time.sleep(1.0)

        # Получаем информацию с публичной ссылкой
        file_info = self.get_file_info(yandex_path)
        public_url = file_info.get("public_url")

        # Retry если ссылка ещё не готова
        if not public_url:
            _time.sleep(2.0)
            file_info = self.get_file_info(yandex_path)
            public_url = file_info.get("public_url")

        return public_url or ""

    def list_files(self, yandex_path: str = "/", limit: int = 100) -> list:
        """
        Список файлов в папке

        Args:
            yandex_path: Путь к папке
            limit: Максимальное количество файлов

        Returns:
            Список файлов
        """
        response = requests.get(f"{self.base_url}/resources", headers=self.headers, params={"path": yandex_path, "limit": limit})

        if response.status_code != 200:
            raise Exception(f"Ошибка получения списка: {response.json()}")

        data = response.json()
        items = data.get("_embedded", {}).get("items", [])
        return items

    def get_disk_info(self) -> dict:
        """
        Информация о диске (свободное место, использование)

        Returns:
            dict с информацией о диске
        """
        response = requests.get(f"{self.base_url}", headers=self.headers)

        if response.status_code != 200:
            raise Exception(f"Ошибка получения информации о диске: {response.json()}")

        return response.json()


# Singleton instance
_yandex_disk_service = None


def get_yandex_disk_service() -> YandexDiskService:
    """Получить экземпляр сервиса Яндекс.Диска"""
    global _yandex_disk_service
    if _yandex_disk_service is None:
        _yandex_disk_service = YandexDiskService()
    return _yandex_disk_service

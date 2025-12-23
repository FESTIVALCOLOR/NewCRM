# -*- coding: utf-8 -*-
"""
Менеджер обновлений программы через Яндекс Диск
"""
import os
import sys
import json
import tempfile
import subprocess
import requests
from config import APP_VERSION, UPDATE_CHECK_URL, UPDATE_YANDEX_PUBLIC_KEY, UPDATE_CHECK_ENABLED


class UpdateManager:
    """Управление проверкой и установкой обновлений"""

    def __init__(self):
        self.current_version = APP_VERSION
        self.update_url = UPDATE_CHECK_URL
        self.public_key = UPDATE_YANDEX_PUBLIC_KEY

    def check_for_updates(self):
        """
        Проверка наличия новой версии на Яндекс Диске

        Returns:
            dict: {'available': bool, 'version': str, 'details': dict} или {'available': False, 'error': str}
        """
        if not UPDATE_CHECK_ENABLED:
            return {"available": False, "disabled": True}

        if not self.public_key:
            print("[UPDATE] Публичный ключ папки обновлений не настроен")
            return {"available": False, "error": "Публичный ключ не настроен"}

        try:
            # Получаем список файлов из публичной папки на Яндекс Диске
            version_data = self._fetch_version_json()

            if not version_data:
                return {"available": False, "error": "Не удалось получить данные о версиях"}

            latest_version = version_data.get("latest_version")

            if not latest_version:
                return {"available": False, "error": "Некорректный формат version.json"}

            # Сравниваем версии
            if self._compare_versions(latest_version, self.current_version) > 0:
                return {
                    "available": True,
                    "version": latest_version,
                    "details": version_data["versions"].get(latest_version, {})
                }

            return {"available": False}

        except Exception as e:
            print(f"[UPDATE] Ошибка проверки обновлений: {e}")
            return {"available": False, "error": str(e)}

    def _fetch_version_json(self):
        """Загрузка version.json из публичной папки на Яндекс Диске"""
        try:
            # Запрос к Яндекс Диску для получения содержимого публичной папки
            response = requests.get(
                self.update_url,
                params={"public_key": self.public_key},
                timeout=10
            )

            if response.status_code != 200:
                print(f"[UPDATE] Ошибка доступа к папке обновлений: {response.status_code}")
                return None

            data = response.json()

            # Ищем version.json в списке файлов
            items = data.get("_embedded", {}).get("items", [])
            version_file = None

            for item in items:
                if item.get("name") == "version.json":
                    version_file = item
                    break

            if not version_file:
                print("[UPDATE] Файл version.json не найден в папке обновлений")
                return None

            # Получаем ссылку на скачивание
            file_url = version_file.get("file")

            if not file_url:
                print("[UPDATE] Не удалось получить ссылку на version.json")
                return None

            # Загружаем и парсим version.json
            version_response = requests.get(file_url, timeout=10)

            if version_response.status_code != 200:
                print(f"[UPDATE] Ошибка загрузки version.json: {version_response.status_code}")
                return None

            return version_response.json()

        except Exception as e:
            print(f"[UPDATE] Ошибка при загрузке version.json: {e}")
            return None

    def _compare_versions(self, v1, v2):
        """
        Сравнение версий формата X.Y.Z

        Args:
            v1 (str): Первая версия
            v2 (str): Вторая версия

        Returns:
            int: 1 если v1 > v2, -1 если v1 < v2, 0 если равны
        """
        try:
            v1_parts = list(map(int, v1.split('.')))
            v2_parts = list(map(int, v2.split('.')))

            # Дополняем нулями до одинаковой длины
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))

            # Сравниваем по частям
            for i in range(max_len):
                if v1_parts[i] > v2_parts[i]:
                    return 1
                elif v1_parts[i] < v2_parts[i]:
                    return -1

            return 0

        except Exception as e:
            print(f"[UPDATE] Ошибка сравнения версий: {e}")
            return 0

    def download_update(self, version, progress_callback=None):
        """
        Загрузка обновления из публичной папки Яндекс Диска

        Args:
            version (str): Версия для загрузки
            progress_callback (callable): Функция для отображения прогресса (current, total)

        Returns:
            str: Путь к загруженному файлу или None при ошибке
        """
        try:
            # Получаем информацию о версии
            version_data = self._fetch_version_json()

            if not version_data:
                print("[UPDATE] Не удалось получить данные о версиях")
                return None

            version_info = version_data["versions"].get(version)

            if not version_info:
                print(f"[UPDATE] Информация о версии {version} не найдена")
                return None

            # Получаем ссылку на загрузку
            download_url = version_info.get("download_url")

            if not download_url:
                print(f"[UPDATE] Ссылка на загрузку версии {version} не найдена")
                return None

            # Путь для сохранения
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"InteriorStudio_{version}.exe")

            # Загрузка с прогрессом
            print(f"[UPDATE] Загрузка обновления версии {version}...")

            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

            print(f"[UPDATE] Обновление загружено: {temp_path}")
            return temp_path

        except Exception as e:
            print(f"[UPDATE] Ошибка загрузки обновления: {e}")
            return None

    def install_update(self, update_path):
        """
        Установка обновления (замена exe файла)

        Args:
            update_path (str): Путь к загруженному обновлению
        """
        try:
            # Получаем путь к текущему exe
            if getattr(sys, 'frozen', False):
                current_exe = sys.executable
            else:
                print("[UPDATE] Установка обновлений работает только для собранного exe")
                return False

            # Создаём batch скрипт для замены exe
            batch_script = f"""@echo off
echo Обновление Interior Studio CRM...
timeout /t 2 /nobreak > nul

echo Замена файла программы...
move /y "{update_path}" "{current_exe}"

if errorlevel 1 (
    echo Ошибка при обновлении!
    pause
    exit /b 1
)

echo Запуск обновлённой версии...
start "" "{current_exe}"

del "%~f0"
"""

            batch_path = os.path.join(tempfile.gettempdir(), "update_crm.bat")

            with open(batch_path, 'w', encoding='cp1251') as f:
                f.write(batch_script)

            print(f"[UPDATE] Запуск установки обновления...")

            # Запускаем batch и завершаем программу
            subprocess.Popen([batch_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)

            # Даём время на запуск батника
            import time
            time.sleep(0.5)

            # Завершаем текущую программу
            sys.exit(0)

        except Exception as e:
            print(f"[UPDATE] Ошибка установки обновления: {e}")
            return False

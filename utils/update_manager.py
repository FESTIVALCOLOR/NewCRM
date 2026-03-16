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
from config import APP_VERSION, UPDATE_CHECK_URL, UPDATE_YANDEX_PUBLIC_KEY, UPDATE_CHECK_ENABLED, API_BASE_URL


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

    def check_server_version(self):
        """
        Сверка версии клиента с сервером

        Returns:
            dict: {'match': bool, 'server_version': str, 'client_version': str}
                  или {'error': str} при ошибке
        """
        try:
            response = requests.get(f"{API_BASE_URL}/api/version", timeout=5)
            if response.status_code == 200:
                data = response.json()
                server_version = data.get("version", "")
                return {
                    "match": server_version == self.current_version,
                    "server_version": server_version,
                    "client_version": self.current_version
                }
            return {"error": f"Сервер вернул код {response.status_code}"}
        except Exception as e:
            print(f"[UPDATE] Ошибка сверки версии с сервером: {e}")
            return {"error": str(e)}

    def upload_update_to_yandex(self, exe_path, version, changelog="", progress_callback=None):
        """
        Загрузка обновления на Яндекс.Диск в папку CRM_UPDATES.
        Хранится только 1 (последняя) версия — старые EXE удаляются автоматически.
        Пользователь может обновиться с любой версии на последнюю (пропуск версий).
        """
        from utils.yandex_disk import YandexDiskManager

        try:
            yd = YandexDiskManager.get_instance()
            if not yd.token:
                raise Exception("Яндекс.Диск токен не настроен")

            from config import YANDEX_DISK_UPDATES
            updates_folder = YANDEX_DISK_UPDATES
            yd.create_folder(updates_folder)

            # Загружаем существующий version.json чтобы узнать старые файлы
            version_json_path = f"{updates_folder}/version.json"
            existing_data = self._download_version_json_from_disk(yd, version_json_path)

            # Удаляем старые EXE-файлы (оставляем только version.json)
            old_files = []
            if existing_data:
                for ver, info in existing_data.get("versions", {}).items():
                    old_file = info.get("file_name")
                    if old_file:
                        old_files.append(old_file)

            for old_file in old_files:
                old_path = f"{updates_folder}/{old_file}"
                try:
                    yd.delete_file(old_path)
                    print(f"[UPDATE] Удалён старый файл: {old_file}")
                except Exception:
                    print(f"[UPDATE] Не удалось удалить {old_file} (возможно уже удалён)")

            # Загружаем новый exe файл
            file_name = f"InteriorStudio_{version}.exe"
            yandex_path = f"{updates_folder}/{file_name}"

            print(f"[UPDATE] Загрузка {exe_path} → {yandex_path}")
            yd.upload_file(exe_path, yandex_path)

            # Формируем version.json — только 1 версия (последняя)
            file_size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            from datetime import date

            new_data = {
                "latest_version": version,
                "versions": {
                    version: {
                        "release_date": date.today().isoformat(),
                        "size_mb": f"{file_size_mb:.1f}",
                        "changelog": changelog or f"Обновление до версии {version}",
                        "file_name": file_name
                    }
                }
            }

            temp_json = os.path.join(tempfile.gettempdir(), "version.json")
            with open(temp_json, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)

            yd.upload_file(temp_json, version_json_path)
            os.remove(temp_json)

            print(f"[UPDATE] Обновление {version} загружено на Яндекс.Диск (старые версии удалены)")
            return True

        except Exception as e:
            print(f"[UPDATE] Ошибка загрузки обновления на Яндекс.Диск: {e}")
            raise

    def _download_version_json_from_disk(self, yd, yandex_path):
        """Загрузить и распарсить version.json с Яндекс.Диска (OAuth)"""
        try:
            temp_path = os.path.join(tempfile.gettempdir(), "version_existing.json")
            yd.download_file(yandex_path, temp_path)
            with open(temp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            os.remove(temp_path)
            return data
        except Exception:
            return None

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
        Загрузка обновления из публичной папки Яндекс Диска.
        Находит EXE-файл по имени из version.json и скачивает через публичный API.
        Поддерживает пропуск версий — всегда скачивается latest.
        """
        try:
            version_data = self._fetch_version_json()
            if not version_data:
                print("[UPDATE] Не удалось получить данные о версиях")
                return None

            version_info = version_data["versions"].get(version)
            if not version_info:
                print(f"[UPDATE] Информация о версии {version} не найдена")
                return None

            file_name = version_info.get("file_name", f"InteriorStudio_{version}.exe")

            # Ищем файл в публичной папке Яндекс Диска
            download_url = self._get_public_file_url(file_name)
            if not download_url:
                print(f"[UPDATE] Файл {file_name} не найден в публичной папке")
                return None

            # Путь для сохранения
            temp_path = os.path.join(tempfile.gettempdir(), file_name)

            print(f"[UPDATE] Загрузка обновления версии {version}...")

            response = requests.get(download_url, stream=True, timeout=300)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            # Если размер из version.json известен, используем как fallback
            if total_size == 0:
                try:
                    size_mb_str = version_info.get("size_mb", "0")
                    total_size = int(float(size_mb_str) * 1024 * 1024)
                except (ValueError, TypeError):
                    pass

            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

            # Проверка целостности: размер файла
            actual_size = os.path.getsize(temp_path)
            if actual_size < 1024 * 1024:  # EXE меньше 1 МБ — явно повреждён
                os.remove(temp_path)
                print(f"[UPDATE] Файл слишком маленький ({actual_size} байт), загрузка повреждена")
                return None

            print(f"[UPDATE] Обновление загружено: {temp_path} ({actual_size / 1024 / 1024:.1f} МБ)")
            return temp_path

        except Exception as e:
            print(f"[UPDATE] Ошибка загрузки обновления: {e}")
            # Очистка частично загруженного файла
            try:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
            except OSError:
                pass
            return None

    def _get_public_file_url(self, file_name):
        """Получить прямую ссылку на файл из публичной папки Яндекс Диска"""
        try:
            response = requests.get(
                self.update_url,
                params={"public_key": self.public_key},
                timeout=10
            )
            if response.status_code != 200:
                return None

            items = response.json().get("_embedded", {}).get("items", [])
            for item in items:
                if item.get("name") == file_name:
                    return item.get("file")
            return None
        except Exception:
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
            subprocess.Popen([batch_path], creationflags=subprocess.CREATE_NEW_CONSOLE)

            # Даём время на запуск батника
            import time
            time.sleep(0.5)

            # Завершаем текущую программу
            sys.exit(0)

        except Exception as e:
            print(f"[UPDATE] Ошибка установки обновления: {e}")
            return False

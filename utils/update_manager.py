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

            # Удаляем старые файлы (оставляем только version.json)
            old_files = []
            if existing_data:
                for ver, info in existing_data.get("versions", {}).items():
                    for key in ("file_name", "file_name_mac"):
                        old_file = info.get(key)
                        if old_file:
                            old_files.append(old_file)

            for old_file in old_files:
                old_path = f"{updates_folder}/{old_file}"
                try:
                    yd.delete_file(old_path)
                    print(f"[UPDATE] Удалён старый файл: {old_file}")
                except Exception:
                    print(f"[UPDATE] Не удалось удалить {old_file} (возможно уже удалён)")

            # Определяем платформу загружаемого файла
            is_mac = exe_path.lower().endswith(('_mac', '_mac.zip', '_macos'))
            if is_mac:
                file_name = f"InteriorStudio_{version}_mac"
            else:
                file_name = f"InteriorStudio_{version}.exe"

            yandex_path = f"{updates_folder}/{file_name}"

            print(f"[UPDATE] Загрузка {exe_path} → {yandex_path}")
            yd.upload_file(exe_path, yandex_path)

            # Формируем version.json — только 1 версия (последняя)
            # Сохраняем файлы обеих платформ (если есть)
            file_size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            from datetime import date

            # Берём существующие данные о другой платформе
            existing_version_info = {}
            if existing_data:
                ev = existing_data.get("versions", {}).get(version, {})
                if ev:
                    existing_version_info = ev

            version_entry = {
                "release_date": date.today().isoformat(),
                "size_mb": f"{file_size_mb:.1f}",
                "changelog": changelog or f"Обновление до версии {version}",
            }

            if is_mac:
                version_entry["file_name_mac"] = file_name
                # Сохранить Windows файл если был
                win_file = existing_version_info.get("file_name")
                if win_file:
                    version_entry["file_name"] = win_file
            else:
                version_entry["file_name"] = file_name
                # Сохранить macOS файл если был
                mac_file = existing_version_info.get("file_name_mac")
                if mac_file:
                    version_entry["file_name_mac"] = mac_file

            new_data = {
                "latest_version": version,
                "versions": {
                    version: version_entry
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
        Автоматически выбирает файл для текущей платформы (Windows/macOS).
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

            # Выбираем файл по платформе
            if sys.platform == 'darwin':
                file_name = version_info.get("file_name_mac")
                if not file_name:
                    print(f"[UPDATE] Версия {version} недоступна для macOS")
                    return None
            else:
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

            # Windows: удалить Zone.Identifier (метка "скачан из интернета").
            # macOS: установить разрешение на выполнение.
            if sys.platform == 'win32':
                try:
                    os.remove(temp_path + ':Zone.Identifier')
                    print("[UPDATE] Zone.Identifier удалён")
                except OSError:
                    pass
            elif sys.platform == 'darwin':
                try:
                    os.chmod(temp_path, 0o755)
                    # Снять карантин macOS
                    import subprocess as _sp
                    _sp.run(['xattr', '-d', 'com.apple.quarantine', temp_path],
                            capture_output=True, timeout=5)
                    print("[UPDATE] macOS: chmod +x, карантин снят")
                except Exception:
                    pass

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
        Установка обновления (замена исполняемого файла).
        Windows: cmd.exe batch-скрипт.
        macOS: bash shell-скрипт.

        Алгоритм:
        1. Ждёт завершения процесса по PID
        2. Retry: rename старый → copy новый → delete старый
        3. Показывает результат, пользователь запускает вручную
        """
        try:
            if getattr(sys, 'frozen', False):
                current_exe = sys.executable
            else:
                print("[UPDATE] Установка обновлений работает только для собранного exe")
                return False

            if sys.platform == 'darwin':
                return self._install_update_macos(update_path, current_exe)
            else:
                return self._install_update_windows(update_path, current_exe)

        except Exception as e:
            print(f"[UPDATE] Ошибка установки обновления: {e}")
            return False

    def _install_update_macos(self, update_path, current_exe):
        """Установка обновления на macOS через bash-скрипт"""
        pid = os.getpid()
        src = update_path
        dst = current_exe

        # На macOS нет проблем с блокировкой файлов — простой shell-скрипт
        script_lines = [
            '#!/bin/bash',
            '',
            'echo ""',
            'echo "  Interior Studio CRM"',
            'echo "  ============================="',
            'echo ""',
            f'echo "  Откуда: {src}"',
            f'echo "  Куда:   {dst}"',
            'echo ""',
            'echo "  Ожидание закрытия программы..."',
            '',
            f'while kill -0 {pid} 2>/dev/null; do sleep 1; done',
            'sleep 2',
            '',
            'echo "  Программа закрыта."',
            '',
            # Проверяем source
            f'if [ ! -f "{src}" ]; then',
            f'    echo "  ОШИБКА: Файл обновления не найден: {src}"',
            '    read -p "  Нажмите Enter..."',
            '    exit 1',
            'fi',
            '',
            f'SRC_SZ=$(stat -f%z "{src}" 2>/dev/null || stat -c%s "{src}" 2>/dev/null)',
            f'DST_SZ=$(stat -f%z "{dst}" 2>/dev/null || stat -c%s "{dst}" 2>/dev/null)',
            'echo "  Новый файл: $SRC_SZ байт"',
            'echo "  Старый файл: $DST_SZ байт"',
            'echo ""',
            'echo "  Замена файла..."',
            '',
            # Бэкап и замена
            f'mv "{dst}" "{dst}.old" 2>/dev/null',
            f'cp "{src}" "{dst}"',
            'if [ $? -ne 0 ]; then',
            f'    echo "  ОШИБКА: Не удалось скопировать файл"',
            f'    mv "{dst}.old" "{dst}" 2>/dev/null',
            '    read -p "  Нажмите Enter..."',
            '    exit 1',
            'fi',
            '',
            f'chmod +x "{dst}"',
            '',
            # Верификация
            f'NEW_SZ=$(stat -f%z "{dst}" 2>/dev/null || stat -c%s "{dst}" 2>/dev/null)',
            'if [ "$SRC_SZ" != "$NEW_SZ" ]; then',
            '    echo "  ОШИБКА: Размеры не совпадают"',
            f'    mv "{dst}.old" "{dst}" 2>/dev/null',
            '    read -p "  Нажмите Enter..."',
            '    exit 1',
            'fi',
            '',
            # Очистка
            f'rm -f "{dst}.old" 2>/dev/null',
            f'rm -f "{src}" 2>/dev/null',
            '',
            'echo ""',
            'echo "  ======================================="',
            'echo "  Обновление установлено успешно!"',
            'echo "  Размер проверен: $NEW_SZ байт"',
            'echo "  ======================================="',
            'echo ""',
            'echo "  Запуск программы..."',
            f'open "{dst}" 2>/dev/null || "{dst}" &',
            'sleep 2',
            '',
            # Самоудаление скрипта
            'rm -f "$0" 2>/dev/null',
        ]

        script_content = '\n'.join(script_lines) + '\n'
        script_path = os.path.join(tempfile.gettempdir(), "update_crm.sh")

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        os.chmod(script_path, 0o755)

        print(f"[UPDATE] macOS: запуск установки: PID={pid}, {src} -> {dst}")

        # Открываем Terminal.app с нашим скриптом
        subprocess.Popen([
            'osascript', '-e',
            f'tell application "Terminal" to do script "{script_path}"'
        ])

        import time
        time.sleep(0.5)
        os._exit(0)

    def _install_update_windows(self, update_path, current_exe):
        """Установка обновления на Windows через cmd.exe batch-скрипт"""
        pid = os.getpid()
        src = update_path
        dst = current_exe
        exe_name = os.path.basename(current_exe)
        exe_name_old = exe_name + '.old'
        exe_dir = os.path.dirname(current_exe)

        # Стратегия путей для batch:
        # - Короткие (8.3) пути для СУЩЕСТВУЮЩИХ файлов/папок (всегда ASCII)
        # - Для copy destination: короткий КАТАЛОГ + длинное ИМЯ файла
        #   (чтобы файл создался как InteriorStudio.exe, а не INTERI~1.EXE)
        try:
            import ctypes
            def _short(p):
                buf = ctypes.create_unicode_buffer(300)
                r = ctypes.windll.kernel32.GetShortPathNameW(p, buf, 300)
                return buf.value if r else p
            src_s = _short(src)           # источник (файл существует)
            dst_s = _short(dst)           # текущий EXE (существует, для ren/del)
            dir_s = _short(exe_dir)       # каталог EXE (существует)
        except Exception:
            src_s, dst_s, dir_s = src, dst, exe_dir

        # Путь для copy: короткий каталог + полное имя файла
        dst_copy = dir_s + '\\' + exe_name
        dst_old_path = dir_s + '\\' + exe_name_old

        batch_lines = [
            '@echo off',
            'title Interior Studio CRM',
            'echo.',
            'echo  Interior Studio CRM',
            'echo  =============================',
            'echo.',
            f'echo  Откуда: {src_s}',
            f'echo  Куда:   {dst_copy}',
            'echo.',
            'echo  Ожидание закрытия программы...',
            '',
            f':WAIT_LOOP',
            f'tasklist /FI "PID eq {pid}" 2>NUL | find /I "{pid}" >NUL',
            'if %ERRORLEVEL%==0 (',
            '    ping -n 2 127.0.0.1 >NUL',
            '    goto WAIT_LOOP',
            ')',
            '',
            'echo  Программа закрыта.',
            'ping -n 3 127.0.0.1 >NUL',
            '',
            # Проверяем что source существует
            f'if not exist "{src_s}" (',
            '    echo  ОШИБКА: Файл обновления не найден!',
            f'    echo  Путь: {src_s}',
            '    pause',
            '    goto CLEANUP',
            ')',
            '',
            # Показываем размеры
            f'for %%A in ("{src_s}") do echo  Новый файл: %%~zA байт',
            f'for %%A in ("{dst_s}") do echo  Старый файл: %%~zA байт',
            'echo.',
            'echo  Замена файла...',
            '',
            'set ATTEMPT=0',
            '',
            ':RETRY',
            'set /A ATTEMPT+=1',
            'if %ATTEMPT% GTR 10 goto FAIL',
            '',
            # Удалить старый .old если есть
            f'if exist "{dst_old_path}" del /F /Q "{dst_old_path}" 2>NUL',
            # Переименовать текущий EXE в .old (ren работает с существующим файлом)
            f'if exist "{dst_s}" ren "{dst_s}" "{exe_name_old}" 2>NUL',
            '',
            # Копировать новый EXE: short_dir + long_name = правильное имя
            f'copy /Y /B "{src_s}" "{dst_copy}"',
            'if %ERRORLEVEL% NEQ 0 (',
            '    echo  Попытка %ATTEMPT%/10: не удалось скопировать, ожидание...',
            '    ping -n 3 127.0.0.1 >NUL',
            '    goto RETRY',
            ')',
            '',
            # Верификация: проверить что файл создан и размер совпадает
            f'if not exist "{dst_copy}" (',
            '    echo  Попытка %ATTEMPT%/10: файл не создан, повтор...',
            '    ping -n 3 127.0.0.1 >NUL',
            '    goto RETRY',
            ')',
            '',
            # Сравнить размеры
            f'for %%A in ("{src_s}") do set SRC_SZ=%%~zA',
            f'for %%A in ("{dst_copy}") do set DST_SZ=%%~zA',
            'if NOT "%SRC_SZ%"=="%DST_SZ%" (',
            '    echo  ВНИМАНИЕ: Размеры не совпадают src=%SRC_SZ% dst=%DST_SZ%',
            '    echo  Попытка %ATTEMPT%/10: повтор...',
            f'    del /F /Q "{dst_copy}" 2>NUL',
            f'    if exist "{dst_old_path}" ren "{dst_old_path}" "{exe_name}" 2>NUL',
            '    ping -n 3 127.0.0.1 >NUL',
            '    goto RETRY',
            ')',
            '',
            'goto DONE',
            '',
            ':DONE',
            f'if exist "{dst_old_path}" del /F /Q "{dst_old_path}" 2>NUL',
            f'if exist "{src_s}" del /F /Q "{src_s}" 2>NUL',
            'echo.',
            'echo  =======================================',
            'echo  Обновление установлено успешно!',
            'echo  Размер проверен: %DST_SZ% байт',
            f'echo  Файл: {dst_copy}',
            'echo  =======================================',
            'echo.',
            'echo  Запуск программы...',
            f'start "" "{dst_copy}"',
            'ping -n 3 127.0.0.1 >NUL',
            'goto CLEANUP',
            '',
            ':FAIL',
            ':: Rollback',
            f'if exist "{dst_old_path}" if not exist "{dst_copy}" ren "{dst_old_path}" "{exe_name}" 2>NUL',
            'echo.',
            'echo  ОШИБКА: Не удалось заменить файл после 10 попыток.',
            'echo  Убедитесь что программа полностью закрыта.',
            'echo.',
            'pause',
            '',
            ':CLEANUP',
            'del /F /Q "%~f0" 2>NUL',
        ]

        batch_script = '\r\n'.join(batch_lines) + '\r\n'
        batch_path = os.path.join(tempfile.gettempdir(), "update_crm.cmd")

        # cp866 — OEM кодировка для cmd.exe на русской Windows.
        # Пути все ASCII (8.3), русский текст в echo корректно отображается.
        with open(batch_path, 'w', encoding='cp866') as f:
            f.write(batch_script)

        print(f"[UPDATE] Запуск установки: PID={pid}")
        print(f"[UPDATE]   Source: {src} -> {src_s}")
        print(f"[UPDATE]   Target: {dst} -> {dst_copy}")

        subprocess.Popen(
            ['cmd.exe', '/c', batch_path],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        import time
        time.sleep(0.5)

        os._exit(0)

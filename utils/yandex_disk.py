import requests
import json
import urllib.parse
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class YandexDiskManager:
    def __init__(self, token=None):
        self.token = token  # OAuth токен
        self.base_url = 'https://cloud-api.yandex.net/v1/disk'
        # Корневая папка для архива проектов
        self.archive_root = 'disk:/АРХИВ ПРОЕКТОВ'

        # Создаем сессию с повторными попытками
        self.session = requests.Session()

        # Настраиваем стратегию повторных попыток
        retry_strategy = Retry(
            total=3,  # Максимум 3 попытки
            backoff_factor=1,  # Задержка между попытками: 1, 2, 4 секунды
            status_forcelist=[429, 500, 502, 503, 504],  # Повторять при этих HTTP кодах
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
    
    def upload_file(self, local_path, yandex_path):
        """Загрузка файла на Яндекс.Диск"""
        # Получаем ссылку для загрузки
        url = f'{self.base_url}/resources/upload'
        params = {'path': yandex_path, 'overwrite': 'true'}
        headers = {'Authorization': f'OAuth {self.token}'}

        response = self.session.get(url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            raise Exception(f"Ошибка получения ссылки для загрузки: {response.status_code} - {response.text}")

        response_data = response.json()
        if 'href' not in response_data:
            raise Exception(f"В ответе API нет поля 'href': {response_data}")

        upload_url = response_data['href']

        # ИСПРАВЛЕНИЕ 25.01.2026: Увеличен таймаут до 600 сек для больших файлов (150-200 МБ)
        # Используем data= вместо files= для streaming upload (меньше памяти)
        with open(local_path, 'rb') as f:
            upload_response = self.session.put(upload_url, data=f, timeout=600)

        if upload_response.status_code not in [200, 201, 202]:
            raise Exception(f"Ошибка загрузки файла: {upload_response.status_code}")

    def download_file(self, yandex_path, local_path):
        """Скачивание файла с Яндекс.Диска"""
        url = f'{self.base_url}/resources/download'
        params = {'path': yandex_path}
        headers = {'Authorization': f'OAuth {self.token}'}

        response = self.session.get(url, params=params, headers=headers, timeout=10)
        download_url = response.json()['href']

        # Скачиваем файл
        file_response = self.session.get(download_url, timeout=30)
        with open(local_path, 'wb') as f:
            f.write(file_response.content)

    def get_public_link(self, yandex_path):
        """Получение публичной ссылки"""
        headers = {'Authorization': f'OAuth {self.token}'}

        try:
            # Шаг 1: Публикуем файл
            publish_url = f'{self.base_url}/resources/publish'
            publish_params = {'path': yandex_path}

            publish_response = self.session.put(publish_url, params=publish_params, headers=headers, timeout=10)
            print(f"[DEBUG] Публикация: {publish_response.status_code}")

            # Успешная публикация или уже опубликован
            if publish_response.status_code in [200, 201, 409]:
                # Шаг 2: Получаем метаданные с public_url
                meta_url = f'{self.base_url}/resources'
                meta_params = {'path': yandex_path, 'fields': 'public_url,public_key'}

                meta_response = self.session.get(meta_url, params=meta_params, headers=headers, timeout=10)
                print(f"[DEBUG] Метаданные: {meta_response.status_code}")

                if meta_response.status_code == 200:
                    meta_data = meta_response.json()
                    print(f"[DEBUG] Данные: {meta_data}")

                    # Извлекаем public_url
                    public_url = meta_data.get('public_url', '')

                    if public_url:
                        print(f"[OK] Получена публичная ссылка: {public_url}")
                        return public_url

                    # Если public_url нет, пробуем сформировать из public_key
                    public_key = meta_data.get('public_key', '')
                    if public_key:
                        public_url = f"https://disk.yandex.ru/i/{public_key}"
                        print(f"[OK] Сформирована ссылка из public_key: {public_url}")
                        return public_url

                else:
                    print(f"[ERROR] Ошибка получения метаданных: {meta_response.text}")

            else:
                print(f"[ERROR] Ошибка публикации: {publish_response.status_code} - {publish_response.text}")

            return ''

        except Exception as e:
            print(f"[ERROR] Ошибка получения публичной ссылки: {e}")
            import traceback
            traceback.print_exc()
            return ''

    def upload_file_to_contract_folder(self, local_file_path, contract_folder_path, subfolder_name, file_name=None, progress_callback=None):
        """Загрузка файла в подпапку договора на Яндекс.Диске

        Args:
            local_file_path: Локальный путь к файлу
            contract_folder_path: Путь к папке договора на Яндекс.Диске
            subfolder_name: Название подпапки (Документы, Анкета и т.д.)
            file_name: Имя файла (опционально, если None - берется из local_file_path)
            progress_callback: функция обратного вызова для обновления прогресса (step, file_name, phase)

        Returns:
            Словарь с данными {'public_link': str, 'yandex_path': str, 'file_name': str} или None в случае ошибки
        """
        if not self.token:
            print("[ERROR] Токен не установлен")
            return None

        try:
            import os

            # Определяем имя файла
            if file_name is None:
                file_name = os.path.basename(local_file_path)

            # Обновляем прогресс: подготовка
            if progress_callback:
                progress_callback(0, file_name, 'preparing')

            # Создаем подпапку
            subfolder_path = f"{contract_folder_path}/{subfolder_name}"
            self.create_folder(subfolder_path)
            time.sleep(0.2)

            # Формируем полный путь к файлу на Яндекс.Диске
            yandex_file_path = f"{subfolder_path}/{file_name}"

            # Обновляем прогресс: загрузка
            if progress_callback:
                progress_callback(1, file_name, 'uploading')

            # Загружаем файл
            print(f"[INFO] Загрузка файла {file_name} на Яндекс.Диск...")
            self.upload_file(local_file_path, yandex_file_path)

            # Обновляем прогресс: получение ссылки
            if progress_callback:
                progress_callback(2, file_name, 'finalizing')

            # Получаем публичную ссылку
            public_link = self.get_public_link(yandex_file_path)

            if public_link:
                print(f"[OK] Файл загружен: {yandex_file_path}")
                return {
                    'public_link': public_link,
                    'yandex_path': yandex_file_path,
                    'file_name': file_name
                }
            else:
                print(f"[WARN] Файл загружен, но не удалось получить публичную ссылку")
                return {
                    'public_link': yandex_file_path,
                    'yandex_path': yandex_file_path,
                    'file_name': file_name
                }

        except Exception as e:
            print(f"[ERROR] Ошибка загрузки файла: {e}")
            return None

    def create_folder(self, folder_path):
        """Создание папки на Яндекс.Диске"""
        if not self.token:
            print("[ERROR] Токен не установлен")
            return False

        url = f'{self.base_url}/resources'
        params = {'path': folder_path}
        headers = {'Authorization': f'OAuth {self.token}'}

        try:
            response = self.session.put(url, params=params, headers=headers, timeout=10)
            if response.status_code == 201:
                print(f"[OK] Папка создана: {folder_path}")
                return True
            elif response.status_code == 409:
                print(f"[INFO] Папка уже существует: {folder_path}")
                return True
            else:
                print(f"[ERROR] Ошибка создания папки {folder_path}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[ERROR] Исключение при создании папки: {e}")
            return False

    def move_folder(self, from_path, to_path):
        """Перемещение папки на Яндекс.Диске"""
        if not self.token:
            print("[ERROR] Токен не установлен")
            return False

        url = f'{self.base_url}/resources/move'
        params = {
            'from': from_path,
            'path': to_path,
            'overwrite': 'false'
        }
        headers = {'Authorization': f'OAuth {self.token}'}

        try:
            response = self.session.post(url, params=params, headers=headers, timeout=10)
            if response.status_code in [201, 202]:
                print(f"[OK] Папка перемещена: {from_path} -> {to_path}")
                return True
            else:
                print(f"[ERROR] Ошибка перемещения папки: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[ERROR] Исключение при перемещении папки: {e}")
            return False

    def delete_folder(self, folder_path):
        """Удаление папки с Яндекс.Диска"""
        if not self.token:
            print("[ERROR] Токен не установлен")
            return False

        url = f'{self.base_url}/resources'
        params = {'path': folder_path, 'permanently': 'true'}
        headers = {'Authorization': f'OAuth {self.token}'}

        try:
            response = self.session.delete(url, params=params, headers=headers, timeout=10)
            if response.status_code in [202, 204]:
                print(f"[OK] Папка удалена: {folder_path}")
                return True
            elif response.status_code == 404:
                print(f"[INFO] Папка не найдена (уже удалена?): {folder_path}")
                return True
            else:
                print(f"[ERROR] Ошибка удаления папки: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[ERROR] Исключение при удалении папки: {e}")
            return False

    def file_exists(self, file_path):
        """Проверка существования файла на Яндекс.Диске"""
        if not self.token:
            print("[ERROR] Токен не установлен")
            return False

        url = f'{self.base_url}/resources'
        params = {'path': file_path}
        headers = {'Authorization': f'OAuth {self.token}'}

        try:
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                return False
            else:
                print(f"[WARN] Неожиданный ответ при проверке файла: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Исключение при проверке файла: {e}")
            return False

    def delete_file(self, file_path):
        """Удаление файла с Яндекс.Диска"""
        if not self.token:
            print("[ERROR] Токен не установлен")
            return False

        url = f'{self.base_url}/resources'
        params = {'path': file_path, 'permanently': 'true'}
        headers = {'Authorization': f'OAuth {self.token}'}

        try:
            response = self.session.delete(url, params=params, headers=headers, timeout=10)
            if response.status_code in [202, 204]:
                print(f"[OK] Файл удален: {file_path}")
                return True
            elif response.status_code == 404:
                print(f"[INFO] Файл не найден (уже удален?): {file_path}")
                return True
            else:
                print(f"[ERROR] Ошибка удаления файла: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[ERROR] Исключение при удалении файла: {e}")
            return False

    def folder_exists(self, folder_path):
        """Проверка существования папки"""
        if not self.token:
            return False

        url = f'{self.base_url}/resources'
        params = {'path': folder_path}
        headers = {'Authorization': f'OAuth {self.token}'}

        try:
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            return response.status_code == 200
        except:
            return False

    def get_folder_contents(self, folder_path):
        """Получение списка содержимого папки"""
        if not self.token:
            return []

        url = f'{self.base_url}/resources'
        params = {'path': folder_path, 'limit': 1000}
        headers = {'Authorization': f'OAuth {self.token}'}

        try:
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('_embedded', {}).get('items', [])
            return []
        except Exception as e:
            print(f"[ERROR] Ошибка получения содержимого папки: {e}")
            return []

    def copy_file(self, from_path, to_path):
        """Копирование файла на Яндекс.Диске"""
        if not self.token:
            return False

        url = f'{self.base_url}/resources/copy'
        params = {
            'from': from_path,
            'path': to_path,
            'overwrite': 'false'
        }
        headers = {'Authorization': f'OAuth {self.token}'}

        try:
            response = self.session.post(url, params=params, headers=headers, timeout=10)
            if response.status_code in [201, 202]:
                return True
            else:
                print(f"[WARN] Ошибка копирования файла: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Исключение при копировании файла: {e}")
            return False

    def copy_folder_contents(self, from_folder, to_folder):
        """Рекурсивное копирование содержимого папки"""
        if not self.token:
            return False

        try:
            items = self.get_folder_contents(from_folder)

            if not items:
                print(f"[INFO] Папка пуста или не найдена: {from_folder}")
                return True

            copied_count = 0
            for item in items:
                item_name = item.get('name')
                item_type = item.get('type')
                from_path = item.get('path')

                if not item_name or not from_path:
                    continue

                to_path = f"{to_folder}/{item_name}"

                if item_type == 'dir':
                    # Создаем подпапку
                    self.create_folder(to_path)
                    time.sleep(0.2)
                    # Рекурсивно копируем содержимое
                    self.copy_folder_contents(from_path, to_path)
                else:
                    # Копируем файл
                    if self.copy_file(from_path, to_path):
                        copied_count += 1
                        print(f"[OK] Скопирован файл: {item_name}")
                    time.sleep(0.2)

            print(f"[OK] Скопировано файлов: {copied_count}")
            return True

        except Exception as e:
            print(f"[ERROR] Ошибка копирования содержимого папки: {e}")
            return False

    def build_contract_folder_path(self, agent_type, project_type, city, address, area, status=None):
        """Формирование пути к папке договора

        Args:
            agent_type: Тип агента (ФЕСТИВАЛЬ, ПЕТРОВИЧ)
            project_type: Тип проекта (Индивидуальный, Шаблонный)
            city: Город (СПБ, МСК, ВН)
            address: Адрес
            area: Площадь
            status: Статус проекта (для определения "Авторские надзоры")

        Returns:
            Полный путь к папке договора
        """
        # Определяем тип проекта для структуры папок
        if status == 'АВТОРСКИЙ НАДЗОР':
            project_folder = 'Авторские надзоры'
        elif project_type == 'Индивидуальный':
            project_folder = 'Индивидуальные'
        elif project_type == 'Шаблонный':
            project_folder = 'Шаблонные'
        else:
            project_folder = project_type

        # Формируем название папки проекта
        # Очищаем адрес от лишних символов
        clean_address = address.replace('/', '-').replace('\\', '-')
        folder_name = f"{city}-{clean_address}-{area}м2"

        # Полный путь
        full_path = f"{self.archive_root}/{agent_type}/{project_folder}/{city}/{folder_name}"
        return full_path

    def create_contract_folder_structure(self, agent_type, project_type, city, address, area, status=None):
        """Создание полной структуры папок для договора

        Returns:
            Путь к созданной папке или None в случае ошибки
        """
        if not self.token:
            print("[ERROR] Токен не установлен")
            return None

        # Определяем тип проекта для структуры папок
        if status == 'АВТОРСКИЙ НАДЗОР':
            project_folder = 'Авторские надзоры'
        elif project_type == 'Индивидуальный':
            project_folder = 'Индивидуальные'
        elif project_type == 'Шаблонный':
            project_folder = 'Шаблонные'
        else:
            project_folder = project_type

        # Создаем структуру папок уровень за уровнем с небольшими задержками
        # Уровень 1: Тип агента
        level1 = f"{self.archive_root}/{agent_type}"
        self.create_folder(level1)
        time.sleep(0.3)  # Небольшая задержка между запросами

        # Уровень 2: Тип проекта
        level2 = f"{level1}/{project_folder}"
        self.create_folder(level2)
        time.sleep(0.3)

        # Уровень 3: Город
        level3 = f"{level2}/{city}"
        self.create_folder(level3)
        time.sleep(0.3)

        # Уровень 4: Папка проекта
        clean_address = address.replace('/', '-').replace('\\', '-')
        folder_name = f"{city}-{clean_address}-{area}м2"
        level4 = f"{level3}/{folder_name}"

        if self.create_folder(level4):
            return level4
        else:
            return None

    def create_stage_folders(self, contract_folder_path):
        """Создание структуры папок для стадий проекта

        Args:
            contract_folder_path: путь к папке договора на Яндекс.Диске

        Returns:
            dict с путями к созданным папкам стадий
        """
        if not self.token:
            print("[ERROR] Токен не установлен")
            return {}

        # Убираем префикс disk: если он есть
        if contract_folder_path.startswith('disk:'):
            contract_folder_path = contract_folder_path[5:]

        stage_folders = {
            'measurement': f"{contract_folder_path}/Замер",
            'stage1': f"{contract_folder_path}/1 стадия - Планировочное решение",
            'stage2_concept': f"{contract_folder_path}/2 стадия - Концепция дизайна/Концепция-коллажи",
            'stage2_3d': f"{contract_folder_path}/2 стадия - Концепция дизайна/3D визуализация",
            'stage3': f"{contract_folder_path}/3 стадия - Чертежный проект"
        }

        # Создаем родительскую папку для 2 стадии
        stage2_parent = f"{contract_folder_path}/2 стадия - Концепция дизайна"
        self.create_folder(stage2_parent)
        time.sleep(0.2)

        # Создаем все папки стадий
        for stage_name, folder_path in stage_folders.items():
            self.create_folder(folder_path)
            time.sleep(0.2)

        print(f"[OK] Созданы папки стадий для договора")
        return stage_folders

    def upload_stage_files(self, local_files, contract_folder_path, stage, variation=None, progress_callback=None):
        """Загрузка множественных файлов для стадии

        Args:
            local_files: список путей к локальным файлам
            contract_folder_path: путь к папке договора
            stage: идентификатор стадии ('measurement', 'stage1', 'stage2_concept', 'stage2_3d', 'stage3')
            variation: номер вариации (опционально, для stage2_concept и stage2_3d)
            progress_callback: функция обратного вызова для обновления прогресса (current, total, file_name)

        Returns:
            list of dict с данными загруженных файлов
        """
        if not self.token:
            print("[ERROR] Токен не установлен")
            return []

        try:
            import os

            # Получаем путь к папке стадии (с учетом вариации)
            stage_folder = self.get_stage_folder_path(contract_folder_path, stage, variation=variation)

            if not stage_folder:
                print(f"[ERROR] Неизвестная стадия: {stage}")
                return []

            # Создаем все родительские папки и саму папку стадии
            # Для stage2_concept и stage2_3d нужно создать родительскую папку "2 стадия"
            if stage in ['stage2_concept', 'stage2_3d']:
                # Убираем префикс disk: если он есть
                clean_contract_folder = contract_folder_path
                if clean_contract_folder.startswith('disk:'):
                    clean_contract_folder = clean_contract_folder[5:]

                parent_folder = f"{clean_contract_folder}/2 стадия - Концепция дизайна"
                print(f"[INFO] Создание родительской папки: {parent_folder}")
                self.create_folder(parent_folder)
                time.sleep(0.2)

                # Создаем папку подсекции (Концепция-коллажи или 3D визуализация)
                subsection_folder = self.get_stage_folder_path(contract_folder_path, stage, variation=None)
                if subsection_folder:
                    print(f"[INFO] Создание папки подсекции: {subsection_folder}")
                    self.create_folder(subsection_folder)
                    time.sleep(0.2)

            print(f"[INFO] Создание папки стадии: {stage_folder}")
            self.create_folder(stage_folder)
            time.sleep(0.2)

            uploaded_files = []
            total_files = len(local_files)

            for index, local_file in enumerate(local_files):
                try:
                    file_name = os.path.basename(local_file)
                    yandex_path = f"{stage_folder}/{file_name}"

                    print(f"[INFO] Загрузка {file_name}...")

                    # Вызываем callback для обновления прогресса (загрузка на Яндекс.Диск)
                    if progress_callback:
                        progress_callback(index, total_files, file_name, 'uploading')

                    # Загружаем файл
                    self.upload_file(local_file, yandex_path)
                    time.sleep(0.3)

                    # Получаем публичную ссылку
                    public_link = self.get_public_link(yandex_path)

                    uploaded_files.append({
                        'file_name': file_name,
                        'yandex_path': yandex_path,
                        'public_link': public_link if public_link else yandex_path,
                        'local_path': local_file
                    })

                    print(f"[OK] {file_name} загружен")

                except Exception as e:
                    print(f"[ERROR] Ошибка загрузки {local_file}: {e}")

            print(f"[OK] Загружено файлов для {stage}: {len(uploaded_files)}")
            return uploaded_files

        except Exception as e:
            print(f"[ERROR] Ошибка загрузки файлов стадии: {e}")
            return []

    def get_stage_folder_path(self, contract_folder_path, stage, variation=None):
        """Получение пути к папке стадии

        Args:
            contract_folder_path: путь к папке договора
            stage: идентификатор стадии
            variation: номер вариации (опционально, для stage2_concept и stage2_3d)

        Returns:
            Путь к папке стадии или None
        """
        # Убираем префикс disk: если он есть
        if contract_folder_path.startswith('disk:'):
            contract_folder_path = contract_folder_path[5:]  # Убираем 'disk:'

        stage_map = {
            'measurement': 'Замер',
            'stage1': '1 стадия - Планировочное решение',
            'stage2_concept': '2 стадия - Концепция дизайна/Концепция-коллажи',
            'stage2_3d': '2 стадия - Концепция дизайна/3D визуализация',
            'stage3': '3 стадия - Чертежный проект',
            'references': 'Референсы',
            'photo_documentation': 'Фотофиксация'
        }

        subfolder = stage_map.get(stage)
        if subfolder:
            base_path = f"{contract_folder_path}/{subfolder}"

            # Если указана вариация для stage2_concept или stage2_3d, добавляем подпапку
            if variation and stage in ['stage2_concept', 'stage2_3d']:
                base_path = f"{base_path}/Вариация {variation}"

            return base_path
        return None

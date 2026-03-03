from typing import Optional, List, Dict, Any


class FilesMixin:

    def get_contract_files(self, contract_id: int, stage: str = None) -> List[Dict[str, Any]]:
        """Получить файлы договора"""
        params = {}
        if stage:
            params['stage'] = stage
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/files/contract/{contract_id}",
            params=params
        )
        return self._handle_response(response)

    def create_file_record(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать запись о файле"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/files",
            json=file_data
        )
        return self._handle_response(response)

    def delete_file_record(self, file_id: int) -> bool:
        """Удалить запись о файле"""
        response = self._request(
            'DELETE',
            f"{self.base_url}/api/v1/files/{file_id}"
        )
        self._handle_response(response)
        return True

    def get_updated_files(self, since: str) -> list:
        """Получить файлы, загруженные после указанного timestamp"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/files/updated",
            params={"since": since},
            retry=False,
            timeout=5
        )
        return self._handle_response(response)

    def validate_files(self, file_ids: list, auto_clean: bool = False) -> list:
        """Пакетная проверка существования файлов на Яндекс.Диске"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/files/validate",
            json={"file_ids": file_ids, "auto_clean": auto_clean}
        )
        return self._handle_response(response)

    def scan_contract_files(self, contract_id: int, scope: str = 'all') -> dict:
        """Сканирование файлов на ЯД для договора — находит файлы не в БД.
        scope: 'all' — вся папка проекта, 'supervision' — только Авторский надзор.
        """
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/files/scan/{contract_id}",
            params={'scope': scope},
            timeout=60  # Сканирование может быть долгим
        )
        return self._handle_response(response)

    def upload_file_to_yandex(self, file_bytes: bytes, filename: str, yandex_path: str) -> Dict[str, Any]:
        """Загрузить файл на Яндекс.Диск через сервер"""
        # S-03: Сервер ожидает multipart/form-data (UploadFile), а не JSON base64
        # Для multipart нельзя передавать Content-Type: application/json — requests выставит сам
        upload_headers = {k: v for k, v in self.headers.items() if k.lower() != 'content-type'}
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/files/upload",
            files={'file': (filename, file_bytes)},
            params={'yandex_path': yandex_path},
            headers=upload_headers
        )
        return self._handle_response(response)

    def create_yandex_folder(self, folder_path: str) -> Dict[str, Any]:
        """Создать папку на Яндекс.Диске"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/files/folder",
            params={'folder_path': folder_path}
        )
        return self._handle_response(response)

    def get_yandex_public_link(self, yandex_path: str) -> Dict[str, Any]:
        """Получить публичную ссылку на файл"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/files/public-link",
            params={'yandex_path': yandex_path}
        )
        return self._handle_response(response)

    def list_yandex_files(self, folder_path: str) -> Dict[str, Any]:
        """Получить список файлов в папке Яндекс.Диска"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/files/list",
            params={'folder_path': folder_path}
        )
        return self._handle_response(response)

    def delete_yandex_file(self, yandex_path: str) -> Dict[str, Any]:
        """Удалить файл с Яндекс.Диска"""
        response = self._request(
            'DELETE',
            f"{self.base_url}/api/v1/files/yandex",
            params={'yandex_path': yandex_path}
        )
        return self._handle_response(response)

    def add_project_file(self, contract_id: int, stage: str, file_type: str,
                         public_link: str, yandex_path: str, file_name: str,
                         preview_cache_path: str = None, variation: int = 1) -> Optional[int]:
        """Добавить файл стадии проекта"""
        try:
            file_data = {
                'contract_id': contract_id,
                'stage': stage,
                'file_type': file_type,
                'public_link': public_link,
                'yandex_path': yandex_path,
                'file_name': file_name,
                'variation': variation
            }
            if preview_cache_path:
                file_data['preview_cache_path'] = preview_cache_path

            result = self.create_file_record(file_data)
            return result.get('id')
        except Exception as e:
            print(f"[API] Ошибка добавления файла: {e}")
            return None

    def get_project_files(self, contract_id: int, stage: str = None) -> List[Dict[str, Any]]:
        """Получить файлы стадии проекта (alias для get_contract_files)"""
        return self.get_contract_files(contract_id, stage)

    def get_all_project_files(self) -> List[Dict[str, Any]]:
        """Получить все файлы проектов для синхронизации"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/v1/files/all"
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка получения всех файлов: {e}")
            return []

    def delete_project_file(self, file_id: int) -> Optional[Dict[str, Any]]:
        """Удалить файл стадии проекта"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/v1/files/{file_id}",
                mark_offline=False  # Не переходим в offline при ошибке
            )
            file_info = self._handle_response(response)
            self.delete_file_record(file_id)
            return file_info
        except Exception as e:
            print(f"[API] Ошибка удаления файла: {e}")
            return None

    def update_project_file_order(self, file_id: int, new_order: int) -> bool:
        """Обновить порядок файла в галерее"""
        try:
            response = self._request(
                'PATCH',
                f"{self.base_url}/api/v1/files/{file_id}/order",
                json={'file_order': new_order}
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка обновления порядка файла: {e}")
            return False

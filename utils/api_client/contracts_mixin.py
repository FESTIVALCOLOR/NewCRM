from typing import Optional, List, Dict, Any


class ContractsMixin:

    def get_contracts(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить список договоров"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/contracts",
            params={"skip": skip, "limit": limit}
        )
        return self._handle_response(response)

    def get_contracts_paginated(
        self, skip: int = 0, limit: int = 100
    ) -> tuple:
        """Получить список договоров с информацией о пагинации.

        Возвращает кортеж (список договоров, общее количество записей).
        Общее количество читается из заголовка X-Total-Count ответа сервера.
        """
        response = self._request(
            'GET',
            f"{self.base_url}/api/contracts",
            params={"skip": skip, "limit": limit}
        )
        data = self._handle_response(response)
        # Читаем общее количество записей из заголовка X-Total-Count
        total = int(response.headers.get("X-Total-Count", len(data)))
        return data, total

    def get_contracts_count(
        self,
        status: Optional[str] = None,
        project_type: Optional[str] = None,
        year: Optional[int] = None
    ) -> int:
        """Получить количество договоров без загрузки всех записей"""
        params = {}
        if status is not None:
            params['status'] = status
        if project_type is not None:
            params['project_type'] = project_type
        if year is not None:
            params['year'] = year
        response = self._request(
            'GET',
            f"{self.base_url}/api/contracts/count",
            params=params
        )
        result = self._handle_response(response)
        return result.get('count', 0) if isinstance(result, dict) else 0

    def get_contract(self, contract_id: int) -> Dict[str, Any]:
        """Получить договор по ID"""
        response = self._request('GET', f"{self.base_url}/api/contracts/{contract_id}")
        return self._handle_response(response)

    def create_contract(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать новый договор"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/contracts",
            json=contract_data
        )
        return self._handle_response(response)

    def update_contract(self, contract_id: int, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить договор"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/contracts/{contract_id}",
            json=contract_data
        )
        return self._handle_response(response)

    def update_contract_files(self, contract_id: int, files_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновить файлы договора (замер, референсы, фотофиксация)

        Args:
            contract_id: ID договора
            files_data: Словарь с данными файлов:
                - measurement_image_link: ссылка на изображение замера
                - measurement_file_name: имя файла замера
                - measurement_yandex_path: путь на Яндекс.Диске
                - measurement_date: дата замера
                - contract_file_link: ссылка на договор
                - tech_task_link: ссылка на ТЗ
        """
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/contracts/{contract_id}/files",
            json=files_data
        )
        return self._handle_response(response)

    def delete_contract(self, contract_id: int) -> bool:
        """Удалить договор"""
        response = self._request('DELETE', f"{self.base_url}/api/contracts/{contract_id}")
        self._handle_response(response)
        return True

    def check_contract_number_exists(self, contract_number: str, exclude_id: int = None) -> bool:
        """Проверить существование номера договора

        Args:
            contract_number: Номер договора для проверки
            exclude_id: ID договора, который нужно исключить из проверки (для редактирования)
        """
        try:
            contracts = self.get_contracts(skip=0, limit=10000)
            for contract in contracts:
                if contract.get('contract_number') == contract_number:
                    contract_id = contract.get('id')
                    # Если передан exclude_id, пропускаем этот договор
                    if exclude_id is not None and contract_id == exclude_id:
                        continue
                    return True
            return False
        except Exception as e:
            print(f"[API] Ошибка проверки номера договора: {e}")
            return False

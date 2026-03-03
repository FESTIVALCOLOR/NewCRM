from typing import Optional, List, Dict, Any


class CompatMixin:

    def get_employee_by_id(self, employee_id: int) -> Dict[str, Any]:
        """Получить сотрудника по ID (alias для get_employee)"""
        return self.get_employee(employee_id)

    def get_client_by_id(self, client_id: int) -> Dict[str, Any]:
        """Получить клиента по ID (alias для get_client)"""
        return self.get_client(client_id)

    def get_employee_by_login(self, login: str, password: str) -> Optional[Dict[str, Any]]:
        """Проверить логин/пароль сотрудника через API login"""
        try:
            result = self.login(login, password)
            if result and result.get('access_token'):
                return self.get_current_user()
            return None
        except Exception:
            return None

    def add_crm_card(self, card_data: Dict[str, Any]) -> Optional[int]:
        """Добавить CRM карточку (alias для create_crm_card)"""
        result = self.create_crm_card(card_data)
        return result.get('id') if result else None

    def add_supervision_card(self, card_data: Dict[str, Any]) -> Optional[int]:
        """Добавить карточку надзора (alias для create_supervision_card)"""
        result = self.create_supervision_card(card_data)
        return result.get('id') if result else None

    def add_rate(self, rate_data: Dict[str, Any]) -> Optional[int]:
        """Добавить ставку (alias для create_rate)"""
        result = self.create_rate(rate_data)
        return result.get('id') if result else None

    def get_rate_by_id(self, rate_id: int) -> Dict[str, Any]:
        """Получить ставку по ID (alias для get_rate)"""
        return self.get_rate(rate_id)

    def get_salary_by_id(self, salary_id: int) -> Dict[str, Any]:
        """Получить запись о зарплате по ID (alias для get_salary)"""
        return self.get_salary(salary_id)

    def add_payment(self, payment_data: Dict[str, Any]) -> Optional[int]:
        """Добавить платёж (alias для create_payment)"""
        result = self.create_payment(payment_data)
        return result.get('id') if result else None

    def add_contract_file(self, file_data: Dict[str, Any]) -> Optional[int]:
        """Добавить файл договора (alias для create_file_record)"""
        result = self.create_file_record(file_data)
        return result.get('id') if result else None

    def delete_contract_file(self, file_id: int) -> bool:
        """Удалить файл договора (alias для delete_file_record)"""
        return self.delete_file_record(file_id)

    def get_supervision_card_data(self, card_id: int) -> Dict[str, Any]:
        """Получить данные карточки надзора (alias для get_supervision_card)"""
        return self.get_supervision_card(card_id)

    def sync_approval_stages_to_json(self, crm_card_id: int) -> bool:
        """Синхронизация стадий согласования (на сервере выполняется автоматически)"""
        # На сервере эта операция выполняется автоматически при обновлении
        return True

    def update_crm_card_column(self, card_id: int, column_name: str) -> bool:
        """Обновить колонку карточки (alias для move_crm_card)"""
        try:
            self.move_crm_card(card_id, column_name)
            return True
        except Exception as e:
            print(f"[API] Ошибка обновления колонки: {e}")
            return False

    def update_supervision_card_column(self, card_id: int, column_name: str) -> bool:
        """Обновить колонку карточки надзора (alias для move_supervision_card)"""
        try:
            self.move_supervision_card(card_id, column_name)
            return True
        except Exception as e:
            print(f"[API] Ошибка обновления колонки надзора: {e}")
            return False

    def get_supervision_cards_active(self) -> List[Dict[str, Any]]:
        """Получить активные карточки надзора (alias)"""
        return self.get_supervision_cards(status="active")

    def get_supervision_cards_archived(self) -> List[Dict[str, Any]]:
        """Получить архивные карточки надзора (alias)"""
        return self.get_supervision_cards(status="archived")

    def get_supervision_statistics_report(self, year: int, quarter: int = None,
                                          month: int = None, agent_type: str = None,
                                          city: str = None) -> Dict[str, Any]:
        """Получить статистику надзора для отчета (alias)"""
        return self.get_supervision_statistics(year, quarter, month, agent_type, city)

    def get_crm_card_data(self, card_id: int) -> Dict[str, Any]:
        """Получить данные карточки для проверок (alias для get_crm_card)"""
        return self.get_crm_card(card_id)

    def get_employees_by_department(self, department: str) -> List[Dict[str, Any]]:
        """Получить сотрудников по отделу"""
        all_employees = self.get_employees(limit=500)
        return [emp for emp in all_employees if emp.get('department') == department]

    def check_login_exists(self, login: str) -> bool:
        """Проверить существование логина"""
        try:
            employees = self.get_employees(limit=1000)
            for emp in employees:
                if emp.get('login') == login:
                    return True
            return False
        except Exception as e:
            print(f"[API] Ошибка проверки логина: {e}")
            return False

    def get_next_contract_number(self, year: int) -> int:
        """Получить следующий номер договора для года"""
        try:
            contracts = self.get_contracts(limit=10000)
            max_number = 0
            year_suffix = str(year)
            for contract in contracts:
                contract_number = contract.get('contract_number', '')
                if year_suffix in contract_number:
                    try:
                        number_part = contract_number.split('-')[0].replace('№', '').strip()
                        num = int(number_part)
                        if num > max_number:
                            max_number = num
                    except (ValueError, IndexError):
                        pass
            return max_number + 1
        except Exception as e:
            print(f"[API] Ошибка получения номера договора: {e}")
            return 1

    def get_crm_card_id_by_contract(self, contract_id: int) -> Optional[int]:
        """Получить ID CRM карточки по ID договора"""
        try:
            for project_type in ['Индивидуальный', 'Шаблонный']:
                cards = self.get_crm_cards(project_type)
                for card in cards:
                    if card.get('contract_id') == contract_id:
                        return card.get('id')
            return None
        except Exception as e:
            print(f"[API] Ошибка получения CRM карточки: {e}")
            return None

    def delete_order(self, contract_id: int, crm_card_id: int = None) -> bool:
        """Полное удаление заказа из системы"""
        try:
            if crm_card_id:
                self.delete_crm_card(crm_card_id)
            self.delete_contract(contract_id)
            return True
        except Exception as e:
            print(f"[API] Ошибка удаления заказа: {e}")
            return False

    def get_projects_by_type(self, project_type: str) -> List[Dict[str, Any]]:
        """Получить список проектов по типу"""
        try:
            cards = self.get_crm_cards(project_type)
            projects = []
            seen_contracts = set()
            for card in cards:
                contract_id = card.get('contract_id')
                if contract_id and contract_id not in seen_contracts:
                    seen_contracts.add(contract_id)
                    projects.append({
                        'contract_id': contract_id,
                        'contract_number': card.get('contract_number'),
                        'address': card.get('address'),
                        'city': card.get('city')
                    })
            return projects
        except Exception as e:
            print(f"[API] Ошибка получения проектов: {e}")
            return []

    def get_previous_executor_by_position(self, crm_card_id: int, position: str) -> Optional[int]:
        """Получить предыдущего исполнителя по должности"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/v1/crm/cards/{crm_card_id}/previous-executor",
                params={'position': position}
            )
            result = self._handle_response(response)
            return result.get('executor_id')
        except Exception as e:
            print(f"[API] Ошибка получения предыдущего исполнителя: {e}")
            return None

    # С12: update_stage_executor_deadline удалён — дублирует crm_mixin.update_stage_executor

    def assign_stage_executor_db(self, card_id: int, stage_name: str, executor_id: int,
                                  assigned_by: int, deadline: str = None) -> bool:
        """Назначить исполнителя на стадию (совместимость с db_manager)"""
        try:
            stage_data = {
                'stage_name': stage_name,
                'executor_id': executor_id,
                'assigned_by': assigned_by
            }
            if deadline:
                stage_data['deadline'] = deadline
            self.assign_stage_executor(card_id, stage_data)
            return True
        except Exception as e:
            print(f"[API] Ошибка назначения исполнителя: {e}")
            return False

    def get_contract_id_by_crm_card(self, crm_card_id: int) -> Optional[int]:
        """Получить ID договора по ID карточки CRM"""
        try:
            card = self.get_crm_card(crm_card_id)
            return card.get('contract_id')
        except Exception as e:
            print(f"[API] Ошибка получения contract_id: {e}")
            return None

    # K9: get_crm_card_by_contract_id удалён — endpoint не существует на сервере

    def get_contracts_by_project_type(self, project_type: str) -> List[Dict[str, Any]]:
        """Получить договоры по типу проекта"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/contracts",
            params={'project_type': project_type}
        )
        return self._handle_response(response)

    def get_unique_cities(self) -> List[str]:
        """Получить уникальные города из договоров"""
        try:
            contracts = self.get_contracts()
            cities = set()
            for c in contracts:
                if c.get('city'):
                    cities.add(c['city'])
            return sorted(list(cities))
        except Exception:
            return []

    def get_unique_agent_types(self) -> List[str]:
        """Получить уникальные типы агентов из договоров"""
        try:
            contracts = self.get_contracts()
            agent_types = set()
            for c in contracts:
                if c.get('agent_type'):
                    agent_types.add(c['agent_type'])
            return sorted(list(agent_types))
        except Exception:
            return []

    def get_payments(self) -> List[Dict[str, Any]]:
        """Получить все платежи"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/payments"
        )
        return self._handle_response(response)

    def get_payments_by_contract(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получить платежи по ID договора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/payments",
            params={'contract_id': contract_id}
        )
        return self._handle_response(response)

    def get_payments_by_employee(self, employee_id: int) -> List[Dict[str, Any]]:
        """Получить платежи по ID сотрудника"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/payments",
            params={'employee_id': employee_id}
        )
        return self._handle_response(response)

    def get_unpaid_payments(self) -> List[Dict[str, Any]]:
        """Получить неоплаченные платежи"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/payments",
            params={'is_paid': False}
        )
        return self._handle_response(response)

    def get_all_payments(self, month: int = None, year: int = None) -> List[Dict[str, Any]]:
        """Получить все платежи с фильтрами по месяцу и году"""
        params = {}
        if month:
            params['month'] = month
        if year:
            params['year'] = year

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/payments",
            params=params if params else None
        )
        return self._handle_response(response)

    def get_all_payments_optimized(self, year: int = None, month: int = None, quarter: int = None) -> List[Dict[str, Any]]:
        """Оптимизированная загрузка всех выплат - один запрос вместо множества"""
        try:
            params = {}
            if year:
                params['year'] = year
            if month:
                params['month'] = month
            if quarter:
                params['quarter'] = quarter

            response = self._request(
                'GET',
                f"{self.base_url}/api/v1/payments/all-optimized",
                params=params
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка загрузки оптимизированных выплат: {e}")
            return []

    def get_payments_summary(self, year: int, month: int = None, quarter: int = None) -> Dict[str, Any]:
        """Получить сводку по платежам"""
        params = {'year': year}
        if month:
            params['month'] = month
        if quarter:
            params['quarter'] = quarter
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/payments/summary",
            params=params
        )
        return self._handle_response(response)

    def get_rates_by_project_type(self, project_type: str) -> List[Dict[str, Any]]:
        """Получить ставки по типу проекта"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/rates",
            params={'project_type': project_type}
        )
        return self._handle_response(response)

    def get_salaries_by_employee(self, employee_id: int) -> List[Dict[str, Any]]:
        """Получить зарплаты по ID сотрудника"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/salaries",
            params={'employee_id': employee_id}
        )
        return self._handle_response(response)

    def get_files_by_contract(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получить файлы по ID договора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/files/contract/{contract_id}"
        )
        return self._handle_response(response)

    def get_file_templates(self) -> List[Dict[str, Any]]:
        """Получить шаблоны файлов

        DEAD CODE: endpoint /api/v1/file-templates не существует на сервере,
        метод не используется в UI. Оставлен для обратной совместимости.
        """
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/v1/file-templates"
            )
            return self._handle_response(response)
        except Exception:
            return []

    def get_cities(self) -> List[str]:
        """Получить список городов"""
        response = self._request('GET', f"{self.base_url}/api/v1/statistics/cities")
        return self._handle_response(response)

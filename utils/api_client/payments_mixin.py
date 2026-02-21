from typing import Optional, List, Dict, Any


class PaymentsMixin:

    def get_payments_for_contract(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получить все оплаты для договора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments/contract/{contract_id}"
        )
        return self._handle_response(response)

    def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать запись оплаты"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/payments",
            json=payment_data
        )
        return self._handle_response(response)

    def get_payment(self, payment_id: int) -> Dict[str, Any]:
        """Получить данные платежа по ID"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments/{payment_id}"
        )
        return self._handle_response(response)

    def update_payment(self, payment_id: int, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить запись оплаты"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/payments/{payment_id}",
            json=payment_data
        )
        return self._handle_response(response)

    def delete_payment(self, payment_id: int) -> Dict[str, Any]:
        """Удалить запись оплаты"""
        response = self._request(
            'DELETE',
            f"{self.base_url}/api/payments/{payment_id}"
        )
        return self._handle_response(response)

    def set_payments_report_month(self, contract_id: int, report_month: str) -> Dict[str, Any]:
        """
        Установить отчетный месяц для всех платежей договора без месяца

        Args:
            contract_id: ID договора
            report_month: Отчетный месяц в формате 'YYYY-MM'

        Returns:
            Количество обновленных платежей
        """
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/payments/contract/{contract_id}/report-month",
            json={'report_month': report_month}
        )
        return self._handle_response(response)

    def get_year_payments(self, year: int, include_null_month: bool = False) -> List[Dict[str, Any]]:
        """Получить платежи за год

        Args:
            year: Год
            include_null_month: Включить платежи с NULL report_month (В работе)
        """
        params = {'year': year}
        if include_null_month:
            params['include_null_month'] = 'true'
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments",
            params=params
        )
        return self._handle_response(response)

    def get_payments_by_type(self, payment_type: str, project_type_filter: str = None) -> List[Dict[str, Any]]:
        """
        Получить платежи по типу выплаты и фильтру типа проекта

        Сигнатура совпадает с вызовом в ui/salaries_tab.py:load_payment_type_data()

        Args:
            payment_type: Тип выплаты ('Индивидуальные проекты', 'Шаблонные проекты', 'Оклады', 'Авторский надзор')
            project_type_filter: Фильтр типа проекта ('Индивидуальный', 'Шаблонный', 'Авторский надзор', None)

        Returns:
            Список платежей с полями:
                - id, contract_id, employee_id, employee_name, position
                - role, stage_name, final_amount, payment_type
                - report_month, payment_status
                - contract_number, address, area, city, agent_type
                - source ('CRM' или 'Оклад')
        """
        params = {'payment_type': payment_type}
        if project_type_filter:
            params['project_type_filter'] = project_type_filter

        response = self._request(
            'GET',
            f"{self.base_url}/api/payments/by-type",
            params=params
        )
        return self._handle_response(response)

    def get_payments_by_supervision_card(self, supervision_card_id: int) -> List[Dict[str, Any]]:
        """ДОБАВЛЕНО 30.01.2026: Получить платежи по ID карточки надзора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments/by-supervision-card/{supervision_card_id}"
        )
        return self._handle_response(response)

    def get_payments_for_supervision(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получить платежи для надзора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments/supervision/{contract_id}"
        )
        return self._handle_response(response)

    def get_payments_for_crm(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получить выплаты для CRM (не надзор)"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments/crm/{contract_id}"
        )
        return self._handle_response(response)

    def mark_payment_as_paid(self, payment_id: int, employee_id: int) -> Dict[str, Any]:
        """Отметить платеж как выплаченный"""
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/payments/{payment_id}/mark-paid",
            json={'employee_id': employee_id}
        )
        return self._handle_response(response)

    def calculate_payment_amount(self, contract_id: int, employee_id: int, role: str,
                                  stage_name: str = None, supervision_card_id: int = None) -> float:
        """Рассчитать сумму оплаты на основе тарифов"""
        try:
            params = {
                'contract_id': contract_id,
                'employee_id': employee_id,
                'role': role
            }
            if stage_name:
                params['stage_name'] = stage_name
            if supervision_card_id:
                params['supervision_card_id'] = supervision_card_id

            response = self._request(
                'GET',
                f"{self.base_url}/api/payments/calculate",
                params=params
            )
            result = self._handle_response(response)
            return result.get('amount', 0)
        except Exception as e:
            print(f"[API] Ошибка расчета оплаты: {e}")
            return 0

    def create_payment_record(self, contract_id: int, employee_id: int, role: str,
                              stage_name: str = None, payment_type: str = 'Полная оплата',
                              report_month: str = None, crm_card_id: int = None,
                              supervision_card_id: int = None) -> Optional[int]:
        """Создать запись о выплате"""
        try:
            payment_data = {
                'contract_id': contract_id,
                'employee_id': employee_id,
                'role': role,
                'payment_type': payment_type
            }
            if stage_name:
                payment_data['stage_name'] = stage_name
            if report_month:
                payment_data['report_month'] = report_month
            if crm_card_id:
                payment_data['crm_card_id'] = crm_card_id
            if supervision_card_id:
                payment_data['supervision_card_id'] = supervision_card_id

            result = self.create_payment(payment_data)
            return result.get('id')
        except Exception as e:
            print(f"[API] Ошибка создания выплаты: {e}")
            return None

    def recalculate_payments(self, contract_id: int = None, role: str = None) -> Dict[str, Any]:
        """Пересчет выплат по текущим тарифам"""
        try:
            params = {}
            if contract_id:
                params['contract_id'] = contract_id
            if role:
                params['role'] = role

            response = self._request(
                'POST',
                f"{self.base_url}/api/payments/recalculate",
                params=params
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка пересчета выплат: {e}")
            return {'status': 'error', 'error': str(e)}

    def update_payment_manual(self, payment_id: int, amount: float, report_month: str) -> Dict[str, Any]:
        """Обновить платеж вручную"""
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/payments/{payment_id}/manual",
            json={'amount': amount, 'report_month': report_month}
        )
        return self._handle_response(response)

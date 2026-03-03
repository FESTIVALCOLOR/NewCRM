from typing import Optional, List, Dict, Any


class StatisticsMixin:

    def get_dashboard_statistics(self, year: int = None, month: int = None, quarter: int = None,
                                  agent_type: str = None, city: str = None) -> Dict[str, Any]:
        """Получить статистику для дашборда"""
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if quarter:
            params['quarter'] = quarter
        if agent_type:
            params['agent_type'] = agent_type
        if city:
            params['city'] = city
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/statistics/dashboard",
            params=params
        )
        return self._handle_response(response)

    def get_employee_statistics(self, year: int = None, month: int = None) -> List[Dict[str, Any]]:
        """Получить статистику по сотрудникам"""
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/statistics/employees",
            params=params
        )
        return self._handle_response(response)

    def get_contracts_by_period(self, year: int, group_by: str = "month", project_type: str = None) -> Dict[str, Any]:
        """Получить договоры сгруппированные по периоду"""
        params = {'year': year, 'group_by': group_by}
        if project_type:
            params['project_type'] = project_type
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/statistics/contracts-by-period",
            params=params
        )
        return self._handle_response(response)

    def get_project_statistics(self, project_type: str, year: int = None, quarter: int = None,
                               month: int = None, agent_type: str = None, city: str = None) -> Dict[str, Any]:
        """
        Получить статистику проектов

        Args:
            project_type: Тип проекта ("Индивидуальный" или "Шаблонный")
            year: Год
            quarter: Квартал (1-4)
            month: Месяц (1-12)
            agent_type: Тип агента
            city: Город

        Returns:
            Статистика проектов
        """
        params = {'project_type': project_type}
        if year:
            params['year'] = year
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type
        if city:
            params['city'] = city

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/statistics/projects",
            params=params
        )
        return self._handle_response(response)

    def get_supervision_statistics(self, year: int = None, quarter: int = None,
                                   month: int = None, agent_type: str = None, city: str = None) -> Dict[str, Any]:
        """
        Получить статистику авторского надзора

        Args:
            year: Год
            quarter: Квартал (1-4)
            month: Месяц (1-12)
            agent_type: Тип агента
            city: Город

        Returns:
            Статистика надзора
        """
        params = {}
        if year:
            params['year'] = year
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type
        if city:
            params['city'] = city

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/statistics/supervision",
            params=params
        )
        return self._handle_response(response)

    def get_crm_statistics(self, project_type: str, period: str, year: int, month: int = None) -> List[Dict[str, Any]]:
        """Получить статистику CRM"""
        params = {
            'project_type': project_type,
            'period': period,
            'year': year
        }
        if month:
            params['month'] = month
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/statistics/crm",
            params=params
        )
        return self._handle_response(response)

    def get_crm_statistics_filtered(self, project_type: str, period: str, year: int,
                                    quarter: int = None, month: int = None, project_id: int = None,
                                    executor_id: int = None, stage_name: str = None,
                                    status_filter: str = None) -> List[Dict[str, Any]]:
        """Получить статистику CRM с фильтрами"""
        params = {
            'project_type': project_type,
            'period': period,
            'year': year
        }
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        if project_id:
            params['project_id'] = project_id
        if executor_id:
            params['executor_id'] = executor_id
        if stage_name:
            params['stage_name'] = stage_name
        if status_filter:
            params['status_filter'] = status_filter

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/statistics/crm/filtered",
            params=params
        )
        return self._handle_response(response)

    def get_supervision_statistics_filtered(self, year: int = None, quarter: int = None,
                                            month: int = None, agent_type: str = None,
                                            city: str = None, address: str = None,
                                            executor_id: int = None, manager_id: int = None,
                                            status: str = None) -> Dict[str, Any]:
        """Получить отфильтрованную статистику надзора"""
        params = {}
        if year:
            params['year'] = year
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type
        if city:
            params['city'] = city
        if address:
            params['address'] = address
        if executor_id:
            params['executor_id'] = executor_id
        if manager_id:
            params['manager_id'] = manager_id
        if status:
            params['status'] = status

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/statistics/supervision/filtered",
            params=params
        )
        return self._handle_response(response)

    def get_general_statistics(self, year: int, quarter: int = None, month: int = None) -> Dict[str, Any]:
        """Получить общую статистику"""
        params = {'year': year}
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/statistics/general",
            params=params
        )
        return self._handle_response(response)

    def get_approval_statistics(self, project_type: str, period: str, year: int,
                                quarter: int = None, month: int = None,
                                project_id: int = None) -> List[Dict[str, Any]]:
        """Получить статистику согласований"""
        params = {
            'project_type': project_type,
            'period': period,
            'year': year
        }
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        if project_id:
            params['project_id'] = project_id

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/statistics/approvals",
            params=params
        )
        return self._handle_response(response)

    def get_funnel_statistics(self, year: int = None, project_type: str = None) -> Dict[str, Any]:
        """Статистика воронки: количество карточек по колонкам"""
        params = {}
        if year:
            params['year'] = year
        if project_type:
            params['project_type'] = project_type
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/statistics/funnel",
            params=params
        )
        return self._handle_response(response)

    def get_executor_load(self, year: int = None, month: int = None) -> List[Dict[str, Any]]:
        """Нагрузка на исполнителей: количество активных стадий"""
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/statistics/executor-load",
            params=params
        )
        return self._handle_response(response)

    def get_employee_report_data(self, project_type: str, period: str, year: int, quarter: int = None, month: int = None) -> Dict[str, Any]:
        """
        Получить данные для отчета по сотрудникам

        Сигнатура совпадает с database/db_manager.py:get_employee_report_data()

        Args:
            project_type: Тип проекта ('Индивидуальный' или 'Шаблонный')
            period: Период ('За год', 'За квартал', 'За месяц')
            year: Год
            quarter: Квартал (1-4), если period == 'За квартал'
            month: Месяц (1-12), если period == 'За месяц'

        Returns:
            Данные отчета с ключами:
                - completed: Список выполненных заказов
                - area: Список по площади
                - deadlines: Список просрочек
                - salaries: Список зарплат
        """
        params = {
            'project_type': project_type,
            'period': period,
            'year': int(year)  # Ensure year is int
        }
        if quarter:
            params['quarter'] = int(quarter)
        if month:
            params['month'] = int(month)

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/reports/employee-report",
            params=params
        )
        return self._handle_response(response)

    def get_clients_dashboard_stats(self, year: Optional[int] = None, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда страницы Клиенты"""
        params = {}
        if year:
            params['year'] = year
        if agent_type:
            params['agent_type'] = agent_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/clients",
            params=params
        )
        return self._handle_response(response)

    def get_contracts_dashboard_stats(self, year: Optional[int] = None, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда страницы Договора"""
        params = {}
        if year:
            params['year'] = year
        if agent_type:
            params['agent_type'] = agent_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/contracts",
            params=params
        )
        return self._handle_response(response)

    def get_crm_dashboard_stats(self, project_type: str, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда СРМ (Индивидуальные/Шаблонные/Надзор)"""
        params = {'project_type': project_type}
        if agent_type:
            params['agent_type'] = agent_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/crm",
            params=params
        )
        return self._handle_response(response)

    def get_employees_dashboard_stats(self) -> Dict[str, Any]:
        """Получить статистику для дашборда страницы Сотрудники"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/employees"
        )
        return self._handle_response(response)

    def get_salaries_dashboard_stats(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда страницы Зарплаты"""
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/salaries",
            params=params
        )
        return self._handle_response(response)

    def get_salaries_payment_type_stats(self, payment_type: str, year: Optional[int] = None,
                                         month: Optional[int] = None, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда вкладок зарплат по типу выплат

        Args:
            payment_type: Тип вкладки ('all', 'individual', 'template', 'salary', 'supervision')
            year: Год для фильтра
            month: Месяц для фильтра
            agent_type: Тип агента для фильтра

        Returns:
            Dict с ключами: total_paid, paid_by_year, paid_by_month, payments_count, to_pay_amount, by_agent
        """
        params = {'payment_type': payment_type}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/salaries-by-type",
            params=params
        )
        return self._handle_response(response)

    def get_salaries_all_payments_stats(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда 'Все выплаты'
        Возвращает: total_paid, paid_by_year, paid_by_month, individual_by_year, template_by_year, supervision_by_year
        """
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/salaries-all",
            params=params
        )
        return self._handle_response(response)

    def get_salaries_individual_stats(self, year: Optional[int] = None, month: Optional[int] = None,
                                       agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда 'Индивидуальные'
        Возвращает: total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count
        """
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/salaries-individual",
            params=params
        )
        return self._handle_response(response)

    def get_salaries_template_stats(self, year: Optional[int] = None, month: Optional[int] = None,
                                     agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда 'Шаблонные'
        Возвращает: total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count
        """
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/salaries-template",
            params=params
        )
        return self._handle_response(response)

    def get_salaries_salary_stats(self, year: Optional[int] = None, month: Optional[int] = None,
                                   project_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда 'Оклады'
        Возвращает: total_paid, paid_by_year, paid_by_month, by_project_type, avg_salary, employees_count
        """
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if project_type:
            params['project_type'] = project_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/salaries-salary",
            params=params
        )
        return self._handle_response(response)

    def get_salaries_supervision_stats(self, year: Optional[int] = None, month: Optional[int] = None,
                                        agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда 'Авторский надзор'
        Возвращает: total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count
        """
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/salaries-supervision",
            params=params
        )
        return self._handle_response(response)

    def get_reports_summary(self, year=None, quarter=None, month=None, agent_type=None,
                             city=None, project_type=None) -> Dict[str, Any]:
        """Получить KPI-метрики для страницы отчётов"""
        params = {}
        if year:
            params['year'] = year
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type
        if city:
            params['city'] = city
        if project_type:
            params['project_type'] = project_type
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/reports/summary",
            params=params
        )
        return self._handle_response(response)

    def get_reports_clients_dynamics(self, year=None, granularity="month") -> Dict[str, Any]:
        """Получить динамику клиентов по месяцам/кварталам"""
        params = {'granularity': granularity}
        if year:
            params['year'] = year
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/reports/clients-dynamics",
            params=params
        )
        return self._handle_response(response)

    def get_reports_contracts_dynamics(self, year=None, granularity="month",
                                        agent_type=None, city=None) -> Dict[str, Any]:
        """Получить динамику договоров по месяцам"""
        params = {'granularity': granularity}
        if year:
            params['year'] = year
        if agent_type:
            params['agent_type'] = agent_type
        if city:
            params['city'] = city
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/reports/contracts-dynamics",
            params=params
        )
        return self._handle_response(response)

    def get_reports_crm_analytics(self, project_type="Индивидуальный", year=None,
                                   quarter=None, month=None) -> Dict[str, Any]:
        """Получить CRM аналитику: воронка, просрочки, время стадий"""
        params = {'project_type': project_type}
        if year:
            params['year'] = year
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/reports/crm-analytics",
            params=params
        )
        return self._handle_response(response)

    def get_reports_supervision_analytics(self, year=None, quarter=None,
                                           month=None) -> Dict[str, Any]:
        """Получить аналитику авторского надзора"""
        params = {}
        if year:
            params['year'] = year
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/reports/supervision-analytics",
            params=params
        )
        return self._handle_response(response)

    def get_reports_distribution(self, dimension, year=None, quarter=None,
                                  month=None) -> Dict[str, Any]:
        """Получить распределение по измерению (city/agent/project_type/subtype)"""
        params = {'dimension': dimension}
        if year:
            params['year'] = year
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/reports/distribution",
            params=params
        )
        return self._handle_response(response)

    def get_agent_types(self) -> List[str]:
        """Получить список всех типов агентов"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/v1/dashboard/agent-types"
        )
        return self._handle_response(response)

    def get_contract_years(self) -> List[int]:
        """Получить список всех годов из договоров (для фильтров дашборда)

        Returns:
            list: Список годов в обратном порядке (от нового к старому)
        """
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/v1/dashboard/contract-years"
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка получения годов договоров: {e}")
            # Возвращаем fallback - 10 лет назад до следующего года
            from datetime import datetime
            current_year = datetime.now().year
            return list(range(current_year + 1, current_year - 10, -1))

# -*- coding: utf-8 -*-
"""
Конкретные реализации дашбордов для каждой страницы
"""

from datetime import datetime
from ui.dashboard_widget import DashboardWidget


class ClientsDashboard(DashboardWidget):
    """Дашборд для страницы Клиенты"""

    def __init__(self, db_manager, api_client=None, parent=None):
        super().__init__(db_manager, api_client, parent)

        # Получаем список агентов
        try:
            self.agent_types = self.db.get_agent_types()
            if not self.agent_types:
                self.agent_types = ['Прямой', 'Агент', 'Партнер']
        except Exception as e:
            print(f"[WARN] Ошибка получения типов агентов: {e}")
            self.agent_types = ['Прямой', 'Агент', 'Партнер']

        # Независимые фильтры для каждой карточки
        self.filter_clients_by_year_year = datetime.now().year
        self.filter_agent_clients_total_agent = None
        self.filter_agent_clients_by_year_agent = None
        self.filter_agent_clients_by_year_year = datetime.now().year

        self.setup_ui()

    def setup_ui(self):
        """Создание UI дашборда"""

        # Динамический список годов из договоров
        years = self.get_years()

        # 1. Всего клиентов
        self.add_metric_card(
            row=0, col=0,
            object_name='total_clients',
            title='Всего клиентов',
            value='0',
            icon_path='resources/icons/users.svg',
            border_color='#2196F3'
        )

        # 2. Всего физлиц
        self.add_metric_card(
            row=0, col=1,
            object_name='total_individual',
            title='Всего физлиц',
            value='0',
            icon_path='resources/icons/user.svg',
            border_color='#4CAF50'
        )

        # 3. Всего юрлиц
        self.add_metric_card(
            row=0, col=2,
            object_name='total_legal',
            title='Всего юрлиц',
            value='0',
            icon_path='resources/icons/briefcase.svg',
            border_color='#FF9800'
        )

        # 4. Клиенты за год (с фильтром Год) - НЕЗАВИСИМЫЙ
        card = self.add_metric_card(
            row=0, col=3,
            object_name='clients_by_year',
            title='Клиенты за год',
            value='0',
            icon_path='resources/icons/calendar.svg',
            border_color='#9C27B0',
            filters=[{'type': 'year', 'options': years}]
        )
        card.connect_filter('year', self.on_clients_by_year_changed)

        # 5. Клиенты агента (всего) с фильтром Агент - НЕЗАВИСИМЫЙ
        card = self.add_metric_card(
            row=0, col=4,
            object_name='agent_clients_total',
            title='Клиенты агента (всего)',
            value='0',
            icon_path='resources/icons/team.svg',
            border_color='#F44336',
            filters=[{'type': 'agent', 'options': self.agent_types}]
        )
        card.connect_filter('agent', self.on_agent_clients_total_changed)

        # 6. Клиенты агента за год (с фильтрами Агент и Год) - НЕЗАВИСИМЫЙ
        card = self.add_metric_card(
            row=0, col=5,
            object_name='agent_clients_by_year',
            title='Клиенты агента (за год)',
            value='0',
            icon_path='resources/icons/team.svg',
            border_color='#E91E63',
            filters=[
                {'type': 'agent', 'options': self.agent_types},
                {'type': 'year', 'options': years}
            ]
        )
        card.connect_filter('agent', self.on_agent_clients_by_year_agent_changed)
        card.connect_filter('year', self.on_agent_clients_by_year_year_changed)

        self.set_column_stretch(6)

    def on_clients_by_year_changed(self, year):
        """Обработка изменения года для карточки 'Клиенты за год'"""
        self.filter_clients_by_year_year = int(year)
        self._update_clients_by_year()

    def on_agent_clients_total_changed(self, agent):
        """Обработка изменения агента для карточки 'Клиенты агента (всего)'"""
        self.filter_agent_clients_total_agent = agent
        self._update_agent_clients_total()

    def on_agent_clients_by_year_agent_changed(self, agent):
        """Обработка изменения агента для карточки 'Клиенты агента (за год)'"""
        self.filter_agent_clients_by_year_agent = agent
        self._update_agent_clients_by_year()

    def on_agent_clients_by_year_year_changed(self, year):
        """Обработка изменения года для карточки 'Клиенты агента (за год)'"""
        self.filter_agent_clients_by_year_year = int(year)
        self._update_agent_clients_by_year()

    def _get_stats(self, year=None, agent_type=None):
        """Получить статистику из API или локальной БД"""
        try:
            if self.api_client and self.api_client.is_online:
                return self.api_client.get_clients_dashboard_stats(year=year, agent_type=agent_type)
            else:
                return self.db.get_clients_dashboard_stats(year=year, agent_type=agent_type)
        except Exception as e:
            print(f"[WARN] API error, using local DB: {e}")
            return self.db.get_clients_dashboard_stats(year=year, agent_type=agent_type)

    def _update_clients_by_year(self):
        """Обновить только карточку 'Клиенты за год'"""
        try:
            stats = self._get_stats(year=self.filter_clients_by_year_year, agent_type=None)
            self.update_metric('clients_by_year', str(stats['clients_by_year']))
        except Exception as e:
            print(f"[ERROR] Ошибка обновления clients_by_year: {e}")

    def _update_agent_clients_total(self):
        """Обновить только карточку 'Клиенты агента (всего)'"""
        try:
            stats = self._get_stats(year=None, agent_type=self.filter_agent_clients_total_agent)
            self.update_metric('agent_clients_total', str(stats['agent_clients_total']))
        except Exception as e:
            print(f"[ERROR] Ошибка обновления agent_clients_total: {e}")

    def _update_agent_clients_by_year(self):
        """Обновить только карточку 'Клиенты агента (за год)'"""
        try:
            stats = self._get_stats(
                year=self.filter_agent_clients_by_year_year,
                agent_type=self.filter_agent_clients_by_year_agent
            )
            self.update_metric('agent_clients_by_year', str(stats['agent_clients_by_year']))
        except Exception as e:
            print(f"[ERROR] Ошибка обновления agent_clients_by_year: {e}")

    def load_data(self):
        """Загрузка всех данных"""
        try:
            # Загружаем базовую статистику (без фильтров)
            stats = self._get_stats(year=None, agent_type=None)

            self.update_metric('total_clients', str(stats['total_clients']))
            self.update_metric('total_individual', str(stats['total_individual']))
            self.update_metric('total_legal', str(stats['total_legal']))

            # Загружаем данные с фильтрами для каждой карточки
            self._update_clients_by_year()
            self._update_agent_clients_total()
            self._update_agent_clients_by_year()

        except Exception as e:
            print(f"[ERROR] Ошибка загрузки данных дашборда клиентов: {e}")
            import traceback
            traceback.print_exc()


class ContractsDashboard(DashboardWidget):
    """Дашборд для страницы Договора"""

    def __init__(self, db_manager, api_client=None, parent=None):
        super().__init__(db_manager, api_client, parent)

        try:
            self.agent_types = self.db.get_agent_types()
            if not self.agent_types:
                self.agent_types = ['Прямой', 'Агент', 'Партнер']
        except Exception as e:
            print(f"[WARN] Ошибка получения типов агентов: {e}")
            self.agent_types = ['Прямой', 'Агент', 'Партнер']

        # Фильтры для карточки "Заказы агента" (связаны с "Площадь агента")
        self.filter_agent_year = datetime.now().year
        self.filter_agent_type = None

        self.setup_ui()

    def setup_ui(self):
        """Создание UI дашборда"""

        # Динамический список годов из договоров
        years = self.get_years()

        # 1. Всего индивидуальных заказов
        self.add_metric_card(
            row=0, col=0,
            object_name='individual_orders',
            title='Индивидуальные заказы',
            value='0',
            icon_path='resources/icons/clipboard1.svg',
            border_color='#F57C00'
        )

        # 2. Площадь индивидуальных
        self.add_metric_card(
            row=0, col=1,
            object_name='individual_area',
            title='Площадь индивидуальных',
            value='0 м2',
            icon_path='resources/icons/codepen1.svg',
            border_color='#F57C00'
        )

        # 3. Всего шаблонных заказов
        self.add_metric_card(
            row=0, col=2,
            object_name='template_orders',
            title='Шаблонные заказы',
            value='0',
            icon_path='resources/icons/clipboard2.svg',
            border_color='#C62828'
        )

        # 4. Площадь шаблонных
        self.add_metric_card(
            row=0, col=3,
            object_name='template_area',
            title='Площадь шаблонных',
            value='0 м2',
            icon_path='resources/icons/codepen2.svg',
            border_color='#C62828'
        )

        # 5. Заказы агента за год (с фильтрами)
        card = self.add_metric_card(
            row=0, col=4,
            object_name='agent_orders_by_year',
            title='Заказы агента (за год)',
            value='0',
            icon_path='resources/icons/team.svg',
            border_color='#388E3C',
            filters=[
                {'type': 'agent', 'options': self.agent_types},
                {'type': 'year', 'options': years}
            ]
        )
        card.connect_filter('agent', self.on_agent_changed)
        card.connect_filter('year', self.on_year_changed)

        # 6. Площадь агента за год (БЕЗ кнопок фильтров - синхронизируется с предыдущей)
        self.add_metric_card(
            row=0, col=5,
            object_name='agent_area_by_year',
            title='Площадь агента (за год)',
            value='0 м2',
            icon_path='resources/icons/codepen3.svg',
            border_color='#388E3C'
            # Без filters - синхронизируется с карточкой "Заказы агента"
        )

        self.set_column_stretch(6)

    def on_year_changed(self, year):
        """Обработка изменения года"""
        self.filter_agent_year = int(year)
        self._update_agent_stats()

    def on_agent_changed(self, agent):
        """Обработка изменения агента"""
        self.filter_agent_type = agent
        self._update_agent_stats()

    def _get_stats(self, year=None, agent_type=None):
        """Получить статистику из API или локальной БД"""
        try:
            if self.api_client and self.api_client.is_online:
                return self.api_client.get_contracts_dashboard_stats(year=year, agent_type=agent_type)
            else:
                return self.db.get_contracts_dashboard_stats(year=year, agent_type=agent_type)
        except Exception as e:
            print(f"[WARN] API error, using local DB: {e}")
            return self.db.get_contracts_dashboard_stats(year=year, agent_type=agent_type)

    def _update_agent_stats(self):
        """Обновить карточки агента"""
        try:
            stats = self._get_stats(year=self.filter_agent_year, agent_type=self.filter_agent_type)
            self.update_metric('agent_orders_by_year', str(stats['agent_orders_by_year']))
            self.update_metric('agent_area_by_year', f"{stats['agent_area_by_year']:,.0f} м2")
        except Exception as e:
            print(f"[ERROR] Ошибка обновления agent stats: {e}")

    def load_data(self):
        """Загрузка данных"""
        try:
            # Загружаем базовую статистику (без фильтров)
            stats = self._get_stats(year=None, agent_type=None)

            self.update_metric('individual_orders', str(stats['individual_orders']))
            self.update_metric('individual_area', f"{stats['individual_area']:,.0f} м2")
            self.update_metric('template_orders', str(stats['template_orders']))
            self.update_metric('template_area', f"{stats['template_area']:,.0f} м2")

            # Загружаем данные агента с фильтрами
            self._update_agent_stats()

        except Exception as e:
            print(f"[ERROR] Ошибка загрузки данных дашборда договоров: {e}")
            import traceback
            traceback.print_exc()


class CRMDashboard(DashboardWidget):
    """Дашборд для страницы СРМ (Индивидуальные/Шаблонные/Надзор)"""

    def __init__(self, db_manager, project_type, api_client=None, parent=None):
        """
        Args:
            project_type: 'Индивидуальный', 'Шаблонный', или 'Авторский надзор'
        """
        self.project_type = project_type
        super().__init__(db_manager, api_client, parent)

        try:
            self.agent_types = self.db.get_agent_types()
            if not self.agent_types:
                self.agent_types = ['Прямой', 'Агент', 'Партнер']
        except Exception as e:
            print(f"[WARN] Ошибка получения типов агентов: {e}")
            self.agent_types = ['Прямой', 'Агент', 'Партнер']

        # Независимые фильтры для каждой карточки
        self.filter_agent_active = None
        self.filter_agent_archive = None

        self.setup_ui()

    def setup_ui(self):
        """Создание UI дашборда"""

        # Определяем цвета в зависимости от типа проекта
        if self.project_type == 'Индивидуальный':
            color = '#F57C00'
        elif self.project_type == 'Шаблонный':
            color = '#C62828'
        else:  # Авторский надзор
            color = '#388E3C'

        # 1. Всего заказов
        self.add_metric_card(
            row=0, col=0,
            object_name='total_orders',
            title='Всего заказов',
            value='0',
            icon_path='resources/icons/clipboard1.svg',
            border_color=color
        )

        # 2. Всего площадь
        self.add_metric_card(
            row=0, col=1,
            object_name='total_area',
            title='Всего площадь',
            value='0 м2',
            icon_path='resources/icons/codepen1.svg',
            border_color=color
        )

        # 3. Активные заказы в СРМ
        self.add_metric_card(
            row=0, col=2,
            object_name='active_orders',
            title='Активные в СРМ',
            value='0',
            icon_path='resources/icons/active.svg',
            border_color='#4CAF50'
        )

        # 4. Архивные заказы
        self.add_metric_card(
            row=0, col=3,
            object_name='archive_orders',
            title='Архивные заказы',
            value='0',
            icon_path='resources/icons/archive.svg',
            border_color='#9E9E9E'
        )

        # 5. Активные заказы агента - НЕЗАВИСИМЫЙ фильтр
        card = self.add_metric_card(
            row=0, col=4,
            object_name='agent_active_orders',
            title='Активные агента',
            value='0',
            icon_path='resources/icons/team.svg',
            border_color='#2196F3',
            filters=[{'type': 'agent', 'options': self.agent_types}]
        )
        card.connect_filter('agent', self.on_agent_active_changed)

        # 6. Архивные заказы агента - НЕЗАВИСИМЫЙ фильтр
        card = self.add_metric_card(
            row=0, col=5,
            object_name='agent_archive_orders',
            title='Архивные агента',
            value='0',
            icon_path='resources/icons/archive.svg',
            border_color='#607D8B',
            filters=[{'type': 'agent', 'options': self.agent_types}]
        )
        card.connect_filter('agent', self.on_agent_archive_changed)

        self.set_column_stretch(6)

    def on_agent_active_changed(self, agent):
        """Обработка изменения агента для активных заказов"""
        self.filter_agent_active = agent
        self._update_agent_active()

    def on_agent_archive_changed(self, agent):
        """Обработка изменения агента для архивных заказов"""
        self.filter_agent_archive = agent
        self._update_agent_archive()

    def _get_stats(self, agent_type=None):
        """Получить статистику из API или локальной БД"""
        try:
            if self.api_client and self.api_client.is_online:
                return self.api_client.get_crm_dashboard_stats(
                    project_type=self.project_type,
                    agent_type=agent_type
                )
            else:
                return self.db.get_crm_dashboard_stats(
                    project_type=self.project_type,
                    agent_type=agent_type
                )
        except Exception as e:
            print(f"[WARN] API error, using local DB: {e}")
            return self.db.get_crm_dashboard_stats(
                project_type=self.project_type,
                agent_type=agent_type
            )

    def _update_agent_active(self):
        """Обновить карточку активных заказов агента"""
        try:
            stats = self._get_stats(agent_type=self.filter_agent_active)
            self.update_metric('agent_active_orders', str(stats['agent_active_orders']))
        except Exception as e:
            print(f"[ERROR] Ошибка обновления agent_active_orders: {e}")

    def _update_agent_archive(self):
        """Обновить карточку архивных заказов агента"""
        try:
            stats = self._get_stats(agent_type=self.filter_agent_archive)
            self.update_metric('agent_archive_orders', str(stats['agent_archive_orders']))
        except Exception as e:
            print(f"[ERROR] Ошибка обновления agent_archive_orders: {e}")

    def load_data(self):
        """Загрузка данных"""
        try:
            # Загружаем базовую статистику (без фильтров агента)
            stats = self._get_stats(agent_type=None)

            self.update_metric('total_orders', str(stats['total_orders']))
            self.update_metric('total_area', f"{stats['total_area']:,.0f} м2")
            self.update_metric('active_orders', str(stats['active_orders']))
            self.update_metric('archive_orders', str(stats['archive_orders']))

            # Загружаем данные агента с независимыми фильтрами
            self._update_agent_active()
            self._update_agent_archive()

        except Exception as e:
            print(f"[ERROR] Ошибка загрузки данных дашборда СРМ: {e}")
            import traceback
            traceback.print_exc()


class EmployeesDashboard(DashboardWidget):
    """Дашборд для страницы Сотрудники"""

    def __init__(self, db_manager, api_client=None, parent=None):
        super().__init__(db_manager, api_client, parent)
        self.setup_ui()
        # НЕ вызываем load_data() здесь - будет вызван в refresh() при показе дашборда

    def setup_ui(self):
        """Создание UI дашборда"""

        # 1. Активные сотрудники
        self.add_metric_card(
            row=0, col=0,
            object_name='active_employees',
            title='Активные сотрудники',
            value='0',
            icon_path='resources/icons/active.svg',
            border_color='#4CAF50'
        )

        # 2. Сотрудники в резерве
        self.add_metric_card(
            row=0, col=1,
            object_name='reserve_employees',
            title='Сотрудники в резерве',
            value='0',
            icon_path='resources/icons/pause.svg',
            border_color='#FF9800'
        )

        # 3. Руководящий состав
        self.add_metric_card(
            row=0, col=2,
            object_name='active_admin',
            title='Руководящий состав',
            value='0',
            icon_path='resources/icons/team.svg',
            border_color='#9C27B0'
        )

        # 4. Проектный отдел
        self.add_metric_card(
            row=0, col=3,
            object_name='active_project',
            title='Проектный отдел',
            value='0',
            icon_path='resources/icons/team.svg',
            border_color='#2196F3'
        )

        # 5. Исполнительный отдел
        self.add_metric_card(
            row=0, col=4,
            object_name='active_execution',
            title='Исполнительный отдел',
            value='0',
            icon_path='resources/icons/team.svg',
            border_color='#00BCD4'
        )

        # 6. Ближайший день рождения
        self.add_metric_card(
            row=0, col=5,
            object_name='nearest_birthday',
            title='Ближайший ДР',
            value='Нет данных',
            icon_path='resources/icons/birthday.svg',
            border_color='#E91E63'
        )

        self.set_column_stretch(6)

    def load_data(self):
        """Загрузка данных"""
        try:
            # Получаем статистику из API или локальной БД
            if self.api_client and self.api_client.is_online:
                try:
                    stats = self.api_client.get_employees_dashboard_stats()
                except Exception as e:
                    print(f"[WARN] API error, using local DB: {e}")
                    stats = self.db.get_employees_dashboard_stats()
            else:
                stats = self.db.get_employees_dashboard_stats()

            self.update_metric('active_employees', str(stats.get('active_employees', 0)))
            self.update_metric('reserve_employees', str(stats.get('reserve_employees', 0)))

            # Поддержка разных ключей от API и локальной БД
            active_admin = stats.get('active_admin') or stats.get('active_management', 0)
            active_project = stats.get('active_project') or stats.get('active_projects_dept', 0)
            active_execution = stats.get('active_execution') or stats.get('active_execution_dept', 0)

            self.update_metric('active_admin', str(active_admin))
            self.update_metric('active_project', str(active_project))
            self.update_metric('active_execution', str(active_execution))

            # Для дня рождения - поддержка разных ключей
            birthday_text = stats.get('nearest_birthday') or str(stats.get('upcoming_birthdays', 'Нет данных'))
            if isinstance(birthday_text, int):
                birthday_text = f"{birthday_text} чел."
            if len(str(birthday_text)) > 30:
                birthday_text = str(birthday_text)[:27] + '...'
            self.update_metric('nearest_birthday', str(birthday_text))

        except Exception as e:
            print(f"[ERROR] Ошибка загрузки данных дашборда сотрудников: {e}")
            import traceback
            traceback.print_exc()


class SalariesDashboard(DashboardWidget):
    """Дашборд для страницы Зарплаты"""

    def __init__(self, db_manager, api_client=None, parent=None):
        super().__init__(db_manager, api_client, parent)

        self.current_year = datetime.now().year
        self.current_month = datetime.now().month

        self.setup_ui()
        # НЕ вызываем load_data() здесь - будет вызван в refresh() при показе дашборда

    def setup_ui(self):
        """Создание UI дашборда"""

        # Динамический список годов из договоров
        years = self.get_years()

        months = [
            f'{i:02d} - {["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                         "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"][i-1]}'
            for i in range(1, 13)
        ]

        # 1. Всего выплачено
        self.add_metric_card(
            row=0, col=0,
            object_name='total_paid',
            title='Всего выплачено',
            value='0 руб',
            icon_path='resources/icons/money.svg',
            border_color='#4CAF50'
        )

        # 2. Выплачено за год
        card = self.add_metric_card(
            row=0, col=1,
            object_name='paid_by_year',
            title='Выплачено за год',
            value='0 руб',
            icon_path='resources/icons/dollar.svg',
            border_color='#2196F3',
            filters=[{'type': 'year', 'options': years}]
        )
        card.connect_filter('year', self.on_year_changed)

        # 3. Выплачено за месяц
        card = self.add_metric_card(
            row=0, col=2,
            object_name='paid_by_month',
            title='Выплачено за месяц',
            value='0 руб',
            icon_path='resources/icons/calendar.svg',
            border_color='#FF9800',
            filters=[
                {'type': 'month', 'options': months},
                {'type': 'year', 'options': years}
            ]
        )
        card.connect_filter('month', self.on_month_changed)
        card.connect_filter('year', self.on_year_changed)

        # 4. Индивидуальные за год
        card = self.add_metric_card(
            row=0, col=3,
            object_name='individual_by_year',
            title='Индивидуальные (год)',
            value='0 руб',
            icon_path='resources/icons/clipboard1.svg',
            border_color='#F57C00',
            filters=[{'type': 'year', 'options': years}]
        )
        card.connect_filter('year', self.on_year_changed)

        # 5. Шаблонные за год
        card = self.add_metric_card(
            row=0, col=4,
            object_name='template_by_year',
            title='Шаблонные (год)',
            value='0 руб',
            icon_path='resources/icons/clipboard2.svg',
            border_color='#C62828',
            filters=[{'type': 'year', 'options': years}]
        )
        card.connect_filter('year', self.on_year_changed)

        # 6. Авторские надзоры за год
        card = self.add_metric_card(
            row=0, col=5,
            object_name='supervision_by_year',
            title='Авт. надзоры (год)',
            value='0 руб',
            icon_path='resources/icons/clipboard3.svg',
            border_color='#388E3C',
            filters=[{'type': 'year', 'options': years}]
        )
        card.connect_filter('year', self.on_year_changed)

        self.set_column_stretch(6)

    def on_year_changed(self, year):
        """Обработка изменения года"""
        self.current_year = int(year)
        self.load_data()

    def on_month_changed(self, month_str):
        """Обработка изменения месяца"""
        # Извлекаем номер месяца из строки "01 - Январь"
        self.current_month = int(month_str.split(' - ')[0])
        self.load_data()

    def load_data(self):
        """Загрузка данных"""
        try:
            # Получаем статистику из API или локальной БД
            if self.api_client and self.api_client.is_online:
                try:
                    stats = self.api_client.get_salaries_dashboard_stats(
                        year=self.current_year,
                        month=self.current_month
                    )
                except Exception as e:
                    print(f"[WARN] API error, using local DB: {e}")
                    stats = self.db.get_salaries_dashboard_stats(
                        year=self.current_year,
                        month=self.current_month
                    )
            else:
                stats = self.db.get_salaries_dashboard_stats(
                    year=self.current_year,
                    month=self.current_month
                )

            self.update_metric('total_paid', f"{stats['total_paid']:,.0f} руб")
            self.update_metric('paid_by_year', f"{stats['paid_by_year']:,.0f} руб")
            self.update_metric('paid_by_month', f"{stats['paid_by_month']:,.0f} руб")
            self.update_metric('individual_by_year', f"{stats['individual_by_year']:,.0f} руб")
            self.update_metric('template_by_year', f"{stats['template_by_year']:,.0f} руб")
            self.update_metric('supervision_by_year', f"{stats['supervision_by_year']:,.0f} руб")

        except Exception as e:
            print(f"[ERROR] Ошибка загрузки данных дашборда зарплат: {e}")


class SalariesAllPaymentsDashboard(DashboardWidget):
    """Дашборд для вкладки 'Все выплаты'
    6 карточек: Всего выплачено, За год, За месяц, Индивидуальные(год), Шаблонные(год), Надзор(год)
    ВАЖНО: Учитываются ТОЛЬКО платежи со статусом 'Оплачено'
    """

    def __init__(self, db_manager, api_client=None, parent=None):
        super().__init__(db_manager, api_client, parent)
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.setup_ui()

    def setup_ui(self):
        years = self.get_years()
        months = [
            f'{i:02d} - {["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"][i-1]}'
            for i in range(1, 13)
        ]

        # 1. Всего выплачено
        self.add_metric_card(
            row=0, col=0,
            object_name='total_paid',
            title='Всего выплачено',
            value='0 руб',
            icon_path='resources/icons/money.svg',
            border_color='#4CAF50'
        )

        # 2. Выплачено за год (с селектором года)
        card = self.add_metric_card(
            row=0, col=1,
            object_name='paid_by_year',
            title='Выплачено за год',
            value='0 руб',
            icon_path='resources/icons/dollar.svg',
            border_color='#2196F3',
            filters=[{'type': 'year', 'options': years}]
        )
        card.connect_filter('year', self.on_year_changed)

        # 3. Выплачено за месяц (с селекторами года и месяца)
        card = self.add_metric_card(
            row=0, col=2,
            object_name='paid_by_month',
            title='Выплачено за месяц',
            value='0 руб',
            icon_path='resources/icons/calendar.svg',
            border_color='#FF9800',
            filters=[
                {'type': 'year', 'options': years},
                {'type': 'month', 'options': months}
            ]
        )
        card.connect_filter('year', self.on_month_year_changed)
        card.connect_filter('month', self.on_month_changed)

        # 4. Индивидуальные (год) - привязан к году из п.2
        self.add_metric_card(
            row=0, col=3,
            object_name='individual_by_year',
            title='Индивидуальные (ГОД)',
            value='0 руб',
            icon_path='resources/icons/clipboard1.svg',
            border_color='#F57C00'
        )

        # 5. Шаблонные (год) - привязан к году из п.2
        self.add_metric_card(
            row=0, col=4,
            object_name='template_by_year',
            title='Шаблонные (ГОД)',
            value='0 руб',
            icon_path='resources/icons/clipboard2.svg',
            border_color='#C62828'
        )

        # 6. Авторский надзор (год) - привязан к году из п.2
        self.add_metric_card(
            row=0, col=5,
            object_name='supervision_by_year',
            title='Авт. надзор (ГОД)',
            value='0 руб',
            icon_path='resources/icons/eye.svg',
            border_color='#388E3C'
        )

        self.set_column_stretch(6)

    def on_year_changed(self, year):
        """Изменение года - обновляет карточки 2, 4, 5, 6"""
        self.current_year = int(year)
        self._update_year_based_cards()

    def on_month_year_changed(self, year):
        """Изменение года для месячной карточки"""
        self.current_year = int(year)
        self._update_month_card()

    def on_month_changed(self, month_str):
        """Изменение месяца"""
        self.current_month = int(month_str.split(' - ')[0])
        self._update_month_card()

    def _get_stats(self, year=None, month=None):
        """Получить статистику"""
        try:
            if self.api_client and self.api_client.is_online:
                return self.api_client.get_salaries_all_payments_stats(year=year, month=month)
            else:
                return self.db.get_salaries_all_payments_stats(year=year, month=month)
        except Exception as e:
            print(f"[WARN] Ошибка получения статистики AllPayments: {e}")
            return {'total_paid': 0, 'paid_by_year': 0, 'paid_by_month': 0,
                    'individual_by_year': 0, 'template_by_year': 0, 'supervision_by_year': 0}

    def _update_year_based_cards(self):
        """Обновить карточки зависящие от года"""
        try:
            stats = self._get_stats(year=self.current_year)
            self.update_metric('paid_by_year', f"{stats['paid_by_year']:,.0f} руб")
            self.update_metric('individual_by_year', f"{stats['individual_by_year']:,.0f} руб")
            self.update_metric('template_by_year', f"{stats['template_by_year']:,.0f} руб")
            self.update_metric('supervision_by_year', f"{stats['supervision_by_year']:,.0f} руб")
        except Exception as e:
            print(f"[ERROR] Ошибка обновления год-карточек: {e}")

    def _update_month_card(self):
        """Обновить карточку месяца"""
        try:
            stats = self._get_stats(year=self.current_year, month=self.current_month)
            self.update_metric('paid_by_month', f"{stats['paid_by_month']:,.0f} руб")
        except Exception as e:
            print(f"[ERROR] Ошибка обновления месяц-карточки: {e}")

    def load_data(self):
        """Загрузка данных"""
        try:
            stats = self._get_stats()
            self.update_metric('total_paid', f"{stats['total_paid']:,.0f} руб")
            self._update_year_based_cards()
            self._update_month_card()
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки дашборда 'Все выплаты': {e}")


class SalariesIndividualDashboard(DashboardWidget):
    """Дашборд для вкладки 'Индивидуальные'
    6 карточек: Всего выплачено, За год, За месяц, По агенту, Средний чек, Кол-во выплат
    """

    def __init__(self, db_manager, api_client=None, parent=None):
        super().__init__(db_manager, api_client, parent)
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.filter_agent_type = None

        try:
            self.agent_types = self.db.get_agent_types()
            if not self.agent_types:
                self.agent_types = ['Фестиваль', 'Петрович']
        except:
            self.agent_types = ['Фестиваль', 'Петрович']

        self.setup_ui()

    def setup_ui(self):
        years = self.get_years()
        months = [
            f'{i:02d} - {["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"][i-1]}'
            for i in range(1, 13)
        ]

        # 1. Всего выплачено
        self.add_metric_card(
            row=0, col=0,
            object_name='total_paid',
            title='Всего выплачено',
            value='0 руб',
            icon_path='resources/icons/money.svg',
            border_color='#F57C00'
        )

        # 2. Выплачено за год
        card = self.add_metric_card(
            row=0, col=1,
            object_name='paid_by_year',
            title='Выплачено за год',
            value='0 руб',
            icon_path='resources/icons/dollar.svg',
            border_color='#2196F3',
            filters=[{'type': 'year', 'options': years}]
        )
        card.connect_filter('year', self.on_year_changed)

        # 3. Выплачено за месяц
        card = self.add_metric_card(
            row=0, col=2,
            object_name='paid_by_month',
            title='Выплачено за месяц',
            value='0 руб',
            icon_path='resources/icons/calendar.svg',
            border_color='#FF9800',
            filters=[
                {'type': 'year', 'options': years},
                {'type': 'month', 'options': months}
            ]
        )
        card.connect_filter('year', self.on_month_year_changed)
        card.connect_filter('month', self.on_month_changed)

        # 4. По типу агента
        card = self.add_metric_card(
            row=0, col=3,
            object_name='by_agent',
            title='По типу агента',
            value='0 руб',
            icon_path='resources/icons/user.svg',
            border_color='#9C27B0',
            filters=[{'type': 'agent', 'options': self.agent_types}]
        )
        card.connect_filter('agent', self.on_agent_changed)

        # 5. Средний чек
        self.add_metric_card(
            row=0, col=4,
            object_name='avg_payment',
            title='Средний чек',
            value='0 руб',
            icon_path='resources/icons/trending-up.svg',
            border_color='#00BCD4'
        )

        # 6. Кол-во выплат (привязан к году)
        self.add_metric_card(
            row=0, col=5,
            object_name='payments_count',
            title='Кол-во выплат',
            value='0',
            icon_path='resources/icons/layers.svg',
            border_color='#607D8B'
        )

        self.set_column_stretch(6)

    def on_year_changed(self, year):
        self.current_year = int(year)
        self._update_year_based_cards()

    def on_month_year_changed(self, year):
        self.current_year = int(year)
        self._update_month_card()

    def on_month_changed(self, month_str):
        self.current_month = int(month_str.split(' - ')[0])
        self._update_month_card()

    def on_agent_changed(self, agent):
        self.filter_agent_type = agent
        self._update_agent_card()

    def _get_stats(self, year=None, month=None, agent_type=None):
        try:
            if self.api_client and self.api_client.is_online:
                return self.api_client.get_salaries_individual_stats(year=year, month=month, agent_type=agent_type)
            else:
                return self.db.get_salaries_individual_stats(year=year, month=month, agent_type=agent_type)
        except Exception as e:
            print(f"[WARN] Ошибка получения статистики Individual: {e}")
            return {'total_paid': 0, 'paid_by_year': 0, 'paid_by_month': 0,
                    'by_agent': 0, 'avg_payment': 0, 'payments_count': 0}

    def _update_year_based_cards(self):
        try:
            stats = self._get_stats(year=self.current_year)
            self.update_metric('paid_by_year', f"{stats['paid_by_year']:,.0f} руб")
            self.update_metric('payments_count', str(stats['payments_count']))
        except Exception as e:
            print(f"[ERROR] Ошибка обновления год-карточек: {e}")

    def _update_month_card(self):
        try:
            stats = self._get_stats(year=self.current_year, month=self.current_month)
            self.update_metric('paid_by_month', f"{stats['paid_by_month']:,.0f} руб")
        except Exception as e:
            print(f"[ERROR] Ошибка обновления месяц-карточки: {e}")

    def _update_agent_card(self):
        try:
            stats = self._get_stats(agent_type=self.filter_agent_type)
            self.update_metric('by_agent', f"{stats['by_agent']:,.0f} руб")
        except Exception as e:
            print(f"[ERROR] Ошибка обновления агент-карточки: {e}")

    def load_data(self):
        try:
            stats = self._get_stats()
            self.update_metric('total_paid', f"{stats['total_paid']:,.0f} руб")
            self.update_metric('avg_payment', f"{stats['avg_payment']:,.0f} руб")
            self._update_year_based_cards()
            self._update_month_card()
            self._update_agent_card()
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки дашборда 'Индивидуальные': {e}")


class SalariesTemplateDashboard(DashboardWidget):
    """Дашборд для вкладки 'Шаблонные'
    6 карточек: Всего выплачено, За год, За месяц, По агенту, Средний чек, Кол-во выплат
    """

    def __init__(self, db_manager, api_client=None, parent=None):
        super().__init__(db_manager, api_client, parent)
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.filter_agent_type = None

        try:
            self.agent_types = self.db.get_agent_types()
            if not self.agent_types:
                self.agent_types = ['Фестиваль', 'Петрович']
        except:
            self.agent_types = ['Фестиваль', 'Петрович']

        self.setup_ui()

    def setup_ui(self):
        years = self.get_years()
        months = [
            f'{i:02d} - {["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"][i-1]}'
            for i in range(1, 13)
        ]

        # 1. Всего выплачено
        self.add_metric_card(
            row=0, col=0,
            object_name='total_paid',
            title='Всего выплачено',
            value='0 руб',
            icon_path='resources/icons/money.svg',
            border_color='#C62828'
        )

        # 2. Выплачено за год
        card = self.add_metric_card(
            row=0, col=1,
            object_name='paid_by_year',
            title='Выплачено за год',
            value='0 руб',
            icon_path='resources/icons/dollar.svg',
            border_color='#2196F3',
            filters=[{'type': 'year', 'options': years}]
        )
        card.connect_filter('year', self.on_year_changed)

        # 3. Выплачено за месяц
        card = self.add_metric_card(
            row=0, col=2,
            object_name='paid_by_month',
            title='Выплачено за месяц',
            value='0 руб',
            icon_path='resources/icons/calendar.svg',
            border_color='#FF9800',
            filters=[
                {'type': 'year', 'options': years},
                {'type': 'month', 'options': months}
            ]
        )
        card.connect_filter('year', self.on_month_year_changed)
        card.connect_filter('month', self.on_month_changed)

        # 4. По типу агента
        card = self.add_metric_card(
            row=0, col=3,
            object_name='by_agent',
            title='По типу агента',
            value='0 руб',
            icon_path='resources/icons/user.svg',
            border_color='#9C27B0',
            filters=[{'type': 'agent', 'options': self.agent_types}]
        )
        card.connect_filter('agent', self.on_agent_changed)

        # 5. Средний чек
        self.add_metric_card(
            row=0, col=4,
            object_name='avg_payment',
            title='Средний чек',
            value='0 руб',
            icon_path='resources/icons/trending-up.svg',
            border_color='#00BCD4'
        )

        # 6. Кол-во выплат
        self.add_metric_card(
            row=0, col=5,
            object_name='payments_count',
            title='Кол-во выплат',
            value='0',
            icon_path='resources/icons/layers.svg',
            border_color='#607D8B'
        )

        self.set_column_stretch(6)

    def on_year_changed(self, year):
        self.current_year = int(year)
        self._update_year_based_cards()

    def on_month_year_changed(self, year):
        self.current_year = int(year)
        self._update_month_card()

    def on_month_changed(self, month_str):
        self.current_month = int(month_str.split(' - ')[0])
        self._update_month_card()

    def on_agent_changed(self, agent):
        self.filter_agent_type = agent
        self._update_agent_card()

    def _get_stats(self, year=None, month=None, agent_type=None):
        try:
            if self.api_client and self.api_client.is_online:
                return self.api_client.get_salaries_template_stats(year=year, month=month, agent_type=agent_type)
            else:
                return self.db.get_salaries_template_stats(year=year, month=month, agent_type=agent_type)
        except Exception as e:
            print(f"[WARN] Ошибка получения статистики: {e}")
            return {'total_paid': 0, 'paid_by_year': 0, 'paid_by_month': 0,
                    'by_agent': 0, 'avg_payment': 0, 'payments_count': 0}

    def _update_year_based_cards(self):
        try:
            stats = self._get_stats(year=self.current_year)
            self.update_metric('paid_by_year', f"{stats['paid_by_year']:,.0f} руб")
            self.update_metric('payments_count', str(stats['payments_count']))
        except Exception as e:
            print(f"[ERROR] Ошибка обновления год-карточек: {e}")

    def _update_month_card(self):
        try:
            stats = self._get_stats(year=self.current_year, month=self.current_month)
            self.update_metric('paid_by_month', f"{stats['paid_by_month']:,.0f} руб")
        except Exception as e:
            print(f"[ERROR] Ошибка обновления месяц-карточки: {e}")

    def _update_agent_card(self):
        try:
            stats = self._get_stats(agent_type=self.filter_agent_type)
            self.update_metric('by_agent', f"{stats['by_agent']:,.0f} руб")
        except Exception as e:
            print(f"[ERROR] Ошибка обновления агент-карточки: {e}")

    def load_data(self):
        try:
            stats = self._get_stats()
            self.update_metric('total_paid', f"{stats['total_paid']:,.0f} руб")
            self.update_metric('avg_payment', f"{stats['avg_payment']:,.0f} руб")
            self._update_year_based_cards()
            self._update_month_card()
            self._update_agent_card()
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки дашборда 'Шаблонные': {e}")


class SalariesSalaryDashboard(DashboardWidget):
    """Дашборд для вкладки 'Оклады'
    6 карточек: Всего выплачено, За год, За месяц, По типу проекта, Средний оклад, Кол-во сотрудников
    """

    def __init__(self, db_manager, api_client=None, parent=None):
        super().__init__(db_manager, api_client, parent)
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.filter_project_type = None

        self.project_types = ['Индивидуальный', 'Шаблонный', 'Авторский надзор']
        self.setup_ui()

    def setup_ui(self):
        years = self.get_years()
        months = [
            f'{i:02d} - {["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"][i-1]}'
            for i in range(1, 13)
        ]

        # 1. Всего выплачено
        self.add_metric_card(
            row=0, col=0,
            object_name='total_paid',
            title='Всего выплачено',
            value='0 руб',
            icon_path='resources/icons/money.svg',
            border_color='#9C27B0'
        )

        # 2. Выплачено за год
        card = self.add_metric_card(
            row=0, col=1,
            object_name='paid_by_year',
            title='Выплачено за год',
            value='0 руб',
            icon_path='resources/icons/dollar.svg',
            border_color='#2196F3',
            filters=[{'type': 'year', 'options': years}]
        )
        card.connect_filter('year', self.on_year_changed)

        # 3. Выплачено за месяц
        card = self.add_metric_card(
            row=0, col=2,
            object_name='paid_by_month',
            title='Выплачено за месяц',
            value='0 руб',
            icon_path='resources/icons/calendar.svg',
            border_color='#FF9800',
            filters=[
                {'type': 'year', 'options': years},
                {'type': 'month', 'options': months}
            ]
        )
        card.connect_filter('year', self.on_month_year_changed)
        card.connect_filter('month', self.on_month_changed)

        # 4. По типу проекта
        card = self.add_metric_card(
            row=0, col=3,
            object_name='by_project_type',
            title='По типу проекта',
            value='0 руб',
            icon_path='resources/icons/briefcase.svg',
            border_color='#F57C00',
            filters=[{'type': 'project_type', 'options': self.project_types}]
        )
        card.connect_filter('project_type', self.on_project_type_changed)

        # 5. Средний оклад
        self.add_metric_card(
            row=0, col=4,
            object_name='avg_salary',
            title='Средний оклад',
            value='0 руб',
            icon_path='resources/icons/trending-up.svg',
            border_color='#00BCD4'
        )

        # 6. Кол-во сотрудников (уникальных за год)
        self.add_metric_card(
            row=0, col=5,
            object_name='employees_count',
            title='Кол-во сотрудников',
            value='0',
            icon_path='resources/icons/users.svg',
            border_color='#607D8B'
        )

        self.set_column_stretch(6)

    def on_year_changed(self, year):
        self.current_year = int(year)
        self._update_year_based_cards()

    def on_month_year_changed(self, year):
        self.current_year = int(year)
        self._update_month_card()

    def on_month_changed(self, month_str):
        self.current_month = int(month_str.split(' - ')[0])
        self._update_month_card()

    def on_project_type_changed(self, project_type):
        self.filter_project_type = project_type
        self._update_project_type_card()

    def _get_stats(self, year=None, month=None, project_type=None):
        try:
            if self.api_client and self.api_client.is_online:
                return self.api_client.get_salaries_salary_stats(year=year, month=month, project_type=project_type)
            else:
                return self.db.get_salaries_salary_stats(year=year, month=month, project_type=project_type)
        except Exception as e:
            print(f"[WARN] Ошибка получения статистики: {e}")
            return {'total_paid': 0, 'paid_by_year': 0, 'paid_by_month': 0,
                    'by_project_type': 0, 'avg_salary': 0, 'employees_count': 0}

    def _update_year_based_cards(self):
        try:
            stats = self._get_stats(year=self.current_year)
            self.update_metric('paid_by_year', f"{stats['paid_by_year']:,.0f} руб")
            self.update_metric('employees_count', str(stats['employees_count']))
        except Exception as e:
            print(f"[ERROR] Ошибка обновления год-карточек: {e}")

    def _update_month_card(self):
        try:
            stats = self._get_stats(year=self.current_year, month=self.current_month)
            self.update_metric('paid_by_month', f"{stats['paid_by_month']:,.0f} руб")
        except Exception as e:
            print(f"[ERROR] Ошибка обновления месяц-карточки: {e}")

    def _update_project_type_card(self):
        try:
            stats = self._get_stats(project_type=self.filter_project_type)
            self.update_metric('by_project_type', f"{stats['by_project_type']:,.0f} руб")
        except Exception as e:
            print(f"[ERROR] Ошибка обновления project_type-карточки: {e}")

    def load_data(self):
        try:
            stats = self._get_stats()
            self.update_metric('total_paid', f"{stats['total_paid']:,.0f} руб")
            self.update_metric('avg_salary', f"{stats['avg_salary']:,.0f} руб")
            self._update_year_based_cards()
            self._update_month_card()
            self._update_project_type_card()
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки дашборда 'Оклады': {e}")


class SalariesSupervisionDashboard(DashboardWidget):
    """Дашборд для вкладки 'Авторский надзор'
    6 карточек: Всего выплачено, За год, За месяц, По агенту, Средний чек, Кол-во выплат
    """

    def __init__(self, db_manager, api_client=None, parent=None):
        super().__init__(db_manager, api_client, parent)
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.filter_agent_type = None

        try:
            self.agent_types = self.db.get_agent_types()
            if not self.agent_types:
                self.agent_types = ['Фестиваль', 'Петрович']
        except:
            self.agent_types = ['Фестиваль', 'Петрович']

        self.setup_ui()

    def setup_ui(self):
        years = self.get_years()
        months = [
            f'{i:02d} - {["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"][i-1]}'
            for i in range(1, 13)
        ]

        # 1. Всего выплачено
        self.add_metric_card(
            row=0, col=0,
            object_name='total_paid',
            title='Всего выплачено',
            value='0 руб',
            icon_path='resources/icons/money.svg',
            border_color='#388E3C'
        )

        # 2. Выплачено за год
        card = self.add_metric_card(
            row=0, col=1,
            object_name='paid_by_year',
            title='Выплачено за год',
            value='0 руб',
            icon_path='resources/icons/dollar.svg',
            border_color='#2196F3',
            filters=[{'type': 'year', 'options': years}]
        )
        card.connect_filter('year', self.on_year_changed)

        # 3. Выплачено за месяц
        card = self.add_metric_card(
            row=0, col=2,
            object_name='paid_by_month',
            title='Выплачено за месяц',
            value='0 руб',
            icon_path='resources/icons/calendar.svg',
            border_color='#FF9800',
            filters=[
                {'type': 'year', 'options': years},
                {'type': 'month', 'options': months}
            ]
        )
        card.connect_filter('year', self.on_month_year_changed)
        card.connect_filter('month', self.on_month_changed)

        # 4. По типу агента
        card = self.add_metric_card(
            row=0, col=3,
            object_name='by_agent',
            title='По типу агента',
            value='0 руб',
            icon_path='resources/icons/user.svg',
            border_color='#9C27B0',
            filters=[{'type': 'agent', 'options': self.agent_types}]
        )
        card.connect_filter('agent', self.on_agent_changed)

        # 5. Средний чек
        self.add_metric_card(
            row=0, col=4,
            object_name='avg_payment',
            title='Средний чек',
            value='0 руб',
            icon_path='resources/icons/trending-up.svg',
            border_color='#00BCD4'
        )

        # 6. Кол-во выплат
        self.add_metric_card(
            row=0, col=5,
            object_name='payments_count',
            title='Кол-во выплат',
            value='0',
            icon_path='resources/icons/layers.svg',
            border_color='#607D8B'
        )

        self.set_column_stretch(6)

    def on_year_changed(self, year):
        self.current_year = int(year)
        self._update_year_based_cards()

    def on_month_year_changed(self, year):
        self.current_year = int(year)
        self._update_month_card()

    def on_month_changed(self, month_str):
        self.current_month = int(month_str.split(' - ')[0])
        self._update_month_card()

    def on_agent_changed(self, agent):
        self.filter_agent_type = agent
        self._update_agent_card()

    def _get_stats(self, year=None, month=None, agent_type=None):
        try:
            if self.api_client and self.api_client.is_online:
                return self.api_client.get_salaries_supervision_stats(year=year, month=month, agent_type=agent_type)
            else:
                return self.db.get_salaries_supervision_stats(year=year, month=month, agent_type=agent_type)
        except Exception as e:
            print(f"[WARN] Ошибка получения статистики: {e}")
            return {'total_paid': 0, 'paid_by_year': 0, 'paid_by_month': 0,
                    'by_agent': 0, 'avg_payment': 0, 'payments_count': 0}

    def _update_year_based_cards(self):
        try:
            stats = self._get_stats(year=self.current_year)
            self.update_metric('paid_by_year', f"{stats['paid_by_year']:,.0f} руб")
            self.update_metric('payments_count', str(stats['payments_count']))
        except Exception as e:
            print(f"[ERROR] Ошибка обновления год-карточек: {e}")

    def _update_month_card(self):
        try:
            stats = self._get_stats(year=self.current_year, month=self.current_month)
            self.update_metric('paid_by_month', f"{stats['paid_by_month']:,.0f} руб")
        except Exception as e:
            print(f"[ERROR] Ошибка обновления месяц-карточки: {e}")

    def _update_agent_card(self):
        try:
            stats = self._get_stats(agent_type=self.filter_agent_type)
            self.update_metric('by_agent', f"{stats['by_agent']:,.0f} руб")
        except Exception as e:
            print(f"[ERROR] Ошибка обновления агент-карточки: {e}")

    def load_data(self):
        try:
            stats = self._get_stats()
            self.update_metric('total_paid', f"{stats['total_paid']:,.0f} руб")
            self.update_metric('avg_payment', f"{stats['avg_payment']:,.0f} руб")
            self._update_year_based_cards()
            self._update_month_card()
            self._update_agent_card()
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки дашборда 'Авторский надзор': {e}")


class ReportsStatisticsDashboard(DashboardWidget):
    """Агрегированный дашборд для страницы Отчеты и статистика
    Объединяет данные: Клиенты + Договора + СРМ + Надзор
    """

    def __init__(self, db_manager, api_client=None, parent=None):
        super().__init__(db_manager, api_client, parent)
        self.setup_ui()
        # НЕ вызываем load_data() здесь - будет вызван в refresh() при показе дашборда

    def setup_ui(self):
        """Создание UI агрегированного дашборда"""

        # Строка 1: Клиенты
        self.add_metric_card(
            row=0, col=0,
            object_name='total_clients',
            title='Всего клиентов',
            value='0',
            icon_path='resources/icons/users.svg',
            border_color='#2196F3'
        )

        self.add_metric_card(
            row=0, col=1,
            object_name='total_individual_clients',
            title='Физические лица',
            value='0',
            icon_path='resources/icons/user.svg',
            border_color='#4CAF50'
        )

        self.add_metric_card(
            row=0, col=2,
            object_name='total_legal_clients',
            title='Юридические лица',
            value='0',
            icon_path='resources/icons/briefcase.svg',
            border_color='#FF9800'
        )

        # Строка 2: Договора
        self.add_metric_card(
            row=0, col=3,
            object_name='individual_orders',
            title='Индивидуальные заказы',
            value='0',
            icon_path='resources/icons/clipboard1.svg',
            border_color='#F57C00'
        )

        self.add_metric_card(
            row=0, col=4,
            object_name='template_orders',
            title='Шаблонные заказы',
            value='0',
            icon_path='resources/icons/clipboard2.svg',
            border_color='#C62828'
        )

        self.add_metric_card(
            row=0, col=5,
            object_name='supervision_orders',
            title='Надзоры',
            value='0',
            icon_path='resources/icons/eye.svg',
            border_color='#388E3C'
        )

        # Строка 3: СРМ активные
        self.add_metric_card(
            row=1, col=0,
            object_name='crm_individual_active',
            title='СРМ Индивидуальные (активные)',
            value='0',
            icon_path='resources/icons/activity.svg',
            border_color='#F57C00'
        )

        self.add_metric_card(
            row=1, col=1,
            object_name='crm_template_active',
            title='СРМ Шаблонные (активные)',
            value='0',
            icon_path='resources/icons/activity.svg',
            border_color='#C62828'
        )

        self.add_metric_card(
            row=1, col=2,
            object_name='crm_supervision_active',
            title='СРМ Надзор (активные)',
            value='0',
            icon_path='resources/icons/check-circle.svg',
            border_color='#388E3C'
        )

        # Строка 3: СРМ архив
        self.add_metric_card(
            row=1, col=3,
            object_name='crm_individual_archive',
            title='СРМ Индивидуальные (архив)',
            value='0',
            icon_path='resources/icons/archive.svg',
            border_color='#9E9E9E'
        )

        self.add_metric_card(
            row=1, col=4,
            object_name='crm_template_archive',
            title='СРМ Шаблонные (архив)',
            value='0',
            icon_path='resources/icons/archive.svg',
            border_color='#9E9E9E'
        )

        self.add_metric_card(
            row=1, col=5,
            object_name='crm_supervision_archive',
            title='СРМ Надзор (архив)',
            value='0',
            icon_path='resources/icons/x-circle.svg',
            border_color='#9E9E9E'
        )

        self.set_column_stretch(6)

    def load_data(self):
        """Загрузка агрегированных данных"""
        try:
            if not self.db:
                print(f"[ERROR] self.db is None in ReportsStatisticsDashboard.load_data()")
                return

            # Проверяем статус подключения один раз
            use_api = self.api_client and self.api_client.is_online

            # Загружаем данные клиентов
            if use_api:
                try:
                    clients_stats = self.api_client.get_clients_dashboard_stats()
                except Exception:
                    clients_stats = self.db.get_clients_dashboard_stats()
            else:
                clients_stats = self.db.get_clients_dashboard_stats()

            # Загружаем данные договоров
            if use_api:
                try:
                    contracts_stats = self.api_client.get_contracts_dashboard_stats()
                except Exception:
                    contracts_stats = self.db.get_contracts_dashboard_stats()
            else:
                contracts_stats = self.db.get_contracts_dashboard_stats()

            # Загружаем данные СРМ
            if use_api:
                try:
                    crm_individual = self.api_client.get_crm_dashboard_stats('Индивидуальный')
                    crm_template = self.api_client.get_crm_dashboard_stats('Шаблонный')
                    crm_supervision = self.api_client.get_crm_dashboard_stats('Авторский надзор')
                except Exception:
                    crm_individual = self.db.get_crm_dashboard_stats('Индивидуальный')
                    crm_template = self.db.get_crm_dashboard_stats('Шаблонный')
                    crm_supervision = self.db.get_crm_dashboard_stats('Авторский надзор')
            else:
                crm_individual = self.db.get_crm_dashboard_stats('Индивидуальный')
                crm_template = self.db.get_crm_dashboard_stats('Шаблонный')
                crm_supervision = self.db.get_crm_dashboard_stats('Авторский надзор')

            # Обновляем метрики клиентов
            self.update_metric('total_clients', str(clients_stats.get('total_clients', 0)))
            self.update_metric('total_individual_clients', str(clients_stats.get('total_individual', 0)))
            self.update_metric('total_legal_clients', str(clients_stats.get('total_legal', 0)))

            # Обновляем метрики договоров
            self.update_metric('individual_orders', str(contracts_stats.get('individual_orders', 0)))
            self.update_metric('template_orders', str(contracts_stats.get('template_orders', 0)))

            # Надзоры считаем из СРМ надзора
            supervision_total = crm_supervision.get('total_orders', 0)
            self.update_metric('supervision_orders', str(supervision_total))

            # Обновляем метрики СРМ
            self.update_metric('crm_individual_active', str(crm_individual.get('active_orders', 0)))
            self.update_metric('crm_template_active', str(crm_template.get('active_orders', 0)))
            self.update_metric('crm_supervision_active', str(crm_supervision.get('active_orders', 0)))

            self.update_metric('crm_individual_archive', str(crm_individual.get('archive_orders', 0)))
            self.update_metric('crm_template_archive', str(crm_template.get('archive_orders', 0)))
            self.update_metric('crm_supervision_archive', str(crm_supervision.get('archive_orders', 0)))

        except Exception as e:
            print(f"[ERROR] Ошибка загрузки агрегированного дашборда отчетов: {e}")
            import traceback
            traceback.print_exc()


class EmployeeReportsDashboard(DashboardWidget):
    """Агрегированный дашборд для страницы Отчеты по сотрудникам
    Объединяет данные: Сотрудники + Зарплаты
    """

    def __init__(self, db_manager, api_client=None, parent=None):
        super().__init__(db_manager, api_client, parent)

        self.current_year = datetime.now().year
        self.current_month = datetime.now().month

        self.setup_ui()
        # НЕ вызываем load_data() здесь - будет вызван в refresh() при показе дашборда

    def setup_ui(self):
        """Создание UI агрегированного дашборда"""

        # Динамический список годов из договоров
        years = self.get_years()

        months = [
            ('Январь', 1), ('Февраль', 2), ('Март', 3), ('Апрель', 4),
            ('Май', 5), ('Июнь', 6), ('Июль', 7), ('Август', 8),
            ('Сентябрь', 9), ('Октябрь', 10), ('Ноябрь', 11), ('Декабрь', 12)
        ]

        # Строка 1: Сотрудники
        self.add_metric_card(
            row=0, col=0,
            object_name='active_employees',
            title='Активные сотрудники',
            value='0',
            icon_path='resources/icons/users.svg',
            border_color='#2196F3'
        )

        self.add_metric_card(
            row=0, col=1,
            object_name='reserve_employees',
            title='Резерв',
            value='0',
            icon_path='resources/icons/user-minus.svg',
            border_color='#9E9E9E'
        )

        self.add_metric_card(
            row=0, col=2,
            object_name='active_management',
            title='Руководство',
            value='0',
            icon_path='resources/icons/award.svg',
            border_color='#FF9800'
        )

        self.add_metric_card(
            row=0, col=3,
            object_name='active_projects_dept',
            title='Отдел проектов',
            value='0',
            icon_path='resources/icons/briefcase.svg',
            border_color='#4CAF50'
        )

        self.add_metric_card(
            row=0, col=4,
            object_name='active_execution_dept',
            title='Отдел реализации',
            value='0',
            icon_path='resources/icons/tool.svg',
            border_color='#F44336'
        )

        self.add_metric_card(
            row=0, col=5,
            object_name='upcoming_birthdays',
            title='Дни рождения (30 дней)',
            value='0',
            icon_path='resources/icons/gift.svg',
            border_color='#E91E63'
        )

        # Строка 2: Зарплаты
        self.add_metric_card(
            row=1, col=0,
            object_name='total_paid',
            title='Всего выплачено',
            value='0 руб',
            icon_path='resources/icons/dollar-sign.svg',
            border_color='#4CAF50'
        )

        card = self.add_metric_card(
            row=1, col=1,
            object_name='paid_by_year',
            title='Выплачено за год',
            value='0 руб',
            icon_path='resources/icons/calendar.svg',
            border_color='#2196F3',
            filters=[{'type': 'year', 'options': years}]
        )
        card.connect_filter('year', self.on_year_changed)

        card = self.add_metric_card(
            row=1, col=2,
            object_name='paid_by_month',
            title='Выплачено за месяц',
            value='0 руб',
            icon_path='resources/icons/clock.svg',
            border_color='#9C27B0',
            filters=[
                {'type': 'year', 'options': years},
                {'type': 'month', 'options': [m[0] for m in months]}
            ]
        )
        card.connect_filter('year', self.on_year_changed)
        card.connect_filter('month', self.on_month_changed)

        card = self.add_metric_card(
            row=1, col=3,
            object_name='individual_by_year',
            title='Индивидуальные (год)',
            value='0 руб',
            icon_path='resources/icons/trending-up.svg',
            border_color='#F57C00',
            filters=[{'type': 'year', 'options': years}]
        )
        card.connect_filter('year', self.on_year_changed)

        card = self.add_metric_card(
            row=1, col=4,
            object_name='template_by_year',
            title='Шаблонные (год)',
            value='0 руб',
            icon_path='resources/icons/trending-down.svg',
            border_color='#C62828',
            filters=[{'type': 'year', 'options': years}]
        )
        card.connect_filter('year', self.on_year_changed)

        card = self.add_metric_card(
            row=1, col=5,
            object_name='supervision_by_year',
            title='Надзор (год)',
            value='0 руб',
            icon_path='resources/icons/eye.svg',
            border_color='#388E3C',
            filters=[{'type': 'year', 'options': years}]
        )
        card.connect_filter('year', self.on_year_changed)

        self.set_column_stretch(6)

    def on_year_changed(self, year):
        """Обработка изменения года"""
        self.current_year = int(year)
        self.load_data()

    def on_month_changed(self, month_name):
        """Обработка изменения месяца"""
        months = {
            'Январь': 1, 'Февраль': 2, 'Март': 3, 'Апрель': 4,
            'Май': 5, 'Июнь': 6, 'Июль': 7, 'Август': 8,
            'Сентябрь': 9, 'Октябрь': 10, 'Ноябрь': 11, 'Декабрь': 12
        }
        self.current_month = months.get(month_name, datetime.now().month)
        self.load_data()

    def load_data(self):
        """Загрузка агрегированных данных"""
        try:
            if not self.db:
                print(f"[ERROR] self.db is None in EmployeeReportsDashboard.load_data()")
                return

            # Проверяем статус подключения один раз
            use_api = self.api_client and self.api_client.is_online

            # Загружаем данные сотрудников
            if use_api:
                try:
                    employees_stats = self.api_client.get_employees_dashboard_stats()
                except Exception:
                    employees_stats = self.db.get_employees_dashboard_stats()
            else:
                employees_stats = self.db.get_employees_dashboard_stats()

            # Загружаем данные зарплат
            if use_api:
                try:
                    salaries_stats = self.api_client.get_salaries_dashboard_stats(
                        year=self.current_year,
                        month=self.current_month
                    )
                except Exception:
                    salaries_stats = self.db.get_salaries_dashboard_stats(
                        year=self.current_year,
                        month=self.current_month
                    )
            else:
                salaries_stats = self.db.get_salaries_dashboard_stats(
                    year=self.current_year,
                    month=self.current_month
                )

            # Обновляем метрики сотрудников (поддержка разных ключей от API и локальной БД)
            self.update_metric('active_employees', str(employees_stats.get('active_employees', 0)))
            self.update_metric('reserve_employees', str(employees_stats.get('reserve_employees', 0)))

            active_mgmt = employees_stats.get('active_management') or employees_stats.get('active_admin', 0)
            active_proj = employees_stats.get('active_projects_dept') or employees_stats.get('active_project', 0)
            active_exec = employees_stats.get('active_execution_dept') or employees_stats.get('active_execution', 0)
            birthdays = employees_stats.get('upcoming_birthdays') or employees_stats.get('nearest_birthday', 0)

            self.update_metric('active_management', str(active_mgmt))
            self.update_metric('active_projects_dept', str(active_proj))
            self.update_metric('active_execution_dept', str(active_exec))
            self.update_metric('upcoming_birthdays', str(birthdays))

            # Обновляем метрики зарплат
            self.update_metric('total_paid', f"{salaries_stats.get('total_paid', 0):,.0f} руб")
            self.update_metric('paid_by_year', f"{salaries_stats.get('paid_by_year', 0):,.0f} руб")
            self.update_metric('paid_by_month', f"{salaries_stats.get('paid_by_month', 0):,.0f} руб")
            self.update_metric('individual_by_year', f"{salaries_stats.get('individual_by_year', 0):,.0f} руб")
            self.update_metric('template_by_year', f"{salaries_stats.get('template_by_year', 0):,.0f} руб")
            self.update_metric('supervision_by_year', f"{salaries_stats.get('supervision_by_year', 0):,.0f} руб")

        except Exception as e:
            print(f"[ERROR] Ошибка загрузки агрегированного дашборда сотрудников: {e}")
            import traceback
            traceback.print_exc()

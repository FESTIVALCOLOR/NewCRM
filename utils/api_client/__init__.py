"""
API клиент для взаимодействия с сервером.

Декомпозирован из монолитного utils/api_client.py на domain-mixin файлы.
Сборка: APIClient наследует APIClientBase + все миксины.
Обратная совместимость: `from utils.api_client import APIClient` работает как раньше.
"""

from utils.api_client.base import APIClientBase
from utils.api_client.exceptions import (
    APIError, APITimeoutError, APIConnectionError, APIAuthError, APIResponseError,
)
from utils.api_client.auth_mixin import AuthMixin
from utils.api_client.clients_mixin import ClientsMixin
from utils.api_client.contracts_mixin import ContractsMixin
from utils.api_client.employees_mixin import EmployeesMixin
from utils.api_client.crm_mixin import CrmMixin
from utils.api_client.supervision_mixin import SupervisionMixin
from utils.api_client.payments_mixin import PaymentsMixin
from utils.api_client.rates_mixin import RatesMixin
from utils.api_client.salaries_mixin import SalariesMixin
from utils.api_client.files_mixin import FilesMixin
from utils.api_client.statistics_mixin import StatisticsMixin
from utils.api_client.timeline_mixin import TimelineMixin
from utils.api_client.messenger_mixin import MessengerMixin
from utils.api_client.permissions_mixin import PermissionsMixin
from utils.api_client.misc_mixin import MiscMixin
from utils.api_client.compat_mixin import CompatMixin


class APIClient(
    AuthMixin,
    ClientsMixin,
    ContractsMixin,
    EmployeesMixin,
    CrmMixin,
    SupervisionMixin,
    PaymentsMixin,
    RatesMixin,
    SalariesMixin,
    FilesMixin,
    StatisticsMixin,
    TimelineMixin,
    MessengerMixin,
    PermissionsMixin,
    MiscMixin,
    CompatMixin,
    APIClientBase,
):
    """
    Полный API клиент — собран из APIClientBase + domain-миксинов.
    Полностью совместим с прежним монолитным APIClient.
    """
    pass


__all__ = [
    'APIClient',
    'APIClientBase',
    'APIError',
    'APITimeoutError',
    'APIConnectionError',
    'APIAuthError',
    'APIResponseError',
]

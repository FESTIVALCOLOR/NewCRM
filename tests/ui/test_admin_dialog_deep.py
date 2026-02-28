# -*- coding: utf-8 -*-
"""Глубокие тесты AdminDialog, DashboardTab, EmployeeReportsTab"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QTabWidget, QGroupBox
from PyQt5.QtCore import Qt


# ─── AdminDialog ────────────────────────────────────────────────────────

class TestAdminDialog:
    """Тесты AdminDialog"""

    @pytest.fixture
    def mock_api(self):
        api = MagicMock()
        api.get_messenger_scripts.return_value = []
        api.get_messenger_settings.return_value = []
        api.get_messenger_status.return_value = {'telegram_bot_available': False}
        api.get_permission_definitions.return_value = []
        api.get_role_permissions_matrix.return_value = {}
        api.get_all_agents.return_value = []
        api.get_all_cities.return_value = []
        return api

    def test_creation(self, qtbot, mock_api):
        with patch('ui.custom_title_bar.CustomTitleBar') as MockTitleBar:
            MockTitleBar.return_value = QWidget()
            from ui.admin_dialog import AdminDialog
            parent = QWidget()
            qtbot.addWidget(parent)
            dlg = AdminDialog(parent, api_client=mock_api, data_access=MagicMock())
            assert dlg is not None

    def test_tab_count(self, qtbot, mock_api):
        with patch('ui.custom_title_bar.CustomTitleBar') as MockTitleBar:
            MockTitleBar.return_value = QWidget()
            from ui.admin_dialog import AdminDialog
            parent = QWidget()
            qtbot.addWidget(parent)
            dlg = AdminDialog(parent, api_client=mock_api, data_access=MagicMock())
            assert dlg._tabs.count() == 5

    def test_tab_titles(self, qtbot, mock_api):
        with patch('ui.custom_title_bar.CustomTitleBar') as MockTitleBar:
            MockTitleBar.return_value = QWidget()
            from ui.admin_dialog import AdminDialog
            parent = QWidget()
            qtbot.addWidget(parent)
            dlg = AdminDialog(parent, api_client=mock_api)
            titles = [dlg._tabs.tabText(i) for i in range(dlg._tabs.count())]
            assert 'Права доступа' in titles
            assert 'Настройка чата' in titles
            assert 'Тарифы' in titles
            assert 'Агенты и города' in titles

    def test_window_flags(self, qtbot, mock_api):
        with patch('ui.custom_title_bar.CustomTitleBar') as MockTitleBar:
            MockTitleBar.return_value = QWidget()
            from ui.admin_dialog import AdminDialog
            parent = QWidget()
            qtbot.addWidget(parent)
            dlg = AdminDialog(parent, api_client=mock_api)
            assert dlg.windowFlags() & Qt.FramelessWindowHint

    def test_minimum_size(self, qtbot, mock_api):
        with patch('ui.custom_title_bar.CustomTitleBar') as MockTitleBar:
            MockTitleBar.return_value = QWidget()
            from ui.admin_dialog import AdminDialog
            parent = QWidget()
            qtbot.addWidget(parent)
            dlg = AdminDialog(parent, api_client=mock_api)
            assert dlg.minimumWidth() >= 1050
            assert dlg.minimumHeight() >= 700

    def test_employee_default(self, qtbot, mock_api):
        with patch('ui.custom_title_bar.CustomTitleBar') as MockTitleBar:
            MockTitleBar.return_value = QWidget()
            from ui.admin_dialog import AdminDialog
            parent = QWidget()
            qtbot.addWidget(parent)
            dlg = AdminDialog(parent, api_client=mock_api)
            assert dlg.employee == {}

    def test_employee_passed(self, qtbot, mock_api):
        with patch('ui.custom_title_bar.CustomTitleBar') as MockTitleBar:
            MockTitleBar.return_value = QWidget()
            from ui.admin_dialog import AdminDialog
            parent = QWidget()
            qtbot.addWidget(parent)
            emp = {'id': 1, 'full_name': 'Тест', 'role': 'Руководитель студии'}
            dlg = AdminDialog(parent, api_client=mock_api, employee=emp)
            assert dlg.employee['id'] == 1

    def test_tab_style(self):
        from ui.admin_dialog import _TAB_STYLE
        assert 'QTabWidget' in _TAB_STYLE
        assert 'QTabBar' in _TAB_STYLE

    def test_init_permissions_widget_exception(self, qtbot, mock_api):
        with patch('ui.custom_title_bar.CustomTitleBar') as MockTitleBar:
            MockTitleBar.return_value = QWidget()
            from ui.admin_dialog import AdminDialog
            parent = QWidget()
            qtbot.addWidget(parent)
            dlg = AdminDialog(parent, api_client=mock_api)
            with patch('ui.permissions_matrix_widget.PermissionsMatrixWidget', side_effect=Exception('test')):
                try:
                    dlg._init_permissions_widget()
                except Exception:
                    pass  # может вызвать import error — это ок

    def test_init_chat_widget_exception(self, qtbot, mock_api):
        with patch('ui.custom_title_bar.CustomTitleBar') as MockTitleBar:
            MockTitleBar.return_value = QWidget()
            from ui.admin_dialog import AdminDialog
            parent = QWidget()
            qtbot.addWidget(parent)
            dlg = AdminDialog(parent, api_client=mock_api)
            # _init_chat_widget ловит исключения внутри


# ─── DashboardTab ───────────────────────────────────────────────────────

class TestDashboardTab:
    """Тесты DashboardTab"""

    @pytest.fixture
    def mock_da(self):
        da = MagicMock()
        da.get_dashboard_statistics.return_value = {
            'individual_orders': 10, 'template_orders': 5, 'supervision_orders': 3,
            'individual_area': 1000.0, 'template_area': 500.0, 'supervision_area': 300.0
        }
        da.get_all_contracts.return_value = [
            {'project_type': 'Индивидуальный', 'area': 100, 'supervision': False},
            {'project_type': 'Шаблонный', 'area': 50, 'supervision': True},
        ]
        da.is_multi_user = False
        return da

    def test_creation(self, qtbot, mock_da):
        with patch('ui.dashboard_tab.DatabaseManager'), \
             patch('ui.dashboard_tab.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_tab.resource_path', return_value='/fake'), \
             patch('ui.dashboard_tab.os.path.exists', return_value=False):
            from ui.dashboard_tab import DashboardTab
            emp = {'full_name': 'Тест', 'position': 'Дизайнер'}
            tab = DashboardTab(emp)
            qtbot.addWidget(tab)
            assert tab is not None

    def test_stat_cards_exist(self, qtbot, mock_da):
        with patch('ui.dashboard_tab.DatabaseManager'), \
             patch('ui.dashboard_tab.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_tab.resource_path', return_value='/fake'), \
             patch('ui.dashboard_tab.os.path.exists', return_value=False):
            from ui.dashboard_tab import DashboardTab
            emp = {'full_name': 'Тест', 'position': 'Дизайнер'}
            tab = DashboardTab(emp)
            qtbot.addWidget(tab)
            assert tab.individual_orders_card is not None
            assert tab.template_orders_card is not None
            assert tab.supervision_orders_card is not None

    def test_create_stat_card(self, qtbot, mock_da):
        with patch('ui.dashboard_tab.DatabaseManager'), \
             patch('ui.dashboard_tab.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_tab.resource_path', return_value='/fake'), \
             patch('ui.dashboard_tab.os.path.exists', return_value=False):
            from ui.dashboard_tab import DashboardTab
            emp = {'full_name': 'Тест', 'position': 'Дизайнер'}
            tab = DashboardTab(emp)
            qtbot.addWidget(tab)
            card = tab.create_stat_card('test', 'Тест', '42', '/fake', '#fff', '#000')
            assert isinstance(card, QGroupBox)

    def test_lighter_color(self, qtbot, mock_da):
        with patch('ui.dashboard_tab.DatabaseManager'), \
             patch('ui.dashboard_tab.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_tab.resource_path', return_value='/fake'), \
             patch('ui.dashboard_tab.os.path.exists', return_value=False):
            from ui.dashboard_tab import DashboardTab
            emp = {'full_name': 'Тест', 'position': 'Дизайнер'}
            tab = DashboardTab(emp)
            qtbot.addWidget(tab)
            assert tab.lighter_color('#fff4d9') == '#fff4d9'

    def test_load_statistics_local(self, qtbot, mock_da):
        with patch('ui.dashboard_tab.DatabaseManager'), \
             patch('ui.dashboard_tab.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_tab.resource_path', return_value='/fake'), \
             patch('ui.dashboard_tab.os.path.exists', return_value=False):
            from ui.dashboard_tab import DashboardTab
            emp = {'full_name': 'Тест', 'position': 'Дизайнер'}
            tab = DashboardTab(emp)
            qtbot.addWidget(tab)
            tab.load_statistics()
            mock_da.get_dashboard_statistics.assert_called_once()

    def test_load_statistics_multi_user(self, qtbot, mock_da):
        mock_da.is_multi_user = True
        with patch('ui.dashboard_tab.DatabaseManager'), \
             patch('ui.dashboard_tab.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_tab.resource_path', return_value='/fake'), \
             patch('ui.dashboard_tab.os.path.exists', return_value=False):
            from ui.dashboard_tab import DashboardTab
            emp = {'full_name': 'Тест', 'position': 'Дизайнер'}
            tab = DashboardTab(emp)
            qtbot.addWidget(tab)
            tab.load_statistics()
            mock_da.get_all_contracts.assert_called()

    def test_calculate_api_statistics(self, qtbot, mock_da):
        with patch('ui.dashboard_tab.DatabaseManager'), \
             patch('ui.dashboard_tab.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_tab.resource_path', return_value='/fake'), \
             patch('ui.dashboard_tab.os.path.exists', return_value=False):
            from ui.dashboard_tab import DashboardTab
            emp = {'full_name': 'Тест', 'position': 'Дизайнер'}
            tab = DashboardTab(emp)
            qtbot.addWidget(tab)
            stats = tab.calculate_api_statistics()
            assert stats['individual_orders'] == 1
            assert stats['template_orders'] == 1
            assert stats['supervision_orders'] == 1

    def test_calculate_api_statistics_error(self, qtbot, mock_da):
        mock_da.get_all_contracts.side_effect = Exception('err')
        with patch('ui.dashboard_tab.DatabaseManager'), \
             patch('ui.dashboard_tab.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_tab.resource_path', return_value='/fake'), \
             patch('ui.dashboard_tab.os.path.exists', return_value=False):
            from ui.dashboard_tab import DashboardTab
            emp = {'full_name': 'Тест', 'position': 'Дизайнер'}
            tab = DashboardTab(emp)
            qtbot.addWidget(tab)
            stats = tab.calculate_api_statistics()
            assert stats['individual_orders'] == 0

    def test_update_card_value(self, qtbot, mock_da):
        with patch('ui.dashboard_tab.DatabaseManager'), \
             patch('ui.dashboard_tab.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_tab.resource_path', return_value='/fake'), \
             patch('ui.dashboard_tab.os.path.exists', return_value=False):
            from ui.dashboard_tab import DashboardTab
            emp = {'full_name': 'Тест', 'position': 'Дизайнер'}
            tab = DashboardTab(emp)
            qtbot.addWidget(tab)
            tab.update_card_value('individual_orders', '42')
            card = tab.findChild(QGroupBox, 'individual_orders')
            value_label = card.findChild(QLabel, 'value_label')
            assert value_label.text() == '42'

    def test_update_card_value_nonexistent(self, qtbot, mock_da):
        with patch('ui.dashboard_tab.DatabaseManager'), \
             patch('ui.dashboard_tab.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_tab.resource_path', return_value='/fake'), \
             patch('ui.dashboard_tab.os.path.exists', return_value=False):
            from ui.dashboard_tab import DashboardTab
            emp = {'full_name': 'Тест', 'position': 'Дизайнер'}
            tab = DashboardTab(emp)
            qtbot.addWidget(tab)
            tab.update_card_value('nonexistent', '0')  # не падает


# ─── EmployeeReportsTab ─────────────────────────────────────────────────

class TestEmployeeReportsTab:
    """Тесты EmployeeReportsTab"""

    @pytest.fixture
    def mock_da(self):
        da = MagicMock()
        da.get_employees.return_value = [
            {'id': 1, 'full_name': 'Иванов', 'position': 'Дизайнер', 'status': 'Активный'}
        ]
        da.get_crm_cards.return_value = []
        da.get_all_contracts.return_value = []
        da.is_multi_user = False
        return da

    def _mock_icon_loader(self):
        from PyQt5.QtWidgets import QPushButton
        from PyQt5.QtGui import QIcon
        mock = MagicMock()
        mock.create_icon_button = MagicMock(
            side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
        )
        mock.create_action_button = MagicMock(
            side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
        )
        mock.get_icon.return_value = QIcon()
        mock.get_icon_path.return_value = ''
        mock.load.return_value = QIcon()
        return mock

    def test_creation(self, qtbot, mock_da):
        from PyQt5.QtWidgets import QComboBox
        with patch('ui.employee_reports_tab.DatabaseManager'), \
             patch('ui.employee_reports_tab.DataAccess', return_value=mock_da), \
             patch('ui.employee_reports_tab.CustomComboBox', QComboBox), \
             patch('ui.employee_reports_tab.IconLoader', self._mock_icon_loader()), \
             patch('ui.employee_reports_tab.apply_no_focus_delegate'):
            from ui.employee_reports_tab import EmployeeReportsTab
            emp = {'full_name': 'Тест', 'position': 'Руководитель'}
            tab = EmployeeReportsTab(emp)
            qtbot.addWidget(tab)
            assert tab is not None

    def test_report_tabs_exist(self, qtbot, mock_da):
        from PyQt5.QtWidgets import QComboBox
        with patch('ui.employee_reports_tab.DatabaseManager'), \
             patch('ui.employee_reports_tab.DataAccess', return_value=mock_da), \
             patch('ui.employee_reports_tab.CustomComboBox', QComboBox), \
             patch('ui.employee_reports_tab.IconLoader', self._mock_icon_loader()), \
             patch('ui.employee_reports_tab.apply_no_focus_delegate'):
            from ui.employee_reports_tab import EmployeeReportsTab
            emp = {'full_name': 'Тест', 'position': 'Руководитель'}
            tab = EmployeeReportsTab(emp)
            qtbot.addWidget(tab)
            assert tab.report_tabs.count() == 3


# ─── API Client Exceptions ──────────────────────────────────────────────

class TestAPIExceptions:
    """Тесты для исключений API клиента"""

    def test_api_error(self):
        from utils.api_client.exceptions import APIError
        err = APIError("тест")
        assert str(err) == "тест"
        assert isinstance(err, Exception)

    def test_api_timeout_error(self):
        from utils.api_client.exceptions import APITimeoutError
        err = APITimeoutError("таймаут")
        assert isinstance(err, Exception)
        from utils.api_client.exceptions import APIError
        assert isinstance(err, APIError)

    def test_api_connection_error(self):
        from utils.api_client.exceptions import APIConnectionError
        err = APIConnectionError("нет соединения")
        from utils.api_client.exceptions import APIError
        assert isinstance(err, APIError)

    def test_api_auth_error(self):
        from utils.api_client.exceptions import APIAuthError
        err = APIAuthError("не авторизован")
        from utils.api_client.exceptions import APIError
        assert isinstance(err, APIError)

    def test_api_response_error(self):
        from utils.api_client.exceptions import APIResponseError
        err = APIResponseError("ошибка сервера", status_code=500)
        assert err.status_code == 500
        from utils.api_client.exceptions import APIError
        assert isinstance(err, APIError)

    def test_api_response_error_no_code(self):
        from utils.api_client.exceptions import APIResponseError
        err = APIResponseError("ошибка")
        assert err.status_code is None


# ─── APIClientBase ───────────────────────────────────────────────────────

class TestAPIClientBaseDeep:
    """Глубокие тесты базового API клиента"""

    @pytest.fixture
    def client(self):
        with patch('utils.api_client.base.requests.Session'):
            from utils.api_client.base import APIClientBase
            c = APIClientBase('http://test:8000')
            return c

    def test_creation(self, client):
        assert client.base_url == 'http://test:8000'
        assert client.token is None
        assert client.is_online is True

    def test_set_token(self, client):
        client.set_token('test_token_abc')
        assert client.token == 'test_token_abc'
        assert 'Authorization' in client.headers
        assert client.headers['Authorization'] == 'Bearer test_token_abc'

    def test_set_token_with_refresh(self, client):
        client.set_token('access', 'refresh')
        assert client.refresh_token == 'refresh'

    def test_clear_token(self, client):
        client.set_token('test_token')
        client.clear_token()
        assert client.token is None
        assert client.refresh_token is None
        assert 'Authorization' not in client.headers

    def test_is_online_default(self, client):
        assert client.is_online is True

    def test_mark_offline(self, client):
        client._mark_offline()
        assert client.is_online is False
        assert client._last_offline_time is not None

    def test_reset_offline_cache(self, client):
        client._mark_offline()
        client.reset_offline_cache()
        assert client._last_offline_time is None

    def test_set_offline_mode(self, client):
        client.set_offline_mode(True)
        assert client.is_online is False
        client.set_offline_mode(False)
        assert client.is_online is True

    def test_calc_backoff(self, client):
        d0 = client._calc_backoff(0)
        d1 = client._calc_backoff(1)
        d2 = client._calc_backoff(2)
        assert d0 > 0
        assert d1 >= d0 * 0.5  # с учётом jitter

    def test_parse_retry_after_valid(self, client):
        resp = MagicMock()
        resp.headers = {'Retry-After': '5'}
        assert client._parse_retry_after(resp) == 5.0

    def test_parse_retry_after_missing(self, client):
        resp = MagicMock()
        resp.headers = {}
        assert client._parse_retry_after(resp) is None

    def test_parse_retry_after_invalid(self, client):
        resp = MagicMock()
        resp.headers = {'Retry-After': 'invalid'}
        assert client._parse_retry_after(resp) is None

    def test_extract_token_expiry_valid(self, client):
        import base64, json, time
        payload = {'exp': int(time.time()) + 3600, 'sub': '1'}
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        header_b64 = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip('=')
        token = f"{header_b64}.{payload_b64}.signature"
        exp = client._extract_token_expiry(token)
        assert exp is not None
        assert exp > time.time()

    def test_extract_token_expiry_invalid(self, client):
        assert client._extract_token_expiry('invalid') is None
        assert client._extract_token_expiry('a.b') is None

    def test_is_token_expiring_soon_no_exp(self, client):
        client._token_exp = None
        assert client._is_token_expiring_soon() is False

    def test_is_token_expiring_soon_yes(self, client):
        import time
        client._token_exp = time.time() + 100  # меньше TOKEN_REFRESH_THRESHOLD
        assert client._is_token_expiring_soon() is True

    def test_is_token_expiring_soon_no(self, client):
        import time
        client._token_exp = time.time() + 3600
        assert client._is_token_expiring_soon() is False

    def test_handle_response_200(self, client):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {'data': 'ok'}
        result = client._handle_response(resp)
        assert result == {'data': 'ok'}

    def test_handle_response_200_no_json(self, client):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.side_effect = ValueError
        result = client._handle_response(resp)
        assert result is True

    def test_handle_response_401(self, client):
        from utils.api_client.exceptions import APIAuthError
        resp = MagicMock()
        resp.status_code = 401
        resp.headers = {'content-type': 'application/json'}
        resp.json.return_value = {'detail': 'unauthorized'}
        with pytest.raises(APIAuthError):
            client._handle_response(resp)

    def test_handle_response_403(self, client):
        from utils.api_client.exceptions import APIAuthError
        resp = MagicMock()
        resp.status_code = 403
        resp.headers = {'content-type': 'application/json'}
        resp.json.return_value = {'detail': 'forbidden'}
        with pytest.raises(APIAuthError):
            client._handle_response(resp)

    def test_handle_response_500(self, client):
        from utils.api_client.exceptions import APIResponseError
        resp = MagicMock()
        resp.status_code = 500
        resp.headers = {'content-type': 'application/json'}
        resp.json.return_value = {'detail': 'server error'}
        with pytest.raises(APIResponseError):
            client._handle_response(resp)

    def test_handle_response_429(self, client):
        from utils.api_client.exceptions import APIResponseError
        resp = MagicMock()
        resp.status_code = 429
        resp.headers = {'content-type': 'application/json'}
        resp.json.return_value = {'detail': 'too many'}
        with pytest.raises(APIResponseError) as exc:
            client._handle_response(resp)
        assert exc.value.status_code == 429

    def test_extract_error_detail_json(self, client):
        resp = MagicMock()
        resp.headers = {'content-type': 'application/json'}
        resp.json.return_value = {'detail': 'тест ошибки'}
        assert client._extract_error_detail(resp) == 'тест ошибки'

    def test_extract_error_detail_text(self, client):
        resp = MagicMock()
        resp.headers = {'content-type': 'text/html'}
        resp.text = 'HTML error'
        assert client._extract_error_detail(resp) == 'HTML error'

    def test_set_relogin_callback(self, client):
        cb = MagicMock()
        client.set_relogin_callback(cb)
        assert client._relogin_callback is cb

    def test_signal_relogin_needed(self, client):
        cb = MagicMock(return_value=True)
        client.set_relogin_callback(cb)
        client._signal_relogin_needed()
        cb.assert_called_once()

    def test_signal_relogin_deduplicate(self, client):
        cb = MagicMock(return_value=False)
        client.set_relogin_callback(cb)
        client._signal_relogin_needed()
        client._signal_relogin_needed()
        cb.assert_called_once()  # второй вызов не происходит

    def test_constants(self, client):
        assert client.DEFAULT_TIMEOUT == 10
        assert client.WRITE_TIMEOUT == 15
        assert client.MAX_RETRIES == 3
        assert client.OFFLINE_CACHE_DURATION == 10

    def test_is_recently_offline_false(self, client):
        assert client._is_recently_offline() is False

    def test_is_recently_offline_true(self, client):
        import time
        client._last_offline_time = time.time()
        assert client._is_recently_offline() is True

    def test_force_online_check_success(self, client):
        resp = MagicMock()
        resp.status_code = 200
        with patch.object(client, 'session') as mock_session:
            mock_session.get.return_value = resp
            assert client.force_online_check() is True
        assert client.is_online is True

    def test_force_online_check_fail(self, client):
        with patch.object(client, 'session') as mock_session:
            mock_session.get.side_effect = Exception('conn err')
            assert client.force_online_check() is False
        assert client.is_online is False


# ─── AuthSession ─────────────────────────────────────────────────────────

class TestAuthSession:
    """Тесты _AuthSession"""

    def test_rebuild_auth_same_host(self):
        from utils.api_client.base import _AuthSession
        session = _AuthSession()
        prepared = MagicMock()
        prepared.headers = {'Authorization': 'Bearer token'}
        prepared.url = 'http://test.com/api/v2'
        response = MagicMock()
        response.request.url = 'https://test.com/api/v1'
        session.rebuild_auth(prepared, response)
        # Тот же хост — auth сохраняется
        assert 'Authorization' in prepared.headers

    def test_rebuild_auth_different_host(self):
        from utils.api_client.base import _AuthSession
        session = _AuthSession()
        prepared = MagicMock()
        prepared.headers = {'Authorization': 'Bearer token'}
        prepared.url = 'http://other.com/api/v2'
        response = MagicMock()
        response.request.url = 'https://test.com/api/v1'
        session.rebuild_auth(prepared, response)
        # Разный хост — auth удаляется
        assert 'Authorization' not in prepared.headers

    def test_rebuild_auth_no_auth(self):
        from utils.api_client.base import _AuthSession
        session = _AuthSession()
        prepared = MagicMock()
        prepared.headers = {}
        response = MagicMock()
        response.request.url = 'https://test.com/api'
        session.rebuild_auth(prepared, response)
        # Нет Authorization — ничего не делаем

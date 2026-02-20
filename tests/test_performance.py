# -*- coding: utf-8 -*-
"""
Test proizvoditelnosti zagruzki UI komponentov.

Zameryaet vremya:
- Avtorizacii cherez API
- Sozdaniya MainWindow (init_ui bez vkladok)
- setup_tabs() - sozdanie vsekh vkladok
- Kazhdoj vkladki otdelno (konstruktor + init_ui)
- ensure_data_loaded() dlya kazhdoj vkladki (zagruzka dannykh)
- Sozdaniya dashbordov
- Otkrytiya CRM CardEditDialog

Zapusk:
    .venv/Scripts/python.exe tests/test_performance.py
"""
import sys
import os
import io
import time
from contextlib import contextmanager
from collections import OrderedDict

# Fix console encoding for Windows cp1251
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer


# ========== UTILS ==========

@contextmanager
def measure(label, results):
    start = time.perf_counter()
    yield
    elapsed = (time.perf_counter() - start) * 1000
    results[label] = elapsed


def rating(ms):
    if ms < 100:
        return 'OK'
    elif ms < 300:
        return 'GOOD'
    elif ms < 700:
        return 'FAIR'
    elif ms < 1500:
        return 'SLOW'
    else:
        return 'CRIT'


def bar_str(ms):
    n = min(int(ms / 50), 40)
    return '#' * n


# ========== MAIN TEST ==========

def run_performance_test():
    results = OrderedDict()
    errors = {}

    app = QApplication.instance() or QApplication(sys.argv)

    print()
    print('=' * 70)
    print('  PERFORMANCE TEST: UI LOADING TIMES')
    print('=' * 70)
    print()

    from config import API_BASE_URL
    print(f'  API server: {API_BASE_URL}')
    print(f'  User: admin / admin123')
    print()

    api_client = None
    employee_data = None

    # --- 1. Auth ---
    with measure('1. Auth (API login)', results):
        try:
            from utils.api_client import APIClient
            api_client = APIClient(API_BASE_URL)
            login_data = api_client.login('admin', 'admin123')
            employee_data = api_client.get_employee(login_data['employee_id'])
        except Exception as e:
            errors['Auth'] = str(e)
            print(f'  [ERROR] Auth failed: {e}')
            print('  Trying offline mode...')

    if not employee_data:
        try:
            from database.db_manager import DatabaseManager
            db = DatabaseManager()
            employee_data = db.verify_credentials('admin', 'admin123')
            if employee_data:
                employee_data['offline_mode'] = True
                api_client = None
            else:
                print('  [FATAL] Cannot auth via API or locally')
                return
        except Exception as e:
            print(f'  [FATAL] {e}')
            return

    print(f'  Logged in: {employee_data.get("full_name", "?")}')
    print(f'  Role: {employee_data.get("position", "?")}')
    print()

    # --- 2. MainWindow (frame only, no tabs) ---
    main_window = None
    with measure('2. MainWindow.__init__ + init_ui (no tabs)', results):
        try:
            from ui.main_window import MainWindow
            main_window = MainWindow(employee_data, api_client=api_client)
        except Exception as e:
            errors['MainWindow'] = str(e)
            print(f'  [ERROR] MainWindow: {e}')

    if not main_window:
        print('  [FATAL] MainWindow not created')
        return

    # --- 3. setup_tabs() ---
    with measure('3. setup_tabs() - all tabs creation', results):
        try:
            main_window.setup_tabs()
            app.processEvents()
        except Exception as e:
            errors['setup_tabs'] = str(e)
            print(f'  [ERROR] setup_tabs: {e}')

    # --- 4. Individual tab constructors ---
    print('  Measuring individual tab constructors...')

    tab_classes = [
        ('4a. ClientsTab', 'ui.clients_tab', 'ClientsTab',
         lambda cls: cls(employee_data, api_client=api_client)),
        ('4b. ContractsTab', 'ui.contracts_tab', 'ContractsTab',
         lambda cls: cls(employee_data, api_client=api_client)),
        ('4c. CRMTab', 'ui.crm_tab', 'CRMTab',
         lambda cls: cls(employee_data, True, api_client=api_client)),
        ('4d. CRMSupervisionTab', 'ui.crm_supervision_tab', 'CRMSupervisionTab',
         lambda cls: cls(employee_data, api_client=api_client)),
        ('4e. ReportsTab', 'ui.reports_tab', 'ReportsTab',
         lambda cls: cls(employee_data, api_client=api_client)),
        ('4f. EmployeesTab', 'ui.employees_tab', 'EmployeesTab',
         lambda cls: cls(employee_data, api_client=api_client)),
        ('4g. SalariesTab', 'ui.salaries_tab', 'SalariesTab',
         lambda cls: cls(employee_data, api_client=api_client)),
        ('4h. EmployeeReportsTab', 'ui.employee_reports_tab', 'EmployeeReportsTab',
         lambda cls: cls(employee_data, api_client=api_client)),
    ]

    tab_instances = {}
    for label, module_name, class_name, factory in tab_classes:
        with measure(label, results):
            try:
                module = __import__(module_name, fromlist=[class_name])
                cls = getattr(module, class_name)
                tab_instances[class_name] = factory(cls)
            except Exception as e:
                errors[label] = str(e)
                print(f'  [ERROR] {label}: {e}')

    # --- 5. ensure_data_loaded (data loading) ---
    print('  Measuring data loading (ensure_data_loaded / API)...')

    data_load_map = [
        ('5a. Clients data load', 'ClientsTab', 'ensure_data_loaded'),
        ('5b. Contracts data load', 'ContractsTab', 'ensure_data_loaded'),
        ('5c. CRM data load', 'CRMTab', 'ensure_data_loaded'),
        ('5d. CRM Supervision data load', 'CRMSupervisionTab', 'ensure_data_loaded'),
        ('5e. Reports data load', 'ReportsTab', 'ensure_data_loaded'),
        ('5f. Employees data load', 'EmployeesTab', 'ensure_data_loaded'),
        ('5g. Salaries data load', 'SalariesTab', 'ensure_data_loaded'),
        ('5h. Employee Reports data load', 'EmployeeReportsTab', 'load_report_data'),
    ]

    for label, class_name, method_name in data_load_map:
        tab = tab_instances.get(class_name)
        if not tab:
            results[label] = -1
            continue
        with measure(label, results):
            try:
                method = getattr(tab, method_name, None)
                if method:
                    if method_name == 'load_report_data':
                        method('Индивидуальный')
                    else:
                        if hasattr(tab, '_data_loaded'):
                            tab._data_loaded = False
                        method()
                else:
                    results[label] = -1
            except Exception as e:
                errors[label] = str(e)

    # --- 6. Dashboards ---
    with measure('6. Create 11 dashboards', results):
        try:
            from ui.dashboards import (ClientsDashboard, ContractsDashboard, CRMDashboard,
                                       EmployeesDashboard,
                                       SalariesAllPaymentsDashboard, SalariesIndividualDashboard,
                                       SalariesTemplateDashboard, SalariesSalaryDashboard,
                                       SalariesSupervisionDashboard)
            from database.db_manager import DatabaseManager
            db = DatabaseManager()
            dashboards = [
                ClientsDashboard(db, api_client),
                ContractsDashboard(db, api_client),
                CRMDashboard(db, 'Индивидуальный', api_client),
                CRMDashboard(db, 'Шаблонный', api_client),
                CRMDashboard(db, 'Авторский надзор', api_client),
                EmployeesDashboard(db, api_client),
                SalariesAllPaymentsDashboard(db, api_client),
                SalariesIndividualDashboard(db, api_client),
                SalariesTemplateDashboard(db, api_client),
                SalariesSalaryDashboard(db, api_client),
                SalariesSupervisionDashboard(db, api_client),
            ]
        except Exception as e:
            errors['Dashboards'] = str(e)

    # --- 7. CRM CardEditDialog ---
    with measure('7. CRM CardEditDialog (open)', results):
        try:
            from ui.crm_card_edit_dialog import CardEditDialog
            from database.db_manager import DatabaseManager
            if api_client:
                try:
                    cards = api_client.get_crm_cards(project_type='Индивидуальный')
                except Exception:
                    cards = []
            else:
                cards = DatabaseManager().get_crm_cards()

            if cards:
                card = cards[0]
                dialog = CardEditDialog(
                    card_data=card,
                    employee=employee_data,
                    db=DatabaseManager(),
                    api_client=api_client,
                    parent=None
                )
                dialog.show()
                app.processEvents()
                for _ in range(50):
                    app.processEvents()
                    time.sleep(0.01)
                dialog.hide()
                dialog.deleteLater()
            else:
                results['7. CRM CardEditDialog (open)'] = -1
        except Exception as e:
            errors['CardEditDialog'] = str(e)
            import traceback
            traceback.print_exc()

    # --- 8. Full cycle ---
    with measure('8. TOTAL: login -> MainWindow with data', results):
        try:
            mw2 = MainWindow(employee_data, api_client=api_client)
            mw2.show()
            for _ in range(100):
                app.processEvents()
                time.sleep(0.01)
            mw2.hide()
            mw2.deleteLater()
        except Exception as e:
            errors['Full cycle'] = str(e)

    # ========== REPORT ==========
    print()
    print('=' * 70)
    print('  RESULTS')
    print('=' * 70)
    print()

    total_init = 0
    total_data = 0

    for label, ms in results.items():
        if ms < 0:
            print(f'  {label:55s}  SKIPPED')
            continue
        grade = rating(ms)
        bar = bar_str(ms)
        print(f'  {label:55s}  {ms:8.0f} ms  [{grade:4s}]  {bar}')

        if label.startswith('4'):
            total_init += ms
        elif label.startswith('5'):
            total_data += ms

    # Summary
    print()
    print('-' * 70)
    print('  SUMMARY')
    print('-' * 70)
    print()

    auth_ms = results.get('1. Auth (API login)', 0)
    init_ms = results.get('2. MainWindow.__init__ + init_ui (no tabs)', 0)
    tabs_ms = results.get('3. setup_tabs() - all tabs creation', 0)
    dash_ms = results.get('6. Create 11 dashboards', 0)
    total_startup = auth_ms + init_ms + tabs_ms + dash_ms

    print(f'  Tab constructors (8 total):       {total_init:8.0f} ms  [{rating(total_init)}]')
    print(f'  Data loading (8 total):            {total_data:8.0f} ms  [{rating(total_data)}]')
    print(f'  App startup (auth+init+tabs+dash): {total_startup:8.0f} ms  [{rating(total_startup)}]')

    if errors:
        print()
        print('  ERRORS:')
        for key, err in errors.items():
            print(f'    {key}: {err}')

    # Recommendations
    print()
    print('-' * 70)
    print('  RECOMMENDATIONS')
    print('-' * 70)
    print()

    recs = []

    slow_constructors = [(k, v) for k, v in results.items() if k.startswith('4') and v > 300]
    for label, ms in slow_constructors:
        tab_name = label.split('. ')[1]
        recs.append(f'  [{ms:.0f}ms] {tab_name}: lazy init / QTimer.singleShot for heavy widgets')

    slow_data = [(k, v) for k, v in results.items() if k.startswith('5') and v > 500]
    for label, ms in slow_data:
        tab_name = label.split('. ')[1].split(' data')[0]
        recs.append(f'  [{ms:.0f}ms] {tab_name} data: use local DB for first load / pagination / background thread')

    if dash_ms > 300:
        recs.append(f'  [{dash_ms:.0f}ms] Dashboards: create one at a time with processEvents()')

    if tabs_ms > 500:
        recs.append(f'  [{tabs_ms:.0f}ms] setup_tabs: create only visible tab first, lazy-load rest')

    card_ms = results.get('7. CRM CardEditDialog (open)', 0)
    if card_ms > 500:
        recs.append(f'  [{card_ms:.0f}ms] CardEditDialog: cache employees globally, defer tab widgets')

    if total_startup > 2000:
        recs.append(f'  [{total_startup:.0f}ms] Total startup > 2s: add splash screen / progress bar')

    if not recs:
        print('  All metrics are within acceptable range!')
    else:
        for rec in recs:
            print(rec)

    print()
    print('  Scale: <100ms OK | 100-300ms GOOD | 300-700ms FAIR | 700-1500ms SLOW | >1500ms CRIT')
    print()
    print('=' * 70)
    print()

    app.processEvents()
    return results


if __name__ == '__main__':
    run_performance_test()

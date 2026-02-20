# -*- coding: utf-8 -*-
"""
Регрессионные тесты на баги, обнаруженные при тестировании:

1. Бесконечный цикл: validate → load → validate → ...
2. Несовпадение ID: локальные SQLite ID ≠ серверные PostgreSQL ID
3. Неправильное имя метода: delete_contract_file вместо delete_project_file
4. Серверная валидация с пустым токеном ЯД → файлы помечаются мёртвыми
5. scan_contract_files: сканирование папок ЯД и обнаружение файлов не в БД
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# ТЕСТ 1: delete_project_file существует в DatabaseManager
# ============================================================================

class TestDatabaseManagerMethods:
    """Проверяем, что методы CRUD файлов существуют с правильными именами"""

    def test_delete_project_file_exists(self):
        """DatabaseManager.delete_project_file должен существовать (не delete_contract_file!)"""
        from database.db_manager import DatabaseManager
        assert hasattr(DatabaseManager, 'delete_project_file'), (
            "DatabaseManager.delete_project_file не существует! "
            "Код валидации вызывал delete_contract_file, которого нет."
        )

    def test_delete_contract_file_NOT_on_db_manager(self):
        """delete_contract_file НЕ должен быть на DatabaseManager — это частая ошибка"""
        from database.db_manager import DatabaseManager
        # Если кто-то добавит alias, тест напомнит, что правильное имя — delete_project_file
        assert not hasattr(DatabaseManager, 'delete_contract_file'), (
            "delete_contract_file не должен существовать на DatabaseManager. "
            "Правильное имя: delete_project_file."
        )

    def test_get_project_files_exists(self):
        """DatabaseManager.get_project_files должен существовать"""
        from database.db_manager import DatabaseManager
        assert hasattr(DatabaseManager, 'get_project_files')

    def test_add_project_file_exists(self):
        """DatabaseManager.add_project_file должен существовать"""
        from database.db_manager import DatabaseManager
        assert hasattr(DatabaseManager, 'add_project_file')


# ============================================================================
# ТЕСТ 2: DataAccess.delete_file_record вызывает правильный метод
# ============================================================================

class TestDataAccessFileRecord:
    """Проверяем, что DataAccess вызывает delete_project_file, а не delete_contract_file"""

    def test_delete_file_record_calls_correct_method(self):
        """DataAccess.delete_file_record должен вызывать db.delete_project_file"""
        from utils.data_access import DataAccess
        mock_db = MagicMock()
        mock_db.delete_project_file.return_value = {'yandex_path': '/test'}

        da = DataAccess(api_client=None)
        da.db = mock_db

        da.delete_file_record(42)
        mock_db.delete_project_file.assert_called_once_with(42)

    def test_delete_file_record_api_mode(self):
        """В API режиме delete_file_record идёт через api_client"""
        from utils.data_access import DataAccess
        mock_api = MagicMock()
        mock_api.delete_file_record.return_value = True

        da = DataAccess(api_client=mock_api)

        da.delete_file_record(42)
        mock_api.delete_file_record.assert_called_once_with(42)


# ============================================================================
# ТЕСТ 3: Серверный file_exists бросает Exception при пустом токене
# ============================================================================

class TestServerFileExistsTokenCheck:
    """Серверный file_exists должен бросать Exception, а не молча возвращать False"""

    def test_file_exists_raises_on_empty_token(self):
        """file_exists с пустым токеном → Exception (не False!)"""
        from server.yandex_disk_service import YandexDiskService
        yd = YandexDiskService.__new__(YandexDiskService)
        yd.token = ""
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.headers = {}

        with pytest.raises(Exception, match="not configured"):
            yd.file_exists("disk:/test/file.pdf")

    def test_file_exists_raises_on_none_token(self):
        """file_exists с None токеном → Exception"""
        from server.yandex_disk_service import YandexDiskService
        yd = YandexDiskService.__new__(YandexDiskService)
        yd.token = None
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.headers = {}

        with pytest.raises(Exception, match="not configured"):
            yd.file_exists("disk:/test/file.pdf")

    def test_file_exists_raises_on_401(self):
        """file_exists с протухшим токеном (401) → Exception"""
        from server.yandex_disk_service import YandexDiskService
        yd = YandexDiskService.__new__(YandexDiskService)
        yd.token = "expired_token"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.headers = {"Authorization": "OAuth expired_token"}

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch('server.yandex_disk_service.requests.get', return_value=mock_response):
            with pytest.raises(Exception, match="invalid or expired"):
                yd.file_exists("disk:/test/file.pdf")

    def test_file_exists_returns_true_for_200(self):
        """file_exists с валидным токеном и существующим файлом → True"""
        from server.yandex_disk_service import YandexDiskService
        yd = YandexDiskService.__new__(YandexDiskService)
        yd.token = "valid_token"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.headers = {"Authorization": "OAuth valid_token"}

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('server.yandex_disk_service.requests.get', return_value=mock_response):
            assert yd.file_exists("disk:/test/file.pdf") is True

    def test_file_exists_returns_false_for_404(self):
        """file_exists с валидным токеном и несуществующим файлом → False"""
        from server.yandex_disk_service import YandexDiskService
        yd = YandexDiskService.__new__(YandexDiskService)
        yd.token = "valid_token"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.headers = {"Authorization": "OAuth valid_token"}

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('server.yandex_disk_service.requests.get', return_value=mock_response):
            assert yd.file_exists("disk:/test/missing.pdf") is False


# ============================================================================
# ТЕСТ 4: scan_contract_files определяет стадии по папкам
# ============================================================================

class TestScanContractFiles:
    """Сканирование папок ЯД и определение стадий"""

    def test_scan_returns_files_with_stages(self):
        """scan_contract_files должен распознать стадии по именам папок"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = "test_token"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.session = MagicMock()

        # Мокаем get_folder_contents для разных папок
        root_items = [
            {'name': 'Замер', 'type': 'dir', 'path': 'disk:/root/Замер'},
            {'name': '1 стадия - Планировочное решение', 'type': 'dir', 'path': 'disk:/root/1 стадия - Планировочное решение'},
        ]
        measurement_items = [
            {'name': 'plan.pdf', 'type': 'file', 'path': 'disk:/root/Замер/plan.pdf'},
        ]
        stage1_items = [
            {'name': 'layout.jpg', 'type': 'file', 'path': 'disk:/root/1 стадия - Планировочное решение/layout.jpg'},
            {'name': 'plan.dwg', 'type': 'file', 'path': 'disk:/root/1 стадия - Планировочное решение/plan.dwg'},
        ]

        def mock_get_contents(path):
            if path == 'disk:/root':
                return root_items
            elif 'Замер' in path:
                return measurement_items
            elif '1 стадия' in path:
                return stage1_items
            return []

        yd.get_folder_contents = MagicMock(side_effect=mock_get_contents)

        result = yd.scan_contract_files('disk:/root')

        assert len(result) == 3
        stages = {f['stage'] for f in result}
        assert 'measurement' in stages
        assert 'stage1' in stages

        # Проверяем типы файлов
        pdf_files = [f for f in result if f['file_type'] == 'pdf']
        image_files = [f for f in result if f['file_type'] == 'image']
        cad_files = [f for f in result if f['file_type'] == 'cad']
        assert len(pdf_files) == 1
        assert len(image_files) == 1
        assert len(cad_files) == 1

    def test_scan_empty_folder(self):
        """scan_contract_files на пустой папке возвращает []"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = "test_token"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.session = MagicMock()
        yd.get_folder_contents = MagicMock(return_value=[])

        result = yd.scan_contract_files('disk:/empty')
        assert result == []

    def test_scan_no_token(self):
        """scan_contract_files без токена возвращает []"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = None

        result = yd.scan_contract_files('disk:/root')
        assert result == []

    def test_scan_supervision_files(self):
        """scan_contract_files находит файлы авторского надзора"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = "test_token"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.session = MagicMock()

        root_items = [
            {'name': 'Авторский надзор', 'type': 'dir', 'path': 'disk:/root/Авторский надзор'},
        ]
        supervision_items = [
            {'name': 'Стадия 1: Закупка керамогранита', 'type': 'dir',
             'path': 'disk:/root/Авторский надзор/Стадия 1: Закупка керамогранита'},
        ]
        stage_items = [
            {'name': 'invoice.pdf', 'type': 'file',
             'path': 'disk:/root/Авторский надзор/Стадия 1: Закупка керамогранита/invoice.pdf'},
        ]

        def mock_get_contents(path):
            if path == 'disk:/root':
                return root_items
            elif 'Авторский надзор' in path and 'Стадия' not in path:
                return supervision_items
            elif 'Стадия 1' in path:
                return stage_items
            return []

        yd.get_folder_contents = MagicMock(side_effect=mock_get_contents)

        result = yd.scan_contract_files('disk:/root')
        assert len(result) == 1
        assert result[0]['stage'] == 'supervision'
        assert result[0]['file_name'] == 'invoice.pdf'

    def test_scan_detect_file_types(self):
        """scan_contract_files правильно определяет типы файлов"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = "test_token"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.session = MagicMock()

        items = [
            {'name': 'Замер', 'type': 'dir', 'path': 'disk:/root/Замер'},
        ]
        files = [
            {'name': 'photo.jpg', 'type': 'file', 'path': 'disk:/root/Замер/photo.jpg'},
            {'name': 'doc.pdf', 'type': 'file', 'path': 'disk:/root/Замер/doc.pdf'},
            {'name': 'plan.dwg', 'type': 'file', 'path': 'disk:/root/Замер/plan.dwg'},
            {'name': 'data.xlsx', 'type': 'file', 'path': 'disk:/root/Замер/data.xlsx'},
            {'name': 'readme.txt', 'type': 'file', 'path': 'disk:/root/Замер/readme.txt'},
        ]

        def mock_get_contents(path):
            if path == 'disk:/root':
                return items
            return files

        yd.get_folder_contents = MagicMock(side_effect=mock_get_contents)

        result = yd.scan_contract_files('disk:/root')
        types = {f['file_name']: f['file_type'] for f in result}
        assert types['photo.jpg'] == 'image'
        assert types['doc.pdf'] == 'pdf'
        assert types['plan.dwg'] == 'cad'
        assert types['data.xlsx'] == 'excel'
        assert types['readme.txt'] == 'other'

    def test_scan_questionnaire_folder(self):
        """scan_contract_files распознаёт папку 'Анкета' как questionnaire"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = "test_token"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.session = MagicMock()

        root_items = [
            {'name': 'Анкета', 'type': 'dir', 'path': 'disk:/root/Анкета'},
            {'name': 'Документы', 'type': 'dir', 'path': 'disk:/root/Документы'},
        ]
        anketa_items = [
            {'name': 'form.pdf', 'type': 'file', 'path': 'disk:/root/Анкета/form.pdf'},
        ]
        docs_items = [
            {'name': 'contract.docx', 'type': 'file', 'path': 'disk:/root/Документы/contract.docx'},
        ]

        def mock_get_contents(path):
            if path == 'disk:/root':
                return root_items
            elif 'Анкета' in path:
                return anketa_items
            elif 'Документы' in path:
                return docs_items
            return []

        yd.get_folder_contents = MagicMock(side_effect=mock_get_contents)

        result = yd.scan_contract_files('disk:/root')
        assert len(result) == 2
        stages = {f['stage'] for f in result}
        assert 'questionnaire' in stages
        assert 'documents' in stages

    def test_scan_fuzzy_folder_matching(self):
        """scan_contract_files распознаёт папки с нестандартными именами (нечёткий маппинг)"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = "test_token"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.session = MagicMock()

        root_items = [
            {'name': 'Замеры объекта', 'type': 'dir', 'path': 'disk:/root/Замеры объекта'},
            {'name': 'Чертежи проекта', 'type': 'dir', 'path': 'disk:/root/Чертежи проекта'},
        ]
        measurement_items = [
            {'name': 'plan.pdf', 'type': 'file', 'path': 'disk:/root/Замеры объекта/plan.pdf'},
        ]
        stage3_items = [
            {'name': 'drawing.dwg', 'type': 'file', 'path': 'disk:/root/Чертежи проекта/drawing.dwg'},
        ]

        def mock_get_contents(path):
            if path == 'disk:/root':
                return root_items
            elif 'Замеры' in path:
                return measurement_items
            elif 'Чертежи' in path:
                return stage3_items
            return []

        yd.get_folder_contents = MagicMock(side_effect=mock_get_contents)

        result = yd.scan_contract_files('disk:/root')
        assert len(result) == 2
        stages = {f['file_name']: f['stage'] for f in result}
        assert stages['plan.pdf'] == 'measurement'
        assert stages['drawing.dwg'] == 'stage3'


# ============================================================================
# ТЕСТ 5: load_supervision_files не вызывает validate повторно
# ============================================================================

class TestLoadSupervisionFilesNoLoop:
    """Проверяем, что load_supervision_files(validate=False) не запускает валидацию"""

    def test_load_with_validate_false_skips_validation(self):
        """load_supervision_files(validate=False) НЕ вызывает validate"""
        # Проверяем сигнатуру метода — validate=True по умолчанию
        import inspect
        # Нужно импортировать модуль, но SupervisionCardEditDialog требует Qt
        # Проверяем через файл
        import ast
        source_path = PROJECT_ROOT / 'ui' / 'supervision_card_edit_dialog.py'
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()

        tree = ast.parse(source)
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'load_supervision_files':
                args = node.args
                defaults = args.defaults
                # Должен быть аргумент validate с default=True
                arg_names = [a.arg for a in args.args]
                if 'validate' in arg_names:
                    idx = arg_names.index('validate')
                    # defaults align to the end of args
                    default_idx = idx - (len(arg_names) - len(defaults))
                    if default_idx >= 0:
                        default_val = defaults[default_idx]
                        assert isinstance(default_val, ast.Constant) and default_val.value is True, \
                            "validate должен быть True по умолчанию"
                        found = True
                break
        assert found, "load_supervision_files должен иметь параметр validate=True"

    def test_validate_callback_passes_validate_false(self):
        """Код валидации при перезагрузке передаёт validate=False"""
        source_path = PROJECT_ROOT / 'ui' / 'supervision_card_edit_dialog.py'
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Проверяем, что в коде есть load_supervision_files(validate=False)
        assert 'load_supervision_files(validate=False)' in source, (
            "Код валидации должен вызывать load_supervision_files(validate=False) "
            "чтобы предотвратить бесконечный цикл"
        )


# ============================================================================
# ТЕСТ 6: API Client scan_contract_files метод
# ============================================================================

class TestAPIClientScanMethod:
    """Проверяем что scan_contract_files метод есть в APIClient"""

    def test_scan_method_exists(self):
        """APIClient.scan_contract_files должен существовать"""
        from utils.api_client import APIClient
        assert hasattr(APIClient, 'scan_contract_files')

    def test_scan_method_signature(self):
        """scan_contract_files принимает contract_id"""
        import inspect
        from utils.api_client import APIClient
        sig = inspect.signature(APIClient.scan_contract_files)
        params = list(sig.parameters.keys())
        assert 'contract_id' in params


# ============================================================================
# ТЕСТ 7: Потокобезопасность — _reload_files_signal вместо QTimer из потоков
# ============================================================================

class TestThreadSafeReload:
    """Проверяем, что код использует pyqtSignal вместо QTimer.singleShot из потоков"""

    def test_supervision_uses_signal_not_qtimer_in_validate(self):
        """Валидация supervision использует _reload_files_signal.emit() вместо QTimer"""
        source_path = PROJECT_ROOT / 'ui' / 'supervision_card_edit_dialog.py'
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Должен содержать _reload_files_signal.emit()
        assert '_reload_files_signal.emit()' in source, (
            "Код должен использовать _reload_files_signal.emit() "
            "для потокобезопасной перезагрузки файлов"
        )

    def test_supervision_has_reload_signal_definition(self):
        """SupervisionCardEditDialog определяет _reload_files_signal"""
        source_path = PROJECT_ROOT / 'ui' / 'supervision_card_edit_dialog.py'
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert '_reload_files_signal = pyqtSignal()' in source, (
            "_reload_files_signal должен быть определён как pyqtSignal()"
        )

    def test_crm_uses_signal_not_qtimer_in_validate(self):
        """Валидация CRM использует _reload_stage_files_signal.emit()"""
        source_path = PROJECT_ROOT / 'ui' / 'crm_card_edit_dialog.py'
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert '_reload_stage_files_signal.emit()' in source, (
            "CRM должен использовать _reload_stage_files_signal.emit() "
            "для потокобезопасной перезагрузки файлов"
        )

    def test_crm_has_reload_signal_definition(self):
        """CardEditDialog определяет _reload_stage_files_signal"""
        source_path = PROJECT_ROOT / 'ui' / 'crm_card_edit_dialog.py'
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert '_reload_stage_files_signal = pyqtSignal()' in source, (
            "_reload_stage_files_signal должен быть определён как pyqtSignal()"
        )


# ============================================================================
# ТЕСТ 8: Нормализация путей в scan (disk: prefix)
# ============================================================================

class TestPathNormalization:
    """Пути ЯД должны нормализоваться при сравнении (disk: prefix)"""

    def test_scan_normalizes_paths_for_dedup(self):
        """scan_contract_files на сервере нормализует пути перед сравнением"""
        source_path = PROJECT_ROOT / 'server' / 'routers' / 'files_router.py'
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'normalize_path' in source, (
            "Серверный scan должен содержать функцию normalize_path "
            "для нормализации disk: prefix"
        )

    def test_scan_has_race_condition_protection(self):
        """scan endpoint защищён от параллельных вызовов"""
        source_path = PROJECT_ROOT / 'server' / 'routers' / 'files_router.py'
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert '_scanning_contracts' in source, (
            "Серверный scan должен иметь _scanning_contracts lock "
            "для предотвращения параллельных сканирований"
        )

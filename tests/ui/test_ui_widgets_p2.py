# -*- coding: utf-8 -*-
"""
Тесты для P2 UI виджетов:
- ui/custom_combobox.py (CustomComboBox)
- ui/custom_dateedit.py (CustomDateEdit)
- ui/flow_layout.py (FlowLayout)
- ui/bubble_tooltip.py (BubbleToolTip)
- ui/custom_title_bar.py (CustomTitleBar)
- ui/file_list_widget.py (FileListWidget, FileListItemWidget)
- ui/file_gallery_widget.py (FileGalleryWidget)
- ui/file_preview_widget.py (FilePreviewWidget)
- ui/variation_gallery_widget.py (VariationGalleryWidget)
- ui/permissions_matrix_widget.py (PERMISSION_GROUPS, ROLES, DEFAULT_ROLE_PERMISSIONS)
- ui/dashboard_widget.py (FilterButton, MetricCard)

Покрытие:
- Создание виджетов
- Бизнес-логика: wheel events, flow layout, permissions constants
- Сигналы: upload_requested, delete_requested
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==================== CustomComboBox ====================

class TestCustomComboBox:
    """CustomComboBox — QComboBox с блокировкой wheel."""

    def test_creates(self, qtbot):
        from ui.custom_combobox import CustomComboBox
        combo = CustomComboBox()
        qtbot.addWidget(combo)
        assert combo is not None

    def test_focus_policy_strong(self, qtbot):
        from ui.custom_combobox import CustomComboBox
        from PyQt5.QtCore import Qt
        combo = CustomComboBox()
        qtbot.addWidget(combo)
        assert combo.focusPolicy() == Qt.StrongFocus

    def test_wheel_ignored_without_focus(self, qtbot):
        """Wheel event без фокуса — игнорируется."""
        from ui.custom_combobox import CustomComboBox
        from PyQt5.QtCore import QEvent, QPoint, Qt
        from PyQt5.QtGui import QWheelEvent
        combo = CustomComboBox()
        qtbot.addWidget(combo)
        combo.addItems(['A', 'B', 'C'])
        combo.setCurrentIndex(0)
        # Без фокуса
        combo.clearFocus()
        event = QWheelEvent(
            QPoint(10, 10), QPoint(10, 10),
            QPoint(0, 120), QPoint(0, 120),
            Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False
        )
        combo.wheelEvent(event)
        # Значение не должно измениться
        assert combo.currentIndex() == 0


# ==================== CustomDateEdit ====================

class TestCustomDateEdit:
    """CustomDateEdit — QDateEdit с блокировкой wheel."""

    def test_creates(self, qtbot):
        from ui.custom_dateedit import CustomDateEdit
        date_edit = CustomDateEdit()
        qtbot.addWidget(date_edit)
        assert date_edit is not None

    def test_wheel_ignored_when_calendar_closed(self, qtbot):
        """Wheel без открытого календаря — игнорируется."""
        from ui.custom_dateedit import CustomDateEdit
        from PyQt5.QtCore import QDate
        date_edit = CustomDateEdit()
        qtbot.addWidget(date_edit)
        date_edit.setDate(QDate(2026, 1, 15))
        # Календарь закрыт — wheel event должен быть проигнорирован
        from PyQt5.QtCore import QPoint, Qt
        from PyQt5.QtGui import QWheelEvent
        event = QWheelEvent(
            QPoint(10, 10), QPoint(10, 10),
            QPoint(0, 120), QPoint(0, 120),
            Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False
        )
        date_edit.wheelEvent(event)


# ==================== FlowLayout ====================

class TestFlowLayout:
    """FlowLayout — адаптивный layout."""

    def test_creates(self, qtbot):
        from ui.flow_layout import FlowLayout
        layout = FlowLayout()
        assert layout is not None

    def test_initial_count_zero(self):
        from ui.flow_layout import FlowLayout
        layout = FlowLayout()
        assert layout.count() == 0

    def test_add_widget(self, qtbot):
        from ui.flow_layout import FlowLayout
        from PyQt5.QtWidgets import QWidget, QPushButton
        container = QWidget()
        qtbot.addWidget(container)
        layout = FlowLayout(container)
        btn = QPushButton("Test")
        layout.addWidget(btn)
        assert layout.count() == 1

    def test_item_at_valid(self, qtbot):
        from ui.flow_layout import FlowLayout
        from PyQt5.QtWidgets import QWidget, QPushButton
        container = QWidget()
        qtbot.addWidget(container)
        layout = FlowLayout(container)
        btn = QPushButton("A")
        layout.addWidget(btn)
        assert layout.itemAt(0) is not None

    def test_item_at_invalid(self):
        from ui.flow_layout import FlowLayout
        layout = FlowLayout()
        assert layout.itemAt(5) is None
        assert layout.itemAt(-1) is None

    def test_take_at(self, qtbot):
        from ui.flow_layout import FlowLayout
        from PyQt5.QtWidgets import QWidget, QPushButton
        container = QWidget()
        qtbot.addWidget(container)
        layout = FlowLayout(container)
        btn = QPushButton("X")
        layout.addWidget(btn)
        item = layout.takeAt(0)
        assert item is not None
        assert layout.count() == 0

    def test_take_at_invalid(self):
        from ui.flow_layout import FlowLayout
        layout = FlowLayout()
        assert layout.takeAt(0) is None

    def test_has_height_for_width(self):
        from ui.flow_layout import FlowLayout
        layout = FlowLayout()
        assert layout.hasHeightForWidth() is True

    def test_height_for_width_empty(self):
        from ui.flow_layout import FlowLayout
        layout = FlowLayout()
        h = layout.heightForWidth(500)
        assert isinstance(h, int)

    def test_minimum_size(self, qtbot):
        from ui.flow_layout import FlowLayout
        from PyQt5.QtWidgets import QWidget, QPushButton
        from PyQt5.QtCore import QSize
        container = QWidget()
        qtbot.addWidget(container)
        layout = FlowLayout(container)
        btn = QPushButton("Test Button")
        layout.addWidget(btn)
        size = layout.minimumSize()
        assert isinstance(size, QSize)
        assert size.width() > 0

    def test_size_hint_equals_minimum(self):
        from ui.flow_layout import FlowLayout
        layout = FlowLayout()
        assert layout.sizeHint() == layout.minimumSize()

    def test_expanding_directions_none(self):
        """FlowLayout не растягивается ни в одном направлении."""
        from ui.flow_layout import FlowLayout
        layout = FlowLayout()
        dirs = layout.expandingDirections()
        assert int(dirs) == 0

    def test_multiple_widgets_layout(self, qtbot):
        """Несколько виджетов раскладываются корректно."""
        from ui.flow_layout import FlowLayout
        from PyQt5.QtWidgets import QWidget, QPushButton
        from PyQt5.QtCore import QRect
        container = QWidget()
        qtbot.addWidget(container)
        layout = FlowLayout(container, spacing=5)
        for i in range(5):
            layout.addWidget(QPushButton(f"Btn {i}"))
        assert layout.count() == 5
        # Проверяем heightForWidth
        h = layout.heightForWidth(200)
        assert h > 0


# ==================== BubbleToolTip ====================

class TestBubbleToolTip:
    """BubbleToolTip — tooltip-облачко."""

    def test_singleton(self, qtbot):
        from ui.bubble_tooltip import BubbleToolTip
        instance1 = BubbleToolTip.instance()
        instance2 = BubbleToolTip.instance()
        qtbot.addWidget(instance1)
        assert instance1 is instance2

    def test_has_show_bubble(self):
        from ui.bubble_tooltip import BubbleToolTip
        assert hasattr(BubbleToolTip, 'show_bubble')


class TestToolTipFilter:
    """ToolTipFilter — фильтр событий для tooltip."""

    def test_creates(self, qtbot):
        from ui.bubble_tooltip import ToolTipFilter
        from PyQt5.QtWidgets import QWidget
        parent = QWidget()
        qtbot.addWidget(parent)
        f = ToolTipFilter(parent)
        assert f is not None


# ==================== CustomTitleBar ====================

class TestCustomTitleBar:
    """CustomTitleBar — кастомный заголовок окна."""

    def test_creates_simple_mode(self, qtbot):
        from ui.custom_title_bar import CustomTitleBar
        from PyQt5.QtWidgets import QDialog
        dialog = QDialog()
        qtbot.addWidget(dialog)
        title_bar = CustomTitleBar(dialog, title="Тест", simple_mode=True)
        assert title_bar is not None

    def test_set_title(self, qtbot):
        from ui.custom_title_bar import CustomTitleBar
        from PyQt5.QtWidgets import QDialog
        dialog = QDialog()
        qtbot.addWidget(dialog)
        title_bar = CustomTitleBar(dialog, title="Начальный", simple_mode=True)
        title_bar.set_title("Новый заголовок")

    def test_has_close_button_simple_mode(self, qtbot):
        from ui.custom_title_bar import CustomTitleBar
        from PyQt5.QtWidgets import QDialog, QPushButton
        dialog = QDialog()
        qtbot.addWidget(dialog)
        title_bar = CustomTitleBar(dialog, title="Тест", simple_mode=True)
        buttons = title_bar.findChildren(QPushButton)
        assert len(buttons) >= 1  # Минимум кнопка закрытия


# ==================== FileListWidget ====================

class TestFileListWidget:
    """FileListWidget — список файлов."""

    def test_creates(self, qtbot):
        from ui.file_list_widget import FileListWidget
        widget = FileListWidget(
            title="Документы",
            stage="docs",
            file_types=['pdf', 'docx'],
            can_delete=True,
            can_upload=True,
        )
        qtbot.addWidget(widget)
        assert widget is not None

    def test_load_empty_files(self, qtbot):
        from ui.file_list_widget import FileListWidget
        widget = FileListWidget(
            title="Тест",
            stage="test",
            file_types=['pdf'],
            can_delete=False,
            can_upload=False,
        )
        qtbot.addWidget(widget)
        widget.load_files([])

    def test_load_files_with_data(self, qtbot):
        from ui.file_list_widget import FileListWidget
        widget = FileListWidget(
            title="Файлы",
            stage="stage",
            file_types=['pdf'],
            can_delete=True,
            can_upload=True,
        )
        qtbot.addWidget(widget)
        files = [
            {'id': 1, 'file_name': 'doc.pdf', 'file_type': 'pdf',
             'public_link': 'http://link', 'yandex_path': '/path'},
        ]
        widget.load_files(files)

    def test_clear_files(self, qtbot):
        from ui.file_list_widget import FileListWidget
        widget = FileListWidget(
            title="Тест",
            stage="test",
            file_types=['pdf'],
            can_delete=False,
            can_upload=False,
        )
        qtbot.addWidget(widget)
        widget.clear_files()

    def test_has_upload_signal(self):
        from ui.file_list_widget import FileListWidget
        assert hasattr(FileListWidget, 'upload_requested')

    def test_has_delete_signal(self):
        from ui.file_list_widget import FileListWidget
        assert hasattr(FileListWidget, 'delete_requested')


class TestFileListItemWidget:
    """FileListItemWidget — элемент файла в списке."""

    def test_creates(self, qtbot):
        from ui.file_list_widget import FileListItemWidget
        item = FileListItemWidget(
            file_id=1,
            file_name="document.pdf",
            file_type="pdf",
            public_link="http://example.com/doc.pdf",
            can_delete=True,
        )
        qtbot.addWidget(item)
        assert item is not None


# ==================== FileGalleryWidget ====================

class TestFileGalleryWidget:
    """FileGalleryWidget — галерея файлов."""

    def test_creates(self, qtbot):
        from ui.file_gallery_widget import FileGalleryWidget
        widget = FileGalleryWidget(
            title="Изображения",
            stage="images",
            file_types=['image'],
            can_delete=True,
            can_upload=True,
        )
        qtbot.addWidget(widget)
        assert widget is not None

    def test_get_files_count_empty(self, qtbot):
        from ui.file_gallery_widget import FileGalleryWidget
        widget = FileGalleryWidget(
            title="Тест",
            stage="test",
            file_types=['image'],
            can_delete=False,
            can_upload=False,
        )
        qtbot.addWidget(widget)
        assert widget.get_files_count() == 0

    def test_clear_previews(self, qtbot):
        from ui.file_gallery_widget import FileGalleryWidget
        widget = FileGalleryWidget(
            title="Тест",
            stage="test",
            file_types=['image'],
            can_delete=False,
            can_upload=False,
        )
        qtbot.addWidget(widget)
        widget.clear_previews()

    def test_has_signals(self):
        from ui.file_gallery_widget import FileGalleryWidget
        assert hasattr(FileGalleryWidget, 'upload_requested')
        assert hasattr(FileGalleryWidget, 'delete_requested')
        assert hasattr(FileGalleryWidget, 'files_changed')


# ==================== FilePreviewWidget ====================

class TestFilePreviewWidget:
    """FilePreviewWidget — превью файла."""

    def test_creates(self, qtbot):
        from ui.file_preview_widget import FilePreviewWidget
        widget = FilePreviewWidget(
            file_id=1,
            file_name="photo.jpg",
            file_type="image",
            public_link="http://example.com/photo.jpg",
            preview_pixmap=None,
            can_delete=True,
        )
        qtbot.addWidget(widget)
        assert widget is not None

    def test_has_delete_signal(self):
        from ui.file_preview_widget import FilePreviewWidget
        assert hasattr(FilePreviewWidget, 'delete_requested')


# ==================== VariationGalleryWidget ====================

class TestVariationGalleryWidget:
    """VariationGalleryWidget — галерея вариаций."""

    def test_creates(self, qtbot):
        from ui.variation_gallery_widget import VariationGalleryWidget
        widget = VariationGalleryWidget(
            title="Визуализации",
            stage="viz",
            file_types=['image'],
            can_delete=True,
            can_upload=True,
        )
        qtbot.addWidget(widget)
        assert widget is not None

    def test_get_variation_count(self, qtbot):
        from ui.variation_gallery_widget import VariationGalleryWidget
        widget = VariationGalleryWidget(
            title="Тест",
            stage="test",
            file_types=['image'],
            can_delete=False,
            can_upload=False,
        )
        qtbot.addWidget(widget)
        count = widget.get_variation_count()
        assert count >= 1  # Минимум 1 вариация по умолчанию

    def test_clear_all(self, qtbot):
        from ui.variation_gallery_widget import VariationGalleryWidget
        widget = VariationGalleryWidget(
            title="Тест",
            stage="test",
            file_types=['image'],
            can_delete=False,
            can_upload=False,
        )
        qtbot.addWidget(widget)
        widget.clear_all()

    def test_has_signals(self):
        from ui.variation_gallery_widget import VariationGalleryWidget
        assert hasattr(VariationGalleryWidget, 'upload_requested')
        assert hasattr(VariationGalleryWidget, 'delete_requested')
        assert hasattr(VariationGalleryWidget, 'add_variation_requested')
        assert hasattr(VariationGalleryWidget, 'delete_variation_requested')


# ==================== PermissionsMatrixWidget ====================

class TestPermissionsConstants:
    """Константы матрицы прав."""

    def test_permission_groups_not_empty(self):
        from ui.permissions_matrix_widget import PERMISSION_GROUPS
        assert len(PERMISSION_GROUPS) > 0

    def test_has_crm_group(self):
        from ui.permissions_matrix_widget import PERMISSION_GROUPS
        assert 'CRM' in PERMISSION_GROUPS

    def test_has_supervision_group(self):
        from ui.permissions_matrix_widget import PERMISSION_GROUPS
        assert 'Надзор' in PERMISSION_GROUPS

    def test_roles_count(self):
        from ui.permissions_matrix_widget import ROLES
        assert len(ROLES) == 9

    def test_roles_includes_leader(self):
        from ui.permissions_matrix_widget import ROLES
        assert 'Руководитель студии' in ROLES

    def test_default_permissions_for_leader(self):
        """Руководитель имеет все права."""
        from ui.permissions_matrix_widget import DEFAULT_ROLE_PERMISSIONS, PERMISSION_GROUPS
        leader_perms = DEFAULT_ROLE_PERMISSIONS['Руководитель студии']
        all_perms = set()
        for perms in PERMISSION_GROUPS.values():
            all_perms.update(perms)
        # Руководитель должен иметь все права
        assert all_perms.issubset(leader_perms)

    def test_default_permissions_manager_limited(self):
        """Менеджер имеет ограниченные права."""
        from ui.permissions_matrix_widget import DEFAULT_ROLE_PERMISSIONS
        manager_perms = DEFAULT_ROLE_PERMISSIONS.get('Менеджер', set())
        leader_perms = DEFAULT_ROLE_PERMISSIONS['Руководитель студии']
        assert len(manager_perms) < len(leader_perms)

    def test_all_roles_have_defaults(self):
        """У каждой роли есть дефолтные права."""
        from ui.permissions_matrix_widget import DEFAULT_ROLE_PERMISSIONS, ROLES
        for role in ROLES:
            assert role in DEFAULT_ROLE_PERMISSIONS, f"Нет дефолтных прав для {role}"

    def test_no_unknown_permissions_in_defaults(self):
        """Все права в defaults присутствуют в PERMISSION_GROUPS."""
        from ui.permissions_matrix_widget import DEFAULT_ROLE_PERMISSIONS, PERMISSION_GROUPS
        all_known = set()
        for perms in PERMISSION_GROUPS.values():
            all_known.update(perms)
        for role, perms in DEFAULT_ROLE_PERMISSIONS.items():
            for p in perms:
                assert p in all_known, f"Неизвестное право '{p}' у роли '{role}'"


# ==================== DashboardWidget ====================

class TestDashboardWidgetImport:
    """dashboard_widget.py — импорт и константы."""

    def test_imports_filter_button(self):
        from ui.dashboard_widget import FilterButton
        assert FilterButton is not None

    def test_imports_metric_card(self):
        from ui.dashboard_widget import MetricCard
        assert MetricCard is not None

    def test_filter_button_creates(self, qtbot):
        from ui.dashboard_widget import FilterButton
        btn = FilterButton(filter_type='year', options=['2025', '2026'], border_color='#ccc')
        qtbot.addWidget(btn)
        assert btn is not None

    def test_filter_button_get_value(self, qtbot):
        from ui.dashboard_widget import FilterButton
        btn = FilterButton(filter_type='year', options=['2025', '2026'], border_color='#ccc')
        qtbot.addWidget(btn)
        # Изначально значение None (ничего не выбрано)
        assert btn.get_value() is None
        # После выбора — значение сохраняется
        btn.select_option('2025')
        assert btn.get_value() == '2025'

    def test_filter_button_set_options(self, qtbot):
        from ui.dashboard_widget import FilterButton
        btn = FilterButton(filter_type='type', options=['A', 'B'], border_color='#ccc')
        qtbot.addWidget(btn)
        btn.set_options(['X', 'Y', 'Z'])

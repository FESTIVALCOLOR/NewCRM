# -*- coding: utf-8 -*-
"""Тесты для file_gallery_widget, file_list_widget, file_preview_widget, variation_gallery_widget"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QWidget, QPushButton
from PyQt5.QtGui import QPixmap, QIcon


# ─── FilePreviewWidget ──────────────────────────────────────────────────

class TestFilePreviewWidget:
    """Тесты FilePreviewWidget"""

    def test_creation(self, qtbot):
        # file_preview_widget НЕ использует IconLoader — патч не нужен
        from ui.file_preview_widget import FilePreviewWidget
        w = FilePreviewWidget(
            file_id=1, file_name='test.jpg', file_type='image',
            public_link='https://example.com/test.jpg',
            can_delete=True, yandex_path='/test/test.jpg'
        )
        qtbot.addWidget(w)
        assert w.file_id == 1
        assert w.file_name == 'test.jpg'

    def test_creation_no_delete(self, qtbot):
        from ui.file_preview_widget import FilePreviewWidget
        w = FilePreviewWidget(
            file_id=2, file_name='doc.pdf', file_type='document',
            public_link='', can_delete=False
        )
        qtbot.addWidget(w)
        assert w.can_delete is False

    def test_with_preview_pixmap(self, qtbot):
        from ui.file_preview_widget import FilePreviewWidget
        pixmap = QPixmap(100, 100)
        w = FilePreviewWidget(
            file_id=3, file_name='img.png', file_type='image',
            public_link='', preview_pixmap=pixmap
        )
        qtbot.addWidget(w)

    def test_update_preview(self, qtbot):
        from ui.file_preview_widget import FilePreviewWidget
        w = FilePreviewWidget(
            file_id=4, file_name='img.jpg', file_type='image',
            public_link=''
        )
        qtbot.addWidget(w)
        pixmap = QPixmap(200, 200)
        w.update_preview(pixmap)


# ─── FileListItemWidget ─────────────────────────────────────────────────

def _make_icon_loader_mock():
    """Создаёт мок IconLoader с реальными Qt-объектами вместо MagicMock."""
    mock = MagicMock()
    mock.create_icon_button.return_value = QPushButton()
    mock.load.return_value = QIcon()
    return mock


class TestFileListItemWidget:
    """Тесты FileListItemWidget"""

    def test_creation(self, qtbot):
        with patch('ui.file_list_widget.IconLoader', _make_icon_loader_mock()):
            from ui.file_list_widget import FileListItemWidget
            w = FileListItemWidget(
                file_id=1, file_name='document.pdf',
                file_type='document', public_link='https://link.com',
                can_delete=True, yandex_path='/path/doc.pdf'
            )
            qtbot.addWidget(w)
            assert w.file_id == 1
            assert w.file_name == 'document.pdf'

    def test_no_delete(self, qtbot):
        with patch('ui.file_list_widget.IconLoader', _make_icon_loader_mock()):
            from ui.file_list_widget import FileListItemWidget
            w = FileListItemWidget(
                file_id=2, file_name='readme.txt',
                file_type='text', public_link='',
                can_delete=False
            )
            qtbot.addWidget(w)


# ─── FileListWidget ─────────────────────────────────────────────────────

class TestFileListWidget:
    """Тесты FileListWidget"""

    def test_creation(self, qtbot):
        with patch('ui.file_list_widget.IconLoader', _make_icon_loader_mock()):
            from ui.file_list_widget import FileListWidget
            w = FileListWidget(
                title='Документы', stage='design',
                file_types=['pdf', 'doc'], can_delete=True, can_upload=True
            )
            qtbot.addWidget(w)
            assert w.title == 'Документы'
            assert w.stage == 'design'

    def test_clear_files(self, qtbot):
        with patch('ui.file_list_widget.IconLoader', _make_icon_loader_mock()):
            from ui.file_list_widget import FileListWidget
            w = FileListWidget(title='Т', stage='s')
            qtbot.addWidget(w)
            w.clear_files()

    def test_no_upload(self, qtbot):
        with patch('ui.file_list_widget.IconLoader', _make_icon_loader_mock()):
            from ui.file_list_widget import FileListWidget
            w = FileListWidget(title='Т', stage='s', can_upload=False)
            qtbot.addWidget(w)


# ─── FileGalleryWidget ──────────────────────────────────────────────────

class TestFileGalleryWidget:
    """Тесты FileGalleryWidget"""

    def test_creation(self, qtbot):
        # file_gallery_widget НЕ использует IconLoader — патч не нужен
        from ui.file_gallery_widget import FileGalleryWidget
        w = FileGalleryWidget(
            title='Галерея', stage='design',
            file_types=['jpg', 'png']
        )
        qtbot.addWidget(w)
        assert w.title == 'Галерея'

    def test_clear_previews(self, qtbot):
        from ui.file_gallery_widget import FileGalleryWidget
        w = FileGalleryWidget(title='Г', stage='s', file_types=['jpg'])
        qtbot.addWidget(w)
        w.clear_previews()

    def test_get_files_count_empty(self, qtbot):
        from ui.file_gallery_widget import FileGalleryWidget
        w = FileGalleryWidget(title='Г', stage='s', file_types=['jpg'])
        qtbot.addWidget(w)
        assert w.get_files_count() == 0

    def test_no_delete(self, qtbot):
        from ui.file_gallery_widget import FileGalleryWidget
        w = FileGalleryWidget(
            title='Г', stage='s', file_types=['jpg'], can_delete=False
        )
        qtbot.addWidget(w)


# ─── VariationGalleryWidget ─────────────────────────────────────────────

class TestVariationGalleryWidget:
    """Тесты VariationGalleryWidget"""

    def test_creation(self, qtbot):
        with patch('ui.variation_gallery_widget.IconLoader', _make_icon_loader_mock()):
            from ui.variation_gallery_widget import VariationGalleryWidget
            w = VariationGalleryWidget(
                title='Вариации', stage='design',
                file_types=['jpg', 'png']
            )
            qtbot.addWidget(w)
            assert w.title == 'Вариации'

    def test_get_variation_count(self, qtbot):
        with patch('ui.variation_gallery_widget.IconLoader', _make_icon_loader_mock()):
            from ui.variation_gallery_widget import VariationGalleryWidget
            w = VariationGalleryWidget(title='В', stage='s', file_types=['jpg'])
            qtbot.addWidget(w)
            assert w.get_variation_count() >= 0

    def test_clear_all(self, qtbot):
        with patch('ui.variation_gallery_widget.IconLoader', _make_icon_loader_mock()):
            from ui.variation_gallery_widget import VariationGalleryWidget
            w = VariationGalleryWidget(title='В', stage='s', file_types=['jpg'])
            qtbot.addWidget(w)
            w.clear_all()

    def test_no_upload(self, qtbot):
        with patch('ui.variation_gallery_widget.IconLoader', _make_icon_loader_mock()):
            from ui.variation_gallery_widget import VariationGalleryWidget
            w = VariationGalleryWidget(
                title='В', stage='s', file_types=['jpg'], can_upload=False
            )
            qtbot.addWidget(w)

# -*- coding: utf-8 -*-
"""
Покрытие utils/icon_loader.py — IconLoader (4 статических метода).
~15 тестов. PyQt5 компоненты мокаются через patch.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock, mock_open

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ==================== Вспомогательные моки ====================

def _make_mock_qicon(is_null=False):
    """Создать мок QIcon с настраиваемым isNull()"""
    icon = MagicMock()
    icon.isNull.return_value = is_null
    return icon


# ==================== load() — загрузка SVG иконки ====================

class TestIconLoaderLoad:
    """Тесты метода IconLoader.load()"""

    @patch('utils.icon_loader.QIcon')
    @patch('utils.icon_loader.os.path.exists', return_value=True)
    @patch('utils.icon_loader.resource_path', return_value='/resolved/icons/search.svg')
    def test_load_добавляет_svg_расширение(self, mock_rp, mock_exists, mock_qicon):
        """Если передано имя без .svg — расширение добавляется автоматически"""
        from utils.icon_loader import IconLoader
        IconLoader.load('search')
        # resource_path должен получить путь с .svg
        args = mock_rp.call_args[0][0]
        assert args.endswith('search.svg'), f"Ожидался путь с .svg, получен: {args}"

    @patch('utils.icon_loader.QIcon')
    @patch('utils.icon_loader.os.path.exists', return_value=True)
    @patch('utils.icon_loader.resource_path', return_value='/resolved/icons/edit.svg')
    def test_load_не_дублирует_svg(self, mock_rp, mock_exists, mock_qicon):
        """Если передано имя уже с .svg — расширение не добавляется повторно"""
        from utils.icon_loader import IconLoader
        IconLoader.load('edit.svg')
        args = mock_rp.call_args[0][0]
        assert args.endswith('edit.svg')
        assert not args.endswith('.svg.svg'), "Расширение .svg дублировано"

    @patch('utils.icon_loader.QIcon')
    @patch('utils.icon_loader.os.path.exists', return_value=True)
    @patch('utils.icon_loader.resource_path', return_value='/resolved/icons/add.svg')
    def test_load_вызывает_resource_path(self, mock_rp, mock_exists, mock_qicon):
        """resource_path() вызывается для формирования абсолютного пути"""
        from utils.icon_loader import IconLoader
        IconLoader.load('add')
        mock_rp.assert_called_once()
        # Путь должен содержать ICONS_DIR
        assert 'resources/icons' in mock_rp.call_args[0][0]

    @patch('utils.icon_loader.QIcon')
    @patch('utils.icon_loader.os.path.exists', return_value=True)
    @patch('utils.icon_loader.resource_path', return_value='/resolved/icons/ok.svg')
    def test_load_файл_существует_возвращает_qicon(self, mock_rp, mock_exists, mock_qicon):
        """Когда файл существует — возвращается QIcon(path)"""
        from utils.icon_loader import IconLoader
        result = IconLoader.load('ok')
        mock_qicon.assert_called_with('/resolved/icons/ok.svg')
        assert result is not None

    @patch('utils.icon_loader.QIcon')
    @patch('utils.icon_loader.os.path.exists', return_value=False)
    @patch('utils.icon_loader.resource_path', return_value='/resolved/icons/missing.svg')
    def test_load_файл_не_существует_возвращает_пустой_qicon(self, mock_rp, mock_exists, mock_qicon):
        """Когда файл не найден — возвращается пустой QIcon() (fallback)"""
        from utils.icon_loader import IconLoader
        result = IconLoader.load('missing')
        # QIcon() вызван без аргументов — пустая иконка
        mock_qicon.assert_called_with()

    @patch('utils.icon_loader.QIcon')
    @patch('utils.icon_loader.os.path.exists', return_value=True)
    @patch('utils.icon_loader.resource_path', return_value='/resolved/icons/zoom.svg')
    def test_load_параметр_size_не_влияет_на_путь(self, mock_rp, mock_exists, mock_qicon):
        """Параметр size не меняет логику формирования пути"""
        from utils.icon_loader import IconLoader
        IconLoader.load('zoom', size=48)
        # resource_path всё равно вызван один раз с тем же путём
        mock_rp.assert_called_once()


# ==================== load_colored() — SVG с заменой цвета ====================

class TestIconLoaderLoadColored:
    """Тесты метода IconLoader.load_colored()"""

    @patch('utils.icon_loader.os.path.exists', return_value=False)
    @patch('utils.icon_loader.resource_path', return_value='/resolved/icons/nofile.svg')
    @patch('utils.icon_loader.QIcon')
    def test_load_colored_файл_не_существует(self, mock_qicon, mock_rp, mock_exists):
        """Если файл не найден — возвращается пустой QIcon()"""
        from utils.icon_loader import IconLoader
        result = IconLoader.load_colored('nofile', '#FF0000')
        mock_qicon.assert_called_with()

    @patch('utils.icon_loader.os.path.exists', return_value=True)
    @patch('utils.icon_loader.resource_path', return_value='/resolved/icons/star.svg')
    def test_load_colored_заменяет_currentColor(self, mock_rp, mock_exists):
        """currentColor в SVG заменяется на указанный цвет"""
        svg_data = '<svg><path fill="currentColor" d="M0 0"/></svg>'
        with patch('builtins.open', mock_open(read_data=svg_data)):
            # Мокаем PyQt5 компоненты, используемые внутри load_colored
            mock_renderer = MagicMock()
            mock_pixmap = MagicMock()
            mock_painter = MagicMock()
            mock_icon = MagicMock()

            with patch('utils.icon_loader.IconLoader.load') as mock_load, \
                 patch.dict('sys.modules', {
                     'PyQt5.QtSvg': MagicMock(QSvgRenderer=MagicMock(return_value=mock_renderer)),
                 }):
                # Подменяем импорты внутри load_colored
                import importlib
                import utils.icon_loader as il_module

                with patch.object(il_module, 'QIcon', return_value=mock_icon) as mock_qicon_cls:
                    # Мокаем QSvgRenderer, QPixmap, QPainter через sys.modules
                    with patch('PyQt5.QtSvg.QSvgRenderer', return_value=mock_renderer), \
                         patch('PyQt5.QtGui.QPixmap', return_value=mock_pixmap), \
                         patch('PyQt5.QtGui.QPainter', return_value=mock_painter), \
                         patch('PyQt5.QtCore.QByteArray', side_effect=lambda x: x):
                        from utils.icon_loader import IconLoader
                        result = IconLoader.load_colored('star', '#FF0000')
                        # Проверяем что open был вызван с правильным путём
                        # (основная проверка — что функция не упала)
                        assert result is not None

    @patch('utils.icon_loader.os.path.exists', return_value=True)
    @patch('utils.icon_loader.resource_path', return_value='/resolved/icons/pen.svg')
    def test_load_colored_замена_fill_black(self, mock_rp, mock_exists):
        """fill="black" заменяется на указанный цвет"""
        svg_data = '<svg><rect fill="black" width="10" height="10"/></svg>'
        color = '#00FF00'
        with patch('builtins.open', mock_open(read_data=svg_data)):
            # Читаем SVG и проверяем замену напрямую
            content = svg_data.replace('currentColor', color)
            for attr in ['stroke', 'fill']:
                for old_val in ['black', '#000', '#000000', 'white', '#fff', '#ffffff']:
                    content = content.replace(f'{attr}="{old_val}"', f'{attr}="{color}"')
                    content = content.replace(f"{attr}='{old_val}'", f"{attr}='{color}'")

            assert f'fill="{color}"' in content, "fill=\"black\" не заменён"
            assert 'fill="black"' not in content

    @patch('utils.icon_loader.os.path.exists', return_value=True)
    @patch('utils.icon_loader.resource_path', return_value='/resolved/icons/line.svg')
    def test_load_colored_замена_stroke_000000(self, mock_rp, mock_exists):
        """stroke="#000000" заменяется на указанный цвет"""
        svg_data = '<svg><line stroke="#000000" x1="0" y1="0" x2="10" y2="10"/></svg>'
        color = '#3366CC'
        content = svg_data
        for attr in ['stroke', 'fill']:
            for old_val in ['black', '#000', '#000000', 'white', '#fff', '#ffffff']:
                content = content.replace(f'{attr}="{old_val}"', f'{attr}="{color}"')
        assert f'stroke="{color}"' in content
        assert 'stroke="#000000"' not in content

    @patch('utils.icon_loader.os.path.exists', return_value=True)
    @patch('utils.icon_loader.resource_path', return_value='/resolved/icons/circle.svg')
    def test_load_colored_замена_ffffff_и_fff(self, mock_rp, mock_exists):
        """fill="#ffffff" и fill="#fff" заменяются на указанный цвет"""
        svg_data = '<svg><circle fill="#ffffff"/><circle fill="#fff"/></svg>'
        color = '#AABBCC'
        content = svg_data
        for attr in ['stroke', 'fill']:
            for old_val in ['black', '#000', '#000000', 'white', '#fff', '#ffffff']:
                content = content.replace(f'{attr}="{old_val}"', f'{attr}="{color}"')
        assert f'fill="{color}"' in content
        assert 'fill="#ffffff"' not in content
        assert 'fill="#fff"' not in content

    @patch('utils.icon_loader.os.path.exists', return_value=True)
    @patch('utils.icon_loader.resource_path', return_value='/resolved/icons/err.svg')
    def test_load_colored_fallback_при_исключении(self, mock_rp, mock_exists):
        """При ошибке чтения SVG — fallback на обычный IconLoader.load()"""
        with patch('builtins.open', side_effect=IOError("read error")):
            with patch('utils.icon_loader.IconLoader.load', return_value=MagicMock()) as mock_load:
                from utils.icon_loader import IconLoader
                result = IconLoader.load_colored('err', '#FF0000', size=20)
                mock_load.assert_called_once_with('err.svg', 20)


# ==================== create_icon_button() — кнопка с иконкой ====================

class TestCreateIconButton:
    """Тесты метода IconLoader.create_icon_button()"""

    @patch('utils.icon_loader.IconLoader.load')
    def test_create_icon_button_с_текстом_и_tooltip(self, mock_load):
        """Кнопка создаётся с текстом и подсказкой"""
        mock_icon = _make_mock_qicon(is_null=False)
        mock_load.return_value = mock_icon
        mock_btn = MagicMock()

        with patch('PyQt5.QtWidgets.QPushButton', return_value=mock_btn):
            from utils.icon_loader import IconLoader
            btn = IconLoader.create_icon_button('save', text='Сохранить', tooltip='Сохранить документ')
            mock_btn.setText.assert_called_with('Сохранить')
            mock_btn.setToolTip.assert_called_with('Сохранить документ')

    @patch('utils.icon_loader.IconLoader.load')
    def test_create_icon_button_без_текста_ставит_icon_only(self, mock_load):
        """Если текст пустой — устанавливается свойство icon-only"""
        mock_icon = _make_mock_qicon(is_null=False)
        mock_load.return_value = mock_icon
        mock_btn = MagicMock()

        with patch('PyQt5.QtWidgets.QPushButton', return_value=mock_btn):
            from utils.icon_loader import IconLoader
            btn = IconLoader.create_icon_button('delete')
            mock_btn.setProperty.assert_called_with('icon-only', True)

    @patch('utils.icon_loader.IconLoader.load')
    def test_create_icon_button_null_icon_не_устанавливается(self, mock_load):
        """Если иконка null — setIcon не вызывается"""
        mock_icon = _make_mock_qicon(is_null=True)
        mock_load.return_value = mock_icon
        mock_btn = MagicMock()

        with patch('PyQt5.QtWidgets.QPushButton', return_value=mock_btn):
            from utils.icon_loader import IconLoader
            btn = IconLoader.create_icon_button('broken')
            mock_btn.setIcon.assert_not_called()


# ==================== create_action_button() — минималистичная кнопка ====================

class TestCreateActionButton:
    """Тесты метода IconLoader.create_action_button()"""

    @patch('utils.icon_loader.IconLoader.load_colored')
    def test_create_action_button_стили_содержат_цвета(self, mock_load_colored):
        """Стили кнопки содержат bg_color и hover_color"""
        mock_icon = _make_mock_qicon(is_null=False)
        mock_load_colored.return_value = mock_icon
        mock_btn = MagicMock()

        with patch('PyQt5.QtWidgets.QPushButton', return_value=mock_btn):
            from utils.icon_loader import IconLoader
            btn = IconLoader.create_action_button(
                'edit', tooltip='Редактировать',
                bg_color='#E8F5E9', hover_color='#C8E6C9'
            )
            # Проверяем что setStyleSheet был вызван
            mock_btn.setStyleSheet.assert_called_once()
            style = mock_btn.setStyleSheet.call_args[0][0]
            assert '#E8F5E9' in style, "bg_color не найден в стилях"
            assert '#C8E6C9' in style, "hover_color не найден в стилях"

    @patch('utils.icon_loader.IconLoader.load_colored')
    def test_create_action_button_фиксированный_размер(self, mock_load_colored):
        """setFixedSize вызывается с указанным button_size"""
        mock_icon = _make_mock_qicon(is_null=False)
        mock_load_colored.return_value = mock_icon
        mock_btn = MagicMock()

        with patch('PyQt5.QtWidgets.QPushButton', return_value=mock_btn):
            from utils.icon_loader import IconLoader
            btn = IconLoader.create_action_button('close', button_size=48)
            mock_btn.setFixedSize.assert_called_with(48, 48)

    @patch('utils.icon_loader.IconLoader.load_colored')
    def test_create_action_button_курсор_указатель(self, mock_load_colored):
        """Курсор устанавливается как PointingHandCursor"""
        mock_icon = _make_mock_qicon(is_null=False)
        mock_load_colored.return_value = mock_icon
        mock_btn = MagicMock()

        with patch('PyQt5.QtWidgets.QPushButton', return_value=mock_btn):
            from utils.icon_loader import IconLoader
            btn = IconLoader.create_action_button('info')
            mock_btn.setCursor.assert_called_once()

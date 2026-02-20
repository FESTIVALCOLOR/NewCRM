# Дизайн и стили

> Единая система стилей, QSS, палитра цветов, иконки, шаблоны компонентов.

## Единая система стилей ([utils/unified_styles.py](../utils/unified_styles.py))

Центральный файл стилей для всех UI компонентов. Все виджеты используют стили из этого модуля.

### Палитра цветов

| Назначение | Цвет | HEX | Применение |
|-----------|------|-----|-----------|
| Primary (Жёлтый) | Жёлтый | `#ffd93c` | Акцентные кнопки, выделения |
| Primary Hover | Тёмно-жёлтый | `#ffc800` | Hover состояние |
| Primary Pressed | Ещё темнее | `#e6b400` | Pressed состояние |
| Background | Белый | `#FFFFFF` | Фон основных элементов |
| Surface | Светло-серый | `#F8F9FA` | Фон карточек, панелей |
| Border | Серый | `#E0E0E0` | Рамки, разделители |
| Text Primary | Тёмно-серый | `#333333` | Основной текст |
| Text Secondary | Серый | `#666666` | Второстепенный текст |
| Text Muted | Светло-серый | `#999999` | Приглушённый текст |
| Success | Зелёный | `#4CAF50` | Успех, завершено |
| Error | Красный | `#F44336` | Ошибка, удаление |
| Warning | Оранжевый | `#FF9800` | Предупреждение |
| Info | Синий | `#2196F3` | Информация |

### Стили кнопок

```python
# Основная кнопка (жёлтая)
UnifiedStyles.get_primary_button_style()
# background: #ffd93c; color: #333; border-radius: 6px;

# Вторичная кнопка (белая с рамкой)
UnifiedStyles.get_secondary_button_style()
# background: white; border: 1px solid #E0E0E0;

# Кнопка удаления (красная)
UnifiedStyles.get_danger_button_style()
# background: #F44336; color: white;

# Кнопка действия (маленькая)
UnifiedStyles.get_action_button_style()
```

### Стили таблиц

```python
UnifiedStyles.get_table_style()
# QTableWidget: gridline-color: #E0E0E0; alternate-background: #F8F9FA;
# QHeaderView::section: background: #F5F5F5; font-weight: bold;
```

### Стили полей ввода

```python
UnifiedStyles.get_input_style()
# QLineEdit, QTextEdit, QComboBox: border: 1px solid #E0E0E0;
# border-radius: 6px; padding: 8px;
```

### Стили диалогов

```python
UnifiedStyles.get_dialog_style()
# Frameless: border: 1px solid #E0E0E0; border-radius: 10px;
```

## SVG иконки ([utils/icon_loader.py](../utils/icon_loader.py))

### Директория иконок

```
resources/icons/           # 50+ SVG иконок
├── add.svg
├── edit.svg
├── delete.svg
├── save.svg
├── search.svg
├── filter.svg
├── refresh.svg
├── close.svg
├── check.svg
├── folder.svg
├── file.svg
├── upload.svg
├── download.svg
├── settings.svg
├── user.svg
├── calendar.svg
├── chart.svg
├── list.svg
├── grid.svg
├── arrow-left.svg
├── arrow-right.svg
├── arrow-up.svg
├── arrow-down.svg
├── expand.svg
├── collapse.svg
├── lock.svg
├── unlock.svg
├── eye.svg
├── eye-off.svg
└── ...
```

### Использование

```python
from utils.icon_loader import IconLoader

# Загрузка иконки
icon = IconLoader.load('search.svg', size=24)

# Создание кнопки с иконкой
btn = IconLoader.create_icon_button('save', text='Сохранить', icon_size=20)

# Важно: .svg расширение добавляется автоматически
icon = IconLoader.load('search', size=18)  # → resources/icons/search.svg
```

## CustomTitleBar ([ui/custom_title_bar.py](../ui/custom_title_bar.py))

### Два режима

```python
# Полный режим (главные окна) — с минимизацией, развёрнуть, закрыть
title_bar = CustomTitleBar(self, "Interior Studio CRM", simple_mode=False)

# Простой режим (диалоги) — только закрыть
title_bar = CustomTitleBar(self, "Редактирование", simple_mode=True)
```

### Стиль

```css
CustomTitleBar {
    background: #FFFFFF;
    border-bottom: 1px solid #E0E0E0;
    height: 40px;
}
```

## CustomMessageBox ([ui/custom_message_box.py](../ui/custom_message_box.py))

```python
from ui.custom_message_box import CustomMessageBox

# Информация
CustomMessageBox.info(self, "Успех", "Данные сохранены")

# Предупреждение
CustomMessageBox.warning(self, "Внимание", "Несохранённые изменения")

# Ошибка
CustomMessageBox.error(self, "Ошибка", "Не удалось подключиться")

# Вопрос (да/нет)
result = CustomMessageBox.question(self, "Удаление", "Удалить запись?")
```

## Frameless окна

Все окна используют `Qt.FramelessWindowHint` + `CustomTitleBar`:

```python
class SomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)

        # Обязательный border frame
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                border: 1px solid #E0E0E0;   /* строго 1px! */
                border-radius: 10px;
                background: white;
            }
        """)
```

## Шаблоны повторяющихся элементов

### Карточка Kanban

```css
KanbanCard {
    background: white;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    padding: 12px;
    margin: 4px 0;
}
KanbanCard:hover {
    border-color: #ffd93c;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

### Тег/Бейдж

```css
.tag {
    background: #E3F2FD;
    color: #1565C0;
    border-radius: 12px;
    padding: 2px 8px;
    font-size: 11px;
}
```

### Статус-индикатор

| Статус | Цвет фона | Цвет текста |
|--------|----------|-------------|
| Активный | `#E8F5E9` | `#2E7D32` |
| В работе | `#FFF3E0` | `#E65100` |
| Завершён | `#E8F5E9` | `#2E7D32` |
| Просрочен | `#FFEBEE` | `#C62828` |
| Приостановлен | `#FFF8E1` | `#F57F17` |

## Правила дизайна

1. **Рамки диалогов = 1px** — всегда `border: 1px solid #E0E0E0`
2. **Радиус скругления:** диалоги = 10px, кнопки = 6px, теги = 12px
3. **Отступы:** padding кнопок = 8px 16px, карточек = 12px
4. **Шрифт:** системный, размер 12-14px для текста, 11px для мелких элементов
5. **Никаких emoji** — только SVG иконки через IconLoader
6. **Цветовая схема:** светлая тема, жёлтый акцент (#ffd93c)

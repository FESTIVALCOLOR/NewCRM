# Следующие шаги для завершения реализации файлов стадий

## ✅ УЖЕ СДЕЛАНО

1. ✅ База данных - таблица `project_files` создана
2. ✅ Утилиты - PreviewGenerator, CacheManager
3. ✅ YandexDiskManager - методы для работы со стадиями
4. ✅ UI компоненты - FilePreviewWidget, FileGalleryWidget
5. ✅ Сигналы в CardEditDialog - `stage_files_uploaded`, `stage_upload_error`

## 📋 ЧТО ОСТАЛОСЬ СДЕЛАТЬ

### Шаг 1: Добавить обработчики сигналов в CardEditDialog

В конец класса CardEditDialog (перед TechTaskDialog) добавить:

```python
def on_stage_files_uploaded(self, stage):
    """Обработчик успешной загрузки файлов стадии"""
    print(f"[OK] Файлы стадии {stage} успешно загружены")
    # Перезагружаем файлы для стадии
    self.reload_stage_files(stage)

    from ui.message_boxes import CustomMessageBox
    CustomMessageBox(self, 'Успех', f'Файлы успешно загружены', 'success').exec_()

def on_stage_upload_error(self, error_msg):
    """Обработчик ошибки загрузки файлов"""
    from ui.message_boxes import CustomMessageBox
    CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки файлов:\n{error_msg}', 'error').exec_()
```

### Шаг 2: Добавить метод загрузки файлов стадий

```python
def upload_stage_files(self, stage):
    """Множественная загрузка файлов для стадии

    Args:
        stage: идентификатор стадии
    """
    from PyQt5.QtWidgets import QFileDialog, QProgressDialog
    import threading
    import os
    from config import YANDEX_DISK_TOKEN
    from utils.yandex_disk import YandexDiskManager
    from utils.preview_generator import PreviewGenerator

    # Определяем фильтр файлов в зависимости от стадии
    if stage == 'stage1':
        file_filter = "PDF Files (*.pdf)"
    elif stage in ['stage2_concept', 'stage2_3d']:
        file_filter = "Images and PDF (*.jpg *.jpeg *.png *.pdf)"
    elif stage == 'stage3':
        file_filter = "PDF and Excel (*.pdf *.xls *.xlsx)"
    else:
        file_filter = "All Files (*.*)"

    # Множественный выбор файлов
    file_paths, _ = QFileDialog.getOpenFileNames(
        self,
        f"Выберите файлы для загрузки",
        "",
        file_filter
    )

    if not file_paths:
        return

    # Получаем contract_id
    contract_id = self.card_data.get('contract_id')
    if not contract_id:
        from ui.message_boxes import CustomMessageBox
        CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
        return

    # Получаем путь к папке договора на Яндекс.Диске
    conn = self.db.connect()
    cursor = conn.cursor()
    cursor.execute('SELECT yandex_folder_path FROM contracts WHERE id = ?', (contract_id,))
    result = cursor.fetchone()
    conn.close()

    if not result or not result['yandex_folder_path']:
        from ui.message_boxes import CustomMessageBox
        CustomMessageBox(
            self,
            'Ошибка',
            'Папка договора на Яндекс.Диске не найдена.\nСначала сохраните договор.',
            'warning'
        ).exec_()
        return

    contract_folder = result['yandex_folder_path']

    # Показываем индикатор загрузки
    progress = QProgressDialog(
        "Загрузка файлов на Яндекс.Диск...",
        "Отмена",
        0,
        len(file_paths),
        self
    )
    progress.setWindowModality(Qt.WindowModal)
    progress.setWindowTitle("Загрузка файлов")
    progress.show()

    # Загружаем файлы асинхронно
    def upload_thread():
        try:
            yd = YandexDiskManager(YANDEX_DISK_TOKEN)
            uploaded_files = yd.upload_stage_files(
                file_paths,
                contract_folder,
                stage
            )

            # Генерируем превью и сохраняем в БД
            for i, file_data in enumerate(uploaded_files):
                if progress.wasCanceled():
                    break

                progress.setValue(i + 1)
                progress.setLabelText(f"Обработка {file_data['file_name']}...")

                # Определяем тип файла
                ext = os.path.splitext(file_data['file_name'])[1].lower()
                if ext in ['.jpg', '.jpeg', '.png']:
                    file_type = 'image'
                elif ext == '.pdf':
                    file_type = 'pdf'
                elif ext in ['.xls', '.xlsx']:
                    file_type = 'excel'
                else:
                    file_type = 'unknown'

                # Генерируем превью
                preview_cache_path = None
                if file_type in ['image', 'pdf']:
                    cache_path = PreviewGenerator.get_cache_path(
                        contract_id,
                        stage,
                        file_data['file_name']
                    )
                    pixmap = PreviewGenerator.generate_preview_for_file(
                        file_data['local_path'],
                        file_type
                    )
                    if pixmap:
                        PreviewGenerator.save_preview_to_cache(pixmap, cache_path)
                        preview_cache_path = cache_path

                # Сохраняем в БД
                self.db.add_project_file(
                    contract_id=contract_id,
                    stage=stage,
                    file_type=file_type,
                    public_link=file_data['public_link'],
                    yandex_path=file_data['yandex_path'],
                    file_name=file_data['file_name'],
                    preview_cache_path=preview_cache_path
                )

            progress.close()

            # Сигнал успешной загрузки
            self.stage_files_uploaded.emit(stage)

        except Exception as e:
            progress.close()
            self.stage_upload_error.emit(str(e))

    thread = threading.Thread(target=upload_thread)
    thread.start()
```

### Шаг 3: Добавить метод удаления файла

```python
def delete_stage_file(self, file_id, stage):
    """Удаление файла стадии

    Args:
        file_id: ID файла в БД
        stage: идентификатор стадии
    """
    from ui.message_boxes import CustomQuestionBox
    from PyQt5.QtWidgets import QDialog
    from config import YANDEX_DISK_TOKEN
    from utils.yandex_disk import YandexDiskManager
    import os

    # Подтверждение удаления
    reply = CustomQuestionBox(
        self,
        'Подтверждение',
        'Вы уверены, что хотите удалить этот файл?'
    ).exec_()

    if reply != QDialog.Accepted:
        return

    # Удаляем из БД и получаем пути
    file_info = self.db.delete_project_file(file_id)

    if file_info:
        # Удаляем с Яндекс.Диска
        try:
            yd = YandexDiskManager(YANDEX_DISK_TOKEN)
            yd.delete_file(file_info['yandex_path'])
        except Exception as e:
            print(f"[WARN] Не удалось удалить файл с Яндекс.Диска: {e}")

        # Удаляем превью из кэша
        if file_info.get('preview_cache_path'):
            try:
                if os.path.exists(file_info['preview_cache_path']):
                    os.remove(file_info['preview_cache_path'])
            except:
                pass

        # Перезагружаем список файлов
        self.reload_stage_files(stage)

        from ui.message_boxes import CustomMessageBox
        CustomMessageBox(self, 'Успех', 'Файл удален', 'success').exec_()
```

### Шаг 4: Добавить метод перезагрузки файлов стадии

```python
def reload_stage_files(self, stage):
    """Перезагрузка файлов стадии

    Args:
        stage: идентификатор стадии
    """
    contract_id = self.card_data.get('contract_id')
    if not contract_id:
        return

    # Получаем файлы из БД
    files = self.db.get_project_files(contract_id, stage)

    # Обновляем соответствующий виджет
    if stage == 'stage2_concept' and hasattr(self, 'stage2_concept_gallery'):
        self.stage2_concept_gallery.load_files(files, self.load_preview_for_file)
    elif stage == 'stage2_3d' and hasattr(self, 'stage2_3d_gallery'):
        self.stage2_3d_gallery.load_files(files, self.load_preview_for_file)
    # Для stage1 и stage3 будет список файлов (не галерея)

def load_preview_for_file(self, file_data):
    """Загрузка превью для файла из кэша

    Args:
        file_data: словарь с данными файла

    Returns:
        QPixmap или None
    """
    from utils.preview_generator import PreviewGenerator

    # Проверяем кэш
    if file_data.get('preview_cache_path'):
        pixmap = PreviewGenerator.load_preview_from_cache(
            file_data['preview_cache_path']
        )
        if pixmap:
            return pixmap

    # Если в кэше нет - возвращаем None (будет показана иконка)
    return None
```

### Шаг 5: Модифицировать create_project_data_widget()

Найти метод `create_project_data_widget()` (примерно строка 4270) и добавить секции для стадий.

Вместо текущего содержимого, добавить после существующих секций ТЗ и замера:

```python
# ========== СЕКЦИЯ: 1 СТАДИЯ - ПЛАНИРОВОЧНОЕ РЕШЕНИЕ ==========
# Пока что пропустим, сфокусируемся на галереях 2 стадии

# ========== СЕКЦИЯ: 2 СТАДИЯ - КОНЦЕПЦИЯ ДИЗАЙНА ==========
stage2_group = QGroupBox("2 стадия - Концепция дизайна")
stage2_group.setStyleSheet("""
    QGroupBox {
        font-weight: bold;
        border: 1px solid #E0E0E0;
        border-radius: 5px;
        margin-top: 10px;
        padding-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }
""")

stage2_layout = QVBoxLayout()

# Подсекция: Концепция-коллажи
from ui.file_gallery_widget import FileGalleryWidget

self.stage2_concept_gallery = FileGalleryWidget(
    title="Концепция-коллажи",
    stage="stage2_concept",
    file_types=['image', 'pdf']
)
self.stage2_concept_gallery.upload_requested.connect(self.upload_stage_files)
self.stage2_concept_gallery.delete_requested.connect(self.delete_stage_file)
stage2_layout.addWidget(self.stage2_concept_gallery)

# Подсекция: 3D визуализация
self.stage2_3d_gallery = FileGalleryWidget(
    title="3D визуализация",
    stage="stage2_3d",
    file_types=['image', 'pdf']
)
self.stage2_3d_gallery.upload_requested.connect(self.upload_stage_files)
self.stage2_3d_gallery.delete_requested.connect(self.delete_stage_file)
stage2_layout.addWidget(self.stage2_3d_gallery)

stage2_group.setLayout(stage2_layout)
layout.addWidget(stage2_group)
```

### Шаг 6: Загрузка файлов при открытии карточки

В методе `load_data()` (примерно строка 4737) добавить в конец:

```python
# Загружаем файлы стадий
if hasattr(self, 'stage2_concept_gallery'):
    self.reload_stage_files('stage2_concept')
if hasattr(self, 'stage2_3d_gallery'):
    self.reload_stage_files('stage2_3d')
```

## 🧪 ТЕСТИРОВАНИЕ

После внедрения всех изменений:

1. Запустите приложение
2. Откройте карточку проекта с договором
3. Перейдите на вкладку "Данные по проекту"
4. Проверьте наличие секции "2 стадия - Концепция дизайна"
5. Попробуйте загрузить изображения через кнопку "Загрузить файлы"
6. Проверьте отображение превью
7. Попробуйте удалить файл

## 📝 ПРИМЕЧАНИЯ

- Для начала реализуем только галереи 2 стадии (Концепция-коллажи и 3D визуализация)
- 1 и 3 стадии (списки PDF/Excel) можно добавить позже
- Превью замера тоже можно добавить позже

Это минимальный набор для демонстрации функциональности!

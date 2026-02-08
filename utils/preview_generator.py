# -*- coding: utf-8 -*-
"""
Генератор превью для изображений и PDF файлов
"""
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
import os
import tempfile

# Проверяем наличие PyMuPDF
try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    print("[WARN] PyMuPDF не установлен. Превью PDF недоступно.")
    print("[WARN] Установите: pip install PyMuPDF")


class PreviewGenerator:
    """Генератор превью файлов"""

    PREVIEW_WIDTH = 400
    PREVIEW_HEIGHT = 267

    @staticmethod
    def generate_image_preview(image_path):
        """Генерация превью изображения

        Args:
            image_path: путь к локальному файлу изображения

        Returns:
            QPixmap или None
        """
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                return None

            # Масштабируем с сохранением пропорций
            scaled = pixmap.scaled(
                PreviewGenerator.PREVIEW_WIDTH,
                PreviewGenerator.PREVIEW_HEIGHT,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            return scaled

        except Exception as e:
            print(f"[ERROR] Ошибка генерации превью изображения: {e}")
            return None

    @staticmethod
    def generate_pdf_preview(pdf_path):
        """Генерация превью первой страницы PDF

        Требует установки библиотеки PyMuPDF (fitz)
        pip install PyMuPDF

        Args:
            pdf_path: путь к локальному PDF файлу

        Returns:
            QPixmap или None
        """
        if not HAS_PYMUPDF:
            return None

        try:
            # Открываем PDF
            doc = fitz.open(pdf_path)
            if doc.page_count == 0:
                doc.close()
                return None

            # Берем первую страницу
            page = doc[0]

            # Рендерим в изображение (масштаб 1.5 для качества)
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)

            # Конвертируем в QImage
            img_data = pix.tobytes("ppm")
            qimage = QImage.fromData(img_data)

            # Конвертируем в QPixmap
            pixmap = QPixmap.fromImage(qimage)

            # Масштабируем
            scaled = pixmap.scaled(
                PreviewGenerator.PREVIEW_WIDTH,
                PreviewGenerator.PREVIEW_HEIGHT,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            doc.close()
            return scaled

        except Exception as e:
            print(f"[ERROR] Ошибка генерации превью PDF: {e}")
            return None

    @staticmethod
    def save_preview_to_cache(pixmap, cache_path):
        """Сохранение превью в кэш

        Args:
            pixmap: QPixmap для сохранения
            cache_path: путь к файлу кэша

        Returns:
            True при успехе, False при ошибке
        """
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            return pixmap.save(cache_path, 'PNG')
        except Exception as e:
            print(f"[ERROR] Ошибка сохранения превью в кэш: {e}")
            return False

    @staticmethod
    def load_preview_from_cache(cache_path):
        """Загрузка превью из кэша

        Args:
            cache_path: путь к файлу кэша

        Returns:
            QPixmap или None
        """
        try:
            if os.path.exists(cache_path):
                pixmap = QPixmap(cache_path)
                if not pixmap.isNull():
                    return pixmap
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки превью из кэша: {e}")

        return None

    @staticmethod
    def get_cache_path(contract_id, stage, file_name):
        """Получение пути к кэшу превью

        Args:
            contract_id: ID договора
            stage: стадия проекта
            file_name: имя файла

        Returns:
            Путь к файлу кэша
        """
        import hashlib
        # Используем постоянную директорию рядом с приложением
        # Получаем путь к директории скрипта (корень приложения)
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(app_dir, 'preview_cache')
        os.makedirs(cache_dir, exist_ok=True)

        # Use hash to handle any filename characters (including Cyrillic)
        name_hash = hashlib.md5(file_name.encode('utf-8')).hexdigest()[:12]
        # Keep extension for readability
        _, ext = os.path.splitext(file_name)
        preview_name = f"{contract_id}_{stage}_{name_hash}{ext or '.png'}"

        return os.path.join(cache_dir, preview_name)

    @staticmethod
    def cleanup_cache(max_size_mb=500, max_age_days=30):
        """Clean up preview cache: remove old files and limit total size"""
        import time
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_dir = os.path.join(app_dir, 'preview_cache')
        if not os.path.exists(cache_dir):
            return

        now = time.time()
        max_age_seconds = max_age_days * 86400
        files = []

        for f in os.listdir(cache_dir):
            filepath = os.path.join(cache_dir, f)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                age = now - stat.st_mtime
                if age > max_age_seconds:
                    os.remove(filepath)
                else:
                    files.append((filepath, stat.st_size, stat.st_mtime))

        # If still over size limit, remove oldest first
        total_size = sum(f[1] for f in files)
        max_size_bytes = max_size_mb * 1024 * 1024
        if total_size > max_size_bytes:
            files.sort(key=lambda x: x[2])  # oldest first
            while total_size > max_size_bytes and files:
                filepath, size, _ = files.pop(0)
                os.remove(filepath)
                total_size -= size

    @staticmethod
    def generate_preview_for_file(file_path, file_type):
        """Универсальный метод генерации превью в зависимости от типа файла

        Args:
            file_path: путь к локальному файлу
            file_type: тип файла ('image', 'pdf', 'excel')

        Returns:
            QPixmap или None
        """
        if file_type == 'image':
            return PreviewGenerator.generate_image_preview(file_path)
        elif file_type == 'pdf':
            return PreviewGenerator.generate_pdf_preview(file_path)
        else:
            # Для Excel и других типов файлов возвращаем None
            # В UI будет отображена иконка типа файла
            return None

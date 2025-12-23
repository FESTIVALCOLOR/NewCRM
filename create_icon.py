"""
Скрипт для создания правильной ICO иконки из PNG
"""
from PIL import Image
import os

# Открываем существующую иконку (PNG)
source_path = 'resources/icon.ico'
output_path = 'resources/icon_new.ico'

# Если это PNG, создадим правильный ICO с несколькими размерами
img = Image.open(source_path)

# Создаем ICO с разными размерами для Windows
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

# Создаем список изображений разных размеров
icon_images = []
for size in sizes:
    # Создаем копию и изменяем размер
    resized = img.resize(size, Image.Resampling.LANCZOS)
    icon_images.append(resized)

# Сохраняем как ICO со всеми размерами
icon_images[0].save(
    output_path,
    format='ICO',
    sizes=sizes,
    append_images=icon_images[1:]
)

print(f"[OK] Icon created: {output_path}")
print(f"Sizes: {sizes}")

# Заменяем старую иконку
import shutil
shutil.copy2(source_path, 'resources/icon_backup.ico')  # Бэкап старой
shutil.move(output_path, source_path)
print(f"[OK] Icon replaced: {source_path}")

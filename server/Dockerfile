# Python образ
FROM python:3.11-slim

# Рабочая директория
WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание непривилегированного пользователя
RUN useradd -m -u 1000 appuser

# Создание директорий для файлов с правами appuser
RUN mkdir -p uploads previews && chown -R appuser:appuser uploads previews /app

# Переключение на непривилегированного пользователя
USER appuser

# Порт приложения
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--limit-concurrency", "100", "--backlog", "2048"]

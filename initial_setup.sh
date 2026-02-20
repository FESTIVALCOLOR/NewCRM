#!/bin/bash
# Первоначальная установка Interior Studio CRM на сервер 147.45.154.193

set -e

echo "======================================================================"
echo "  ПЕРВОНАЧАЛЬНАЯ УСТАНОВКА INTERIOR STUDIO CRM"
echo "  Сервер: 147.45.154.193"
echo "======================================================================"
echo ""

SERVER="147.45.154.193"
USER="root"
PROJECT_PATH="/root/interior_studio"
GIT_REPO="https://github.com/FESTIVALCOLOR/NewCRM.git"

echo "📡 Подключение к серверу $SERVER..."
echo ""

ssh -t $USER@$SERVER bash << ENDSSH
    set -e

    echo "✓ Подключен к серверу"
    echo ""

    # ==========================================
    # 1. УСТАНОВКА НЕОБХОДИМЫХ ПАКЕТОВ
    # ==========================================

    echo "📦 ЭТАП 1: Установка необходимых пакетов"
    echo "========================================"

    echo "Обновление списка пакетов..."
    apt-get update -qq

    echo "Установка Python 3, pip, git..."
    apt-get install -y python3 python3-pip git sqlite3 > /dev/null 2>&1

    echo "✓ Необходимые пакеты установлены"
    echo ""

    # ==========================================
    # 2. КЛОНИРОВАНИЕ РЕПОЗИТОРИЯ
    # ==========================================

    echo "📥 ЭТАП 2: Клонирование репозитория"
    echo "========================================"

    if [ -d "$PROJECT_PATH" ]; then
        echo "⚠️ Директория $PROJECT_PATH уже существует"
        echo "Удалить и клонировать заново? (y/n)"
        read -p "> " answer
        if [ "\$answer" = "y" ]; then
            echo "Удаление старой директории..."
            rm -rf "$PROJECT_PATH"
        else
            echo "Пропускаю клонирование"
            cd "$PROJECT_PATH"
        fi
    fi

    if [ ! -d "$PROJECT_PATH" ]; then
        echo "Клонирование репозитория..."
        git clone $GIT_REPO "$PROJECT_PATH"
        echo "✓ Репозиторий успешно склонирован"
    fi

    cd "$PROJECT_PATH"
    echo "📁 Рабочая директория: \$(pwd)"
    echo ""

    # ==========================================
    # 3. УСТАНОВКА PYTHON ЗАВИСИМОСТЕЙ
    # ==========================================

    echo "📚 ЭТАП 3: Установка Python зависимостей"
    echo "========================================"

    if [ -f requirements.txt ]; then
        echo "Установка зависимостей из requirements.txt..."
        python3 -m pip install -r requirements.txt --quiet
        echo "✓ Зависимости установлены"
    else
        echo "⚠️ Файл requirements.txt не найден"
        echo "Установка базовых зависимостей..."
        python3 -m pip install fastapi uvicorn sqlalchemy pydantic python-jose passlib bcrypt python-multipart --quiet
        echo "✓ Базовые зависимости установлены"
    fi

    echo ""

    # ==========================================
    # 4. СОЗДАНИЕ БАЗЫ ДАННЫХ
    # ==========================================

    echo "🗄️ ЭТАП 4: Создание базы данных"
    echo "========================================"

    if [ -f interior_studio.db ]; then
        echo "⚠️ База данных уже существует"
        echo "Размер: \$(du -h interior_studio.db | cut -f1)"
    else
        echo "Создание новой базы данных..."

        # Запуск миграций для создания БД
        if [ -f migrate_to_server.py ]; then
            python3 migrate_to_server.py
            echo "✓ База данных создана через migrate_to_server.py"
        elif [ -f database/db_manager.py ]; then
            python3 -c "from database.db_manager import DatabaseManager; db = DatabaseManager(); print('База создана')"
            echo "✓ База данных создана"
        else
            echo "⚠️ Не найдены скрипты для создания БД"
        fi
    fi

    echo ""

    # ==========================================
    # 5. НАСТРОЙКА ЛОГОВ
    # ==========================================

    echo "📋 ЭТАП 5: Настройка логов"
    echo "========================================"

    echo "Создание файлов логов..."
    touch /var/log/interior_studio.log
    touch /var/log/interior_studio_error.log
    chmod 644 /var/log/interior_studio.log
    chmod 644 /var/log/interior_studio_error.log

    echo "✓ Файлы логов созданы"
    echo ""

    # ==========================================
    # 6. НАСТРОЙКА SYSTEMD SERVICE
    # ==========================================

    echo "⚙️ ЭТАП 6: Настройка systemd service"
    echo "========================================"

    if [ -f interior_studio.service ]; then
        echo "Копирование service файла..."
        cp interior_studio.service /etc/systemd/system/

        echo "Перезагрузка systemd..."
        systemctl daemon-reload

        echo "Включение автозапуска..."
        systemctl enable interior_studio.service

        echo "✓ Systemd service настроен"
    else
        echo "⚠️ Файл interior_studio.service не найден"
    fi

    echo ""

    # ==========================================
    # 7. НАСТРОЙКА FIREWALL
    # ==========================================

    echo "🔥 ЭТАП 7: Настройка firewall"
    echo "========================================"

    if command -v ufw > /dev/null; then
        echo "Открытие порта 8000..."
        ufw allow 8000/tcp > /dev/null 2>&1 || true
        echo "✓ Порт 8000 открыт в firewall"
    else
        echo "⚠️ UFW не установлен, пропускаю настройку firewall"
    fi

    echo ""

    # ==========================================
    # 8. ЗАПУСК СЕРВЕРА
    # ==========================================

    echo "🚀 ЭТАП 8: Запуск сервера"
    echo "========================================"

    # Запуск через systemd
    if [ -f /etc/systemd/system/interior_studio.service ]; then
        echo "Запуск через systemd..."
        systemctl start interior_studio.service
        sleep 3

        if systemctl is-active --quiet interior_studio.service; then
            echo "✓ Сервис успешно запущен"
        else
            echo "⚠️ Ошибка запуска через systemd, запуск вручную..."
            nohup python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8000 > /var/log/interior_studio.log 2>&1 &
            sleep 3
        fi
    else
        echo "Запуск вручную..."
        nohup python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8000 > /var/log/interior_studio.log 2>&1 &
        sleep 3
    fi

    echo ""

    # ==========================================
    # 9. ПРОВЕРКА ЗАПУСКА
    # ==========================================

    echo "✅ ЭТАП 9: Проверка запуска"
    echo "========================================"

    if pgrep -f "uvicorn server.main:app" > /dev/null; then
        PID=\$(pgrep -f "uvicorn server.main:app")
        echo "✓ Сервер запущен (PID: \$PID)"

        echo ""
        echo "Проверка порта 8000..."
        sleep 2
        if netstat -tuln | grep -q ":8000 "; then
            echo "✓ Порт 8000 прослушивается"
        else
            echo "⚠️ Порт 8000 не прослушивается"
        fi

        echo ""
        echo "Последние строки лога:"
        echo "----------------------------------------"
        tail -15 /var/log/interior_studio.log
        echo "----------------------------------------"
    else
        echo "❌ Сервер не запустился"
        echo ""
        echo "Логи ошибок:"
        tail -20 /var/log/interior_studio.log
    fi

    echo ""
    echo "======================================================================"
    echo "✅ УСТАНОВКА ЗАВЕРШЕНА!"
    echo "======================================================================"
    echo ""
    echo "🌐 API доступен по адресу:"
    echo "   http://147.45.154.193:8000"
    echo ""
    echo "📖 Документация API:"
    echo "   http://147.45.154.193:8000/docs"
    echo ""
    echo "📋 Команды для управления:"
    echo "   systemctl status interior_studio    # Статус"
    echo "   systemctl restart interior_studio   # Перезапуск"
    echo "   systemctl stop interior_studio      # Остановка"
    echo "   systemctl start interior_studio     # Запуск"
    echo "   tail -f /var/log/interior_studio.log  # Логи"
    echo ""
    echo "======================================================================"
ENDSSH

echo ""
echo "✓ Установка завершена"

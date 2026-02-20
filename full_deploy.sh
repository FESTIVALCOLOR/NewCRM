#!/bin/bash
# Полное развертывание Interior Studio CRM на сервер 147.45.154.193
# Включает: Git pull, миграции, systemd service, перезапуск

set -e  # Остановиться при ошибке

echo "======================================================================"
echo "  ПОЛНОЕ РАЗВЕРТЫВАНИЕ INTERIOR STUDIO CRM"
echo "  Сервер: 147.45.154.193"
echo "  Дата: $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================================"
echo ""

SERVER="147.45.154.193"
USER="root"
PROJECT_PATH="/root/interior_studio"

echo "📡 Подключение к серверу $SERVER..."
echo ""

ssh -t $USER@$SERVER bash << 'ENDSSH'
    set -e

    echo "✓ Подключен к серверу"
    echo ""

    # ==========================================
    # 1. ПОЛУЧЕНИЕ ОБНОВЛЕНИЙ ИЗ GIT
    # ==========================================

    echo "📥 ЭТАП 1: Получение обновлений из Git"
    echo "========================================"

    cd /root/interior_studio || { echo "❌ Директория проекта не найдена"; exit 1; }
    echo "📁 Рабочая директория: $(pwd)"

    # Проверка Git репозитория
    if [ ! -d .git ]; then
        echo "❌ Git репозиторий не инициализирован"
        echo "   Выполните: git clone <repository_url> /root/interior_studio"
        exit 1
    fi

    # Получение изменений
    echo "Получение изменений из origin/main..."
    git fetch origin

    # Показать что будет обновлено
    echo ""
    echo "📋 Изменения которые будут применены:"
    git log HEAD..origin/main --oneline --decorate || echo "  Нет новых изменений"
    echo ""

    # Применить изменения
    echo "Применение обновлений..."
    git pull origin main

    if [ $? -eq 0 ]; then
        echo "✓ Изменения успешно применены"
    else
        echo "❌ Ошибка при получении изменений"
        exit 1
    fi

    echo ""

    # ==========================================
    # 2. ОБНОВЛЕНИЕ ЗАВИСИМОСТЕЙ
    # ==========================================

    echo "📚 ЭТАП 2: Обновление зависимостей Python"
    echo "========================================"

    if [ -f requirements.txt ]; then
        echo "Установка зависимостей из requirements.txt..."
        python3 -m pip install -r requirements.txt --upgrade --quiet

        if [ $? -eq 0 ]; then
            echo "✓ Зависимости успешно обновлены"
        else
            echo "⚠️ Предупреждение: Некоторые зависимости не удалось обновить"
        fi
    else
        echo "⚠️ Файл requirements.txt не найден"
    fi

    echo ""

    # ==========================================
    # 3. МИГРАЦИИ БАЗЫ ДАННЫХ
    # ==========================================

    echo "🗄️ ЭТАП 3: Применение миграций базы данных"
    echo "========================================"

    # Создание бэкапа базы данных
    if [ -f interior_studio.db ]; then
        BACKUP_FILE="interior_studio_backup_$(date +%Y%m%d_%H%M%S).db"
        echo "Создание резервной копии: $BACKUP_FILE"
        cp interior_studio.db "$BACKUP_FILE"
        echo "✓ Резервная копия создана"
    fi

    # Применение миграций
    if [ -f migrate_to_server.py ]; then
        echo "Запуск миграций..."
        python3 migrate_to_server.py

        if [ $? -eq 0 ]; then
            echo "✓ Миграции успешно применены"
        else
            echo "⚠️ Предупреждение: Ошибка при применении миграций"
        fi
    else
        echo "⚠️ Файл migrate_to_server.py не найден"
    fi

    echo ""

    # ==========================================
    # 4. НАСТРОЙКА SYSTEMD SERVICE
    # ==========================================

    echo "⚙️ ЭТАП 4: Настройка systemd service"
    echo "========================================"

    if [ -f interior_studio.service ]; then
        echo "Копирование service файла..."
        sudo cp interior_studio.service /etc/systemd/system/

        echo "Перезагрузка systemd..."
        sudo systemctl daemon-reload

        echo "Включение автозапуска..."
        sudo systemctl enable interior_studio.service

        echo "✓ Systemd service настроен"
    else
        echo "⚠️ Файл interior_studio.service не найден, пропускаю настройку"
    fi

    echo ""

    # ==========================================
    # 5. ОСТАНОВКА СТАРОГО ПРОЦЕССА
    # ==========================================

    echo "🛑 ЭТАП 5: Остановка старого процесса"
    echo "========================================"

    # Попытка остановить через systemd
    if systemctl is-active --quiet interior_studio.service; then
        echo "Остановка через systemd..."
        sudo systemctl stop interior_studio.service
        sleep 2
    fi

    # Убить оставшиеся процессы
    echo "Проверка на оставшиеся процессы uvicorn..."
    pkill -f "uvicorn server.main:app" && echo "Старые процессы завершены" || echo "Процессов не найдено"
    sleep 2

    echo "✓ Старые процессы остановлены"
    echo ""

    # ==========================================
    # 6. ЗАПУСК НОВОГО ПРОЦЕССА
    # ==========================================

    echo "🚀 ЭТАП 6: Запуск нового процесса"
    echo "========================================"

    # Запуск через systemd если доступен
    if [ -f /etc/systemd/system/interior_studio.service ]; then
        echo "Запуск через systemd..."
        sudo systemctl start interior_studio.service
        sleep 3

        # Проверка статуса
        if systemctl is-active --quiet interior_studio.service; then
            echo "✓ Сервис успешно запущен через systemd"
            sudo systemctl status interior_studio.service --no-pager -l
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
    # 7. ПРОВЕРКА ЗАПУСКА
    # ==========================================

    echo "✅ ЭТАП 7: Проверка запуска"
    echo "========================================"

    # Проверка процесса
    if pgrep -f "uvicorn server.main:app" > /dev/null; then
        PID=$(pgrep -f "uvicorn server.main:app")
        echo "✓ Сервер запущен"
        echo "  PID: $PID"

        # Показать использование ресурсов
        echo ""
        echo "Использование ресурсов:"
        ps -p $PID -o pid,ppid,%cpu,%mem,cmd --no-headers
    else
        echo "❌ Сервер не запустился"
        echo ""
        echo "Последние 20 строк лога:"
        tail -20 /var/log/interior_studio.log
        exit 1
    fi

    # Проверка порта
    echo ""
    if netstat -tuln | grep -q ":8000 "; then
        echo "✓ Порт 8000 прослушивается"
    else
        echo "⚠️ Порт 8000 не прослушивается"
    fi

    # Показать последние строки лога
    echo ""
    echo "Последние 10 строк лога:"
    echo "----------------------------------------"
    tail -10 /var/log/interior_studio.log
    echo "----------------------------------------"

    echo ""
    echo "======================================================================"
    echo "✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО УСПЕШНО!"
    echo "======================================================================"
    echo ""
    echo "🌐 API доступен по адресу:"
    echo "   http://147.45.154.193:8000"
    echo ""
    echo "📖 Документация API (Swagger):"
    echo "   http://147.45.154.193:8000/docs"
    echo ""
    echo "📋 Просмотр логов в реальном времени:"
    echo "   ssh root@147.45.154.193 'tail -f /var/log/interior_studio.log'"
    echo ""
    echo "🔄 Управление сервисом:"
    echo "   sudo systemctl status interior_studio   # Проверить статус"
    echo "   sudo systemctl restart interior_studio  # Перезапустить"
    echo "   sudo systemctl stop interior_studio     # Остановить"
    echo "   sudo systemctl start interior_studio    # Запустить"
    echo ""
    echo "======================================================================"
ENDSSH

echo ""
echo "✓ Развертывание завершено"
echo ""
echo "Для просмотра логов выполните:"
echo "  ssh $USER@$SERVER 'tail -f /var/log/interior_studio.log'"

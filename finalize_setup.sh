#!/bin/bash
# Финализация установки и запуск сервера

echo "======================================================================"
echo "  ФИНАЛИЗАЦИЯ УСТАНОВКИ И ЗАПУСК СЕРВЕРА"
echo "======================================================================"

SERVER="147.45.154.193"
USER="root"

ssh $USER@$SERVER << 'ENDSSH'
    cd /root/interior_studio

    echo "📁 Директория: $(pwd)"
    echo ""

    # Создание базы данных напрямую через Python
    echo "🗄️ Создание базы данных..."
    python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/root/interior_studio')

from database.db_manager import DatabaseManager

print("Инициализация базы данных...")
db = DatabaseManager('interior_studio.db')
print("✓ База данных создана успешно")
PYTHON_EOF

    echo ""

    # Создание файлов логов
    echo "📋 Создание файлов логов..."
    touch /var/log/interior_studio.log
    chmod 644 /var/log/interior_studio.log

    # Настройка systemd
    echo "⚙️ Настройка systemd service..."
    if [ -f interior_studio.service ]; then
        cp interior_studio.service /etc/systemd/system/
        systemctl daemon-reload
        systemctl enable interior_studio.service
        echo "✓ Service настроен"
    fi

    echo ""

    # Остановка старых процессов
    echo "🛑 Остановка старых процессов..."
    pkill -f "uvicorn server.main:app" 2>/dev/null || true
    sleep 2

    # Запуск сервера
    echo "🚀 Запуск сервера..."
    if [ -f /etc/systemd/system/interior_studio.service ]; then
        systemctl start interior_studio.service
        sleep 3
    else
        nohup python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8000 > /var/log/interior_studio.log 2>&1 &
        sleep 3
    fi

    # Проверка
    echo ""
    echo "✅ Проверка запуска..."
    if pgrep -f "uvicorn" > /dev/null; then
        PID=$(pgrep -f "uvicorn")
        echo "✓ Сервер запущен (PID: $PID)"

        echo ""
        echo "Последние строки лога:"
        echo "========================================"
        tail -20 /var/log/interior_studio.log
        echo "========================================"
    else
        echo "❌ Сервер не запустился"
        tail -30 /var/log/interior_studio.log
    fi

    echo ""
    echo "======================================================================"
    echo "✅ УСТАНОВКА ЗАВЕРШЕНА"
    echo "======================================================================"
    echo "🌐 API: http://147.45.154.193:8000"
    echo "📖 Docs: http://147.45.154.193:8000/docs"
    echo "======================================================================"
ENDSSH

#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Установка Interior Studio CRM API${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Проверка что скрипт запущен от root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Ошибка: Запустите скрипт от root (sudo)${NC}"
    exit 1
fi

# Шаг 1: Обновление системы
echo -e "${YELLOW}[1/8] Обновление системы...${NC}"
apt update && apt upgrade -y

# Шаг 2: Установка Docker
echo -e "${YELLOW}[2/8] Установка Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl start docker
    systemctl enable docker
    rm get-docker.sh
    echo -e "${GREEN}✓ Docker установлен${NC}"
else
    echo -e "${GREEN}✓ Docker уже установлен${NC}"
fi

# Шаг 3: Установка Docker Compose
echo -e "${YELLOW}[3/8] Установка Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✓ Docker Compose установлен${NC}"
else
    echo -e "${GREEN}✓ Docker Compose уже установлен${NC}"
fi

# Шаг 4: Установка git
echo -e "${YELLOW}[4/8] Установка Git...${NC}"
apt install -y git

# Шаг 5: Клонирование репозитория
echo -e "${YELLOW}[5/8] Клонирование репозитория...${NC}"
cd /opt
if [ -d "interior_studio" ]; then
    echo -e "${YELLOW}Папка существует, обновляем...${NC}"
    cd interior_studio
    git pull
else
    git clone https://github.com/FESTIVALCOLOR/NewCRM.git interior_studio
    cd interior_studio
fi

# Шаг 6: Настройка переменных окружения
echo -e "${YELLOW}[6/8] Настройка переменных окружения...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Создание файла .env${NC}"

    # Генерация паролей
    POSTGRES_PASSWORD=$(openssl rand -hex 16)
    SECRET_KEY=$(openssl rand -hex 32)

    cat > .env <<EOF
# PostgreSQL
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# JWT Secret
SECRET_KEY=$SECRET_KEY

# Яндекс.Диск токен (ЗАПОЛНИТЕ ВРУЧНУЮ!)
YANDEX_DISK_TOKEN=

EOF

    echo -e "${GREEN}✓ Файл .env создан${NC}"
    echo -e "${YELLOW}ВАЖНО: Отредактируйте /opt/interior_studio/.env и добавьте YANDEX_DISK_TOKEN${NC}"
else
    echo -e "${GREEN}✓ Файл .env уже существует${NC}"
fi

# Шаг 7: Создание самоподписанного SSL сертификата (временно)
echo -e "${YELLOW}[7/8] Создание SSL сертификата...${NC}"
mkdir -p nginx/ssl
if [ ! -f "nginx/ssl/cert.pem" ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/key.pem \
        -out nginx/ssl/cert.pem \
        -subj "/C=RU/ST=Moscow/L=Moscow/O=Interior Studio/CN=localhost"
    echo -e "${GREEN}✓ SSL сертификат создан${NC}"
    echo -e "${YELLOW}ВАЖНО: Замените на настоящий сертификат для продакшена!${NC}"
else
    echo -e "${GREEN}✓ SSL сертификат уже существует${NC}"
fi

# Шаг 8: Запуск приложения
echo -e "${YELLOW}[8/8] Запуск приложения...${NC}"
docker-compose down
docker-compose up -d --build

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Установка завершена!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Проверка статуса:"
echo -e "  ${YELLOW}docker-compose ps${NC}"
echo ""
echo -e "Просмотр логов:"
echo -e "  ${YELLOW}docker-compose logs -f${NC}"
echo ""
echo -e "API доступен на:"
echo -e "  ${GREEN}https://$(hostname -I | awk '{print $1}')${NC}"
echo ""
echo -e "${YELLOW}ВАЖНО: Не забудьте:${NC}"
echo -e "  1. Добавить YANDEX_DISK_TOKEN в /opt/interior_studio/.env"
echo -e "  2. Создать администратора в БД"
echo -e "  3. Настроить firewall (открыть порты 80, 443)"
echo ""

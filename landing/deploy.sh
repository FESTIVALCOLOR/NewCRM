#!/usr/bin/env bash
# Сборка и деплой лендинга на сервер
# Использование: bash landing/deploy.sh [production]
#
# Без аргументов: собирает с base=/beta/ (превью на crm.festivalcolor.ru/beta/)
# С аргументом production: собирает с base=/ (для festivalcolor.ru корневого домена)

set -e

cd "$(dirname "$0")"

MODE=${1:-preview}

if [ "$MODE" = "production" ]; then
  echo "🏭 Сборка PRODUCTION (base=/)"
  VITE_BASE_PATH="/" npm run build
else
  echo "🔍 Сборка PREVIEW (base=/beta/)"
  npm run build
fi

echo "📦 Копирую dist на сервер..."
rsync -avz --delete dist/ timeweb:/opt/interior_studio/landing/dist/

echo "🔄 Перезапускаю nginx..."
ssh timeweb "docker exec crm_nginx nginx -s reload"

echo "✅ Лендинг задеплоен!"
if [ "$MODE" = "production" ]; then
  echo "   → https://festivalcolor.ru/"
else
  echo "   → https://crm.festivalcolor.ru/beta/"
fi

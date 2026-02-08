#!/bin/bash
# Interior Studio CRM - Docker Deployment Script
# Usage: ./deploy.sh [--no-backup]

set -e

SERVER="timeweb"
REMOTE_DIR="/opt/interior_studio"
LOCAL_SERVER_DIR="server"

echo "=== Interior Studio CRM Deployment ==="
echo ""

# Step 1: Syntax validation
echo "[1/5] Validating Python syntax..."
for f in server/*.py; do
    python -m py_compile "$f" 2>/dev/null || {
        echo "SYNTAX ERROR in $f"
        exit 1
    }
done
echo "  OK"

# Step 2: Backup (skip with --no-backup)
if [ "$1" != "--no-backup" ]; then
    echo "[2/5] Creating database backup..."
    ssh $SERVER "cd $REMOTE_DIR && docker-compose exec -T postgres pg_dump -U crm_user interior_studio_crm > backups/backup_\$(date +%Y%m%d_%H%M%S).sql && echo 'Backup created'" || echo "  WARNING: Backup failed, continuing..."
else
    echo "[2/5] Skipping backup (--no-backup)"
fi

# Step 3: Copy server files
echo "[3/5] Copying server files..."
scp -r $LOCAL_SERVER_DIR/*.py $SERVER:$REMOTE_DIR/server/
echo "  OK"

# Step 4: Rebuild and restart Docker
echo "[4/5] Rebuilding Docker container..."
ssh $SERVER "cd $REMOTE_DIR && docker-compose down && docker-compose build --no-cache api && docker-compose up -d"
echo "  Waiting 5 seconds for startup..."
sleep 5

# Step 5: Health check
echo "[5/5] Health check..."
HEALTH=$(ssh $SERVER "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/docs" 2>/dev/null)
if [ "$HEALTH" = "200" ]; then
    echo "  API is healthy (HTTP 200)"
    echo ""
    echo "=== Deployment successful ==="
else
    echo "  WARNING: API returned HTTP $HEALTH"
    echo "  Check logs: ssh $SERVER 'cd $REMOTE_DIR && docker-compose logs --tail=50 api'"
    exit 1
fi

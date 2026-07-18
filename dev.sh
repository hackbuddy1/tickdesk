#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate

docker compose up -d
echo "waiting for db..."
until docker compose exec -T db pg_isready -U tick -d tickdesk >/dev/null 2>&1; do sleep 1; done
echo "db ready"

python scripts/feed.py > /tmp/feed.log 2>&1 &
FEED_PID=$!
echo "feed started (pid $FEED_PID, logs: /tmp/feed.log)"
trap "kill $FEED_PID 2>/dev/null" EXIT

cd backend
exec uvicorn app.main:app --reload --port 8000

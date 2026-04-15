#!/bin/bash
# Local development runner — starts both services

set -e

echo "Starting Kitchen Agent (polling mode)..."
cd "$(dirname "$0")"

export PYTHONPATH="$(pwd)"
export USE_WEBHOOK="false"
export GEMINI_KEY="${GEMINI_KEY:-$(grep GEMINI_KEY .env 2>/dev/null | cut -d= -f2)}"
export TELEGRAM_TOKEN="${TELEGRAM_TOKEN:-$(grep TELEGRAM_TOKEN .env 2>/dev/null | cut -d= -f2)}"
export DB_PATH="kitchen_agent/storage/kitchen.db"
export CHROMA_PATH="kitchen_agent/storage/chroma"
export REMINDER_DAEMON_URL="http://localhost:8001"
export AGENT_BASE_URL="http://localhost:8000"
export PORT=8000
export REMINDER_PORT=8001

echo "Installing dependencies if needed..."
pip install -q -r kitchen_agent/requirements.txt 2>/dev/null || true

echo "Starting reminder daemon on port 8001..."
python -m uvicorn kitchen_agent.scheduler.reminder_daemon:app --host 0.0.0.0 --port 8001 &
DAEMON_PID=$!

sleep 2

echo "Starting kitchen agent on port 8000..."
python -m uvicorn kitchen_agent.bot:app --host 0.0.0.0 --port 8000 --reload

kill $DAEMON_PID 2>/dev/null || true

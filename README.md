# Karl Kitchen Agent

Karl is a FastAPI-based kitchen assistant that can:

- Chat with users via Telegram (polling or webhook mode).
- Track kitchen inventory and shopping list data.
- Run reminder scheduling through a companion reminder daemon.
- Persist local state in SQLite and Chroma-backed storage.

## Project structure

- `kitchen_agent/bot.py` — main FastAPI app + Telegram update handling.
- `kitchen_agent/api/routes.py` — API routes for chat, inventory, shopping, and memory maintenance.
- `kitchen_agent/scheduler/reminder_daemon.py` — reminder daemon service.
- `kitchen_agent/storage/` — database, memory, and vector store helpers.
- `docker-compose.yml` — local multi-service setup.
- `run_local.sh` — convenience script for local development startup.

## Requirements

- Python 3.11+
- `pip`
- Telegram bot token (required for Telegram mode)
- Google Gemini API key (for LLM features)

## Setup (local development)

1. Clone the repo and move into it.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Create a `.env` file (or export environment variables).

### 1) Create virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r kitchen_agent/requirements.txt
```

### 2) Configure environment variables

Create `.env` in the project root:

```env
GEMINI_KEY=your_gemini_api_key
TELEGRAM_TOKEN=your_telegram_bot_token

# Optional overrides
GEMINI_MODEL=gemini-2.0-flash
DB_PATH=kitchen_agent/storage/kitchen.db
CHROMA_PATH=kitchen_agent/storage/chroma
REMINDER_DAEMON_URL=http://localhost:8001
AGENT_BASE_URL=http://localhost:8000
USE_WEBHOOK=false
PORT=8000
REMINDER_PORT=8001
```

## Run the project

### Option A: One-command local runner

```bash
./run_local.sh
```

This starts:

- Reminder daemon on `http://localhost:8001`
- Kitchen agent API on `http://localhost:8000`

### Option B: Run services manually

Start reminder daemon:

```bash
python -m uvicorn kitchen_agent.scheduler.reminder_daemon:app --host 0.0.0.0 --port 8001
```

In another terminal, start kitchen agent:

```bash
python -m uvicorn kitchen_agent.bot:app --host 0.0.0.0 --port 8000 --reload
```

## Docker setup

### Build and run with Docker Compose

```bash
docker compose up --build
```

Services:

- `kitchen-agent` on port `8000`
- `reminder-daemon` on port `8001`
- Optional `chroma` container exposed as `8002`

## API quickstart

Health check:

```bash
curl http://localhost:8000/health
```

Chat endpoint:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"chat_id":"demo","message":"What can I cook with rice and eggs?"}'
```

Inventory list:

```bash
curl http://localhost:8000/inventory
```

Shopping list:

```bash
curl http://localhost:8000/shopping
```

## Telegram modes

- **Polling mode** (`USE_WEBHOOK=false`): bot actively polls Telegram for updates (good for local development).
- **Webhook mode** (`USE_WEBHOOK=true`): bot receives updates at `POST /telegram/webhook` and requires a reachable public URL in `AGENT_BASE_URL`.

## Deployment notes

`railway.toml` is included for Railway deployment with two services:

- `kitchen-agent`
- `reminder-daemon`

Set required secrets (at minimum `GEMINI_KEY` and `TELEGRAM_TOKEN`) in your Railway project.

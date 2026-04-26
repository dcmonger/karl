# AGENTS.md

## Scope
This repo contains the **Karl Kitchen Agent** — a LangGraph-powered Telegram bot for kitchen management.

## Architecture
Two FastAPI services (run together locally, separate on Railway):
- **Agent service** (port 8000): Telegram bot + LangGraph agent + tools
- **Reminder daemon** (port 8001): APScheduler for proactive messages

Data stores:
- **SQLite** (`kitchen_agent/storage/kitchen.db`): inventory, shopping list, reminders, memory
- **ChromaDB** (`kitchen_agent/storage/chroma`): preferences, recipe history

## Local development
```bash
# One-liner (starts both services)
./run_local.sh

# Or manually (two terminals)
pip install -r kitchen_agent/requirements.txt
python -m uvicorn kitchen_agent.scheduler.reminder_daemon:app --port 8001 &
python -m uvicorn kitchen_agent.messenger:app --port 8000 --reload
```

Required env vars (in `.env`):
```
GEMINI_KEY=<your-key>
TELEGRAM_TOKEN=<your-bot-token>
```

Optional (with defaults):
```
USE_WEBHOOK=false  # true for Railway deployment
DB_PATH=kitchen_agent/storage/kitchen.db
CHROMA_PATH=kitchen_agent/storage/chroma
REMINDER_DAEMON_URL=http://localhost:8001
AGENT_BASE_URL=http://localhost:8000
AUTHORIZED_TELEGRAM_USER_IDS=123456789  # optional allowlist
```

## Key entry points
- `kitchen_agent/messenger.py` — FastAPI server + Telegram polling/webhook
- `kitchen_agent/api/routes.py` — API routes for chat, inventory, shopping, memory
- `kitchen_agent/agents/kitchen_agent.py` — LangGraph agent definition
- `kitchen_agent/memory/profile.py` — profile wrapper for inventory, shopping, reminders, preferences, and recipe history (does not persist conversation transcript)
- `kitchen_agent/tools/` — LangGraph tools (9 total):
  - Read: `check_inventory`, `get_item_quantity`, `search_recipes`
  - Write: `update_inventory`, `consume_inventory`, `add_to_shopping_list`
  - Memory: `log_preference`, `log_recipe_feedback`
  - Scheduler: `schedule_reminder`
- `kitchen_agent/scheduler/reminder_daemon.py` — APScheduler worker (port 8001)
- `kitchen_agent/storage/database.py` — SQLite schema + InventoryDB, ShoppingListDB, ReminderDB, MemoryDB
- `kitchen_agent/storage/vector_store.py` — ChromaDB collections: PreferenceStore, RecipeHistoryStore

## Code style
- Keep changes focused and minimal.
- Use `rg` for search.
- Tools go in `kitchen_agent/tools/` as individual files.
- Database classes in `kitchen_agent/storage/database.py`.
- ChromaDB stores in `kitchen_agent/storage/vector_store.py`.

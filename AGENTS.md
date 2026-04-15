# AGENTS.md

## Scope
These instructions apply to the entire repository.

## Project overview
- This repo contains the **Karl Kitchen Agent** service and related components.
- Main app entrypoint: `kitchen_agent/bot.py`.
- Reminder daemon entrypoint: `kitchen_agent/scheduler/reminder_daemon.py`.

## Local development
- Preferred quickstart: `./run_local.sh`.
- Manual run commands:
  - `python -m uvicorn kitchen_agent.scheduler.reminder_daemon:app --host 0.0.0.0 --port 8001`
  - `python -m uvicorn kitchen_agent.bot:app --host 0.0.0.0 --port 8000 --reload`
- Dependencies: `pip install -r kitchen_agent/requirements.txt`.

## Environment variables
At minimum, set:
- `GEMINI_KEY`
- `TELEGRAM_TOKEN`

Common local defaults:
- `USE_WEBHOOK=false`
- `PORT=8000`
- `REMINDER_PORT=8001`
- `DB_PATH=kitchen_agent/storage/kitchen.db`
- `CHROMA_PATH=kitchen_agent/storage/chroma`
- `REMINDER_DAEMON_URL=http://localhost:8001`
- `AGENT_BASE_URL=http://localhost:8000`

## Notes for agents
- Keep changes focused and minimal.
- If you change runtime behavior, update `README.md` accordingly.
- Prefer `rg` for search over slower recursive tools.

"""Messenger process — runs FastAPI + Telegram transport (polling or webhook mode)."""
import os
import sys
import logging
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(__file__))

import httpx
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
import uvicorn

from kitchen_agent.config.settings import TELEGRAM_TOKEN, AGENT_BASE_URL
from kitchen_agent.agents.kitchen_agent import KitchenAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").lower() == "true"
WEBHOOK_PATH = "/telegram/webhook"
POLL_TIMEOUT = 60
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
AUTHORIZED_TELEGRAM_USER_IDS = {
    uid.strip()
    for uid in os.getenv("AUTHORIZED_TELEGRAM_USER_IDS", "").split(",")
    if uid.strip()
}

_agents: dict[str, KitchenAgent] = {}
_offset = 0

_telegram_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _telegram_client
    if _telegram_client is None:
        _telegram_client = httpx.AsyncClient(timeout=30.0)
    return _telegram_client


async def send_telegram_message(chat_id: str, text: str, parse_mode: str = "Markdown") -> dict:
    """Send a text message to a Telegram user."""
    client = _get_client()
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    response = await client.post(url, json=payload)
    response.raise_for_status()
    return response.json()


async def get_updates(offset: int = None, timeout: int = 60) -> dict:
    """Get new updates (long polling)."""
    client = _get_client()
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    response = await client.get(url, params=params, timeout=timeout + 10)
    response.raise_for_status()
    return response.json()


async def set_webhook(url: str) -> dict:
    """Set the webhook URL for incoming updates."""
    client = _get_client()
    telegram_url = f"{BASE_URL}/setWebhook"
    payload = {"url": url}
    response = await client.post(telegram_url, json=payload)
    response.raise_for_status()
    return response.json()


async def delete_webhook() -> dict:
    """Remove the webhook."""
    client = _get_client()
    telegram_url = f"{BASE_URL}/deleteWebhook"
    response = await client.post(telegram_url)
    response.raise_for_status()
    return response.json()


def get_agent(user_id: str) -> KitchenAgent:
    """Get or create agent for a user. Uses sender_id for memory continuity."""
    if user_id not in _agents:
        _agents[user_id] = KitchenAgent(user_id=user_id)
    return _agents[user_id]


def is_authorized_user(user_id: str) -> bool:
    """Return True when whitelist is empty or user_id is explicitly allowed."""
    if not AUTHORIZED_TELEGRAM_USER_IDS:
        return True
    return user_id in AUTHORIZED_TELEGRAM_USER_IDS


async def process_update(update: dict):
    """Process a single Telegram update."""
    global _offset
    
    if "message" not in update:
        return
    
    msg = update["message"]
    chat_id = str(msg["chat"]["id"])
    sender_id = str(msg.get("from", {}).get("id", chat_id))
    text = msg.get("text", "")
    update_id = update["update_id"]
    
    _offset = update_id + 1
    
    if not text:
        return

    if not is_authorized_user(sender_id):
        logger.warning(f"Unauthorized message blocked from sender_id={sender_id}, chat_id={chat_id}")
        await send_telegram_message(chat_id, "You're not an authorized user.")
        return
    
    logger.info(f"Message from {sender_id}: {text[:80]}")
    
    try:
        agent = get_agent(sender_id)
        response = await agent.run_async(text, user_id=sender_id)
        await send_telegram_message(chat_id, response)
        logger.info(f"Response sent to {chat_id}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await send_telegram_message(chat_id, f"Sorry, I ran into an issue: {e}")


async def polling_loop():
    """Long-polling loop for Telegram updates. Runs asynchronously."""
    global _offset
    logger.info("Starting Telegram polling loop...")
    
    while True:
        try:
            updates = await get_updates(offset=_offset, timeout=POLL_TIMEOUT)
            if updates.get("ok") and updates.get("result"):
                for update in updates["result"]:
                    try:
                        await process_update(update)
                    except Exception as e:
                        logger.error(f"Error in process_update: {e}")
        except Exception as e:
            logger.error(f"Polling error: {e}")
            import asyncio
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if USE_WEBHOOK:
        webhook_url = f"{AGENT_BASE_URL}{WEBHOOK_PATH}"
        logger.info(f"Setting webhook to {webhook_url}")
        await delete_webhook()
        await set_webhook(webhook_url)
    else:
        logger.info("Starting async polling...")
        import asyncio
        asyncio.create_task(polling_loop())
    
    yield
    
    logger.info("Shutting down...")
    global _telegram_client
    if _telegram_client:
        await _telegram_client.aclose()


app = FastAPI(title="Kitchen Agent", lifespan=lifespan)


@app.get("/")
async def root():
    return {"agent": "Karl - Kitchen Manager"}


@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    """Webhook endpoint — receives Telegram updates."""
    try:
        update = await req.json()
        await process_update(update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return Response(status_code=200)


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "webhook" if USE_WEBHOOK else "polling"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("messenger:app", host="0.0.0.0", port=port, reload=False)

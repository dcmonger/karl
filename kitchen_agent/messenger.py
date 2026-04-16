"""Messenger process — runs FastAPI + Telegram transport (polling or webhook mode)."""
import os
import sys
import threading
import logging
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(__file__))

import requests
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


def send_telegram_message(chat_id: str, text: str, parse_mode: str = "Markdown") -> dict:
    """Send a text message to a Telegram user."""
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def get_updates(offset: int = None, timeout: int = 60) -> dict:
    """Get new updates (long polling)."""
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    response = requests.get(url, params=params, timeout=timeout + 10)
    response.raise_for_status()
    return response.json()


def set_webhook(url: str) -> dict:
    """Set the webhook URL for incoming updates."""
    telegram_url = f"{BASE_URL}/setWebhook"
    payload = {"url": url}
    response = requests.post(telegram_url, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def delete_webhook() -> dict:
    """Remove the webhook."""
    telegram_url = f"{BASE_URL}/deleteWebhook"
    response = requests.post(telegram_url, timeout=10)
    response.raise_for_status()
    return response.json()


def get_agent(chat_id: str) -> KitchenAgent:
    if chat_id not in _agents:
        _agents[chat_id] = KitchenAgent(chat_id=chat_id)
    return _agents[chat_id]


def is_authorized_user(user_id: str) -> bool:
    """Return True when whitelist is empty or user_id is explicitly allowed."""
    if not AUTHORIZED_TELEGRAM_USER_IDS:
        return True
    return user_id in AUTHORIZED_TELEGRAM_USER_IDS


def process_update(update: dict):
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
        send_telegram_message(chat_id, "You're not an authorized user.")
        return
    
    logger.info(f"Message from {chat_id}: {text[:80]}")
    
    try:
        agent = get_agent(chat_id)
        response = agent.run(text, chat_id=chat_id)
        send_telegram_message(chat_id, response)
        logger.info(f"Response sent to {chat_id}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        send_telegram_message(chat_id, f"Sorry, I ran into an issue: {e}")


def polling_loop():
    """Long-polling loop for Telegram updates. Runs in a background thread."""
    global _offset
    logger.info("Starting Telegram polling loop...")
    
    while True:
        try:
            updates = get_updates(offset=_offset, timeout=POLL_TIMEOUT)
            if updates.get("ok") and updates.get("result"):
                for update in updates["result"]:
                    try:
                        process_update(update)
                    except Exception as e:
                        logger.error(f"Error in process_update: {e}")
        except Exception as e:
            logger.error(f"Polling error: {e}")
            import time
            time.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if USE_WEBHOOK:
        webhook_url = f"{AGENT_BASE_URL}{WEBHOOK_PATH}"
        logger.info(f"Setting webhook to {webhook_url}")
        delete_webhook()
        set_webhook(webhook_url)
    else:
        logger.info("Starting polling in background thread...")
        t = threading.Thread(target=polling_loop, daemon=True)
        t.start()
    
    yield
    
    logger.info("Shutting down...")


app = FastAPI(title="Kitchen Agent", lifespan=lifespan)


@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    """Webhook endpoint — receives Telegram updates."""
    try:
        update = await req.json()
        process_update(update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return Response(status_code=200)


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "webhook" if USE_WEBHOOK else "polling"}


@app.get("/")
async def root():
    return {
        "agent": "Karl - Kitchen Manager",
        "endpoints": {
            "chat": "POST /chat",
            "inventory": "GET /inventory",
            "shopping": "GET /shopping",
            "telegram_webhook": f"POST {WEBHOOK_PATH}",
        }
    }


class ChatRequest(BaseModel):
    message: str
    chat_id: str = "default"


class SendMessageRequest(BaseModel):
    chat_id: str
    text: str
    parse_mode: str = "Markdown"


@app.post("/chat")
async def chat(req: ChatRequest):
    """Direct chat endpoint (for testing without Telegram)."""
    agent = get_agent(req.chat_id)
    response = agent.run(req.message, chat_id=req.chat_id)
    return {"response": response, "chat_id": req.chat_id}


@app.post("/internal/send-message")
async def internal_send_message(req: SendMessageRequest):
    """Internal endpoint used by services (e.g., reminder daemon) to deliver Telegram messages."""
    result = send_telegram_message(req.chat_id, req.text, parse_mode=req.parse_mode)
    return {"status": "sent", "telegram_result": result}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("messenger:app", host="0.0.0.0", port=port, reload=False)

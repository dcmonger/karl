"""Main entry point — runs FastAPI + Telegram bot (polling or webhook mode)."""
import os
import sys
import threading
import logging
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(__file__))

import requests
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from kitchen_agent.config.settings import TELEGRAM_TOKEN, AGENT_BASE_URL
from kitchen_agent.messaging.telegram_client import send_message, get_updates, set_webhook, delete_webhook
from kitchen_agent.agents.kitchen_agent import KitchenAgent
from kitchen_agent.storage.memory import get_working_memory, append_interaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").lower() == "true"
WEBHOOK_PATH = "/telegram/webhook"
POLL_TIMEOUT = 60

_agents: dict[str, KitchenAgent] = {}
_offset = 0


def get_agent(chat_id: str) -> KitchenAgent:
    if chat_id not in _agents:
        _agents[chat_id] = KitchenAgent(chat_id=chat_id)
    return _agents[chat_id]


class Update(BaseModel):
    update_id: int
    message: dict = None


def process_update(update: dict):
    """Process a single Telegram update."""
    global _offset
    
    if "message" not in update:
        return
    
    msg = update["message"]
    chat_id = str(msg["chat"]["id"])
    text = msg.get("text", "")
    update_id = update["update_id"]
    
    _offset = update_id + 1
    
    if not text:
        return
    
    logger.info(f"Message from {chat_id}: {text[:80]}")
    
    try:
        agent = get_agent(chat_id)
        response = agent.run(text, chat_id=chat_id)
        send_message(chat_id, response)
        logger.info(f"Response sent to {chat_id}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        send_message(chat_id, f"Sorry, I ran into an issue: {e}")


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


@app.post("/chat")
async def chat(req: ChatRequest):
    """Direct chat endpoint (for testing without Telegram)."""
    agent = get_agent(req.chat_id)
    response = agent.run(req.message, chat_id=req.chat_id)
    return {"response": response, "chat_id": req.chat_id}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("bot:app", host="0.0.0.0", port=port, reload=False)

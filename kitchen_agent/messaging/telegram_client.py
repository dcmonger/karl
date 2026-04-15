"""Telegram client — sends messages to users via Telegram Bot API."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from kitchen_agent.config.settings import TELEGRAM_TOKEN

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def send_message(chat_id: str, text: str, parse_mode: str = "Markdown") -> dict:
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


def send_message_html(chat_id: str, text: str) -> dict:
    """Send a text message using HTML parse mode."""
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
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
    url = f"{BASE_URL}/setWebhook"
    payload = {"url": url}
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def delete_webhook() -> dict:
    """Remove the webhook."""
    url = f"{BASE_URL}/deleteWebhook"
    response = requests.post(url, timeout=10)
    response.raise_for_status()
    return response.json()


def get_me() -> dict:
    """Get bot info."""
    url = f"{BASE_URL}/getMe"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

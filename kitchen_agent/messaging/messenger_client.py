"""Client helpers for talking to the messenger process."""

import requests

from kitchen_agent.config.settings import AGENT_BASE_URL


def send_user_message(chat_id: str, text: str, parse_mode: str = "Markdown") -> dict:
    """Ask the messenger service to deliver a Telegram message to a user."""
    response = requests.post(
        f"{AGENT_BASE_URL}/internal/send-message",
        json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()

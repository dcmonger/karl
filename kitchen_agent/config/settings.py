"""Settings — env vars, API keys, model config."""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GEMINI_KEY = os.getenv("GEMINI_KEY", "")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash-002")

DEFAULT_CHAT_ID = os.getenv("DEFAULT_CHAT_ID", "default")
DB_PATH = os.getenv("DB_PATH", "kitchen_agent/storage/kitchen.db")
CHROMA_PATH = os.getenv("CHROMA_PATH", "kitchen_agent/storage/chroma")
AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:8000")
REMINDER_DAEMON_URL = os.getenv("REMINDER_DAEMON_URL", "http://localhost:8001")

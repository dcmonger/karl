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
LANGGRAPH_CHECKPOINT_DB_PATH = os.getenv(
    "LANGGRAPH_CHECKPOINT_DB_PATH",
    "kitchen_agent/storage/langgraph_checkpoints.db",
)
CHROMA_PATH = os.getenv("CHROMA_PATH", "kitchen_agent/storage/chroma")
AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:8000")
REMINDER_DAEMON_URL = os.getenv("REMINDER_DAEMON_URL", "http://localhost:8001")


def validate_runtime_env(service: str = "agent") -> None:
    """Fail fast when required runtime env vars are missing."""
    if not TELEGRAM_TOKEN:
        raise RuntimeError("Missing required env var: TELEGRAM_TOKEN")

    if service == "agent":
        if LLM_PROVIDER == "google" and not GEMINI_KEY:
            raise RuntimeError("Missing required env var for google provider: GEMINI_KEY")

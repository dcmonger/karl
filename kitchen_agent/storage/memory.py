"""Long-term memory management — combines SQLite summaries + ChromaDB semantic store."""
from datetime import datetime
from kitchen_agent.storage.database import MemoryDB
from kitchen_agent.storage.vector_store import PreferenceStore, RecipeHistoryStore

_memory_db = MemoryDB()
_pref_store = PreferenceStore()
_recipe_store = RecipeHistoryStore()

RECENT_INTERACTIONS_KEY = "recent_interactions"

MAX_RECENT_INTERACTIONS = 50


def _interaction_key(user_id: str | None) -> str:
    uid = user_id or "default"
    return f"{RECENT_INTERACTIONS_KEY}:{uid}"


def _conversation_key(user_id: str | None) -> str:
    uid = user_id or "default"
    return f"conversation_history:{uid}"


def get_working_memory(user_id: str = None) -> dict:
    """Assembles context for the agent on each turn.

    Note: Inventory and shopping list should come from tools,
    not passed here to avoid duplication.
    """
    recent_prefs = _pref_store.get_preferences(user_id or "default")[-10:]
    recent_recipes = _recipe_store.get_recent_recipes(user_id or "default", limit=5)

    pref_lines = [
        f"- {p.get('entity')}: {p.get('value')} ({p.get('type')})"
        for p in recent_prefs
    ]

    recipe_lines = [
        f"- {r.get('recipe_name')} (rated {r.get('rating')}/5)"
        for r in recent_recipes if r.get("recipe_name")
    ]

    recent_interactions_raw = _memory_db.get(_interaction_key(user_id)) or {"interactions": []}
    recent_interactions = recent_interactions_raw.get("interactions", [])[-10:]

    return {
        "preferences": "\n".join(pref_lines) if pref_lines else "(none recorded)",
        "recent_recipes": "\n".join(recipe_lines) if recipe_lines else "(none recorded)",
        "recent_interactions": recent_interactions,
    }


def append_interaction(user_id: str, role: str, content: str):
    """Append a turn to the rolling recent interactions log."""
    raw = _memory_db.get(_interaction_key(user_id)) or {"interactions": []}
    interactions = raw["interactions"]
    interactions.append({
        "role": role,
        "content": content[:500],
        "timestamp": datetime.now().isoformat(),
    })
    if len(interactions) > MAX_RECENT_INTERACTIONS:
        interactions = interactions[-MAX_RECENT_INTERACTIONS:]
    _memory_db.set(_interaction_key(user_id), {"interactions": interactions})


def append_conversation_message(user_id: str, role: str, content: str):
    """Persist full conversation history per user for restart-safe context."""
    key = _conversation_key(user_id)
    raw = _memory_db.get(key) or {"messages": []}
    messages = raw.get("messages", [])
    messages.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    })
    if len(messages) > 200:
        messages = messages[-200:]
    _memory_db.set(key, {"messages": messages})


def get_conversation_history(
    user_id: str,
    limit: int = 8,
    max_total_chars: int = 3000,
) -> list[dict]:
    """Load a bounded slice of persisted conversation history."""
    raw = _memory_db.get(_conversation_key(user_id)) or {"messages": []}
    messages = raw.get("messages", [])[-limit:]

    bounded: list[dict] = []
    total_chars = 0
    for msg in reversed(messages):
        content = (msg.get("content") or "")[:600]
        msg_len = len(content)
        if total_chars + msg_len > max_total_chars:
            break
        bounded.append({
            "role": msg.get("role"),
            "content": content,
        })
        total_chars += msg_len

    return list(reversed(bounded))



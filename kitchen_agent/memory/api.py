"""Unified storage API — all storage access goes through this module."""
from datetime import datetime
from kitchen_agent.memory.relational_store import (
    ConversationDB,
    InventoryDB,
    ShoppingListDB,
    ReminderDB,
)
from kitchen_agent.memory.vector_store import PreferenceStore, RecipeHistoryStore

_conversation_db = ConversationDB()
_pref_store = PreferenceStore()
_recipe_store = RecipeHistoryStore()


def set_user_id(user_id: str = "default") -> None:
    """Set the current user for subsequent calls."""
    global _current_user_id
    _current_user_id = user_id


_current_user_id = "default"


def retrieve_inventory(location: str = None) -> list:
    """Get all inventory items, optionally filtered by location."""
    db = InventoryDB(user_id=_current_user_id)
    return db.get_all_items(location=location)


def add_inventory_item(
    name: str,
    quantity: str,
    unit: str = None,
    location: str = "pantry",
    category: str = None,
    expiry_days: int = None,
) -> None:
    """Add or update an inventory item."""
    db = InventoryDB(user_id=_current_user_id)
    db.add_item(name, quantity, unit, location, category, expiry_days)


def remove_inventory_item(name: str) -> None:
    """Remove an item from inventory."""
    db = InventoryDB(user_id=_current_user_id)
    db.delete_item(name)


def update_inventory_quantity(name: str, quantity: str) -> None:
    """Update quantity of an inventory item."""
    db = InventoryDB(user_id=_current_user_id)
    db.update_quantity(name, quantity)


def get_inventory_item(name: str) -> dict:
    """Get a specific inventory item."""
    db = InventoryDB(user_id=_current_user_id)
    return db.get_item(name)


def get_expiring_inventory(days: int = 3) -> list:
    """Get items expiring within given days."""
    db = InventoryDB(user_id=_current_user_id)
    return db.get_expiring_items(days)


def retrieve_shopping_list(status: str = None) -> list:
    """Get shopping list items, optionally filtered by status."""
    db = ShoppingListDB(user_id=_current_user_id)
    return db.get_all(status=status)


def add_shopping_item(
    item: str,
    quantity: str = None,
    unit: str = None,
    reason: str = None,
    source_recipe: str = None,
    priority: int = 1,
) -> None:
    """Add an item to shopping list."""
    db = ShoppingListDB(user_id=_current_user_id)
    db.add(item, quantity, unit, reason, source_recipe, priority)


def remove_shopping_item(item: str) -> None:
    """Remove an item from shopping list."""
    db = ShoppingListDB(user_id=_current_user_id)
    db.remove(item)


def update_shopping_item_status(item: str, status: str, feedback: str = None) -> None:
    """Update status of a shopping item."""
    db = ShoppingListDB(user_id=_current_user_id)
    db.update_status(item, status, feedback)


def retrieve_reminders() -> list:
    """Get upcoming reminders."""
    db = ReminderDB(user_id=_current_user_id)
    return db.get_upcoming()


def add_reminder(title: str, message: str, scheduled_time: datetime, metadata: dict = None) -> int:
    """Add a reminder and return its ID."""
    db = ReminderDB(user_id=_current_user_id)
    return db.add(title, message, scheduled_time, metadata)


def complete_reminder(reminder_id: int) -> None:
    """Mark a reminder as complete."""
    db = ReminderDB(user_id=_current_user_id)
    db.mark_complete(reminder_id)


def delete_reminder(reminder_id: int) -> None:
    """Delete a reminder."""
    db = ReminderDB(user_id=_current_user_id)
    db.delete(reminder_id)

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

    recent_interactions_raw = _conversation_db.get(_interaction_key(user_id)) or {"interactions": []}
    recent_interactions = recent_interactions_raw.get("interactions", [])[-10:]

    return {
        "preferences": "\n".join(pref_lines) if pref_lines else "(none recorded)",
        "recent_recipes": "\n".join(recipe_lines) if recipe_lines else "(none recorded)",
        "recent_interactions": recent_interactions,
    }


def append_interaction(user_id: str, role: str, content: str):
    """Append a turn to the rolling recent interactions log."""
    raw = _conversation_db.get(_interaction_key(user_id)) or {"interactions": []}
    interactions = raw["interactions"]
    interactions.append({
        "role": role,
        "content": content[:500],
        "timestamp": datetime.now().isoformat(),
    })
    if len(interactions) > MAX_RECENT_INTERACTIONS:
        interactions = interactions[-MAX_RECENT_INTERACTIONS:]
    _conversation_db.set(_interaction_key(user_id), {"interactions": interactions})


def append_conversation_message(user_id: str, role: str, content: str):
    """Persist full conversation history per user for restart-safe context."""
    key = _conversation_key(user_id)
    raw = _conversation_db.get(key) or {"messages": []}
    messages = raw.get("messages", [])
    messages.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    })
    if len(messages) > 200:
        messages = messages[-200:]
    _conversation_db.set(key, {"messages": messages})


def get_conversation_history(
    user_id: str,
    limit: int = 8,
    max_total_chars: int = 3000,
) -> list[dict]:
    """Load a bounded slice of persisted conversation history."""
    raw = _conversation_db.get(_conversation_key(user_id)) or {"messages": []}
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



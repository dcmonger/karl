"""Long-term memory management — combines SQLite summaries + ChromaDB semantic store."""
import json
from datetime import datetime, timedelta
from typing import Optional
from database import MemoryDB, InventoryDB, ShoppingListDB, ReminderDB
from storage.vector_store import PreferenceStore, RecipeHistoryStore

_memory_db = MemoryDB()
_inventory_db = InventoryDB()
_shopping_db = ShoppingListDB()
_reminder_db = ReminderDB()
_pref_store = PreferenceStore()
_recipe_store = RecipeHistoryStore()

INVENTORY_SNAPSHOT_KEY = "inventory_snapshot"
RECENT_MEALS_KEY = "recent_meals"
PREFERENCES_SUMMARY_KEY = "preferences_summary"
SHOPPING_SUMMARY_KEY = "shopping_summary"
RECENT_INTERACTIONS_KEY = "recent_interactions"
LAST_SUMMARY_TIME_KEY = "last_summary_time"

MAX_RECENT_INTERACTIONS = 50


def get_working_memory(chat_id: str = None) -> dict:
    """Assembles a compact context snapshot for the agent on each turn."""
    inv_items = _inventory_db.get_all_items()
    shopping_items = _shopping_db.get_all(status="pending")
    upcoming_reminders = _reminder_db.get_upcoming(limit=5)
    recent_prefs = _pref_store.get_preferences(chat_id or "default")[-10:]
    recent_recipes = _recipe_store.get_recent_recipes(chat_id or "default", limit=5)

    inv_lines = []
    for item in inv_items:
        expiry_str = f" (expires {item['expiry_date'][:10]})" if item.get("expiry_date") else ""
        unit_str = f" {item['unit']}" if item.get("unit") else ""
        inv_lines.append(
            f"- {item['item_name']}: {item['quantity']}{unit_str} "
            f"[{item['location']}]{expiry_str}"
        )

    shopping_lines = []
    for item in shopping_items:
        unit_str = f" {item['unit']}" if item.get("unit") else ""
        reason_str = f" — for: {item['source_recipe']}" if item.get("source_recipe") else ""
        if item.get("reason"):
            reason_str += f" ({item['reason']})"
        shopping_lines.append(
            f"- {item['item_name']} {item['quantity'] or ''}{unit_str}{reason_str}"
        )

    pref_lines = [
        f"- {p.get('entity')}: {p.get('value')} ({p.get('type')})"
        for p in recent_prefs
    ]

    recipe_lines = [
        f"- {r.get('recipe_name')} (rated {r.get('rating')}/5)"
        for r in recent_recipes if r.get("recipe_name")
    ]

    reminder_lines = [
        f"- {r['title']}: {r['message']} at {r['scheduled_time'][:16]}"
        for r in upcoming_reminders
    ]

    recent_interactions_raw = _memory_db.get(RECENT_INTERACTIONS_KEY) or {"interactions": []}
    recent_interactions = recent_interactions_raw.get("interactions", [])[-10:]

    return {
        "inventory": "\n".join(inv_lines) if inv_lines else "(empty)",
        "inventory_count": len(inv_items),
        "shopping_list": "\n".join(shopping_lines) if shopping_lines else "(empty)",
        "shopping_count": len(shopping_items),
        "preferences": "\n".join(pref_lines) if pref_lines else "(none recorded)",
        "recent_recipes": "\n".join(recipe_lines) if recipe_lines else "(none recorded)",
        "upcoming_reminders": "\n".join(reminder_lines) if reminder_lines else "(none)",
        "recent_interactions": recent_interactions,
    }


def append_interaction(chat_id: str, role: str, content: str):
    """Append a turn to the rolling recent interactions log."""
    raw = _memory_db.get(RECENT_INTERACTIONS_KEY) or {"interactions": []}
    interactions = raw["interactions"]
    interactions.append({
        "role": role,
        "content": content[:500],
        "timestamp": datetime.now().isoformat(),
    })
    if len(interactions) > MAX_RECENT_INTERACTIONS:
        interactions = interactions[-MAX_RECENT_INTERACTIONS:]
    _memory_db.set(RECENT_INTERACTIONS_KEY, {"interactions": interactions})


def update_inventory_snapshot():
    """Refresh the stored inventory snapshot. Called periodically."""
    inv_items = _inventory_db.get_all_items()
    expiring = _inventory_db.get_expiring_items(days=3)
    lines = [f"- {i['item_name']}: {i['quantity']} [{i['location']}]" for i in inv_items]
    _memory_db.set(INVENTORY_SNAPSHOT_KEY, {
        "snapshot": "\n".join(lines) if lines else "(empty)",
        "count": len(inv_items),
        "expiring_count": len(expiring),
        "expiring_items": [i["item_name"] for i in expiring],
        "updated_at": datetime.now().isoformat(),
    })


def update_shopping_snapshot():
    """Refresh the stored shopping list summary."""
    items = _shopping_db.get_all(status="pending")
    lines = [f"- {i['item_name']} ({i['quantity'] or 'qty TBD'})" for i in items]
    _memory_db.set(SHOPPING_SUMMARY_KEY, {
        "snapshot": "\n".join(lines) if lines else "(empty)",
        "count": len(items),
        "updated_at": datetime.now().isoformat(),
    })


def update_preferences_summary(chat_id: str = "default"):
    """Refresh the preferences summary from ChromaDB."""
    prefs = _pref_store.get_preferences(chat_id)
    liked = [p for p in prefs if p.get("value") in ("liked", "love", "enjoy")]
    disliked = [p for p in prefs if p.get("value") in ("disliked", "hate", "avoid")]
    neutral = [p for p in prefs if p not in liked and p not in disliked]
    summary = {
        "liked_entities": [p.get("entity") for p in liked],
        "disliked_entities": [p.get("entity") for p in disliked],
        "total_preferences": len(prefs),
        "updated_at": datetime.now().isoformat(),
    }
    _memory_db.set(PREFERENCES_SUMMARY_KEY, summary)


def summarize_recent_interactions(chat_id: str = "default") -> str:
    """Compress recent interactions into a summary string for long-term memory."""
    raw = _memory_db.get(RECENT_INTERACTIONS_KEY)
    if not raw or not raw.get("interactions"):
        return ""
    interactions = raw["interactions"]
    if len(interactions) < 10:
        return ""

    summary_parts = []
    meal_mentions = [i for i in interactions if any(
        kw in i["content"].lower() for kw in ["cooked", "made", "ate", "recipe", "dinner", "lunch"]
    )]
    if meal_mentions:
        summary_parts.append(f"Recent cooking: {len(meal_mentions)} mentions.")

    pref_mentions = [i for i in interactions if i["role"] == "user" and len(i["content"]) < 200]
    if pref_mentions:
        prefs_found = [i["content"] for i in pref_mentions[-5:] if len(i["content"]) < 200]
        summary_parts.append(f"User stated preferences: {'; '.join(prefs_found)}")

    summary = " | ".join(summary_parts) if summary_parts else ""
    if summary:
        existing = _memory_db.get("interaction_summary") or {"summary": ""}
        existing["summary"] = summary
        existing["interactions_count"] = len(interactions)
        existing["summarized_at"] = datetime.now().isoformat()
        _memory_db.set("interaction_summary", existing)

    interactions.clear()
    if len(interactions) > MAX_RECENT_INTERACTIONS:
        interactions = interactions[-MAX_RECENT_INTERACTIONS:]
    _memory_db.set(RECENT_INTERACTIONS_KEY, {"interactions": interactions})
    _memory_db.set(LAST_SUMMARY_TIME_KEY, {"time": datetime.now().isoformat()})

    return summary


def run_memory_maintenance(chat_id: str = "default"):
    """Periodic maintenance job — refreshes snapshots and summarizes interactions."""
    update_inventory_snapshot()
    update_shopping_snapshot()
    update_preferences_summary(chat_id)
    summarize_recent_interactions(chat_id)


def get_interaction_summary() -> str:
    raw = _memory_db.get("interaction_summary")
    return raw.get("summary", "") if raw else ""

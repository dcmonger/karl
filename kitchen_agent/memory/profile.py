"""Kitchen Agent profile — user-specific storage access."""
from datetime import datetime
from kitchen_agent.memory.relational_store import (
    ConversationDB,
    InventoryDB,
    ShoppingListDB,
    ReminderDB,
)
from kitchen_agent.memory.vector_store import PreferenceStore, RecipeHistoryStore


class Profile:
    """A user's profile with access to all storage operations."""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self._inv_db = InventoryDB(user_id=user_id)
        self._shop_db = ShoppingListDB(user_id=user_id)
        self._remind_db = ReminderDB(user_id=user_id)
        self._conv_db = ConversationDB()
        self._pref_store = PreferenceStore()
        self._recipe_store = RecipeHistoryStore()

    # Conversation tracking
    def _conversation_key(self) -> str:
        return f"conversation_history:{self.user_id}"

    def append_message(self, role: str, content: str) -> None:
        """Add to full conversation history."""
        key = self._conversation_key()
        raw = self._conv_db.get(key) or {"messages": []}
        messages = raw.get("messages", [])
        messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        if len(messages) > 200:
            messages = messages[-200:]
        self._conv_db.set(key, {"messages": messages})

    def get_conversation_history(self, limit: int = 8, max_chars: int = 30000) -> list:
        """Get conversation history with size limits."""
        key = self._conversation_key()
        raw = self._conv_db.get(key) or {"messages": []}
        messages = raw.get("messages", [])[-limit:]
        bounded = []
        total_chars = 0
        for msg in reversed(messages):
            content = (msg.get("content") or "")[:1000]
            msg_len = len(content)
            if total_chars + msg_len > max_chars:
                break
            bounded.append({"role": msg.get("role"), "content": content})
            total_chars += msg_len
        return list(reversed(bounded))

    # Inventory
    def retrieve_inventory(self, location: str = None) -> list:
        return self._inv_db.get_all_items(location=location)

    def add_inventory_item(
        self,
        name: str,
        quantity: str,
        unit: str = None,
        location: str = "pantry",
        category: str = None,
        expiry_days: int = None,
    ) -> None:
        self._inv_db.add_item(name, quantity, unit, location, category, expiry_days)

    def remove_inventory_item(self, name: str) -> None:
        self._inv_db.delete_item(name)

    def update_inventory_quantity(self, name: str, quantity: str) -> None:
        self._inv_db.update_quantity(name, quantity)

    def get_inventory_item(self, name: str) -> dict:
        return self._inv_db.get_item(name)

    def get_expiring_inventory(self, days: int = 3) -> list:
        return self._inv_db.get_expiring_items(days)

    # Shopping
    def retrieve_shopping_list(self, status: str = None) -> list:
        return self._shop_db.get_all(status=status)

    def add_shopping_item(
        self,
        item: str,
        quantity: str = None,
        unit: str = None,
        reason: str = None,
        source_recipe: str = None,
        priority: int = 1,
    ) -> None:
        self._shop_db.add(item, quantity, unit, reason, source_recipe, priority)

    def remove_shopping_item(self, item: str) -> None:
        self._shop_db.remove(item)

    def update_shopping_item_status(self, item: str, status: str, feedback: str = None) -> None:
        self._shop_db.update_status(item, status, feedback)

    # Reminders
    def retrieve_reminders(self) -> list:
        return self._remind_db.get_upcoming()

    def add_reminder(self, title: str, message: str, scheduled_time: datetime, metadata: dict = None) -> int:
        return self._remind_db.add(title, message, scheduled_time, metadata)

    def complete_reminder(self, reminder_id: int) -> None:
        self._remind_db.mark_complete(reminder_id)

    def delete_reminder(self, reminder_id: int) -> None:
        self._remind_db.delete(reminder_id)

    # Preferences & recipes
    def get_preferences(self) -> list:
        return self._pref_store.get_preferences(self.user_id)

    def search_preferences(self, query: str, limit: int = 5) -> list:
        return self._pref_store.search_preferences(self.user_id, query, limit)

    def add_preference(
        self, preference_type: str, entity: str, value: str, notes: str = None
    ) -> None:
        self._pref_store.add_preference(
            self.user_id, preference_type, entity, value, notes
        )

    def get_recent_recipes(self, limit: int = 5) -> list:
        return self._recipe_store.get_recent_recipes(self.user_id, limit)

    def add_recipe(
        self,
        recipe_name: str,
        ingredients: list = None,
        feedback: str = None,
        rating: int = None,
    ) -> None:
        self._recipe_store.add_recipe(
            self.user_id, recipe_name, ingredients, feedback, rating
        )

    def get_working_memory(self) -> dict:
        """Assembles context for the agent on each turn.

        Note: Conversation history is passed via ainvoke() messages,
        not included here to avoid duplication.
        """
        recent_prefs = self._pref_store.get_preferences(self.user_id)[-10:]
        recent_recipes = self._recipe_store.get_recent_recipes(self.user_id, limit=5)

        pref_lines = [
            f"- {p.get('entity')}: {p.get('value')} ({p.get('type')})"
            for p in recent_prefs
        ]

        recipe_lines = [
            f"- {r.get('recipe_name')} (rated {r.get('rating')}/5)"
            for r in recent_recipes if r.get("recipe_name")
        ]

        return {
            "preferences": "\n".join(pref_lines) if pref_lines else "(none recorded)",
            "recent_recipes": "\n".join(recipe_lines) if recipe_lines else "(none recorded)",
        }


def get_profile(user_id: str = "default") -> Profile:
    """Get a Profile instance for the given user_id."""
    return Profile(user_id=user_id)


def get_working_memory(user_id: str = "default") -> dict:
    """Get working memory context for the given user_id."""
    return get_profile(user_id).get_working_memory()
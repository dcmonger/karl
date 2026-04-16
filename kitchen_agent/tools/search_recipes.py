"""search_recipes tool — generates recipe suggestions using Gemini with current inventory."""
from langchain_core.tools import tool
from kitchen_agent.storage.database import InventoryDB
from kitchen_agent.storage.vector_store import PreferenceStore, RecipeHistoryStore
from kitchen_agent.storage.memory import get_working_memory
from kitchen_agent.config.settings import GEMINI_KEY, GEMINI_MODEL

_inventory_db = InventoryDB()
_pref_store = PreferenceStore()
_recipe_store = RecipeHistoryStore()

from langchain_google_genai import ChatGoogleGenerativeAI

_llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    google_api_key=GEMINI_KEY,
    temperature=0.8,
)

SYSTEM_INSTRUCTION = """You are a friendly, practical kitchen assistant. You help users figure out what to cook with what they have, suggest new dishes, and inspire them to eat well. Be concise, enthusiastic, and practical. When suggesting recipes, include rough prep time, cook time, and key ingredients. If inventory is limited, suggest simple flexible recipes. If you recommend a recipe that needs marinating or advance prep, mention it. You know the user's preferences and inventory — respect their likes, dislikes, and dietary needs. Never suggest a recipe that uses ingredients they dislike or are allergic to. Keep responses conversational but informative."""


@tool
def search_recipes(
    query: str = None,
    limit: int = 3,
    chat_id: str = "default",
) -> str:
    """Search for recipe suggestions based on current inventory and preferences.
    
    This tool asks the AI to generate recipe ideas using what you currently have,
    what you've been eating lately, and your preferences. It does NOT search the
    internet — it generates suggestions based on your situation.
    
    Args:
        query: Optional specific query or request (e.g., "something quick for dinner",
            "a challenging weekend project", "vegetarian", "something with chicken").
            If omitted, will suggest diverse options from current inventory.
        limit: How many recipe suggestions to return. Default 3, max 5.
        chat_id: User identifier. Defaults to "default".
    
    Returns:
        Recipe suggestions with ingredients, brief instructions, and prep time.
        Also suggests items to add to shopping list if needed.
    """
    memory = get_working_memory(chat_id)
    prefs = _pref_store.search_preferences(chat_id, query or "food preferences", limit=5)
    pref_lines = "\n".join([
        f"- {p.get('entity')}: {p.get('value')} ({p.get('type')})"
        for p in prefs
    ]) if prefs else "(no strong preferences recorded yet)"
    
    recent_raw = _recipe_store.get_recent_recipes(chat_id, limit=5)
    recent_lines = "\n".join([f"- {r.get('recipe_name')}" for r in recent_raw if r.get('recipe_name')]) or "(none recorded)"
    
    prompt = f"""The user wants recipe suggestions.

CURRENT INVENTORY:
{memory['inventory']}

RECENTLY MADE DISHES:
{recent_lines}

USER PREFERENCES:
{pref_lines}

{'USER REQUEST: ' + query if query else 'SUGGESTION REQUEST: Please suggest diverse recipe ideas based on what they have, considering their preferences and what they might not have had recently. Suggest 1-3 simple/quick options and 1-2 more ambitious options if appropriate.'}

For each suggestion, include:
- Recipe name
- Key ingredients (mark which are already in inventory vs. what they'd need to buy)
- Brief overview of steps
- Prep time + cook time
- Any advance prep needed (e.g., "needs to marinate for 2 hours")

If their inventory is sparse, suggest 1-2 very simple flexible recipes they can make with basics.

Also note any items that are running low or expiring soon that should be used.

Keep it conversational and encouraging. Max {limit} suggestions."""
    
    try:
        result = _llm.invoke(prompt)
        return result.content if hasattr(result, 'content') else str(result)
    except Exception as e:
        return f"Sorry, I had trouble generating recipes right now: {e}"

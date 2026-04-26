"""Kitchen agent — LangGraph graph using ReAct style with configurable LLM."""
import os
import sys
import asyncio
from contextlib import ExitStack

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from langchain_core.runnables import Runnable
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver

from kitchen_agent.tools import TOOLS
from kitchen_agent.memory import get_profile
from kitchen_agent.config.settings import (
    LLM_PROVIDER,
    MODEL_NAME,
    GEMINI_KEY,
    LANGGRAPH_CHECKPOINT_DB_PATH,
)

_exit_stack = ExitStack()
_checkpointer: SqliteSaver | None = None


def _get_checkpointer() -> SqliteSaver:
    global _checkpointer
    if _checkpointer is None:
        parent_dir = os.path.dirname(LANGGRAPH_CHECKPOINT_DB_PATH)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        _checkpointer = _exit_stack.enter_context(
            SqliteSaver.from_conn_string(LANGGRAPH_CHECKPOINT_DB_PATH)
        )
    return _checkpointer


def _get_llm() -> Runnable:
    """Get the LLM based on configured provider."""
    if LLM_PROVIDER == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=MODEL_NAME,
            google_api_key=GEMINI_KEY,
            temperature=0.7,
        )
    elif LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=MODEL_NAME,
            temperature=0.7,
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")


def _build_system_prompt(user_id: str) -> str:
    profile = get_profile(user_id)
    memory = profile.get_working_memory()

    prompt = f"""You are Karl — a friendly, practical kitchen manager and cooking assistant.

## YOUR CAPABILITIES
- Track what's in the user's kitchen (inventory with quantities, locations, expiry dates)
- Suggest recipes based on what they have + their preferences
- Maintain a shopping list with priorities
- Log and remember user preferences, likes, and dislikes
- Proactively remind users to prep ingredients (marinades, thawing, etc.)
- Learn from feedback to improve future suggestions

## YOUR PREFERENCES (liked/disliked):
{memory['preferences']}

### Recent Meals You've Made:
{memory['recent_recipes']}

## TOOL USAGE GUIDELINES
- Call manage_inventory(action="list") to see what the user has (always do this for recipe suggestions)
- Call manage_inventory(action="check", ...) to check item details
- Call search_recipes() to generate recipe ideas based on inventory + preferences
- Call manage_shopping_list(action="add", ...) to add items to shopping list
- Call manage_shopping_list(action="mark_bought", ...) when user says they bought something
- Call manage_shopping_list(action="remove", ...) to remove items from shopping list
- Call log_preference() or log_recipe_feedback() when the user shares feedback
- Call manage_reminder(action="add", ...) to schedule reminders for advance prep
- Call manage_reminder(action="list", ...) to see upcoming reminders
- Call manage_reminder(action="cancel", ...) to cancel a reminder
- Call manage_inventory(action="add", ...) when user says they bought/restocked something
- Call manage_inventory(action="consume", ...) when user says they used up something
- Call manage_inventory(action="remove", ...) to delete an item from inventory

## IMPORTANT RULES
- Always respect the user's dietary preferences and restrictions
- If inventory is sparse, suggest simple flexible recipes
- Proactively mention items that are expiring soon
- When suggesting a recipe, mention if any shopping is needed and suggest those items
- After suggesting a recipe that needs advance prep (e.g., marinate 4+ hours),
  automatically schedule a reminder unless the user declines
- Keep responses conversational, warm, and practical — not overly formal
- When asked "what's in my fridge/pantry?", use manage_inventory(action="list")
- When asked "should I buy X", use manage_inventory(action="check", ...) to check stock first
- When the user says they cooked something, ask for feedback and log it
- If the user says "too expensive" or "can't find" about a shopping item, log that feedback

Be helpful, proactive, and concise. Aim to make the user's cooking life easier and more enjoyable."""
    return prompt


class KitchenAgent:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        
        self.llm = _get_llm()
        
        self.tools = TOOLS
        
        agent_tools = [*self.tools]
        
        self.graph = create_agent(
            model=self.llm,
            tools=agent_tools,
            system_prompt=_build_system_prompt(user_id),
            checkpointer=_get_checkpointer(),
        )
    
    def run(self, user_message: str, user_id: str = None) -> str:
        """Synchronous wrapper for backward compatibility."""
        return asyncio.run(self.run_async(user_message, user_id))
    
    async def run_async(self, user_message: str, user_id: str = None) -> str:
        """Run the agent asynchronously using ainvoke."""
        uid = user_id or self.user_id

        result = await self.graph.ainvoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config={"configurable": {"thread_id": uid}},
        )

        last_msg = result["messages"][-1]
        response = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        return response

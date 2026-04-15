"""Kitchen agent — LangGraph graph using ReAct style with Gemini."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from kitchen_agent.tools import TOOLS
from kitchen_agent.storage.memory import get_working_memory, append_interaction
from kitchen_agent.config.settings import GEMINI_KEY, GEMINI_MODEL


def _build_system_prompt(chat_id: str) -> str:
    memory = get_working_memory(chat_id)
    
    interaction_summary = ""
    try:
        from kitchen_agent.storage.memory import get_interaction_summary
        interaction_summary = get_interaction_summary()
    except Exception:
        pass
    
    learned_context = f"### Learned Context:\n{interaction_summary}" if interaction_summary else ""

    prompt = f"""You are Karl — a friendly, practical kitchen manager and cooking assistant.

## YOUR CAPABILITIES
- Track what's in the user's kitchen (inventory with quantities, locations, expiry dates)
- Suggest recipes based on what they have + their preferences
- Maintain a shopping list with priorities
- Log and remember user preferences, likes, and dislikes
- Proactively remind users to prep ingredients (marinades, thawing, etc.)
- Learn from feedback to improve future suggestions

## WORKING CONTEXT

### Current Inventory ({memory['inventory_count']} items):
{memory['inventory']}

### Shopping List ({memory['shopping_count']} items pending):
{memory['shopping_list']}

### Your Preferences (liked/disliked):
{memory['preferences']}

### Recent Meals You've Made:
{memory['recent_recipes']}

### Upcoming Reminders:
{memory['upcoming_reminders']}

{learned_context}

## TOOL USAGE GUIDELINES
- Call check_inventory() to see what the user has (always do this for recipe suggestions)
- Call get_item_quantity() to check a specific item's details
- Call search_recipes() to generate recipe ideas based on inventory + preferences
- Call add_to_shopping_list() when recommending items to buy
- Call log_preference() or log_recipe_feedback() when the user shares feedback
- Call schedule_reminder() when a recipe needs advance prep (marinating, thawing, proofing)
- When the user says they used up an ingredient, update the inventory via implicit knowledge
  (you can call get_item_quantity() first, then explain what to do — but inventory updates
  happen when the user tells you explicitly)

## IMPORTANT RULES
- Always respect the user's dietary preferences and restrictions
- If inventory is sparse, suggest simple flexible recipes
- Proactively mention items that are expiring soon
- When suggesting a recipe, mention if any shopping is needed and suggest those items
- After suggesting a recipe that needs advance prep (e.g., marinate 4+ hours), 
  automatically schedule a reminder unless the user declines
- Keep responses conversational, warm, and practical — not overly formal
- When asked "what's in my fridge/pantry?", use check_inventory()
- When asked "should I buy X", use get_item_quantity() to check stock first
- When the user says they cooked something, ask for feedback and log it
- If the user says "too expensive" or "can't find" about a shopping item, log that feedback

Be helpful, proactive, and concise. Aim to make the user's cooking life easier and more enjoyable."""
    return prompt


class KitchenAgent:
    def __init__(self, chat_id: str = "default"):
        self.chat_id = chat_id
        
        from langchain_google_genai import ChatGoogleGenerativeAI
        self.llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GEMINI_KEY,
            temperature=0.7,
        )
        
        self.tools = TOOLS
        
        agent_tools = [*self.tools]
        
        self.graph = create_react_agent(
            model=self.llm,
            tools=agent_tools,
            state_modifier=_build_system_prompt(chat_id),
            checkpointer=MemorySaver(),
        )
    
    def run(self, user_message: str, chat_id: str = None) -> str:
        cid = chat_id or self.chat_id
        append_interaction(cid, "user", user_message)
        
        config = {"configurable": {"thread_id": cid}}
        
        result = self.graph.invoke(
            {"messages": [HumanMessage(content=user_message)]},
            config=config,
        )
        
        last_msg = result["messages"][-1]
        response = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        
        append_interaction(cid, "assistant", response)
        return response

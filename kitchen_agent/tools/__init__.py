"""All LangGraph tools for the kitchen agent."""
from kitchen_agent.tools.manage_inventory import manage_inventory
from kitchen_agent.tools.manage_shopping_list import manage_shopping_list
from kitchen_agent.tools.manage_reminder import manage_reminder
from kitchen_agent.tools.log_preference import log_preference, log_recipe_feedback
from kitchen_agent.tools.search_recipes import search_recipes

TOOLS = [
    manage_inventory,
    manage_shopping_list,
    manage_reminder,
    log_preference,
    log_recipe_feedback,
    search_recipes,
]

TOOL_MAP = {t.name: t for t in TOOLS}

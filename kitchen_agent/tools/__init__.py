"""All LangGraph tools for the kitchen agent."""
from kitchen_agent.tools.check_inventory import check_inventory
from kitchen_agent.tools.update_shopping_list import update_shopping_list
from kitchen_agent.tools.log_preference import log_preference, log_recipe_feedback
from kitchen_agent.tools.search_recipes import search_recipes
from kitchen_agent.tools.update_reminder import update_reminder
from kitchen_agent.tools.update_inventory import update_inventory

TOOLS = [
    check_inventory,
    update_shopping_list,
    log_preference,
    log_recipe_feedback,
    search_recipes,
    update_reminder,
    update_inventory,
]

TOOL_MAP = {t.name: t for t in TOOLS}

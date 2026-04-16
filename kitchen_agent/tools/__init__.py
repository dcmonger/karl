"""All LangGraph tools for the kitchen agent."""
from kitchen_agent.tools.check_inventory import check_inventory
from kitchen_agent.tools.get_item_quantity import get_item_quantity
from kitchen_agent.tools.add_to_shopping_list import add_to_shopping_list
from kitchen_agent.tools.log_preference import log_preference, log_recipe_feedback
from kitchen_agent.tools.search_recipes import search_recipes
from kitchen_agent.tools.schedule_reminder import schedule_reminder
from kitchen_agent.tools.update_inventory import update_inventory
from kitchen_agent.tools.consume_inventory import consume_inventory

TOOLS = [
    check_inventory,
    get_item_quantity,
    add_to_shopping_list,
    log_preference,
    log_recipe_feedback,
    search_recipes,
    schedule_reminder,
    update_inventory,
    consume_inventory,
]

TOOL_MAP = {t.name: t for t in TOOLS}

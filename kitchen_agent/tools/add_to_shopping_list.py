"""add_to_shopping_list tool — adds items to the shopping list."""
from langchain_core.tools import tool
from kitchen_agent.storage.database import ShoppingListDB

_shopping_db = ShoppingListDB()


@tool
def add_to_shopping_list(
    item_name: str,
    quantity: str = None,
    unit: str = None,
    reason: str = None,
    source_recipe: str = None,
    priority: int = 1,
) -> str:
    """Add an item to the shopping list.
    
    Args:
        item_name: Name of the item to buy.
        quantity: How much to buy (e.g., "2 lbs", "1 bunch", "a few"). Optional.
        unit: Unit of measurement (e.g., "lbs", "oz", "bunch"). Optional.
        reason: Why you need it (e.g., "running low", "for recipe"). Optional.
        source_recipe: Name of the recipe this item is for. Optional.
        priority: 1=low, 2=medium, 3=high priority. Default is 1.
    
    Returns:
        A confirmation string listing the item that was added.
    """
    _shopping_db.add(
        item=item_name,
        quantity=quantity,
        unit=unit,
        reason=reason,
        source_recipe=source_recipe,
        priority=priority,
    )
    
    details = []
    if quantity:
        details.append(quantity)
    if unit:
        details.append(unit)
    if source_recipe:
        details.append(f"for '{source_recipe}'")
    
    detail_str = " ".join(details) if details else ""
    priority_str = {1: "low", 2: "medium", 3: "high"}.get(priority, "low")
    
    return (
        f"Added to shopping list: {item_name} {detail_str} "
        f"[{priority_str} priority]"
        + (f" — {reason}" if reason else "")
    )

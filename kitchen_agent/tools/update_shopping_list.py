"""update_shopping_list tool — manages the shopping list."""
from langchain_core.tools import tool
from kitchen_agent.memory import (
    add_shopping_item,
    remove_shopping_item,
    update_shopping_item_status,
)


@tool
def update_shopping_list(
    action: str,
    item_name: str,
    user_id: str = "default",
    quantity: str = None,
    unit: str = None,
    reason: str = None,
    source_recipe: str = None,
    priority: int = 1,
    status: str = None,
) -> str:
    """Manage the shopping list — add, remove, or update status.

    Actions:
    - "add": Add an item to the shopping list.
    - "remove": Remove an item from the shopping list.
    - "mark_bought": Mark an item as purchased (status="bought"). Use when the
        user says they bought it, it's been added to inventory, or they no longer
        need to buy it.
    - "mark_pending": Mark an item back to pending status.

    Args:
        action: What to do — "add", "remove", "mark_bought", "mark_pending".
        item_name: Name of the item.
        user_id: User identifier.
        quantity: How much to buy (e.g., "2 lbs"). Optional, for add.
        unit: Unit (e.g., "lbs", "oz"). Optional, for add.
        reason: Why needed (e.g., "running low"). Optional, for add.
        source_recipe: Recipe this is for. Optional, for add.
        priority: 1=low, 2=medium, 3=high. Default 1, for add.
        status: Status for update actions. Optional.

    Returns:
        A confirmation string.
    """
    if action == "add":
        add_shopping_item(
            user_id=user_id,
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
            f"Added to shopping list: {item_name} {detail_str} [{priority_str}]"
            + (f" — {reason}" if reason else "")
        )

    elif action == "remove":
        remove_shopping_item(user_id=user_id, item=item_name)
        return f"Removed '{item_name}' from shopping list."

    elif action == "mark_bought":
        update_shopping_item_status(user_id=user_id, item=item_name, status="bought", feedback=None)
        return f"Marked '{item_name}' as bought."

    elif action == "mark_pending":
        update_shopping_item_status(user_id=user_id, item=item_name, status="pending", feedback=None)
        return f"Marked '{item_name}' as pending."

    else:
        return f"Unknown action: {action}. Use add, remove, mark_bought, or mark_pending."

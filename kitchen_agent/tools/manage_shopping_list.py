"""manage_shopping_list tool — manage the shopping list."""
from langchain_core.tools import tool
from kitchen_agent.memory import get_profile


@tool
def manage_shopping_list(
    action: str,
    item_name: str = None,
    user_id: str = "default",
    quantity: str = None,
    unit: str = None,
    reason: str = None,
    source_recipe: str = None,
    priority: int = 1,
    status: str = None,
) -> str:
    """Manage the shopping list — add, list, remove, or update status.

    Actions:
    - "list": List all shopping list items, optionally filtered by status.
    - "add": Add an item to the shopping list.
    - "remove": Remove an item from the shopping list.
    - "mark_bought": Mark an item as purchased.
    - "mark_pending": Mark an item back to pending status.

    Args:
        action: What to do — "list", "add", "remove", "mark_bought", "mark_pending".
        item_name: Name of the item. Required for add/remove/mark_*.
        user_id: User identifier.
        quantity: How much to buy. Optional, for add.
        unit: Unit (e.g., "lbs", "oz"). Optional, for add.
        reason: Why needed. Optional, for add.
        source_recipe: Recipe this is for. Optional, for add.
        priority: 1=low, 2=medium, 3=high. Default 1, for add.
        status: Status filter. Optional, for list.

    Returns:
        A confirmation string or list of items.
    """
    profile = get_profile(user_id)

    if action == "list":
        items = profile.retrieve_shopping_list(status=status)
        if not items:
            status_hint = f" ({status})" if status else ""
            return f"Your shopping list{status_hint} is empty."
        lines = []
        for item in items:
            qty_str = f"{item['quantity']} {item.get('unit', '')}" if item.get('quantity') else "qty TBD"
            src = f" for '{item['source_recipe']}'" if item.get('source_recipe') else ""
            lines.append(f"- {item['item_name']}: {qty_str}{src} [{item['status']}]")
        header = f"Shopping List ({len(items)} items):\n"
        return header + "\n".join(lines)

    if action == "add":
        profile.add_shopping_item(
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

    if action == "remove":
        profile.remove_shopping_item(item_name)
        return f"Removed '{item_name}' from shopping list."

    if action == "mark_bought":
        profile.update_shopping_item_status(item_name, "bought", feedback=None)
        return f"Marked '{item_name}' as bought."

    if action == "mark_pending":
        profile.update_shopping_item_status(item_name, "pending", feedback=None)
        return f"Marked '{item_name}' as pending."

    return f"Unknown action: {action}. Use list, add, remove, mark_bought, or mark_pending."

"""update_inventory tool — manage inventory (add, update, consume, remove)."""
from langchain_core.tools import tool
from kitchen_agent.memory import (
    set_user_id,
    add_inventory_item,
    remove_inventory_item,
    update_inventory_quantity,
    get_inventory_item,
)


@tool
def update_inventory(
    action: str,
    item_name: str,
    quantity: str = None,
    user_id: str = "default",
    unit: str = None,
    location: str = "pantry",
    category: str = None,
    expiry_days: int = None,
) -> str:
    """Manage inventory — add, update, consume, or remove items.

    Actions:
    - "add": Add a new item to inventory (or restock if exists).
    - "consume": Mark as consumed/used. If quantity omitted, remove entirely.
    - "check": Get item details.
    - "remove": Delete an item from inventory.

    Args:
        action: What to do — "add", "consume", "check", "remove".
        item_name: Name of the item.
        quantity: Amount for add/consume. Optional.
        user_id: User identifier.
        unit: Unit (e.g., "lbs", "oz"). Optional, for add.
        location: Where stored. Default "pantry". Optional, for add.
        category: Category (e.g., "produce", "dairy"). Optional, for add.
        expiry_days: Days until expiry. Optional, for add.

    Returns:
        A confirmation string.
    """
    set_user_id(user_id)

    if action == "add":
        existing = get_inventory_item(item_name)
        add_inventory_item(
            name=item_name,
            quantity=quantity or "1",
            unit=unit,
            location=location,
            category=category,
            expiry_days=expiry_days,
        )
        action_str = "Updated" if existing else "Added"
        unit_str = f" {unit}" if unit else ""
        return f"{action_str} inventory: {item_name} = {quantity or '1'}{unit_str} in {location}."

    elif action == "consume":
        existing = get_inventory_item(item_name)
        if not existing:
            return f"'{item_name}' is not in inventory."
        if quantity is None:
            remove_inventory_item(item_name)
            return f"Used up {item_name}, removed from inventory."
        update_inventory_quantity(item_name, quantity)
        unit = existing.get("unit")
        unit_str = f" {unit}" if unit else ""
        return f"Updated {item_name} remaining to {quantity}{unit_str}."

    elif action == "check":
        item = get_inventory_item(item_name)
        if not item:
            return f"'{item_name}' is not in inventory."
        from datetime import datetime
        unit_str = f" {item['unit']}" if item.get("unit") else ""
        location_str = f" in {item['location']}"
        expiry_str = ""
        if item.get("expiry_date"):
            expiry = datetime.fromisoformat(item["expiry_date"])
            days_left = (expiry.date() - datetime.now().date()).days
            if days_left < 0:
                expiry_str = f" — EXPIRED"
            elif days_left <= 3:
                expiry_str = f" — expires in {days_left} day(s)"
        return (
            f"{item['item_name']}: {item['quantity']}{unit_str}{location_str}{expiry_str}"
        )

    elif action == "remove":
        remove_inventory_item(item_name)
        return f"Removed '{item_name}' from inventory."

    else:
        return f"Unknown action: {action}. Use add, consume, check, or remove."

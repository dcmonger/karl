"""manage_inventory tool — manage inventory (add, list, consume, remove, check)."""
from langchain_core.tools import tool
from datetime import datetime
from kitchen_agent.memory import get_profile


@tool
def manage_inventory(
    action: str,
    item_name: str = None,
    quantity: str = None,
    user_id: str = "default",
    unit: str = None,
    location: str = "pantry",
    category: str = None,
    expiry_days: int = None,
) -> str:
    """Manage kitchen inventory — add, list, check, consume, or remove items.

    Actions:
    - "list": List all inventory items, optionally filtered by location.
    - "add": Add a new item to inventory (or restock if exists).
    - "check": Get details of a specific item.
    - "consume": Mark as consumed/used. If quantity omitted, remove entirely.
    - "remove": Delete an item from inventory.

    Args:
        action: What to do — "list", "add", "check", "consume", "remove".
        item_name: Name of the item. Required for add/check/consume/remove.
        quantity: Amount. For add or consume.
        user_id: User identifier.
        unit: Unit (e.g., "lbs", "oz"). For add.
        location: Where stored. For add. Default "pantry".
        category: Category (e.g., "produce", "dairy"). For add.
        expiry_days: Days until expiry. For add.

    Returns:
        A confirmation string or item details.
    """
    profile = get_profile(user_id)

    if action == "list":
        items = profile.retrieve_inventory(location=location)
        if not items:
            loc_hint = f" in {location}" if location else ""
            return f"Your inventory{loc_hint} is empty."
        lines = []
        for item in items:
            expiry_str = ""
            if item.get("expiry_date"):
                expiry = datetime.fromisoformat(item["expiry_date"])
                days_left = (expiry.date() - datetime.now().date()).days
                if days_left < 0:
                    expiry_str = f" ⚠️ EXPIRED {abs(days_left)} days ago"
                elif days_left == 0:
                    expiry_str = " ⚠️ expires today"
                elif days_left <= 3:
                    expiry_str = f" ⚠️ expires in {days_left} day(s)"
                else:
                    expiry_str = f" (expires {expiry.strftime('%b %d')})"
            acquired = ""
            if item.get("acquired_date"):
                acquired_date = datetime.fromisoformat(item["acquired_date"])
                days_owned = (datetime.now().date() - acquired_date.date()).days
                if days_owned >= 7:
                    acquired = f" (have had {days_owned} days)"
            unit_str = f" {item['unit']}" if item.get("unit") else ""
            lines.append(
                f"• {item['item_name']}: {item['quantity']}{unit_str} "
                f"[{item['location']}]{expiry_str}{acquired}"
            )
        loc_label = f" in {location}" if location else ""
        header = f"Inventory ({len(items)} item{'s' if len(items) != 1 else ''}){loc_label}:\n"
        return header + "\n".join(lines)

    elif action == "add":
        existing = profile.get_inventory_item(item_name)
        profile.add_inventory_item(
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

    elif action == "check":
        item = profile.get_inventory_item(item_name)
        if not item:
            return f"'{item_name}' is not in inventory."
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

    elif action == "consume":
        existing = profile.get_inventory_item(item_name)
        if not existing:
            return f"'{item_name}' is not in inventory."
        if quantity is None:
            profile.remove_inventory_item(item_name)
            return f"Used up {item_name}, removed from inventory."
        profile.update_inventory_quantity(item_name, quantity)
        unit = existing.get("unit")
        unit_str = f" {unit}" if unit else ""
        return f"Updated {item_name} remaining to {quantity}{unit_str}."

    elif action == "remove":
        profile.remove_inventory_item(item_name)
        return f"Removed '{item_name}' from inventory."

    else:
        return f"Unknown action: {action}. Use list, add, check, consume, or remove."

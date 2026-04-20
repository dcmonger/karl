"""get_item_quantity tool — returns quantity info for a specific item."""
from langchain_core.tools import tool
from kitchen_agent.storage.database import InventoryDB


@tool
def get_item_quantity(item_name: str, user_id: str = "default") -> str:
    """Look up the exact quantity and details for a specific inventory item.

    Args:
        item_name: Name of the item to look up.
        user_id: User identifier.

    Returns:
        A string with the item's quantity, unit, location, expiry, and
        how long it's been in inventory. Returns 'not found' if item doesn't exist.
    """
    inventory_db = InventoryDB(user_id=user_id)
    item = inventory_db.get_item(item_name)
    if not item:
        return f"'{item_name}' is not in your inventory."

    from datetime import datetime

    unit_str = f" {item['unit']}" if item.get("unit") else ""
    location_str = f" in the {item['location']}"

    expiry_str = ""
    if item.get("expiry_date"):
        expiry = datetime.fromisoformat(item["expiry_date"])
        days_left = (expiry.date() - datetime.now().date()).days
        if days_left < 0:
            expiry_str = f" — EXPIRED {abs(days_left)} days ago"
        elif days_left == 0:
            expiry_str = " — expires TODAY"
        elif days_left <= 3:
            expiry_str = f" — expires in {days_left} day(s)"
        else:
            expiry_str = f" — expires {expiry.strftime('%b %d')}"

    acquired_str = ""
    if item.get("acquired_date"):
        acquired_date = datetime.fromisoformat(item["acquired_date"])
        days_owned = (datetime.now().date() - acquired_date.date()).days
        if days_owned >= 1:
            acquired_str = f" (you've had it for {days_owned} day(s))"

    return (
        f"{item['item_name']}: {item['quantity']}{unit_str}{location_str}"
        f"{expiry_str}{acquired_str}"
    )

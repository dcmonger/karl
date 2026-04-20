"""check_inventory tool — lists all inventory items with optional location filter."""
from langchain_core.tools import tool
from kitchen_agent.memory import get_profile
from datetime import datetime


@tool
def check_inventory(user_id: str = "default", location: str = None) -> str:
    """Check the current kitchen inventory. Optionally filter by location.

    Args:
        user_id: User identifier.
        location: Optional filter — 'fridge', 'freezer', 'pantry', 'counter', etc.

    Returns:
        A formatted string listing all matching inventory items with their
        quantity, unit, location, and expiry date if applicable.
    """
    profile = get_profile(user_id)
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

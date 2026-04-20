"""update_inventory tool — add or restock inventory items."""
from langchain_core.tools import tool
from kitchen_agent.storage.database import InventoryDB


@tool
def update_inventory(
    item_name: str,
    quantity: str,
    user_id: str = "default",
    unit: str = None,
    location: str = "pantry",
    category: str = None,
    expiry_days: int = None,
) -> str:
    """Add or restock an item in inventory.

    Use when the user explicitly says they bought/restocked an item.
    """
    inventory_db = InventoryDB(user_id=user_id)
    existing = inventory_db.get_item(item_name)
    inventory_db.add_item(
        name=item_name,
        quantity=quantity,
        unit=unit,
        location=location,
        category=category,
        expiry_days=expiry_days,
    )

    action = "Updated" if existing else "Added"
    unit_str = f" {unit}" if unit else ""
    return f"{action} inventory: {item_name} = {quantity}{unit_str} in {location}."

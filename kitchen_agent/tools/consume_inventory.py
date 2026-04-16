"""consume_inventory tool — consume or remove inventory items."""
from langchain_core.tools import tool
from kitchen_agent.storage.database import InventoryDB

_inventory_db = InventoryDB()


@tool
def consume_inventory(item_name: str, quantity: str = None) -> str:
    """Mark inventory as consumed.

    If quantity is omitted, the item is removed entirely (used up).
    If quantity is provided, it replaces the quantity with the remaining amount.
    """
    existing = _inventory_db.get_item(item_name)
    if not existing:
        return f"'{item_name}' is not currently in inventory."

    if quantity is None:
        _inventory_db.delete_item(item_name)
        return f"Marked {item_name} as used up and removed it from inventory."

    _inventory_db.update_quantity(item_name, quantity)
    unit = existing.get("unit")
    unit_str = f" {unit}" if unit else ""
    return f"Updated {item_name} remaining quantity to {quantity}{unit_str}."

"""FastAPI routes for the agent API."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kitchen_agent.agents.kitchen_agent import KitchenAgent

app = FastAPI(title="Kitchen Agent API", version="1.0.0")

_agents: dict[str, KitchenAgent] = {}


def get_agent(chat_id: str) -> KitchenAgent:
    if chat_id not in _agents:
        _agents[chat_id] = KitchenAgent(chat_id=chat_id)
    return _agents[chat_id]


class ChatRequest(BaseModel):
    message: str
    chat_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    chat_id: str


class InventoryUpdateRequest(BaseModel):
    action: str  # "add", "update", "remove", "use_up"
    item_name: str
    quantity: str = None
    unit: str = None
    location: str = "pantry"
    category: str = None
    expiry_days: int = None


class ShoppingListRequest(BaseModel):
    action: str  # "add", "remove", "update_status"
    item_name: str
    quantity: str = None
    unit: str = None
    reason: str = None
    source_recipe: str = None
    priority: int = 1
    status: str = None
    feedback: str = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Main chat endpoint — receives user message, returns agent response."""
    agent = get_agent(req.chat_id)
    try:
        response = agent.run(req.message, chat_id=req.chat_id)
        return ChatResponse(response=response, chat_id=req.chat_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/inventory")
async def inventory_update(req: InventoryUpdateRequest):
    """Direct inventory management endpoint (alternative to natural language)."""
    from kitchen_agent.storage.database import InventoryDB
    db = InventoryDB()
    
    if req.action == "add":
        db.add_item(req.item_name, req.quantity, req.unit, req.location,
                    req.category, req.expiry_days)
        return {"status": "added", "item": req.item_name}
    elif req.action == "update":
        from kitchen_agent.storage.database import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE inventory SET quantity = ? WHERE item_name = ?",
                  (str(req.quantity), req.item_name))
        conn.commit()
        conn.close()
        return {"status": "updated", "item": req.item_name}
    elif req.action == "remove":
        db.delete_item(req.item_name)
        return {"status": "removed", "item": req.item_name}
    elif req.action == "use_up":
        db.delete_item(req.item_name)
        return {"status": "used_up", "item": req.item_name}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")


@app.post("/shopping")
async def shopping_list(req: ShoppingListRequest):
    """Direct shopping list management endpoint."""
    from kitchen_agent.storage.database import ShoppingListDB
    db = ShoppingListDB()
    
    if req.action == "add":
        db.add(req.item_name, req.quantity, req.unit, req.reason,
               req.source_recipe, req.priority)
        return {"status": "added", "item": req.item_name}
    elif req.action == "remove":
        db.remove(req.item_name)
        return {"status": "removed", "item": req.item_name}
    elif req.action == "update_status":
        db.update_status(req.item_name, req.status or "pending", req.feedback)
        return {"status": "updated", "item": req.item_name}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")


@app.post("/memory/maintenance")
async def memory_maintenance(chat_id: str = "default"):
    """Trigger periodic memory maintenance."""
    from kitchen_agent.storage.memory import run_memory_maintenance
    run_memory_maintenance(chat_id)
    return {"status": "maintenance done"}


@app.get("/shopping")
async def get_shopping_list(status: str = None):
    from kitchen_agent.storage.database import ShoppingListDB
    db = ShoppingListDB()
    items = db.get_all(status=status)
    return {"items": items, "count": len(items)}


@app.get("/inventory")
async def get_inventory(location: str = None):
    from kitchen_agent.storage.database import InventoryDB
    db = InventoryDB()
    items = db.get_all(location=location)
    return {"items": items, "count": len(items)}

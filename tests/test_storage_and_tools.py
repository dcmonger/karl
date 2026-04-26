import importlib


def _reload_modules(monkeypatch, tmp_path):
    db_path = tmp_path / "kitchen.db"
    chroma_path = tmp_path / "chroma"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("CHROMA_PATH", str(chroma_path))

    rs = importlib.import_module("kitchen_agent.memory.relational_store")
    profile_mod = importlib.import_module("kitchen_agent.memory.profile")
    inv_mod = importlib.import_module("kitchen_agent.tools.manage_inventory")
    rem_mod = importlib.import_module("kitchen_agent.tools.manage_reminder")

    importlib.reload(rs)
    importlib.reload(profile_mod)
    importlib.reload(inv_mod)
    importlib.reload(rem_mod)

    return rs, profile_mod, inv_mod, rem_mod


def test_shopping_add_and_list(monkeypatch, tmp_path):
    rs, *_ = _reload_modules(monkeypatch, tmp_path)

    db = rs.ShoppingListDB(user_id="u1")
    db.add("milk", "1", "L", "breakfast", None, 2)
    rows = db.get_all()

    assert len(rows) == 1
    assert rows[0]["item_name"] == "milk"
    assert rows[0]["user_id"] == "u1"


def test_manage_inventory_consume_decrements_numeric(monkeypatch, tmp_path):
    _, _, inv_mod, _ = _reload_modules(monkeypatch, tmp_path)

    inv_mod.manage_inventory.invoke({
        "action": "add",
        "item_name": "eggs",
        "quantity": "12",
        "user_id": "u1",
    })
    out = inv_mod.manage_inventory.invoke({
        "action": "consume",
        "item_name": "eggs",
        "quantity": "2",
        "user_id": "u1",
    })

    assert "remaining to 10" in out


def test_manage_inventory_consume_non_numeric(monkeypatch, tmp_path):
    _, _, inv_mod, _ = _reload_modules(monkeypatch, tmp_path)

    inv_mod.manage_inventory.invoke({
        "action": "add",
        "item_name": "broth",
        "quantity": "some",
        "user_id": "u1",
    })
    out = inv_mod.manage_inventory.invoke({
        "action": "consume",
        "item_name": "broth",
        "quantity": "1",
        "user_id": "u1",
    })

    assert "non-numeric" in out


def test_manage_reminder_reports_daemon_sync_error(monkeypatch, tmp_path):
    _, _, _, rem_mod = _reload_modules(monkeypatch, tmp_path)

    class DummyExc(rem_mod.requests.RequestException):
        pass

    def boom(*args, **kwargs):
        raise DummyExc("daemon down")

    monkeypatch.setattr(rem_mod.requests, "post", boom)

    out = rem_mod.manage_reminder.invoke({
        "action": "add",
        "title": "Prep",
        "message": "Do prep",
        "scheduled_time": "2030-01-01 10:00",
        "user_id": "u1",
    })

    assert "Saved in database" in out
    assert "daemon down" in out

"""SQLAlchemy models + repositories for structured data."""
import json
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Column, Float, Integer, String, Text, create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = os.getenv("DB_PATH", "kitchen_agent/storage/kitchen.db")


def _ensure_parent_dir() -> None:
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)


def _db_url() -> str:
    if DB_PATH.startswith("sqlite://"):
        return DB_PATH
    return f"sqlite:///{DB_PATH}"


Base = declarative_base()


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, default="default", index=True)
    item_name = Column(String, nullable=False)
    quantity_numeric = Column(Float, nullable=True)
    quantity_desc = Column(Text, nullable=True)
    unit = Column(String, nullable=True)
    location = Column(String, nullable=False)
    category = Column(String, nullable=True)
    acquired_date = Column(String, nullable=False)
    expiry_date = Column(String, nullable=True)
    metadata_json = Column("metadata", Text, nullable=True)
    created_at = Column(String, default=lambda: datetime.now().isoformat())


class ShoppingList(Base):
    __tablename__ = "shopping_list"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, default="default", index=True)
    item_name = Column(String, nullable=False)
    quantity = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    priority = Column(Integer, default=1)
    reason = Column(String, nullable=True)
    source_recipe = Column(String, nullable=True)
    status = Column(String, default="pending", index=True)
    feedback = Column(String, nullable=True)
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.now().isoformat())


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    scheduled_time = Column(String, nullable=False, index=True)
    status = Column(String, default="pending", index=True)
    user_id = Column(String, nullable=True, index=True)
    metadata_json = Column("metadata", Text, nullable=True)
    created_at = Column(String, default=lambda: datetime.now().isoformat())


_engine = None
_SessionLocal = None


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _ensure_parent_dir()
        _engine = create_engine(_db_url(), future=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _engine


@contextmanager
def get_session():
    _get_engine()
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    engine = _get_engine()
    Base.metadata.create_all(bind=engine)


def _parse_quantity_fields(quantity: str | None) -> tuple[float | None, str | None]:
    if quantity is None:
        return None, None
    normalized = str(quantity).strip()
    if not normalized:
        return None, None
    try:
        return float(normalized), None
    except ValueError:
        return None, normalized


def _format_quantity(quantity_numeric: float | None, quantity_desc: str | None) -> str:
    if quantity_numeric is not None:
        return str(int(quantity_numeric)) if float(quantity_numeric).is_integer() else str(quantity_numeric)
    if quantity_desc:
        return quantity_desc
    return "unknown"


class InventoryDB:
    def __init__(self, user_id: str = "default"):
        init_db()
        self.user_id = user_id

    def add_item(self, name: str, quantity: str = None, unit: str = None, location: str = "pantry",
                 category: str = None, expiry_days: int = None, metadata: dict = None):
        acquired = datetime.now().isoformat()
        expiry = (datetime.now() + timedelta(days=expiry_days)).isoformat() if expiry_days else None
        quantity_numeric, quantity_desc = _parse_quantity_fields(quantity)
        with get_session() as s:
            row = s.execute(
                select(Inventory).where(Inventory.user_id == self.user_id, Inventory.item_name == name)
            ).scalar_one_or_none()
            if row is None:
                row = Inventory(user_id=self.user_id, item_name=name, location=location, acquired_date=acquired)
                s.add(row)
            row.quantity_numeric = quantity_numeric
            row.quantity_desc = quantity_desc
            row.unit = unit
            row.location = location
            row.category = category
            row.acquired_date = acquired
            row.expiry_date = expiry
            row.metadata_json = json.dumps(metadata) if metadata else None

    def get_item(self, name: str) -> Optional[dict]:
        with get_session() as s:
            row = s.execute(
                select(Inventory).where(Inventory.user_id == self.user_id, Inventory.item_name == name)
            ).scalar_one_or_none()
            return _to_inventory_dict(row)

    def get_all_items(self, location: str = None) -> list:
        with get_session() as s:
            stmt = select(Inventory).where(Inventory.user_id == self.user_id)
            if location:
                stmt = stmt.where(Inventory.location == location)
            rows = s.execute(stmt).scalars().all()
            return [_to_inventory_dict(r) for r in rows]

    def update_quantity(self, name: str, quantity: str):
        quantity_numeric, quantity_desc = _parse_quantity_fields(quantity)
        with get_session() as s:
            row = s.execute(
                select(Inventory).where(Inventory.user_id == self.user_id, Inventory.item_name == name)
            ).scalar_one_or_none()
            if row is None:
                return False
            row.quantity_numeric = quantity_numeric
            row.quantity_desc = quantity_desc
            return True

    def delete_item(self, name: str):
        with get_session() as s:
            row = s.execute(
                select(Inventory).where(Inventory.user_id == self.user_id, Inventory.item_name == name)
            ).scalar_one_or_none()
            if row:
                s.delete(row)

    def get_expiring_items(self, days: int = 3) -> list:
        threshold = (datetime.now() + timedelta(days=days)).isoformat()
        with get_session() as s:
            rows = s.execute(
                select(Inventory).where(
                    Inventory.user_id == self.user_id,
                    Inventory.expiry_date.is_not(None),
                    Inventory.expiry_date <= threshold,
                ).order_by(Inventory.expiry_date)
            ).scalars().all()
            return [_to_inventory_dict(r) for r in rows]


class ShoppingListDB:
    def __init__(self, user_id: str = "default"):
        init_db()
        self.user_id = user_id

    def add(self, item: str, quantity: str = None, unit: str = None,
            reason: str = None, source_recipe: str = None, priority: int = 1):
        with get_session() as s:
            s.add(ShoppingList(
                user_id=self.user_id,
                item_name=item,
                quantity=quantity,
                unit=unit,
                reason=reason,
                source_recipe=source_recipe,
                priority=priority,
            ))

    def get_all(self, status: str = None) -> list:
        with get_session() as s:
            stmt = select(ShoppingList).where(ShoppingList.user_id == self.user_id)
            if status:
                stmt = stmt.where(ShoppingList.status == status)
            rows = s.execute(stmt.order_by(ShoppingList.priority.desc(), ShoppingList.created_at)).scalars().all()
            return [_to_dict(r) for r in rows]

    def update_status(self, item: str, status: str, feedback: str = None):
        with get_session() as s:
            rows = s.execute(
                select(ShoppingList).where(ShoppingList.user_id == self.user_id, ShoppingList.item_name == item)
            ).scalars().all()
            for row in rows:
                row.status = status
                if feedback is not None:
                    row.feedback = feedback
                row.updated_at = datetime.now().isoformat()

    def remove(self, item: str):
        with get_session() as s:
            rows = s.execute(
                select(ShoppingList).where(ShoppingList.user_id == self.user_id, ShoppingList.item_name == item)
            ).scalars().all()
            for row in rows:
                s.delete(row)


class ReminderDB:
    def __init__(self, user_id: str = "default"):
        init_db()
        self.user_id = user_id

    def add(self, title: str, message: str, scheduled_time: datetime,
            metadata: dict = None):
        with get_session() as s:
            row = Reminder(
                title=title,
                message=message,
                scheduled_time=scheduled_time.isoformat(),
                user_id=self.user_id,
                metadata_json=json.dumps(metadata) if metadata else None,
            )
            s.add(row)
            s.flush()
            return row.id

    def get_due(self) -> list:
        now = datetime.now().isoformat()
        with get_session() as s:
            rows = s.execute(
                select(Reminder).where(
                    Reminder.user_id == self.user_id,
                    Reminder.status == "pending",
                    Reminder.scheduled_time <= now,
                ).order_by(Reminder.scheduled_time)
            ).scalars().all()
            return [_to_dict(r) for r in rows]

    def get_by_id(self, id: int) -> Optional[dict]:
        with get_session() as s:
            row = s.execute(
                select(Reminder).where(Reminder.user_id == self.user_id, Reminder.id == id)
            ).scalar_one_or_none()
            return _to_dict(row)

    def get_upcoming(self, limit: int = 10) -> list:
        now = datetime.now().isoformat()
        with get_session() as s:
            rows = s.execute(
                select(Reminder).where(
                    Reminder.user_id == self.user_id,
                    Reminder.status == "pending",
                    Reminder.scheduled_time > now,
                ).order_by(Reminder.scheduled_time).limit(limit)
            ).scalars().all()
            return [_to_dict(r) for r in rows]

    def get_all(self) -> list:
        with get_session() as s:
            rows = s.execute(
                select(Reminder).where(Reminder.user_id == self.user_id).order_by(Reminder.scheduled_time)
            ).scalars().all()
            return [_to_dict(r) for r in rows]

    def mark_complete(self, id: int):
        with get_session() as s:
            row = s.execute(
                select(Reminder).where(Reminder.user_id == self.user_id, Reminder.id == id)
            ).scalar_one_or_none()
            if row:
                row.status = "completed"

    def delete(self, id: int):
        with get_session() as s:
            row = s.execute(
                select(Reminder).where(Reminder.user_id == self.user_id, Reminder.id == id)
            ).scalar_one_or_none()
            if row:
                s.delete(row)


def _to_dict(row):
    if row is None:
        return None
    data = {}
    for col in row.__table__.columns:
        if col.name == "metadata":
            data[col.name] = getattr(row, "metadata_json")
        else:
            data[col.name] = getattr(row, col.name)
    return data


def _to_inventory_dict(row):
    data = _to_dict(row)
    if data is None:
        return None
    data["quantity"] = _format_quantity(
        data.get("quantity_numeric"),
        data.get("quantity_desc"),
    )
    return data

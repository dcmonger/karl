"""SQLite database schema for structured data."""
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional
import json

DB_PATH = os.getenv("DB_PATH", "kitchen_agent/storage/kitchen.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT UNIQUE NOT NULL,
            quantity TEXT NOT NULL,
            unit TEXT,
            location TEXT NOT NULL,
            category TEXT,
            acquired_date TEXT NOT NULL,
            expiry_date TEXT,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS shopping_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            quantity TEXT,
            unit TEXT,
            priority INTEGER DEFAULT 1,
            reason TEXT,
            source_recipe TEXT,
            status TEXT DEFAULT 'pending',
            feedback TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            scheduled_time TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            chat_id TEXT,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS agent_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

class InventoryDB:
    def __init__(self):
        init_db()
    
    def add_item(self, name: str, quantity: str, unit: str = None, location: str = "pantry",
                 category: str = None, expiry_days: int = None, metadata: dict = None):
        conn = get_connection()
        c = conn.cursor()
        acquired = datetime.now().isoformat()
        expiry = (datetime.now() + timedelta(days=expiry_days)).isoformat() if expiry_days else None
        
        c.execute("""
            INSERT OR REPLACE INTO inventory 
            (item_name, quantity, unit, location, category, acquired_date, expiry_date, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, str(quantity), unit, location, category, acquired, expiry, 
              json.dumps(metadata) if metadata else None))
        conn.commit()
        conn.close()
    
    def get_item(self, name: str) -> Optional[dict]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM inventory WHERE item_name = ?", (name,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def get_all_items(self, location: str = None) -> list:
        conn = get_connection()
        c = conn.cursor()
        query = "SELECT * FROM inventory WHERE 1=1"
        params = []
        if location:
            query += " AND location = ?"
            params.append(location)
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def update_quantity(self, name: str, quantity: str):
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE inventory SET quantity = ? WHERE item_name = ?", (str(quantity), name))
        if c.rowcount == 0:
            conn.rollback()
            conn.close()
            return False
        conn.commit()
        conn.close()
        return True
    
    def delete_item(self, name: str):
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM inventory WHERE item_name = ?", (name,))
        conn.commit()
        conn.close()
    
    def get_expiring_items(self, days: int = 3) -> list:
        conn = get_connection()
        c = conn.cursor()
        threshold = (datetime.now() + timedelta(days=days)).isoformat()
        c.execute("""
            SELECT * FROM inventory 
            WHERE expiry_date IS NOT NULL AND expiry_date <= ?
            ORDER BY expiry_date
        """, (threshold,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

class ShoppingListDB:
    def __init__(self):
        init_db()
    
    def add(self, item: str, quantity: str = None, unit: str = None, 
            reason: str = None, source_recipe: str = None, priority: int = 1):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO shopping_list (item_name, quantity, unit, reason, source_recipe, priority)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item, quantity, unit, reason, source_recipe, priority))
        conn.commit()
        conn.close()
    
    def get_all(self, status: str = None) -> list:
        conn = get_connection()
        c = conn.cursor()
        query = "SELECT * FROM shopping_list"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY priority DESC, created_at"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def update_status(self, item: str, status: str, feedback: str = None):
        conn = get_connection()
        c = conn.cursor()
        if feedback:
            c.execute("""
                UPDATE shopping_list 
                SET status = ?, feedback = ?, updated_at = CURRENT_TIMESTAMP
                WHERE item_name = ?
            """, (status, feedback, item))
        else:
            c.execute("""
                UPDATE shopping_list 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE item_name = ?
            """, (status, item))
        conn.commit()
        conn.close()
    
    def remove(self, item: str):
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM shopping_list WHERE item_name = ?", (item,))
        conn.commit()
        conn.close()

class ReminderDB:
    def __init__(self):
        init_db()
    
    def add(self, title: str, message: str, scheduled_time: datetime, 
            chat_id: str = None, metadata: dict = None):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO reminders (title, message, scheduled_time, chat_id, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (title, message, scheduled_time.isoformat(), chat_id, 
              json.dumps(metadata) if metadata else None))
        conn.commit()
        last_id = c.lastrowid
        conn.close()
        return last_id
    
    def get_due(self) -> list:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM reminders 
            WHERE status = 'pending' AND scheduled_time <= ?
            ORDER BY scheduled_time
        """, (datetime.now().isoformat(),))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_by_id(self, id: int) -> Optional[dict]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM reminders WHERE id = ?", (id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def get_upcoming(self, limit: int = 10) -> list:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM reminders 
            WHERE status = 'pending' AND scheduled_time > ?
            ORDER BY scheduled_time
            LIMIT ?
        """, (datetime.now().isoformat(), limit))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def mark_complete(self, id: int):
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE reminders SET status = 'completed' WHERE id = ?", (id,))
        conn.commit()
        conn.close()
    
    def delete(self, id: int):
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM reminders WHERE id = ?", (id,))
        conn.commit()
        conn.close()

class MemoryDB:
    def __init__(self):
        init_db()
    
    def set(self, key: str, value: dict):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO agent_memory (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, json.dumps(value)))
        conn.commit()
        conn.close()
    
    def get(self, key: str) -> Optional[dict]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT value FROM agent_memory WHERE key = ?", (key,))
        row = c.fetchone()
        conn.close()
        return json.loads(row['value']) if row else None

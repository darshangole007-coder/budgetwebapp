import sqlite3
from pathlib import Path

DB = Path("budget.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not DB.exists():
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income','expense')),
                amount REAL NOT NULL,
                category TEXT,
                note TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        # insert default categories
        default = ['Salary','Groceries','Eating Out','Transport','Bills','Shopping','Health','Other']
        for c in default:
            cur.execute("INSERT INTO categories (name) VALUES (?)", (c,))
        conn.commit()
        conn.close()

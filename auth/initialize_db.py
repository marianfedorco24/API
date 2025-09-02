import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "auth.db")

conn = sqlite3.connect(db_path)
c = conn.cursor()

# CREATE USERS TABLE
c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        uid INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT,
        google_id TEXT UNIQUE
    )
""")

# CREATE SESSIONS TABLE
c.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        sid TEXT PRIMARY KEY,
        uid INTEGER NOT NULL,
        expiry INTEGER NOT NULL
    )
""")

# CREATE TEMPORARY USER TABLE
c.execute("""
    CREATE TABLE IF NOT EXISTS temp_users (
        token TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        code TEXT NOT NULL,
        expiry INTEGER NOT NULL,
        attempts INTEGER  DEFAULT 0
    )
""")

conn.commit()
conn.close()

print("Auth DB initialized.")
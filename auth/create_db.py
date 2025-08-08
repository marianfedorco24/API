import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "auth.db")

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Create users table
c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        google_id TEXT UNIQUE
    )
""")

conn.commit()
conn.close()

print("Auth DB initialized.")
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "link_organizer.db")

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("""
    CREATE TABLE IF NOT EXISTS user_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pid INTEGER DEFAULT 0,
        uid INTEGER NOT NULL,
        type TEXT NOT NULL,
        icon TEXT,
        name TEXT NOT NULL,
        link TEXT,
        color TEXT
    )
""")


conn.commit()
conn.close()

print("Link Organizer DB initialized.")
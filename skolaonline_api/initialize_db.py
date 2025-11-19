import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "skolaonline_api_cache.db")

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("""
    CREATE TABLE IF NOT EXISTS cached_classes (
        timefrom INTEGER,
        timeto INTEGER,
        class_name TEXT,
        classroom TEXT
    )
""")

conn.commit()
conn.close()

print("SkolaOnline API cache DB initialized.")
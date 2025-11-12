import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "strava_api_cache.db")

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("""
    CREATE TABLE IF NOT EXISTS cached_meals (
        date TEXT PRIMARY KEY,
        meal_num TEXT NOT NULL,
        meal_name TEXT NOT NULL
    )
""")

conn.commit()
conn.close()

print("Strava API cache DB initialized.")
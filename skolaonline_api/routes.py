from flask import Blueprint, request, jsonify, current_app
from dotenv import load_dotenv
import os, sqlite3
from skolaonline_api.main import get_today_lessons
from time import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

skolaonline_api_bp = Blueprint("skolaonline_api", __name__)
load_dotenv(override=True)
EXPECTED_API_KEY = os.getenv("API_KEY")
if not EXPECTED_API_KEY:
    raise ValueError("API_KEY not found in environment variables")
db_path = os.path.join(os.path.dirname(__file__), "skolaonline_api_cache.db")

def get_db():
    conn = sqlite3.connect(db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn

def get_next_midnight_timestamp():
    now = datetime.now(ZoneInfo("Europe/Prague"))
    next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    timestamp = int(next_midnight.timestamp())
    return timestamp

def fetch_next_class_db(time_curr, c):
    c.execute("SELECT * FROM cached_classes WHERE timestamp > ? ORDER BY timestamp ASC LIMIT 1", (time_curr,))
    row = c.fetchone()
    if row:
        next_class = dict(row)
        timestamp = datetime.fromtimestamp(next_class["timestamp"], tz=ZoneInfo("Europe/Prague"))
        less_time = timestamp.strftime("%H:%M")
        if less_time == "00:00":
            less_time = "---"
        next_class["timestamp"] = less_time
        return next_class
    return None

@skolaonline_api_bp.route("/get-next-class", methods=["GET"])
def get_next_class():
    api_key = request.headers.get("x-api-key")
    if api_key != EXPECTED_API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    time_curr = time()
    conn = get_db()
    try:
        c = conn.cursor()
        next_class = fetch_next_class_db(time_curr, c)
        if next_class:
            return jsonify(next_class)
        else:
            current_app.logger.info("Cache miss - fetching new data")
            classes_new = get_today_lessons()
            classes_new.append({
                "subject": "---",
                "Učebna": "---",
                "timestamp": get_next_midnight_timestamp()
            })
            for lesson in classes_new:
                c.execute(
                    "INSERT INTO cached_classes (subject, classroom, timestamp) VALUES (?, ?, ?)",
                    (lesson["subject"], lesson["Učebna"], lesson["timestamp"])
                )
            conn.commit()
            next_class = fetch_next_class_db(time_curr, c)
            if next_class:
                return jsonify(next_class)
            else:
                return jsonify({"error": "No class data available"}), 500
            
    finally:
        conn.close()


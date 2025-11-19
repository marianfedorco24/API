from flask import Blueprint, request, jsonify, current_app
from dotenv import load_dotenv
from strava_api.main import get_today_meal, get_date
import os, sqlite3

strava_api_bp = Blueprint("strava_api", __name__)
load_dotenv()
EXPECTED_API_KEY = os.getenv("API_KEY")
if not EXPECTED_API_KEY:
    raise ValueError("API_KEY not found in environment variables")
db_path = os.path.join(os.path.dirname(__file__), "strava_api_cache.db")

def get_db():
    conn = sqlite3.connect(db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn

@strava_api_bp.route("/get-today-meal", methods=["GET"])
def get_meal():
    # API Key validation
    api_key = request.headers.get("x-api-key")
    if api_key != EXPECTED_API_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM cached_meals WHERE date = ?", (get_date(),))
        row = c.fetchone()
        if row:
            current_app.logger.info("Cache hit - returning cached meal data")
            return jsonify({
                "date": row["date"],
                "meal_num": row["meal_num"],
                "meal_name": row["meal_name"]
            })
        else:
            current_app.logger.info("Cache miss - fetching new meal data")
            meal_data = get_today_meal()
            c.execute("INSERT INTO cached_meals (date, meal_num, meal_name) VALUES (?, ?, ?)", (meal_data["date"], meal_data["meal_num"], meal_data["meal_name"]))
            conn.commit()
        return jsonify(meal_data)
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Database error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
    finally:
        conn.close()
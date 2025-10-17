from flask import Blueprint, request, jsonify, make_response, url_for, redirect, current_app, abort
import sqlite3, os, time
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from link_organizer.lorg_modules import *
from assets import global_modules

# the base url
url_base_api = "https://api.fedorco.dev"
url_base = "https://fedorco.dev"
allowed_colors = [
    "white",
    "red",
    "orange",
    "yellow",
    "green",
    "blue",
    "purple",
    "pink"
]

load_dotenv()

link_organizer_bp = Blueprint("link_organizer", __name__)

@link_organizer_bp.route("/additem", methods=["POST"])
def additem():
    # validate the session id
    session_id = request.cookies.get("session")
    if not session_id:
        return jsonify({"error": "No active session."}), 401
    
    sid_validation = global_modules.validate_session(session_id)
    if not sid_validation:
        return jsonify({"error": "Invalid or expired session!"}), 401
    data = request.get_json()
    # check if all necessary data is present
    if not data:
        return jsonify({"error": "Invalid JSON."}), 406
    
    
    
    required = [k for k in data.keys() if k != "link"]
    if any(data.get(k) in (None, "") for k in required):
        return jsonify({"error": "Some data is missing!"}), 400
    
    name = normalize_name(data["name"])
    if not name:
        return jsonify({"error": "The entered name does not meet the required format."}), 400
    # check the color
    color = data.get("color") or "white"
    color = color if color in allowed_colors else "white"

    if data["type"] not in ("link", "folder"):
        return jsonify({"error": "Invalid type."}), 400

    link = check_url(data["link"])

    if data["type"] == "link" and not link:
        return jsonify({"error": "Your link does not meet the required format"}), 400

    conn = global_modules.get_db("link_organizer")
    try:
        c = conn.cursor()
        c.execute("INSERT INTO user_items (pid, uid, type, icon, name, link, color) VALUES (?, ?, ?, ?, ?, ?, ?)", (int(data["pid"]), sid_validation, data["type"], data["icon"], name, link, color))
        conn.commit()
    except Exception as e:
        conn.rollback()
        current_app.logger.info(f"DB error occured while adding a new item: {e}")
        return jsonify({"error": "DB error occured while adding a new item."}), 500
    finally:
        conn.close()

    return jsonify({
        "message": "A new item created successfully."
    }), 201
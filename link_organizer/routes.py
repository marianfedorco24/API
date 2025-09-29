from flask import Blueprint, request, jsonify, make_response, url_for, redirect, current_app, abort
import sqlite3
import os
import bcrypt
import secrets
import time
import re
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import smtplib, ssl
from email.message import EmailMessage
from urllib.parse import urlsplit, urlunsplit
import validators
import modules

# the base url
url_base_api = "https://api.fedorco.dev"
url_base = "https://fedorco.dev"

load_dotenv()

link_organizer_bp = Blueprint("link_organizer", __name__)

# Path to SQLite database file for auth
db_path_link_organizer = os.path.join(os.path.dirname(__file__), "link_organizer.db")
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # goes from link_organizer/ to API/
db_path_auth = os.path.join(BASE_DIR, "auth", "auth.db")

def get_db(db):
    if db == "link_organizer":
        db_path = db_path_link_organizer
    else:
        db_path = db_path_auth
    conn = sqlite3.connect(db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn

def validate_session(sid):
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM sessions WHERE sid = ?", (sid,))
        session = c.fetchone()
        if not session:
            return False
        sid_expiry = session["expiry"]
        time_now = int(time.time())

        if time_now > int(sid_expiry):
            c.execute("DELETE FROM sessions WHERE sid = ?", (sid,))
            conn.commit()
            return False
        else:
            return True
    except Exception as e:
        current_app.logger.info(f"DB error: {e}")
        abort(500, description="Database error.")
    finally:
        conn.close()

@link_organizer_bp.route("/additem", methods=["POST"])
def additem():
    data = request.get_json()
    # check if all necessary data is present
    if not data:
        return jsonify({"error": "Invalid JSON."}), 406
    if not all(v not in (None, "") for k, v in data.items() if k != "link"):
        return jsonify({"error": "Some data is missing!"}), 400
    

    return data

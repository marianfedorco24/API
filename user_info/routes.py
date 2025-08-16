from flask import Blueprint, request, jsonify, make_response
import sqlite3
import os
import bcrypt
import secrets
import time

user_bp = Blueprint("user", __name__)

# Path to SQLite database file for auth
db_path = os.path.join(os.path.dirname(__file__), "..", "auth", "auth.db")
db_path = os.path.abspath(db_path)

def get_db():
    """
    Connects to the SQLite database and sets row factory to access columns by name.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@user_bp.route("/getinfo", methods=["GET"])
def getinfo():
    session_id = request.cookies.get("session")

    if not session_id:
        return jsonify({"error": "User not logged in."}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT uid FROM sessions WHERE sid = ?", (session_id,))
    user_id_obj = c.fetchone()
    if not user_id_obj:
        conn.close()
        return jsonify({"error": "Invalid session!"}), 400
    user_id = user_id_obj["uid"]
    
    c.execute("SELECT uid, email FROM users WHERE uid = ?", (user_id,))
    user_info = c.fetchone()
    conn.close()

    if not user_info:
        return jsonify({"error": "User not found."}), 404

    user_dict = dict(user_info)
    return jsonify({"user_info": user_dict}), 200
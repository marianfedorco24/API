from flask import Blueprint, request, jsonify, make_response, current_app, abort
import sqlite3
import os
import time

# set the base url
url_base = "https://api.fedorco.dev"

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

@user_bp.route("/getinfo", methods=["GET"])
def getInfo():
    session_id = request.cookies.get("session")
    if not session_id:
        return jsonify({"error": "User not logged in."}), 400
    if validate_session(session_id):
        conn = get_db()
        try:
            c = conn.cursor()
            c.execute("SELECT uid FROM sessions WHERE sid = ?", (session_id,))
            user_id_obj = c.fetchone()
            user_id = user_id_obj["uid"]
            
            c.execute("SELECT uid, email FROM users WHERE uid = ?", (user_id,))
            user_info = c.fetchone()
            if not user_info:
                return jsonify({"error": "User not found."}), 404
            user_dict = dict(user_info)
            response = make_response(jsonify(user_dict), 200)
        except Exception as e:
            current_app.logger.info(f"DB error: {e}")
            return jsonify({"error": "Database error."}), 500
        finally:
            conn.close()
    else:
        response = make_response(jsonify({"error": "Invalid session."}), 401)
        response.set_cookie(
        "session",
        "",
        httponly=True,
        # LATER SET IT TO TRUE!!!
        secure=False,
        # later set to None
        samesite="Lax",
        # LATER SET TO fedorco.dev
        # domain="127.0.0.1",
        expires=0,
        max_age=0,
        path="/"
    )
    return response
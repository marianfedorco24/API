from flask import current_app, abort
import sqlite3, time, re, os

# Path to SQLite database file for auth
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # goes from link_organizer/ to API/
db_path_link_organizer = os.path.join(BASE_DIR, "link_organizer", "link_organizer.db")
db_path_auth = os.path.join(BASE_DIR, "auth", "auth.db")

def get_db(db):
    if db == "link_organizer":
        db_path = db_path_link_organizer
    elif db == "auth":
        db_path = db_path_auth
    conn = sqlite3.connect(db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn

def validate_session(sid):
    conn = get_db("auth")
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
            return int(session["uid"])
    except Exception as e:
        current_app.logger.info(f"DB error in handling SID validation: {e}")
        abort(500, description="DB error in handling SID validation.")
    finally:
        conn.close()
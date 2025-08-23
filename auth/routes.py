from flask import Blueprint, request, jsonify, make_response
import sqlite3
import os
import bcrypt
import secrets
import time

auth_bp = Blueprint("auth", __name__)

# Path to SQLite database file for auth
db_path = os.path.join(os.path.dirname(__file__), "auth.db")

def get_db():
    """
    Connects to the SQLite database and sets row factory to access columns by name.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()

    # Validate input presence
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    conn = get_db()
    c = conn.cursor()

    # Check if email already registered
    c.execute("SELECT uid FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    if user:
        conn.close()
        return jsonify({"error": "User with this email already exists."}), 409

    # Hash password securely
    password_bytes = password.encode("utf-8")
    hashed_pw = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    hashed_pw_str = hashed_pw.decode("utf-8")

    # Insert new user record
    c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_pw_str))
    user_id = c.lastrowid

    # insert new session
    session_id = secrets.token_hex(32)

    session_lifespan_seconds = 30 * 24 * 60 * 60
    time_now = int(time.time())
    expiry = time_now + session_lifespan_seconds

    c.execute("INSERT INTO sessions (sid, uid, expiry) VALUES (?, ?, ?)", (session_id, user_id, expiry))
    conn.commit()
    conn.close()

    response = make_response(jsonify({
        "message": "Signup successful.",
        "user": {
            "uid": user_id,
            "email": email
        }
    }))
    response.set_cookie(
        "session",
        session_id,
        httponly = True,
        # WHEN DEPLOYING, SET IT TO TRUE!!!!!!!!
        secure = False,
        # later set to None
        samesite="Lax",
        # WHEN DEPLOYING, SET IT TO fedorco.dev
        # domain = "127.0.0.1",
        max_age = session_lifespan_seconds
    )

    return response

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")
    password_bytes = password.encode("utf-8")
    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    conn = get_db()
    c = conn.cursor()

    # Fetch user record by email
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "Invalid email or password."}), 401

    # Check password hash
    password_db_str = user["password"]
    password_db_bytes = password_db_str.encode("utf-8")

    # if login is successful
    if bcrypt.checkpw(password_bytes, password_db_bytes):
        session_id = secrets.token_hex(32)

        session_lifespan_seconds = 30 * 24 * 60 * 60
        time_now = int(time.time())
        expiry = time_now + session_lifespan_seconds

        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO sessions (sid, uid, expiry) VALUES (?, ?, ?)", (session_id, user["uid"], expiry))
        conn.commit()
        conn.close()

        response = make_response(jsonify({
            "message": "Login successful.",
            "user": {
                "uid": user["uid"],
                "email": user["email"]
            }
        }))
        response.set_cookie(
            "session",
            session_id,
            httponly = True,
            # WHEN DEPLOYING, SET IT TO TRUE!!!!!!!!
            secure = False,
            # later set to None
            samesite="Lax",
            # WHEN DEPLOYING, SET IT TO fedorco.dev
            # domain = "127.0.0.1",
            max_age = session_lifespan_seconds,
            path="/"
        )

        return response
    else:
        return jsonify({"error": "Invalid email or password."}), 400
    
@auth_bp.route("/logout", methods=["POST"])
def logout():
    session_id = request.cookies.get("session")

    if not session_id:
        return jsonify({"error": "No active session."}), 401

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE sid = ?", (session_id,))
    conn.commit()
    conn.close()

    response = make_response(jsonify({"message": "Logout successful."}))
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
        path="/"
    )

    return response

@auth_bp.route("/change-password", methods=["POST"])
def change_password():
    session_id = request.cookies.get("session")
    if not session_id:
        return jsonify({"error": "No active session."}), 401

    data = request.get_json()
    password_new = data.get("password_new")
    if not password_new:
        return jsonify({"error": "Password is missing."}), 400

    # Find the user from session
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT uid FROM sessions WHERE sid = ?", (session_id,))
    session_obj = c.fetchone()
    if not session_obj:
        conn.close()
        return jsonify({"error": "Invalid session."}), 401
    user_id = session_obj["uid"]

    # Hash the new password securely
    password_new_bytes = password_new.encode("utf-8")
    hashed_pw_new = bcrypt.hashpw(password_new_bytes, bcrypt.gensalt())
    hashed_pw_new_str = hashed_pw_new.decode("utf-8")

    # update the password in DB
    c.execute("UPDATE users SET password = ? WHERE uid = ?", (hashed_pw_new_str, user_id))
    conn.commit()

    # delete old sessions
    c.execute("DELETE FROM sessions where uid = ?", (user_id,))
    conn.commit()
    conn.close()

    response = make_response(jsonify({"message": "Password changed successfully. Please log in again."}))
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
        path="/"
    )

    return response

@auth_bp.route("/delete-account", methods=["POST"])
def delete_account():
    session_id = request.cookies.get("session")

    if not session_id:
        return jsonify({"error": "No active session."}), 401

    conn = get_db()
    c = conn.cursor()

    user_id_obj = c.execute("SELECT uid FROM sessions WHERE sid = ?", (session_id,)).fetchone()

    if not user_id_obj:
        conn.close()
        return jsonify({"error": "Invalid session."}), 401
    
    user_id = user_id_obj["uid"]
    user_obj = c.execute("SELECT * FROM users WHERE uid = ?", (user_id,)).fetchone()
    if not user_obj:
        conn.close()
        return jsonify({"error": "User not found."}), 404
    user_email = user_obj["email"]

    c.execute("DELETE FROM sessions WHERE uid = ?", (user_id,))
    c.execute("DELETE FROM users WHERE uid = ?", (user_id,))

    conn.commit()
    conn.close()

    response = make_response(jsonify({"message": f"Account {user_email} deleted successfully."}))
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
        path="/"
    )

    return response
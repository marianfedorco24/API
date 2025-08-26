from flask import Blueprint, request, jsonify, make_response
import sqlite3
import os
import bcrypt
import secrets
import time
import re

auth_bp = Blueprint("auth", __name__)

# Path to SQLite database file for auth
db_path = os.path.join(os.path.dirname(__file__), "auth.db")

def get_db():
    """
    Connects to the SQLite database and sets row factory to access columns by name.
    """
    conn = sqlite3.connect(db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn

def check_input(input, type):
    input_trimmed = input.strip()
    
    if type == "email":
        if len(input_trimmed) < 5:
            return False
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        return bool(re.fullmatch(email_regex, input_trimmed))
    
    else:
        password_regex = r'^[A-Za-z0-9 !@#$%^&*._-]{5,50}$'
        return bool(re.fullmatch(password_regex, input_trimmed))
    
@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON."}), 406

    # Validate input presence
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400
    
    # Validate input validity
    if not check_input(email, "email") or not check_input(password, "password"):
        return jsonify({"error": "Invalid credentials"}), 406

    conn = get_db()
    try:
        c = conn.cursor()

        # Check if email already registered
        c.execute("SELECT uid FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        if user:
            return jsonify({"error": "User with this email already exists."}), 409

        # Hash password securely
        password_bytes = password.encode("utf-8")
        hashed_pw = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        hashed_pw_str = hashed_pw.decode("utf-8")

        # Insert new user record
        c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_pw_str))
        conn.commit()
    except Exception as e:
        print(f"DB error: {e}")
        return jsonify({"error": "Database error."}), 500
    finally:
        conn.close()

    response = make_response(jsonify({
        "message": "Signup successful."
        }))
    return response

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON."}), 406

    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    remember_me = data.get("remember_me")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    # Validate input validity
    if not check_input(email, "email") or not check_input(password, "password"):
        return jsonify({"error": "Invalid credentials"}), 406

    password_bytes = password.encode("utf-8")

    conn = get_db()
    try:
        c = conn.cursor()
        # Fetch user record by email
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
    except Exception as e:
        print(f"DB error: {e}")
        return jsonify({"error": "Database error."}), 500
    finally:
        conn.close()

    if not user:
        return jsonify({"error": "Invalid email or password."}), 401

    # Check password hash
    password_db_str = user["password"]
    password_db_bytes = password_db_str.encode("utf-8")

    # if login is not successful
    if not bcrypt.checkpw(password_bytes, password_db_bytes):
        return jsonify({"error": "Invalid email or password."}), 401

    session_id = secrets.token_hex(32)

    if remember_me:
        session_lifespan_seconds = 30 * 24 * 60 * 60
    else:
        session_lifespan_seconds = 1 * 24 * 60 * 60

    time_now = int(time.time())
    expiry = time_now + session_lifespan_seconds

    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO sessions (sid, uid, expiry) VALUES (?, ?, ?)", (session_id, user["uid"], expiry))
        conn.commit()
    except Exception as e:
        print(f"DB error: {e}")
        return jsonify({"error": "Database error."}), 500
    finally:
        conn.close()

    response = make_response(jsonify({
    "message": "Login successful.",
    "remember_me": remember_me,
    "localSession": session_id
    }))
    if remember_me:
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
    else:
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
            path="/"
        )
    return response

    
@auth_bp.route("/logout", methods=["POST"])
def logout():
    session_id = request.cookies.get("session")

    if not session_id:
        return jsonify({"error": "No active session."}), 401

    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM sessions WHERE sid = ?", (session_id,))
        conn.commit()
    except Exception as e:
        print(f"DB error: {e}")
        return jsonify({"error": "Database error."}), 500
    finally:
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
    if not data:
        return jsonify({"error": "Invalid JSON."}), 406
    password_new = (data.get("password_new") or "").strip()

    if not password_new:
        return jsonify({"error": "Password is missing."}), 400

    # Validate input validity
    if not check_input(password_new, "password"):
        return jsonify({"error": "Invalid credentials"}), 406

    # Find the user from session
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("SELECT uid FROM sessions WHERE sid = ?", (session_id,))
        session_obj = c.fetchone()
        if not session_obj:
            return jsonify({"error": "Invalid session."}), 401
        user_id = session_obj["uid"]

        # Hash the new password securely
        password_new_bytes = password_new.encode("utf-8")
        hashed_pw_new = bcrypt.hashpw(password_new_bytes, bcrypt.gensalt())
        hashed_pw_new_str = hashed_pw_new.decode("utf-8")

        # update the password in DB
        c.execute("UPDATE users SET password = ? WHERE uid = ?", (hashed_pw_new_str, user_id))

        # delete old sessions
        c.execute("DELETE FROM sessions where uid = ?", (user_id,))

        conn.commit()
    except Exception as e:
        print(f"DB error: {e}")
        return jsonify({"error": "Database error."}), 500
    finally:
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
    try:
        c = conn.cursor()
        user_id_obj = c.execute("SELECT uid FROM sessions WHERE sid = ?", (session_id,)).fetchone()

        if not user_id_obj:
            return jsonify({"error": "Invalid session."}), 401
        
        user_id = user_id_obj["uid"]
        user_obj = c.execute("SELECT * FROM users WHERE uid = ?", (user_id,)).fetchone()
        if not user_obj:
            return jsonify({"error": "User not found."}), 404
        user_email = user_obj["email"]

        c.execute("DELETE FROM sessions WHERE uid = ?", (user_id,))
        c.execute("DELETE FROM users WHERE uid = ?", (user_id,))

        conn.commit()
    except Exception as e:
        print(f"DB error: {e}")
        return jsonify({"error": "Database error."}), 500
    finally:
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
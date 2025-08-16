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
    """
    Receives JSON data with "email" and "password" to register a new user.
    Returns JSON response with success or error message.
    """
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
        samesite = "None",
        # WHEN DEPLOYING, SET IT TO fedorco.dev
        domain = "127.0.0.1",
        max_age = session_lifespan_seconds
    )

    return response

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Receives JSON data with "email" and "password" to authenticate a user.
    Returns JSON with success message and a dummy token or error message.
    """
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
        return jsonify({"error": "Invalid email or password."}), 401
    
@auth_bp.route("/logout", methods=["POST"])
def logout():
    session_id = request.cookies.get("session")

    if not session_id:
        return jsonify({"error": "No active session."}), 400

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
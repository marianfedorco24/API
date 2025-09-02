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

# the base url
url_base_api = "https://api.fedorco.dev"
url_base = "https://fedorco.dev"

load_dotenv()

# email sending variables
SMTP_HOST = "smtp-relay.brevo.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = "noreply@fedorco.dev"

oauth = OAuth()

google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

def init_oauth(app):
    oauth.init_app(app)

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

        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()

        # check if the user has already signed up using email and password
        if user and user["email"] and user["password"]:
            return jsonify({"error": "User with this email already exists."}), 409
        
        # Hash password securely
        password_bytes = password.encode("utf-8")
        hashed_pw = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        hashed_pw_str = hashed_pw.decode("utf-8")

        # generate a 6-digit verification code
        code_str = f"{secrets.randbelow(1000000):06}"
        
        code_bytes = code_str.encode("utf-8")
        hashed_code = bcrypt.hashpw(code_bytes, bcrypt.gensalt())
        hashed_code_str = hashed_code.decode("utf-8")

        # generate an access token for the user (to be stored in a cookie)
        token = secrets.token_hex(16)

        # get the token expiry
        token_expiry_sec = 5 * 60
        time_now = int(time.time())
        token_expiry = time_now + token_expiry_sec

        # send a verification email
        msg = EmailMessage()
        msg["Subject"] = "Your login code"
        msg["From"] = FROM_EMAIL
        msg["To"] = email
        msg.set_content(f"<img src=\"https://fedorco.dev/logo/logo.png\" style=\"width:10rem;\"><br><p>Your one-time code is: <b>{code_str}</b> <br>(valid for 5 minutes)</p>")

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

        c.execute("INSERT INTO temp_users (token, email, password, code, expiry) VALUES (?, ?, ?, ?, ?)", (token, email, hashed_pw_str, hashed_code_str, token_expiry))
        conn.commit()

        response = make_response(jsonify({
            "message": "Email code sent."}))
        response.set_cookie(
            "temp_user_token",
            token,
            httponly = True,
            secure = True,
            samesite="None",
            domain = ".fedorco.dev",
            max_age = token_expiry_sec,
            path="/"
        )
        return response
    except Exception as e:
        current_app.logger.info(f"DB error: {e}")
        return jsonify({"error": "Database error."}), 500
    finally:
        conn.close()

@auth_bp.route("/verify-code", methods=["POST"])
def verify_code():
    data = request.get_json()
    code = (data["code"] or "").strip()

    if not code:
        return jsonify({"error": "Missing verification code."}), 400
    
    code_regex = r'^\d{6}$'
    if not re.match(code_regex, code):
        return jsonify({"error": "Verification code is in invalid format."}), 406

    token = request.cookies.get("temp_user_token")
    if not token:
        return jsonify({"error": "Temporary user token missing."}), 402
    
    conn = get_db()
    try:
        c = conn.cursor()
        # select the temporary user record
        c.execute("SELECT * FROM temp_users WHERE token = ?", (token,))
        temp_user = c.fetchone()
        # check whether the token is valid
        if not temp_user:
            return jsonify({"error": "Invalid temporary user token."}), 401
        # check whether the token is expired
        time_now = time.time()
        if time_now > temp_user["expiry"]:
            c.execute("DELETE FROM temp_users WHERE token = ?", (token))
            conn.commit()
            return jsonify({"error": "Code expired."}), 410
        # check whether the code matches
        if not bcrypt.checkpw(code.encode("utf-8"), temp_user["code"].encode("utf-8")):
            # check whether the user ran out of attempts (We already know we are gonna increment by 1, therefore we check, whether they have exceeded just two attempts - this saves us an unnecessary SQL query)
            if temp_user["attempts"] >= 2:
                c.execute("DELETE FROM temp_users WHERE token = ?", (token,))
                conn.commit()
                return jsonify({"error": "Too many attempts."}), 408
            # increment the attempt counter
            c.execute("UPDATE temp_users SET attempts = attempts + 1 WHERE token = ?", (token,))
            conn.commit()
            return jsonify({"error": "Invalid verification code."}), 403
        c.execute("SELECT * FROM users WHERE email = ?", (temp_user["email"],))
        user = c.fetchone
        # check whether the account was already signed in by google
        if user and not user["password"]:
            c.execute("UPDATE users SET password = ? WHERE uid = ?", (temp_user["password"], user["uid"]))
            conn.commit()
        # if not, create a new account
        else:
            c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (temp_user["email"], temp_user["password"]))
            conn.commit()
    except Exception as e:
        current_app.logger.info(f"DB error: {e}")
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
        current_app.logger.info(f"DB error: {e}")
        return jsonify({"error": "Database error."}), 500
    finally:
        conn.close()

    if not user or not user["password"]:
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
        current_app.logger.info(f"DB error: {e}")
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
            secure = True,
            samesite="None",
            domain = ".fedorco.dev",
            max_age = session_lifespan_seconds,
            path="/"
        )
    else:
        response.set_cookie(
            "session",
            session_id,
            httponly = True,
            secure = True,
            samesite="None",
            domain = ".fedorco.dev",
            path="/"
        )
    return response

    
@auth_bp.route("/logout", methods=["POST"])
def logout():
    session_id = request.cookies.get("session")

    if not session_id:
        return jsonify({"error": "No active session."}), 401
    
    if validate_session(session_id):
        conn = get_db()
        try:
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE sid = ?", (session_id,))
            conn.commit()
        except Exception as e:
            current_app.logger.info(f"DB error: {e}")
            return jsonify({"error": "Database error."}), 500
        finally:
            conn.close()

        response = make_response(jsonify({"message": "Logout successful."}))
    else:
        response = make_response(jsonify({"error": "Invalid session."}), 401)
    response.set_cookie(
        "session",
        "",
        httponly=True,
        secure=True,
        samesite="None",
        domain=".fedorco.dev",
        expires=0,
        max_age=0,
        path="/"
    )
    return response

@auth_bp.route("/change-password", methods=["POST"])
def change_password():
    session_id = request.cookies.get("session")
    if not session_id:
        return jsonify({"error": "No active session."}), 401
    
    if validate_session(session_id):
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
            current_app.logger.info(f"DB error: {e}")
            return jsonify({"error": "Database error."}), 500
        finally:
            conn.close()
        response = make_response(jsonify({"message": "Password changed successfully. Please log in again."}))
    else:
        response = make_response(jsonify({"error": "Invalid session."}), 401)

    response.set_cookie(
        "session",
        "",
        httponly=True,
        secure=True,
        samesite="None",
        domain=".fedorco.dev",
        expires=0,
        max_age=0,
        path="/"
    )
    return response

@auth_bp.route("/delete-account", methods=["POST"])
def delete_account():
    session_id = request.cookies.get("session")

    if not session_id:
        return jsonify({"error": "No active session."}), 401
    
    if validate_session(session_id):
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
            current_app.logger.info(f"DB error: {e}")
            return jsonify({"error": "Database error."}), 500
        finally:
            conn.close()

        response = make_response(jsonify({"message": f"Account {user_email} deleted successfully."}))
    else:
        response = make_response(jsonify({"error": "Invalid session."}), 401)

    response.set_cookie(
        "session",
        "",
        httponly=True,
        secure=True,
        samesite="None",
        domain=".fedorco.dev",
        expires=0,
        max_age=0,
        path="/"
    )
    return response

@auth_bp.route("/google/login")
def google_login():
    redirect_uri = url_for("auth.google_callback", _external=True, _scheme="https")
    return google.authorize_redirect(redirect_uri)

@auth_bp.route("/google/callback")
def google_callback():
    token = google.authorize_access_token()
    user_info = google.userinfo()

    email = user_info["email"]
    google_id = user_info["sub"]

    # Check if user already exists
    conn = get_db()
    try:
        c = conn.cursor()

        # check if user exists by google_id
        c.execute("SELECT * FROM users WHERE google_id = ?", (google_id,))
        user = c.fetchone()

        if not user:
            # check if the user exists by email
            c.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = c.fetchone()
            if user:
                # link the google_id to the existing account
                c.execute("UPDATE users SET google_id = ? WHERE email = ?", (google_id, email))
                conn.commit()
            else:
                # create a new user
                c.execute("INSERT INTO users (email, password, google_id) VALUES (?, ?, ?)", (email, None, google_id))
                conn.commit()
                c.execute("SELECT * FROM users WHERE google_id = ?", (google_id,))
                user = c.fetchone()
    finally:
        conn.close()

    # Create a session for this user
    session_id = secrets.token_hex(32)
    session_lifespan_seconds = 30 * 24 * 60 * 60
    expiry = int(time.time()) + session_lifespan_seconds  # 30 days

    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO sessions (sid, uid, expiry) VALUES (?, ?, ?)", (session_id, user["uid"], expiry))
        conn.commit()
    finally:
        conn.close()

    response = make_response(redirect(url_base + "?s=g"))

    response.set_cookie(
        "session",
        session_id,
        httponly = True,
        secure = True,
        samesite="None",
        domain=".fedorco.dev",
        max_age = session_lifespan_seconds,
        path="/"
    )
    return response
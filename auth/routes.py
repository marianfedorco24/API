from flask import Blueprint, request, jsonify
import sqlite3
import os
import bcrypt

auth_bp = Blueprint('auth', __name__)

# Path to SQLite database file for auth
db_path = os.path.join(os.path.dirname(__file__), 'auth.db')

def get_db():
    """
    Connects to the SQLite database and sets row factory to access columns by name.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """
    Receives JSON data with 'email' and 'password' to register a new user.
    Returns JSON response with success or error message.
    """
    data = request.get_json()

    # Validate input presence
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    conn = get_db()
    c = conn.cursor()

    # Check if email already registered
    c.execute('SELECT id FROM users WHERE email = ?', (email,))
    if c.fetchone():
        conn.close()
        return jsonify({'error': 'User with this email already exists.'}), 409

    # Hash password securely
    password_bytes = password.encode("utf-8")
    hashed_pw = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    hashed_pw_str = hashed_pw.decode("utf-8")

    # Insert new user record
    c.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, hashed_pw_str))
    conn.commit()
    conn.close()

    return jsonify({'message': 'User created successfully.'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Receives JSON data with 'email' and 'password' to authenticate a user.
    Returns JSON with success message and a dummy token or error message.
    """
    data = request.get_json()

    email = data.get('email')
    password = data.get('password')
    password_bytes = password.encode("utf-8")
    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    conn = get_db()
    c = conn.cursor()

    # Fetch user record by email
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'Invalid email or password.'}), 401

    # Check password hash
    password_db_str = user["password"]
    password_db_bytes = password_db_str.encode("utf-8")

    if bcrypt.checkpw(password_bytes, password_db_bytes):
        # Normally you would create and return a JWT or session token here
        # For now, return dummy token for simplicity
        dummy_token = 'your-generated-token-here'

        return jsonify({
            'message': 'Login successful.',
            'token': dummy_token,
            'user': {'id': user['id'], 'email': user['email']}
        }), 200
    else:
        return jsonify({'error': 'Invalid email or password.'}), 401
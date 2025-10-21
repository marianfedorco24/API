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
allowed_icons = [
    "biology",
    "chemistry",
    "coding",
    "cooking",
    "geography",
    "history",
    "languages",
    "default",
    "math",
    "physics",
    "socialstudies"
]

load_dotenv()

link_organizer_bp = Blueprint("link_organizer", __name__)

@link_organizer_bp.route("/add-item", methods=["POST"])
def add_item():
    # validate the session id
    session_id = request.cookies.get("session")
    if not session_id:
        return jsonify({"error": "No active session."}), 401
    sid_validation = global_modules.validate_session(session_id)
    if not sid_validation:
        return jsonify({"error": "Invalid or expired session!"}), 401
    
    # get data
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON."}), 400
    
    # check the parent id
    pid = (data.get("pid") or "0").strip()
    if not pid.isdigit():
        pid = 0

    # check the item type
    item_type = (data.get("type") or "").strip()
    if item_type not in ("link", "folder"):
        return jsonify({"error": "Invalid type."}), 400

    # check the link
    link = data.get("link") or None
    if item_type == "link":
        link = check_url(link)
        if not link:
            return jsonify({"error": "Your link does not meet the required format"}), 400
    
    # check the name
    name = normalize_name(data.get("name"))
    if not name:
        return jsonify({"error": "The entered name does not meet the required format."}), 400
    
    # check the color
    color = (data.get("color") or "white").strip()
    color = color if color in allowed_colors else "white"

    # check the icon
    icon = (data.get("icon") or "default").strip()
    icon = icon if icon in allowed_icons else "default"

    conn = global_modules.get_db("link_organizer")
    try:
        c = conn.cursor()
        c.execute("INSERT INTO user_items (pid, uid, type, icon, name, link, color) VALUES (?, ?, ?, ?, ?, ?, ?)", (int(pid), sid_validation, item_type, icon, name, link, color))
        conn.commit()
        return jsonify({"message": "A new item created successfully."}), 201
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"DB error occurred while adding a new item: {e}")
        return jsonify({"error": "DB error occurred while adding a new item."}), 500
    finally:
        conn.close()

@link_organizer_bp.route("/get-items", methods=["GET"])
def get_items():
    # # validate the session id
    # session_id = request.cookies.get("session")
    # if not session_id:
    #     return jsonify({"error": "No active session."}), 401
    # sid_validation = global_modules.validate_session(session_id)
    # if not sid_validation:
    #     return jsonify({"error": "Invalid or expired session!"}), 401
    sid_validation = "1"
    
    # get pid
    pid = request.args.get("pid", "").strip()
    pid = pid if pid.isdigit() else ""
    if not pid:
        return jsonify({"error": "Parent ID is missing."}), 400
    
    conn = global_modules.get_db("link_organizer")
    try:
        c = conn.cursor()
        c.execute("SELECT color, icon, iid, link, name, pid, type FROM user_items WHERE uid = ? AND pid = ? ", (sid_validation, pid))
        rows = c.fetchall()
        items = [dict(row) for row in rows]
        return jsonify(items)
    except Exception as e:
        current_app.logger.error(f"DB error occurred while loading items from the DB: {e}")
        return jsonify({"error": "DB error occurred while loading items from the DB."}), 500
    finally:
        conn.close()

@link_organizer_bp.route("/delete-item", methods=["DELETE"])
def delete_item():
    # validate the session id
    session_id = request.cookies.get("session")
    if not session_id:
        return jsonify({"error": "No active session."}), 401
    sid_validation = global_modules.validate_session(session_id)
    if not sid_validation:
        return jsonify({"error": "Invalid or expired session!"}), 401
    
    # get item id
    iid = request.args.get("iid", "").strip()
    iid = iid if iid.isdigit() else ""
    if not iid:
        return jsonify({"error": "Item ID is missing."}), 400
    
    conn = global_modules.get_db("link_organizer")
    try:
        c = conn.cursor()
        c.execute("DELETE FROM user_items WHERE uid = ? AND iid = ?", (sid_validation, int(iid)))
        rows_deleted = c.rowcount
        conn.commit()

        if rows_deleted == 0:
            return jsonify({"error": "Item not found or not owned by user."}), 404
        return jsonify({"message": "Item deleted successfully."}), 200
    except Exception as e:
        current_app.logger.error(f"DB error occurred while deleting an item from the DB: {e}")
        return jsonify({"error": "DB error occurred while deleting an item from the DB."}), 500
    finally:
        conn.close()

@link_organizer_bp.route("/edit-item", methods=["PATCH"])
def edit_item():
    # validate the session id
    session_id = request.cookies.get("session")
    if not session_id:
        return jsonify({"error": "No active session."}), 401
    sid_validation = global_modules.validate_session(session_id)
    if not sid_validation:
        return jsonify({"error": "Invalid or expired session!"}), 401
    
    # get iid
    iid = request.args.get("iid", "").strip()
    iid = iid if iid.isdigit() else ""
    if not iid:
        return jsonify({"error": "Item ID is missing."}), 400
    
    # get new data
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON."}), 400
    
    # check the item type
    item_type = (data.get("type") or "").strip()
    if item_type not in ("link", "folder"):
        return jsonify({"error": "Invalid type."}), 400

    # check the link
    link = data.get("link") or None
    if item_type == "link":
        link = check_url(link)
        if not link:
            return jsonify({"error": "Your link does not meet the required format"}), 400
    
    # check the name
    name = normalize_name(data.get("name"))
    if not name:
        return jsonify({"error": "The entered name does not meet the required format."}), 400
    
    # check the color
    color = (data.get("color") or "white").strip()
    color = color if color in allowed_colors else "white"

    # check the icon
    icon = (data.get("icon") or "default").strip()
    icon = icon if icon in allowed_icons else "default"

    conn = global_modules.get_db("link_organizer")
    try:
        c = conn.cursor()
        c.execute("UPDATE user_items SET icon = ?, name = ?, link = ?, color = ? where uid = ? AND iid = ?", (icon, name, link, color, sid_validation, int(iid)))
        rows_edited = c.rowcount
        conn.commit()

        if rows_edited == 0:
            return jsonify({"error": "Item not found or not owned by user."}), 404
        
        return jsonify({"message": "Item edited successfully."}), 200
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"DB error occurred while editing an item: {e}")
        return jsonify({"error": "DB error occurred while editing an item."}), 500
    finally:
        conn.close()
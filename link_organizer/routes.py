from flask import Blueprint, request, jsonify, current_app
from dotenv import load_dotenv
from link_organizer.lorg_modules import *
from assets import global_modules
from functools import wraps

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

def require_session(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = request.cookies.get("session")
        if not session_id:
            return jsonify({"messagetype": "error", "message": "No active session.", "display": False}), 401
        uid = global_modules.validate_session(session_id)
        if not uid:
            return jsonify({"messagetype": "error", "message": "Invalid or expired session.", "display": False}), 401
        return f(uid, *args, **kwargs)
    return decorated_function

@link_organizer_bp.route("/add-item", methods=["POST"])
@require_session
def add_item(uid):
    # get data
    data = request.get_json()
    if not data:
        return jsonify({
            "messagetype": "error",
            "message": "Missing JSON payload.",
            "display": False
            }), 400
    
    # check the parent id
    try:
        pid = int(data.get("pid", 0))
    except (ValueError, TypeError):
        pid = 0

    # check the item type
    item_type = (data.get("type") or "").strip()
    if item_type not in ("link", "folder"):
        return jsonify({
            "messagetype": "error",
            "message": "Invalid item type.",
            "display": False
            }), 400

    # check the link
    link = data.get("link") or None
    if item_type == "link":
        link = check_url(link)
        if not link:
            return jsonify({
            "messagetype": "error",
            "message": "Entered link does not meet the required format.",
            "display": True
            }), 400
    
    # check the name
    name = normalize_name(data.get("name"))
    if not name:
        return jsonify({
            "messagetype": "error",
            "message": "Entered name does not meet the required format.",
            "display": True
            }), 400
    
    # check the color
    color = (data.get("color") or "white").strip()
    color = color if color in allowed_colors else "white"

    # check the icon
    icon = (data.get("icon") or "default").strip()
    icon = icon if icon in allowed_icons else "default"

    conn = global_modules.get_db("link_organizer")
    try:
        c = conn.cursor()
        c.execute("INSERT INTO user_items (pid, uid, type, icon, name, link, color) VALUES (?, ?, ?, ?, ?, ?, ?)", (int(pid), uid, item_type, icon, name, link, color))
        conn.commit()
        return jsonify({
            "messagetype": "success",
            "message": "New item created successfully.",
            "display": True
            }), 201
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"DB error occurred while adding a new item: {e}")
        return jsonify({
            "messagetype": "error",
            "message": "A database error occurred.",
            "display": True
            }), 500
    finally:
        conn.close()

@link_organizer_bp.route("/get-items", methods=["GET"])
@require_session
def get_items(uid):
    # get pid
    pid = request.args.get("pid", "").strip()
    pid = pid if pid.isdigit() else ""
    if not pid:
        return jsonify({
            "messagetype": "error",
            "message": "Parent ID is missing.",
            "display": False
            }), 400
    
    conn = global_modules.get_db("link_organizer")
    try:
        c = conn.cursor()
        c.execute("SELECT color, icon, iid, link, name, pid, type FROM user_items WHERE uid = ? AND pid = ? ", (uid, pid))
        rows = c.fetchall()
        items = [dict(row) for row in rows]
        return jsonify(items)
    except Exception as e:
        current_app.logger.error(f"DB error occurred while loading items from the DB: {e}")
        return jsonify({
            "messagetype": "error",
            "message": "A database error occurred.",
            "display": True
            }), 500
    finally:
        conn.close()

@link_organizer_bp.route("/delete-item", methods=["DELETE"])
@require_session
def delete_item(uid):
    # get item id
    iid = request.args.get("iid", "").strip()
    iid = iid if iid.isdigit() else ""
    if not iid:
        return jsonify({
            "messagetype": "error",
            "message": "Item ID is missing.",
            "display": False
            }), 400
    
    conn = global_modules.get_db("link_organizer")
    try:
        c = conn.cursor()
        c.execute("DELETE FROM user_items WHERE uid = ? AND iid = ?", (uid, int(iid)))
        rows_deleted = c.rowcount
        conn.commit()

        if rows_deleted == 0:
            return jsonify({
            "messagetype": "error",
            "message": "Item not found.",
            "display": True
            }), 404
        return jsonify({
            "messagetype": "success",
            "message": "Item deleted succesfully.",
            "display": True
            }), 200
    except Exception as e:
        current_app.logger.error(f"DB error occurred while deleting an item from the DB: {e}")
        return jsonify({
            "messagetype": "error",
            "message": "A database error occurred.",
            "display": True
            }), 500
    finally:
        conn.close()

@link_organizer_bp.route("/edit-item", methods=["PATCH"])
@require_session
def edit_item(uid):
    # get iid
    iid = request.args.get("iid", "").strip()
    iid = iid if iid.isdigit() else ""
    if not iid:
        return jsonify({
            "messagetype": "error",
            "message": "Item ID is missing.",
            "display": False
            }), 400
    
    # get new data
    data = request.get_json()
    if not data:
        return jsonify({
            "messagetype": "error",
            "message": "Missing JSON payload.",
            "display": False
            }), 400
    
    # check the item type
    item_type = (data.get("type") or "").strip()
    if item_type not in ("link", "folder"):
        return jsonify({
            "messagetype": "error",
            "message": "Invalid item type.",
            "display": False
            }), 400

    # check the link
    link = data.get("link") or None
    if item_type == "link":
        link = check_url(link)
        if not link:
            return jsonify({
            "messagetype": "error",
            "message": "Entered link does not meet the required format.",
            "display": True
            }), 400
    
    # check the name
    name = normalize_name(data.get("name"))
    if not name:
        return jsonify({
            "messagetype": "error",
            "message": "Entered name does not meet the required format.",
            "display": True
            }), 400
    
    # check the color
    color = (data.get("color") or "white").strip()
    color = color if color in allowed_colors else "white"

    # check the icon
    icon = (data.get("icon") or "default").strip()
    icon = icon if icon in allowed_icons else "default"

    conn = global_modules.get_db("link_organizer")
    try:
        c = conn.cursor()
        c.execute("UPDATE user_items SET icon = ?, name = ?, link = ?, color = ? where uid = ? AND iid = ?", (icon, name, link, color, uid, int(iid)))
        rows_edited = c.rowcount
        conn.commit()

        if rows_edited == 0:
            return jsonify({
            "messagetype": "error",
            "message": "Item not found.",
            "display": True
            }), 404
        
        return jsonify({
            "messagetype": "success",
            "message": "Item edited successfully.",
            "display": True
            }), 200
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"DB error occurred while editing an item: {e}")
        return jsonify({
            "messagetype": "error",
            "message": "A database error occurred.",
            "display": True
            }), 500
    finally:
        conn.close()
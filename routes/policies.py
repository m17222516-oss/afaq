from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from database.db import get_db
from routes.auth import log_action, login_required, role_required

policies_bp = Blueprint("policies", __name__, url_prefix="/policies")


@policies_bp.route("/api/policies", methods=["GET"])  # Note: /api/policies, not /api
@login_required
def api_list():
    """JSON endpoint for the slide panel"""
    db = get_db()
    role = session.get("role")
    dept_id = session.get("department_id")

    if role == "superadmin":
        items = db.execute(
            "SELECT p.*, d.name_ar as dept_name, u.full_name as author FROM policies p JOIN departments d ON p.department_id=d.id JOIN users u ON p.created_by=u.id ORDER BY p.department_id, p.created_at DESC"
        ).fetchall()
    else:
        items = db.execute(
            "SELECT p.*, d.name_ar as dept_name, u.full_name as author FROM policies p JOIN departments d ON p.department_id=d.id JOIN users u ON p.created_by=u.id WHERE p.department_id=? ORDER BY p.created_at DESC",
            (dept_id,),
        ).fetchall()

    db.close()
    return jsonify([dict(i) for i in items])


@policies_bp.route("/create", methods=["POST"])  # Note: /create, not /policies/create
@login_required
@role_required("superadmin", "manager")
def create():
    """Create policy via AJAX from slide panel"""
    db = get_db()
    role = session.get("role")

    data = request.get_json()
    title = data.get("title", "").strip()
    body = data.get("body", "").strip()
    dept_id = int(data.get("department_id", session.get("department_id", 0)))

    if role == "manager" and dept_id != session.get("department_id"):
        return jsonify(
            {"success": False, "error": "لا يمكنك إضافة سياسة لقسم آخر"}
        ), 403

    if not title or not body:
        return jsonify({"success": False, "error": "يرجى ملء جميع الحقول"}), 400

    try:
        cursor = db.execute(
            "INSERT INTO policies (title, body, department_id, created_by) VALUES (?,?,?,?)",
            (title, body, dept_id, session["user_id"]),
        )
        db.commit()
        log_action(session["user_id"], "create_policy", f"سياسة: {title}")

        new_policy = db.execute(
            "SELECT p.*, d.name_ar as dept_name, u.full_name as author FROM policies p JOIN departments d ON p.department_id=d.id JOIN users u ON p.created_by=u.id WHERE p.id=?",
            (cursor.lastrowid,),
        ).fetchone()

        db.close()
        return jsonify({"success": True, "policy": dict(new_policy)}), 200
    except Exception as e:
        db.close()
        return jsonify({"success": False, "error": str(e)}), 500


@policies_bp.route("/<int:policy_id>/update", methods=["POST"])
@login_required
@role_required("superadmin", "manager")
def update(policy_id):
    """Update an existing policy"""
    db = get_db()
    role = session.get("role")

    # Check if policy exists
    policy = db.execute("SELECT * FROM policies WHERE id=?", (policy_id,)).fetchone()
    if not policy:
        return jsonify({"success": False, "error": "السياسة غير موجودة"}), 404

    # Check permissions
    if role != "superadmin" and policy["department_id"] != session.get("department_id"):
        return jsonify(
            {"success": False, "error": "لا يمكنك تعديل سياسة من قسم آخر"}
        ), 403

    try:
        data = request.get_json()
        title = data.get("title", "").strip()
        body = data.get("body", "").strip()

        if not title or not body:
            return jsonify({"success": False, "error": "يرجى ملء جميع الحقول"}), 400

        # Only superadmin can change department
        if role == "superadmin" and "department_id" in data:
            dept_id = int(data.get("department_id"))
        else:
            dept_id = policy["department_id"]

        db.execute(
            "UPDATE policies SET title=?, body=?, department_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (title, body, dept_id, policy_id),
        )
        db.commit()

        log_action(
            session["user_id"], "update_policy", f"سياسة: {title} (ID: {policy_id})"
        )

        db.close()
        return jsonify({"success": True}), 200

    except Exception as e:
        db.close()
        return jsonify({"success": False, "error": str(e)}), 500


@policies_bp.route("/<int:policy_id>/delete", methods=["POST"])
@login_required
@role_required("superadmin", "manager")
def delete(policy_id):
    """Delete policy via AJAX"""
    db = get_db()
    policy = db.execute("SELECT * FROM policies WHERE id=?", (policy_id,)).fetchone()

    if not policy:
        db.close()
        return jsonify({"success": False, "error": "السياسة غير موجودة"}), 404

    if session["role"] != "superadmin" and policy["department_id"] != session.get(
        "department_id"
    ):
        db.close()
        return jsonify(
            {"success": False, "error": "لا يمكنك حذف سياسة من قسم آخر"}
        ), 403

    try:
        db.execute("DELETE FROM policies WHERE id=?", (policy_id,))
        db.commit()
        log_action(session["user_id"], "delete_policy", f"سياسة ID: {policy_id}")
        db.close()
        return jsonify({"success": True}), 200
    except Exception as e:
        db.close()
        return jsonify({"success": False, "error": str(e)}), 500

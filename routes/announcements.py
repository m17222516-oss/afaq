import os
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from PIL import Image
from werkzeug.utils import secure_filename

from database.db import get_db
from routes.auth import log_action, login_required, role_required

announcements_bp = Blueprint("announcements", __name__)

# ============================================================
# IMAGE UPLOAD CONFIGURATION
# ============================================================
UPLOAD_FOLDER = "static/uploads/announcements"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB per image

# Create upload folder if not exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_image(image_file):
    """Validate image file size and type using PIL"""
    # Check file size
    image_file.seek(0, os.SEEK_END)
    file_size = image_file.tell()
    image_file.seek(0)

    if file_size > MAX_FILE_SIZE:
        return (
            False,
            f"حجم الصورة كبير جداً. الحد الأقصى هو {MAX_FILE_SIZE // (1024 * 1024)} ميجابايت",
        )

    # Check if it's a valid image using PIL
    try:
        img = Image.open(image_file)
        img.verify()  # Verify image integrity
        image_file.seek(0)  # Reset file pointer after verify
        return True, None
    except Exception:
        return False, "الملف ليس صورة صالحة"


# ============================================================
# ANNOUNCEMENTS ROUTES
# ============================================================


@announcements_bp.route("/announcements")
@login_required
def index():
    db = get_db()
    role = session.get("role")
    dept_id = session.get("department_id")
    priority_filter = request.args.get("priority", "")
    search = request.args.get("q", "").strip()

    base = """SELECT a.*, d.name_ar as dept_name, d.color as dept_color,
              u.full_name as author,
              (SELECT COUNT(*) FROM comments c WHERE c.announcement_id=a.id) as comment_count
              FROM announcements a
              JOIN departments d ON a.department_id=d.id
              JOIN users u ON a.created_by=u.id"""

    where, params = [], []
    if role != "superadmin":
        where.append("a.department_id=?")
        params.append(dept_id)
    if priority_filter:
        where.append("a.priority=?")
        params.append(priority_filter)
    if search:
        where.append("(a.title LIKE ? OR a.body LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]

    if where:
        base += " WHERE " + " AND ".join(where)
    base += " ORDER BY a.is_pinned DESC, a.created_at DESC"

    items = db.execute(base, params).fetchall()

    # Stats
    if role == "superadmin":
        total = db.execute("SELECT COUNT(*) as c FROM announcements").fetchone()["c"]
        urgent = db.execute(
            "SELECT COUNT(*) as c FROM announcements WHERE priority='urgent'"
        ).fetchone()["c"]
        pinned = db.execute(
            "SELECT COUNT(*) as c FROM announcements WHERE is_pinned=1"
        ).fetchone()["c"]
    else:
        total = db.execute(
            "SELECT COUNT(*) as c FROM announcements WHERE department_id=?", (dept_id,)
        ).fetchone()["c"]
        urgent = db.execute(
            "SELECT COUNT(*) as c FROM announcements WHERE department_id=? AND priority='urgent'",
            (dept_id,),
        ).fetchone()["c"]
        pinned = db.execute(
            "SELECT COUNT(*) as c FROM announcements WHERE department_id=? AND is_pinned=1",
            (dept_id,),
        ).fetchone()["c"]

    departments = (
        db.execute("SELECT * FROM departments").fetchall()
        if role == "superadmin"
        else []
    )
    db.close()
    return render_template(
        "announcements/index.html",
        items=items,
        total=total,
        urgent=urgent,
        pinned=pinned,
        departments=departments,
        priority_filter=priority_filter,
        search=search,
    )


@announcements_bp.route("/announcements/<int:ann_id>")
@login_required
def detail(ann_id):
    db = get_db()
    role = session.get("role")
    dept_id = session.get("department_id")

    ann = db.execute(
        "SELECT a.*, d.name_ar as dept_name, d.color as dept_color, u.full_name as author FROM announcements a JOIN departments d ON a.department_id=d.id JOIN users u ON a.created_by=u.id WHERE a.id=?",
        (ann_id,),
    ).fetchone()

    if not ann:
        flash("التبليغ غير موجود", "danger")
        return redirect(url_for("announcements.index"))
    if role != "superadmin" and ann["department_id"] != dept_id:
        flash("ليس لديك صلاحية لعرض هذا التبليغ", "danger")
        return redirect(url_for("announcements.index"))

    comments = db.execute(
        "SELECT c.*, u.full_name, u.role FROM comments c JOIN users u ON c.user_id=u.id WHERE c.announcement_id=? ORDER BY c.created_at ASC",
        (ann_id,),
    ).fetchall()

    reaction_count = db.execute(
        "SELECT COUNT(*) as c FROM reactions WHERE announcement_id=?", (ann_id,)
    ).fetchone()["c"]
    user_reacted = db.execute(
        "SELECT id FROM reactions WHERE announcement_id=? AND user_id=?",
        (ann_id, session["user_id"]),
    ).fetchone() is not None

    db.close()
    return render_template(
        "announcements/detail.html",
        ann=ann,
        comments=comments,
        reaction_count=reaction_count,
        user_reacted=user_reacted,
    )


@announcements_bp.route("/announcements/create", methods=["GET", "POST"])
@login_required
@role_required("superadmin", "manager")
def create():
    db = get_db()
    role = session.get("role")

    departments = (
        db.execute("SELECT * FROM departments").fetchall()
        if role == "superadmin"
        else db.execute(
            "SELECT * FROM departments WHERE id=?", (session.get("department_id"),)
        ).fetchall()
    )

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        # IMPORTANT: Don't strip or escape HTML from the body
        body = request.form.get("body", "")  # Remove .strip() to preserve HTML
        priority = request.form.get("priority", "normal")
        dept_value = request.form.get("department_id")
        is_pinned = 1 if request.form.get("is_pinned") else 0

        send_to_all = dept_value == "all" and role == "superadmin"

        if not send_to_all:
            if dept_value is None or dept_value == "":
                flash("يرجى اختيار القسم", "danger")
                db.close()
                return render_template(
                    "announcements/create.html", departments=departments
                )
            dept_id = int(dept_value)
            if role == "manager" and dept_id != session.get("department_id"):
                flash("لا يمكنك النشر في قسم آخر", "danger")
                db.close()
                return redirect(url_for("announcements.create"))

        if title and body:
            if send_to_all:
                all_depts = db.execute("SELECT id FROM departments").fetchall()
                for d in all_depts:
                    db.execute(
                        "INSERT INTO announcements (title,body,priority,department_id,created_by,is_pinned) VALUES (?,?,?,?,?,?)",
                        (title, body, priority, d["id"], session["user_id"], is_pinned),
                    )
                db.commit()
                log_action(
                    session["user_id"],
                    "create_announcement",
                    f"{title} (جميع الأقسام)",
                )
                flash("تم نشر التبليغ لجميع الأقسام والدوائر بنجاح ✓", "success")
            else:
                db.execute(
                    "INSERT INTO announcements (title,body,priority,department_id,created_by,is_pinned) VALUES (?,?,?,?,?,?)",
                    (title, body, priority, dept_id, session["user_id"], is_pinned),
                )
                db.commit()
                log_action(session["user_id"], "create_announcement", title)
                flash("تم نشر التبليغ بنجاح ✓", "success")
            db.close()
            return redirect(url_for("announcements.index"))
        flash("يرجى ملء جميع الحقول", "danger")

    db.close()
    return render_template("announcements/create.html", departments=departments)


@announcements_bp.route("/announcements/<int:ann_id>/react", methods=["POST"])
@login_required
def react(ann_id):
    """Toggle a like reaction on an announcement"""
    db = get_db()
    role = session.get("role")
    dept_id = session.get("department_id")

    ann = db.execute("SELECT * FROM announcements WHERE id=?", (ann_id,)).fetchone()
    if not ann or (role != "superadmin" and ann["department_id"] != dept_id):
        db.close()
        return jsonify({"success": False, "error": "غير مصرح"}), 403

    existing = db.execute(
        "SELECT id FROM reactions WHERE announcement_id=? AND user_id=?",
        (ann_id, session["user_id"]),
    ).fetchone()

    if existing:
        db.execute("DELETE FROM reactions WHERE id=?", (existing["id"],))
        db.commit()
        liked = False
    else:
        db.execute(
            "INSERT INTO reactions (announcement_id, user_id, reaction_type) VALUES (?,?,?)",
            (ann_id, session["user_id"], "like"),
        )
        db.commit()
        liked = True
        log_action(session["user_id"], "react_announcement", f"#{ann_id}")

    count = db.execute(
        "SELECT COUNT(*) as c FROM reactions WHERE announcement_id=?", (ann_id,)
    ).fetchone()["c"]
    db.close()
    return jsonify({"success": True, "liked": liked, "count": count})


@announcements_bp.route("/announcements/<int:ann_id>/comment", methods=["POST"])
@login_required
def add_comment(ann_id):
    db = get_db()
    ann = db.execute("SELECT * FROM announcements WHERE id=?", (ann_id,)).fetchone()
    if not ann or (
        session.get("role") != "superadmin"
        and ann["department_id"] != session.get("department_id")
    ):
        db.close()
        flash("غير مصرح", "danger")
        return redirect(url_for("announcements.index"))

    body = request.form.get("body", "").strip()
    if body:
        db.execute(
            "INSERT INTO comments (announcement_id,user_id,body) VALUES (?,?,?)",
            (ann_id, session["user_id"], body),
        )
        db.commit()
        log_action(session["user_id"], "comment", f"#{ann_id}")
    db.close()
    return redirect(url_for("announcements.detail", ann_id=ann_id))


@announcements_bp.route("/announcements/<int:ann_id>/delete", methods=["POST"])
@login_required
@role_required("superadmin", "manager")
def delete(ann_id):
    db = get_db()
    ann = db.execute("SELECT * FROM announcements WHERE id=?", (ann_id,)).fetchone()
    if ann and (
        session["role"] == "superadmin"
        or ann["department_id"] == session.get("department_id")
    ):
        db.execute("DELETE FROM comments WHERE announcement_id=?", (ann_id,))
        db.execute("DELETE FROM announcements WHERE id=?", (ann_id,))
        db.commit()
        log_action(session["user_id"], "delete_announcement", f"#{ann_id}")
        flash("تم حذف التبليغ", "success")
    db.close()
    return redirect(url_for("announcements.index"))


@announcements_bp.route("/announcements/<int:ann_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("superadmin", "manager")
def edit(ann_id):
    db = get_db()
    role = session.get("role")
    ann = db.execute("SELECT * FROM announcements WHERE id=?", (ann_id,)).fetchone()

    if not ann:
        flash("التبليغ غير موجود", "danger")
        db.close()
        return redirect(url_for("announcements.index"))

    if role != "superadmin" and ann["department_id"] != session.get("department_id"):
        flash("ليس لديك صلاحية لتعديل هذا التبليغ", "danger")
        db.close()
        return redirect(url_for("announcements.index"))

    departments = (
        db.execute("SELECT * FROM departments").fetchall()
        if role == "superadmin"
        else db.execute(
            "SELECT * FROM departments WHERE id=?", (session.get("department_id"),)
        ).fetchall()
    )

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        priority = request.form.get("priority", "normal")
        dept_id = int(request.form.get("department_id", ann["department_id"]))
        is_pinned = 1 if request.form.get("is_pinned") else 0

        if title and body:
            db.execute(
                "UPDATE announcements SET title=?,body=?,priority=?,department_id=?,is_pinned=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (title, body, priority, dept_id, is_pinned, ann_id),
            )
            db.commit()
            log_action(
                session["user_id"], "edit_announcement", f"تبليغ #{ann_id}: {title}"
            )
            flash("تم تعديل التبليغ بنجاح ✓", "success")
            db.close()
            return redirect(url_for("announcements.detail", ann_id=ann_id))
        flash("يرجى ملء جميع الحقول", "danger")

    db.close()
    return render_template("announcements/edit.html", ann=ann, departments=departments)


@announcements_bp.route("/comment/delete/<int:comment_id>", methods=["POST"])
@login_required
def delete_comment(comment_id):
    """Delete a comment"""
    conn = get_db()
    cursor = conn.cursor()

    # Get comment info with user_id to check permissions
    cursor.execute(
        """
        SELECT c.*, u.role as commenter_role
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.id = ?
    """,
        (comment_id,),
    )
    comment = cursor.fetchone()

    if not comment:
        flash("التعليق غير موجود", "danger")
        return redirect(url_for("announcements.index"))

    announcement_id = comment["announcement_id"]

    # Check permissions: user owns the comment OR is manager/superadmin
    can_delete = False

    if session["role"] in ["manager", "superadmin"]:
        can_delete = True
    elif session["user_id"] == comment["user_id"]:
        can_delete = True

    if can_delete:
        cursor.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        conn.commit()
        flash("تم حذف التعليق بنجاح", "success")
        log_action(session["user_id"], "delete_comment", f"تعليق #{comment_id}")
    else:
        flash("ليس لديك صلاحية لحذف هذا التعليق", "danger")

    conn.close()
    return redirect(url_for("announcements.detail", ann_id=announcement_id))


# ============================================================
# IMAGE UPLOAD ROUTES
# ============================================================


@announcements_bp.route("/upload-image", methods=["POST"])
@login_required
def upload_image():
    """Upload an image for announcement with proper validation"""
    try:
        # Check if file exists
        if "image" not in request.files:
            return jsonify({"success": False, "error": "لا يوجد ملف صورة"}), 400

        file = request.files["image"]

        # Check if filename is empty
        if file.filename == "":
            return jsonify({"success": False, "error": "لم يتم اختيار ملف"}), 400

        # Validate file extension
        if not allowed_file(file.filename):
            return jsonify(
                {
                    "success": False,
                    "error": "نوع الملف غير مدعوم. الاستخدام: PNG, JPG, JPEG, GIF, WEBP",
                }
            ), 400

        # Validate image content and size using PIL
        is_valid, error_message = validate_image(file)
        if not is_valid:
            return jsonify({"success": False, "error": error_message}), 400

        # Generate secure filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = secure_filename(f"{timestamp}_{file.filename}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Save file
        file.save(filepath)

        # Get file size for logging
        file_size = os.path.getsize(filepath)

        # Log upload
        log_action(
            session["user_id"], "upload_image", f"{filename} ({file_size} bytes)"
        )

        # Return URL for the image
        image_url = url_for("static", filename=f"uploads/announcements/{filename}")

        return jsonify(
            {"success": True, "url": image_url, "filename": filename, "size": file_size}
        )

    except Exception as e:
        return jsonify({"success": False, "error": f"حدث خطأ: {str(e)}"}), 500


@announcements_bp.route("/delete-uploaded-image", methods=["POST"])
@login_required
def delete_uploaded_image():
    """Delete an uploaded image that hasn't been used"""
    try:
        data = request.get_json()
        filename = data.get("filename")

        if not filename:
            return jsonify({"success": False, "error": "No filename provided"}), 400

        # Security: ensure filename is safe and in the upload folder
        if ".." in filename or filename.startswith("/"):
            return jsonify({"success": False, "error": "Invalid filename"}), 400

        filepath = os.path.join(UPLOAD_FOLDER, filename)

        if os.path.exists(filepath):
            os.remove(filepath)
            log_action(session["user_id"], "delete_uploaded_image", filename)
            return jsonify({"success": True})

        return jsonify({"success": False, "error": "File not found"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

        @announcements_bp.route("/debug-announcement/<int:ann_id>")
        @login_required
        def debug_announcement(ann_id):
            """Debug route to see raw database content"""
            db = get_db()
            ann = db.execute(
                "SELECT * FROM announcements WHERE id=?", (ann_id,)
            ).fetchone()
            db.close()

            if not ann:
                return "Announcement not found", 404

            # Create a debug page
            debug_html = f"""
            <!DOCTYPE html>
            <html dir="ltr">
            <head>
                <title>Debug Announcement #{ann_id}</title>
                <style>
                    body {{ font-family: monospace; padding: 20px; background: #f5f5f5; }}
                    .section {{ background: white; margin: 20px 0; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    h3 {{ margin-top: 0; color: #333; }}
                    pre {{ background: #f0f0f0; padding: 10px; overflow-x: auto; border-radius: 4px; }}
                    .raw {{ font-family: monospace; white-space: pre-wrap; word-wrap: break-word; }}
                    .rendered {{ border: 1px solid #ddd; padding: 10px; }}
                </style>
            </head>
            <body>
                <h1>Debug Announcement #{ann_id}</h1>

                <div class="section">
                    <h3>📝 Basic Info</h3>
                    <p><strong>Title:</strong> {ann["title"]}</p>
                    <p><strong>Priority:</strong> {ann["priority"]}</p>
                    <p><strong>Department ID:</strong> {ann["department_id"]}</p>
                    <p><strong>Created By:</strong> {ann["created_by"]}</p>
                    <p><strong>Created At:</strong> {ann["created_at"]}</p>
                    <p><strong>Is Pinned:</strong> {ann["is_pinned"]}</p>
                </div>

                <div class="section">
                    <h3>🔍 RAW BODY (What's actually in the database)</h3>
                    <pre class="raw">{ann["body"]}</pre>
                </div>

                <div class="section">
                    <h3>🔧 HTML ENTITIES DECODED</h3>
                    <pre class="raw">{__import__("html").unescape(ann["body"]) if ann["body"] else ""}</pre>
                </div>

                <div class="section">
                    <h3>👁️ RENDERED WITH |safe (What it should look like)</h3>
                    <div class="rendered">
                        {ann["body"] | safe if ann["body"] else ""}
                    </div>
                </div>

                <div class="section">
                    <h3>📊 Body Statistics</h3>
                    <p><strong>Length:</strong> {len(ann["body"]) if ann["body"] else 0} characters</p>
                    <p><strong>Contains &amp;lt;:</strong> {"Yes" if ann["body"] and "&lt;" in ann["body"] else "No"}</p>
                    <p><strong>Contains &amp;gt;:</strong> {"Yes" if ann["body"] and "&gt;" in ann["body"] else "No"}</p>
                    <p><strong>Contains &amp;amp;:</strong> {"Yes" if ann["body"] and "&amp;" in ann["body"] else "No"}</p>
                    <p><strong>Contains &amp;quot;:</strong> {"Yes" if ann["body"] and "&quot;" in ann["body"] else "No"}</p>
                </div>

                <div class="section">
                    <h3>🛠️ Quick Fix Options</h3>
                    <form method="POST" action="/debug-fix/{ann_id}">
                        <button type="submit" name="action" value="unescape" style="padding: 10px 20px; margin: 5px; cursor: pointer;">
                            🔧 Decode HTML Entities
                        </button>
                        <button type="submit" name="action" value="clear" style="padding: 10px 20px; margin: 5px; cursor: pointer; background: #dc3545; color: white;">
                            🗑️ Clear Body (Set to empty)
                        </button>
                    </form>
                </div>

                <div class="section">
                    <h3>🔗 Links</h3>
                    <p><a href="{url_for("announcements.detail", ann_id=ann_id)}">View Normal Detail Page</a></p>
                    <p><a href="{url_for("announcements.edit", ann_id=ann_id)}">Edit Announcement</a></p>
                </div>
            </body>
            </html>
            """
            return debug_html

        @announcements_bp.route("/debug-fix/<int:ann_id>", methods=["POST"])
        @login_required
        def debug_fix(ann_id):
            """Fix corrupted announcement data"""
            import html

            db = get_db()
            action = request.form.get("action")

            if action == "unescape":
                # Decode HTML entities
                ann = db.execute(
                    "SELECT body FROM announcements WHERE id=?", (ann_id,)
                ).fetchone()
                if ann and ann["body"]:
                    fixed_body = html.unescape(ann["body"])
                    db.execute(
                        "UPDATE announcements SET body = ? WHERE id = ?",
                        (fixed_body, ann_id),
                    )
                    db.commit()
                    flash("✅ تم فك تشفير HTML entities بنجاح!", "success")

            elif action == "clear":
                db.execute("UPDATE announcements SET body = '' WHERE id = ?", (ann_id,))
                db.commit()
                flash("🗑️ تم مسح محتوى التبليغ", "warning")

            db.close()
            return redirect(url_for("announcements.debug_announcement", ann_id=ann_id))

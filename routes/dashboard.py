from flask import Blueprint, render_template, session
from database.db import get_db
from routes.auth import login_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    db   = get_db()
    role = session.get('role')
    dept = session.get('department_id')

    if role == 'superadmin':
        announcements = db.execute(
            "SELECT a.*, d.name_ar as dept_name, u.full_name as author FROM announcements a JOIN departments d ON a.department_id=d.id JOIN users u ON a.created_by=u.id ORDER BY a.is_pinned DESC, a.created_at DESC LIMIT 8"
        ).fetchall()
        stats = {
            'users':         db.execute("SELECT COUNT(*) as c FROM users WHERE role!='superadmin'").fetchone()['c'],
            'depts':         db.execute("SELECT COUNT(*) as c FROM departments").fetchone()['c'],
            'announcements': db.execute("SELECT COUNT(*) as c FROM announcements").fetchone()['c'],
            'urgent':        db.execute("SELECT COUNT(*) as c FROM announcements WHERE priority='urgent'").fetchone()['c'],
            'policies':      db.execute("SELECT COUNT(*) as c FROM policies").fetchone()['c'],
        }
    else:
        announcements = db.execute(
            "SELECT a.*, d.name_ar as dept_name, u.full_name as author FROM announcements a JOIN departments d ON a.department_id=d.id JOIN users u ON a.created_by=u.id WHERE a.department_id=? ORDER BY a.is_pinned DESC, a.created_at DESC LIMIT 8",
            (dept,)
        ).fetchall()
        stats = {
            'announcements': db.execute("SELECT COUNT(*) as c FROM announcements WHERE department_id=?", (dept,)).fetchone()['c'],
            'urgent':        db.execute("SELECT COUNT(*) as c FROM announcements WHERE department_id=? AND priority='urgent'", (dept,)).fetchone()['c'],
            'policies':      db.execute("SELECT COUNT(*) as c FROM policies WHERE department_id=?", (dept,)).fetchone()['c'],
        }

    db.close()
    return render_template('dashboard.html', announcements=announcements, stats=stats)

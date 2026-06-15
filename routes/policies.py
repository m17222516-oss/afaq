from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database.db import get_db
from routes.auth import login_required, role_required, log_action

policies_bp = Blueprint('policies', __name__)

@policies_bp.route('/api/policies')
@login_required
def api_list():
    """JSON endpoint for the slide panel"""
    db = get_db()
    role = session.get('role')
    dept_id = session.get('department_id')

    if role == 'superadmin':
        items = db.execute(
            "SELECT p.*, d.name_ar as dept_name, u.full_name as author FROM policies p JOIN departments d ON p.department_id=d.id JOIN users u ON p.created_by=u.id ORDER BY p.department_id, p.created_at DESC"
        ).fetchall()
    else:
        items = db.execute(
            "SELECT p.*, d.name_ar as dept_name, u.full_name as author FROM policies p JOIN departments d ON p.department_id=d.id JOIN users u ON p.created_by=u.id WHERE p.department_id=? ORDER BY p.created_at DESC",
            (dept_id,)
        ).fetchall()

    db.close()
    return jsonify([dict(i) for i in items])


@policies_bp.route('/policies/create', methods=['GET', 'POST'])
@login_required
@role_required('superadmin', 'manager')
def create():
    db = get_db()
    role = session.get('role')
    if role == 'superadmin':
        departments = db.execute("SELECT * FROM departments").fetchall()
    else:
        departments = db.execute("SELECT * FROM departments WHERE id=?", (session.get('department_id'),)).fetchall()

    if request.method == 'POST':
        title   = request.form.get('title', '').strip()
        body    = request.form.get('body', '').strip()
        dept_id = int(request.form.get('department_id', session.get('department_id', 0)))

        if role == 'manager' and dept_id != session.get('department_id'):
            flash('لا يمكنك إضافة سياسة لقسم آخر', 'danger')
        elif title and body:
            db.execute("INSERT INTO policies (title, body, department_id, created_by) VALUES (?,?,?,?)",
                       (title, body, dept_id, session['user_id']))
            db.commit()
            log_action(session['user_id'], 'create_policy', f'سياسة: {title}')
            flash('تم إضافة السياسة بنجاح ✓', 'success')
            db.close()
            return redirect(url_for('announcements.index'))
        else:
            flash('يرجى ملء جميع الحقول', 'danger')

    db.close()
    return render_template('policies/create.html', departments=departments)


@policies_bp.route('/policies/<int:policy_id>/delete', methods=['POST'])
@login_required
@role_required('superadmin', 'manager')
def delete(policy_id):
    db = get_db()
    policy = db.execute("SELECT * FROM policies WHERE id=?", (policy_id,)).fetchone()
    if policy and (session['role'] == 'superadmin' or policy['department_id'] == session.get('department_id')):
        db.execute("DELETE FROM policies WHERE id=?", (policy_id,))
        db.commit()
        log_action(session['user_id'], 'delete_policy', f'#{policy_id}')
        flash('تم حذف السياسة', 'success')
    db.close()
    return redirect(url_for('announcements.index'))

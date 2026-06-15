from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db import get_db, hash_password
from routes.auth import login_required, role_required, log_action

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@role_required('superadmin')
def index():
    db = get_db()
    users = db.execute(
        "SELECT u.*, d.name_ar as dept_name FROM users u LEFT JOIN departments d ON u.department_id=d.id ORDER BY u.created_at DESC"
    ).fetchall()
    departments = db.execute("SELECT * FROM departments ORDER BY id").fetchall()
    logs = db.execute(
        "SELECT al.*, u.full_name FROM audit_log al LEFT JOIN users u ON al.user_id=u.id ORDER BY al.created_at DESC LIMIT 50"
    ).fetchall()
    policies = db.execute(
        "SELECT p.*, d.name_ar as dept_name, u.full_name as author FROM policies p JOIN departments d ON p.department_id=d.id JOIN users u ON p.created_by=u.id ORDER BY p.created_at DESC"
    ).fetchall()
    db.close()
    return render_template('admin/index.html', users=users, departments=departments, logs=logs, policies=policies)


@admin_bp.route('/users/create', methods=['POST'])
@login_required
@role_required('superadmin')
def create_user():
    db = get_db()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    full_name = request.form.get('full_name', '').strip()
    role = request.form.get('role')
    dept_id = request.form.get('department_id') or None

    if not all([username, password, full_name, role]):
        flash('يرجى ملء جميع الحقول المطلوبة', 'danger')
        return redirect(url_for('admin.index'))

    existing = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if existing:
        flash('اسم المستخدم موجود مسبقاً', 'danger')
        db.close()
        return redirect(url_for('admin.index'))

    db.execute(
        "INSERT INTO users (username, password, full_name, role, department_id) VALUES (?,?,?,?,?)",
        (username, hash_password(password), full_name, role, dept_id)
    )
    db.commit()
    log_action(session['user_id'], 'create_user', f'مستخدم: {username}')
    flash(f'تم إنشاء المستخدم {full_name} بنجاح', 'success')
    db.close()
    return redirect(url_for('admin.index'))

@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@role_required('superadmin')
def toggle_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if user and user['role'] != 'superadmin':
        new_status = 0 if user['is_active'] else 1
        db.execute("UPDATE users SET is_active=? WHERE id=?", (new_status, user_id))
        db.commit()
        log_action(session['user_id'], 'toggle_user', f'مستخدم #{user_id} -> {"مفعل" if new_status else "موقوف"}')
        flash('تم تحديث حالة المستخدم', 'success')
    db.close()
    return redirect(url_for('admin.index'))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('superadmin')
def delete_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        flash('المستخدم غير موجود', 'danger')
    elif user['role'] == 'superadmin':
        flash('لا يمكن حذف مدير النظام', 'danger')
    else:
        db.execute("DELETE FROM comments WHERE user_id=?", (user_id,))
        db.execute("DELETE FROM reactions WHERE user_id=?", (user_id,))
        db.execute("DELETE FROM announcements WHERE created_by=?", (user_id,))
        db.execute("DELETE FROM policies WHERE created_by=?", (user_id,))
        db.execute("DELETE FROM users WHERE id=?", (user_id,))
        db.commit()
        log_action(session['user_id'], 'delete_user', f"مستخدم: {user['full_name']} ({user['username']})")
        flash(f"تم حذف المستخدم {user['full_name']} بنجاح", 'success')
    db.close()
    return redirect(url_for('admin.index'))


@admin_bp.route('/users/<int:user_id>/reset_password', methods=['POST'])
@login_required
@role_required('superadmin')
def reset_password(user_id):
    db = get_db()
    new_pass = request.form.get('new_password', '').strip()
    if new_pass and len(new_pass) >= 6:
        db.execute("UPDATE users SET password=? WHERE id=?", (hash_password(new_pass), user_id))
        db.commit()
        log_action(session['user_id'], 'reset_password', f'مستخدم #{user_id}')
        flash('تم تغيير كلمة المرور', 'success')
    else:
        flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'danger')
    db.close()
    return redirect(url_for('admin.index'))

@admin_bp.route('/departments/create', methods=['POST'])
@login_required
@role_required('superadmin')
def create_department():
    db = get_db()
    name = request.form.get('name', '').strip()
    name_ar = request.form.get('name_ar', '').strip()
    icon = request.form.get('icon', 'fas fa-building')
    color = request.form.get('color', '#2563eb')

    if name and name_ar:
        existing = db.execute("SELECT id FROM departments WHERE name=?", (name,)).fetchone()
        if existing:
            flash('القسم موجود مسبقاً', 'danger')
        else:
            db.execute("INSERT INTO departments (name, name_ar, icon, color) VALUES (?,?,?,?)",
                       (name, name_ar, icon, color))
            db.commit()
            log_action(session['user_id'], 'create_department', f'قسم: {name_ar}')
            flash(f'تم إنشاء قسم "{name_ar}" بنجاح', 'success')
    else:
        flash('يرجى ملء جميع الحقول', 'danger')

    db.close()
    return redirect(url_for('admin.index'))

@admin_bp.route('/departments/<int:dept_id>/delete', methods=['POST'])
@login_required
@role_required('superadmin')
def delete_department(dept_id):
    db = get_db()
    users_in_dept = db.execute("SELECT COUNT(*) as c FROM users WHERE department_id=?", (dept_id,)).fetchone()['c']
    if users_in_dept > 0:
        flash('لا يمكن حذف القسم لأنه يحتوي على موظفين', 'danger')
    else:
        db.execute("DELETE FROM departments WHERE id=?", (dept_id,))
        db.commit()
        log_action(session['user_id'], 'delete_department', f'قسم #{dept_id}')
        flash('تم حذف القسم', 'success')
    db.close()
    return redirect(url_for('admin.index'))

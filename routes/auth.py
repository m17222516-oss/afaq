from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db import get_db, hash_password
from datetime import datetime
import functools

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
            if session.get('role') not in roles:
                flash('ليس لديك صلاحية للوصول إلى هذه الصفحة', 'danger')
                return redirect(url_for('announcements.index'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def log_action(user_id, action, details=None):
    db = get_db()
    ip = request.remote_addr
    db.execute("INSERT INTO audit_log (user_id, action, details, ip_address) VALUES (?,?,?,?)",
               (user_id, action, details, ip))
    db.commit()
    db.close()

@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('announcements.index'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            error = 'يرجى إدخال اسم المستخدم وكلمة المرور'
        else:
            db = get_db()
            user = db.execute(
                "SELECT u.*, d.name_ar as dept_name, d.color as dept_color FROM users u LEFT JOIN departments d ON u.department_id=d.id WHERE u.username=? AND u.password=? AND u.is_active=1",
                (username, hash_password(password))
            ).fetchone()
            if user:
                session.permanent = True
                session['user_id']      = user['id']
                session['username']     = user['username']
                session['full_name']    = user['full_name']
                session['role']         = user['role']
                session['department_id']= user['department_id']
                session['dept_name']    = user['dept_name']
                session['dept_color']   = user['dept_color']
                db.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now(), user['id']))
                db.commit()
                log_action(user['id'], 'login', f'{request.remote_addr}')
                db.close()
                return redirect(url_for('announcements.index'))
            else:
                error = 'اسم المستخدم أو كلمة المرور غير صحيحة'
                db.close()

    return render_template('login.html', error=error)

@auth_bp.route('/logout')
def logout():
    if 'user_id' in session:
        log_action(session['user_id'], 'logout', '')
    session.clear()
    return redirect(url_for('auth.login'))

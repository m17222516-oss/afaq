import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'afaq.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        name_ar TEXT NOT NULL,
        icon TEXT DEFAULT 'fas fa-building',
        color TEXT DEFAULT '#2563eb',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('superadmin','manager','employee')),
        department_id INTEGER,
        is_active INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_login DATETIME,
        FOREIGN KEY (department_id) REFERENCES departments(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        priority TEXT DEFAULT 'normal' CHECK(priority IN ('low','normal','high','urgent')),
        department_id INTEGER NOT NULL,
        created_by INTEGER NOT NULL,
        is_pinned INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (department_id) REFERENCES departments(id),
        FOREIGN KEY (created_by) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        announcement_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        body TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (announcement_id) REFERENCES announcements(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        announcement_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        reaction_type TEXT NOT NULL DEFAULT 'like',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(announcement_id, user_id),
        FOREIGN KEY (announcement_id) REFERENCES announcements(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    conn.commit()

    departments = [
        ('sales',      'قسم المبيعات',              'fas fa-chart-line',    '#2563eb'),
        ('callcenter', 'كول سنتر / خدمة العملاء',   'fas fa-headset',       '#1d4ed8'),
        ('audit',      'قسم التدقيق',               'fas fa-search',        '#1e40af'),
        ('cashier',    'قسم الكاشير',               'fas fa-cash-register', '#3b82f6'),
    ]
    for dept in departments:
        c.execute("INSERT OR IGNORE INTO departments (name, name_ar, icon, color) VALUES (?,?,?,?)", dept)

    c.execute("INSERT OR IGNORE INTO users (username, password, full_name, role, department_id) VALUES (?,?,?,?,?)",
              ('superadmin', hash_password('Admin@2025!'), 'مدير النظام', 'superadmin', None))

    conn.commit()

    # Demo managers & employees
    managers = [
        ('sales_mgr',  'Mgr@Sales1',  'أحمد الزيدي',    'manager', 1),
        ('cc_mgr',     'Mgr@CC2025',  'فاطمة العلي',     'manager', 2),
        ('audit_mgr',  'Mgr@Audit1',  'علي الحسني',     'manager', 3),
        ('cash_mgr',   'Mgr@Cash22',  'زينب الموسوي',   'manager', 4),
    ]
    employees = [
        ('emp_sales1', 'Emp@123', 'محمد الجابري',  'employee', 1),
        ('emp_cc1',    'Emp@123', 'سارة الكريمي',  'employee', 2),
        ('emp_audit1', 'Emp@123', 'حسين الصافي',   'employee', 3),
        ('emp_cash1',  'Emp@123', 'نور البصري',    'employee', 4),
    ]
    for u in managers + employees:
        c.execute("INSERT OR IGNORE INTO users (username,password,full_name,role,department_id) VALUES (?,?,?,?,?)",
                  (u[0], hash_password(u[1]), u[2], u[3], u[4]))

    conn.commit()
    conn.close()
    print("✅ Database initialized.")

def add_policies_table():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS policies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        department_id INTEGER NOT NULL,
        created_by INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (department_id) REFERENCES departments(id),
        FOREIGN KEY (created_by) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        announcement_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        reaction_type TEXT NOT NULL DEFAULT 'like',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(announcement_id, user_id),
        FOREIGN KEY (announcement_id) REFERENCES announcements(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    conn.commit()
    conn.close()

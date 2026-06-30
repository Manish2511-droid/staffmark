from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'staffmark-gipc-secret-change-this-in-production')
app.permanent_session_lifetime = timedelta(days=30)
CORS(app, supports_credentials=True)

DB = 'staffmark.db'

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@greenpestcontrol.com')

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            role TEXT DEFAULT 'Technician',
            salary REAL NOT NULL,
            ot_rate REAL DEFAULT 50,
            join_date TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            UNIQUE(employee_id, date),
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        CREATE TABLE IF NOT EXISTS advances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            month_key TEXT NOT NULL,
            note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        CREATE TABLE IF NOT EXISTS overtime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            hours REAL NOT NULL,
            month_key TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        CREATE TABLE IF NOT EXISTS salary_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            month_key TEXT NOT NULL,
            month_label TEXT NOT NULL,
            days_worked REAL NOT NULL,
            total_days INTEGER NOT NULL,
            base_salary REAL NOT NULL,
            earned REAL NOT NULL,
            advance REAL DEFAULT 0,
            overtime_amount REAL DEFAULT 0,
            payable REAL NOT NULL,
            finalized_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(employee_id, month_key),
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
    ''')
    conn.commit()

    existing = conn.execute('SELECT * FROM users WHERE email=?', (ADMIN_EMAIL,)).fetchone()
    if not existing:
        default_pw = os.environ.get('ADMIN_PASSWORD', 'GIPC@2026')
        pw_hash = generate_password_hash(default_pw)
        conn.execute('INSERT INTO users (email, password_hash) VALUES (?,?)', (ADMIN_EMAIL, pw_hash))
        conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated

# ── AUTH ──
@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    email = d.get('email', '').strip().lower()
    password = d.get('password', '')
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
    conn.close()
    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['email'] = user['email']
        session.permanent = True
        return jsonify({'success': True, 'email': user['email']})
    return jsonify({'error': 'Invalid email or password'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/me', methods=['GET'])
def me():
    if session.get('user_id'):
        return jsonify({'logged_in': True, 'email': session.get('email')})
    return jsonify({'logged_in': False})

@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    d = request.json
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    if not check_password_hash(user['password_hash'], d.get('old_password','')):
        conn.close()
        return jsonify({'error': 'Current password is incorrect'}), 400
    new_hash = generate_password_hash(d.get('new_password',''))
    conn.execute('UPDATE users SET password_hash=? WHERE id=?', (new_hash, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ── EMPLOYEES ──
@app.route('/api/employees', methods=['GET'])
@login_required
def get_employees():
    conn = get_db()
    rows = conn.execute('SELECT * FROM employees WHERE active=1 ORDER BY name').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/employees', methods=['POST'])
@login_required
def add_employee():
    d = request.json
    conn = get_db()
    conn.execute(
        'INSERT INTO employees (name, phone, role, salary, ot_rate, join_date) VALUES (?,?,?,?,?,?)',
        (d['name'], d.get('phone',''), d.get('role','Technician'), d['salary'], d.get('ot_rate',50), d.get('join_date',''))
    )
    conn.commit()
    emp_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    emp = conn.execute('SELECT * FROM employees WHERE id=?', (emp_id,)).fetchone()
    conn.close()
    return jsonify(dict(emp)), 201

@app.route('/api/employees/<int:emp_id>', methods=['PUT'])
@login_required
def update_employee(emp_id):
    d = request.json
    conn = get_db()
    conn.execute(
        'UPDATE employees SET name=?, phone=?, role=?, salary=?, ot_rate=? WHERE id=?',
        (d['name'], d.get('phone',''), d.get('role','Technician'), d['salary'], d.get('ot_rate',50), emp_id)
    )
    conn.commit()
    emp = conn.execute('SELECT * FROM employees WHERE id=?', (emp_id,)).fetchone()
    conn.close()
    return jsonify(dict(emp))

@app.route('/api/employees/<int:emp_id>', methods=['DELETE'])
@login_required
def delete_employee(emp_id):
    conn = get_db()
    conn.execute('UPDATE employees SET active=0 WHERE id=?', (emp_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ── ATTENDANCE ──
@app.route('/api/attendance/<month_key>', methods=['GET'])
@login_required
def get_attendance(month_key):
    conn = get_db()
    rows = conn.execute("SELECT * FROM attendance WHERE date LIKE ?", (month_key + '%',)).fetchall()
    conn.close()
    result = {}
    for r in rows:
        eid = str(r['employee_id'])
        day = int(r['date'].split('-')[2])
        if eid not in result:
            result[eid] = {}
        result[eid][day] = r['status']
    return jsonify(result)

@app.route('/api/attendance', methods=['POST'])
@login_required
def set_attendance():
    d = request.json
    conn = get_db()
    if d['status'] is None:
        conn.execute('DELETE FROM attendance WHERE employee_id=? AND date=?', (d['employee_id'], d['date']))
    else:
        conn.execute(
            'INSERT INTO attendance (employee_id, date, status) VALUES (?,?,?) ON CONFLICT(employee_id, date) DO UPDATE SET status=?',
            (d['employee_id'], d['date'], d['status'], d['status'])
        )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ── ADVANCES ──
@app.route('/api/advances/<month_key>', methods=['GET'])
@login_required
def get_advances(month_key):
    conn = get_db()
    rows = conn.execute('SELECT * FROM advances WHERE month_key=? ORDER BY date', (month_key,)).fetchall()
    conn.close()
    result = {}
    for r in rows:
        eid = str(r['employee_id'])
        if eid not in result:
            result[eid] = []
        result[eid].append(dict(r))
    return jsonify(result)

@app.route('/api/advances', methods=['POST'])
@login_required
def add_advance():
    d = request.json
    conn = get_db()
    conn.execute(
        'INSERT INTO advances (employee_id, amount, date, month_key, note) VALUES (?,?,?,?,?)',
        (d['employee_id'], d['amount'], d['date'], d['month_key'], d.get('note',''))
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/advances/<int:adv_id>', methods=['DELETE'])
@login_required
def delete_advance(adv_id):
    conn = get_db()
    conn.execute('DELETE FROM advances WHERE id=?', (adv_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ── OVERTIME ──
@app.route('/api/overtime/<month_key>', methods=['GET'])
@login_required
def get_overtime(month_key):
    conn = get_db()
    rows = conn.execute('SELECT * FROM overtime WHERE month_key=? ORDER BY date', (month_key,)).fetchall()
    conn.close()
    result = {}
    for r in rows:
        eid = str(r['employee_id'])
        if eid not in result:
            result[eid] = []
        result[eid].append(dict(r))
    return jsonify(result)

@app.route('/api/overtime', methods=['POST'])
@login_required
def add_overtime():
    d = request.json
    conn = get_db()
    conn.execute(
        'INSERT INTO overtime (employee_id, date, hours, month_key) VALUES (?,?,?,?)',
        (d['employee_id'], d['date'], d['hours'], d['month_key'])
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/overtime/<int:ot_id>', methods=['DELETE'])
@login_required
def delete_overtime(ot_id):
    conn = get_db()
    conn.execute('DELETE FROM overtime WHERE id=?', (ot_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ── SALARY HISTORY ──
@app.route('/api/salary-history', methods=['GET'])
@login_required
def get_salary_history():
    conn = get_db()
    rows = conn.execute('SELECT * FROM salary_history ORDER BY month_key DESC, id DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/salary-history', methods=['POST'])
@login_required
def save_salary_history():
    d = request.json
    conn = get_db()
    conn.execute('''
        INSERT INTO salary_history
        (employee_id, month_key, month_label, days_worked, total_days, base_salary, earned, advance, overtime_amount, payable)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(employee_id, month_key) DO UPDATE SET
        days_worked=excluded.days_worked, total_days=excluded.total_days, base_salary=excluded.base_salary,
        earned=excluded.earned, advance=excluded.advance, overtime_amount=excluded.overtime_amount,
        payable=excluded.payable, finalized_at=CURRENT_TIMESTAMP
    ''', (
        d['employee_id'], d['month_key'], d['month_label'], d['days_worked'], d['total_days'],
        d['base_salary'], d['earned'], d.get('advance',0), d.get('overtime_amount',0), d['payable']
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/salary-history/<int:hist_id>', methods=['DELETE'])
@login_required
def delete_salary_history(hist_id):
    conn = get_db()
    conn.execute('DELETE FROM salary_history WHERE id=?', (hist_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ── PAGES ──
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

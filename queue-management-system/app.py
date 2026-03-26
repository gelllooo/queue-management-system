from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
import sqlite3

app = Flask(__name__)
socketio = SocketIO(app)

# ---------------- Database Setup ----------------
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Queue table with priority
    c.execute('''
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            service TEXT NOT NULL,
            priority INTEGER DEFAULT 0  -- 0 = normal, 1 = priority
        )
    ''')
    # Optional table for analytics/logging
    c.execute('''
        CREATE TABLE IF NOT EXISTS queue_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            service TEXT,
            served_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---------------- Student Routes ----------------
@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM queue ORDER BY priority DESC, id ASC")
    queue = c.fetchall()
    conn.close()
    return render_template('index.html', queue=queue)

@app.route('/add', methods=['POST'])
def add():
    name = request.form['name']
    service = request.form['service']
    priority = int(request.form.get('priority', 0))  # 0 normal, 1 PWD/senior

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO queue (name, service, priority) VALUES (?, ?, ?)", (name, service, priority))
    conn.commit()
    conn.close()

    # Notify admin in real-time
    socketio.emit('queue_update', {'message': 'New student added'})
    return redirect('/')

# ---------------- Admin Routes ----------------
@app.route('/admin')
def admin():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM queue ORDER BY priority DESC, id ASC")
    queue = c.fetchall()
    conn.close()
    return render_template('admin.html', queue=queue)

@app.route('/next', methods=['POST'])
def next_student():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM queue ORDER BY priority DESC, id ASC LIMIT 1")
    student = c.fetchone()
    if student:
        c.execute("DELETE FROM queue WHERE id = ?", (student[0],))
        # Log served student
        c.execute("INSERT INTO queue_log (student_name, service) VALUES (?, ?)", (student[1], student[2]))
    conn.commit()
    conn.close()

    # Real-time update for admin/students
    socketio.emit('queue_update', {'message': 'Student served'})
    return redirect(url_for('admin'))

# ---------------- SocketIO Event ----------------
@socketio.on('connect')
def handle_connect():
    emit('queue_update', {'message': 'Connected'})

if __name__ == '__main__':
    socketio.run(app, debug=True)
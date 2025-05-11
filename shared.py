import sqlite3, time

db = sqlite3.connect("hybrid_queue.db", check_same_thread=False)
cursor = db.cursor()

def init_shared_db():
    cursor.execute("""CREATE TABLE IF NOT EXISTS queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        keyword TEXT,
        status TEXT DEFAULT 'pending'
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS results (
        queue_id INTEGER,
        file_path TEXT
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        token INTEGER DEFAULT 3,
        is_premium INTEGER DEFAULT 0,
        last_used INTEGER
    )""")
    db.commit()

cooldowns = {}
abuse_tracker = {}

def is_spamming(user_id, cooldown=30, max_strikes=3):
    now = time.time()
    last_time = cooldowns.get(user_id, 0)

    if now - last_time < cooldown:
        abuse_tracker[user_id] = abuse_tracker.get(user_id, 0) + 1
    else:
        abuse_tracker[user_id] = 0

    cooldowns[user_id] = now

    if abuse_tracker[user_id] >= max_strikes:
        cursor.execute("UPDATE users SET token = 0 WHERE user_id = ?", (user_id,))
        db.commit()
        return "banned"
    elif now - last_time < cooldown:
        return "warn"
    return "ok"

def get_token(user_id):
    cursor.execute("SELECT token FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def get_status(user_id):
    cursor.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return "Premium" if row and row[0] == 1 else "Free"

def add_user(user_id, username):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, token) VALUES (?, ?, 3)", (user_id, username))
        db.commit()

def add_to_queue(user_id, username, keyword):
    add_user(user_id, username)
    cursor.execute("INSERT INTO queue (user_id, username, keyword) VALUES (?, ?, ?)", (user_id, username, keyword))
    db.commit()
    return cursor.lastrowid

def fetch_pending():
    cursor.execute("SELECT id, user_id, username, keyword FROM queue WHERE status = 'pending'")
    return cursor.fetchall()

def mark_processing(queue_id):
    cursor.execute("UPDATE queue SET status = 'processing' WHERE id = ?", (queue_id,))
    db.commit()

def mark_done(queue_id, file_path):
    cursor.execute("UPDATE queue SET status = 'done' WHERE id = ?", (queue_id,))
    cursor.execute("INSERT INTO results (queue_id, file_path) VALUES (?, ?)", (queue_id, file_path))
    db.commit()

def get_result(queue_id):
    cursor.execute("SELECT file_path FROM results WHERE queue_id = ?", (queue_id,))
    row = cursor.fetchone()
    return row[0] if row else None
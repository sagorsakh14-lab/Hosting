# database.py — TachZone Hosting Bot

import sqlite3
from config import DB_FILE

def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            full_name   TEXT,
            banned      INTEGER DEFAULT 0,
            joined_at   TEXT DEFAULT (datetime('now'))
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            bot_id      TEXT PRIMARY KEY,
            user_id     INTEGER,
            name        TEXT,
            folder      TEXT,
            status      TEXT DEFAULT 'stopped',
            pid         INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now')),
            started_at  TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ── User ──────────────────────────────────────────────────
def register_user(user_id, username, full_name):
    conn = get_conn()
    conn.execute('''
        INSERT OR IGNORE INTO users (user_id, username, full_name)
        VALUES (?, ?, ?)
    ''', (user_id, username, full_name))
    conn.execute('''
        UPDATE users SET username=?, full_name=?
        WHERE user_id=?
    ''', (username, full_name, user_id))
    conn.commit()
    conn.close()

def is_banned(user_id):
    conn = get_conn()
    row = conn.execute('SELECT banned FROM users WHERE user_id=?', (user_id,)).fetchone()
    conn.close()
    return row and row['banned'] == 1

def ban_user(user_id):
    conn = get_conn()
    conn.execute('UPDATE users SET banned=1 WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = get_conn()
    conn.execute('UPDATE users SET banned=0 WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_conn()
    rows = conn.execute('SELECT * FROM users ORDER BY joined_at DESC').fetchall()
    conn.close()
    return rows

def get_user(user_id):
    conn = get_conn()
    row = conn.execute('SELECT * FROM users WHERE user_id=?', (user_id,)).fetchone()
    conn.close()
    return row

# ── Bot ───────────────────────────────────────────────────
def add_bot(bot_id, user_id, name, folder):
    conn = get_conn()
    conn.execute('''
        INSERT INTO bots (bot_id, user_id, name, folder)
        VALUES (?, ?, ?, ?)
    ''', (bot_id, user_id, name, folder))
    conn.commit()
    conn.close()

def get_user_bots(user_id):
    conn = get_conn()
    rows = conn.execute('SELECT * FROM bots WHERE user_id=? ORDER BY created_at DESC', (user_id,)).fetchall()
    conn.close()
    return rows

def get_bot(bot_id):
    conn = get_conn()
    row = conn.execute('SELECT * FROM bots WHERE bot_id=?', (bot_id,)).fetchone()
    conn.close()
    return row

def update_bot_status(bot_id, status, pid=0):
    conn = get_conn()
    if status == 'running':
        conn.execute('''
            UPDATE bots SET status=?, pid=?, started_at=datetime('now')
            WHERE bot_id=?
        ''', (status, pid, bot_id))
    else:
        conn.execute('UPDATE bots SET status=?, pid=0 WHERE bot_id=?', (status, bot_id))
    conn.commit()
    conn.close()

def rename_bot(bot_id, new_name):
    conn = get_conn()
    conn.execute('UPDATE bots SET name=? WHERE bot_id=?', (new_name, bot_id))
    conn.commit()
    conn.close()

def delete_bot(bot_id):
    conn = get_conn()
    conn.execute('DELETE FROM bots WHERE bot_id=?', (bot_id,))
    conn.commit()
    conn.close()

def get_all_bots():
    conn = get_conn()
    rows = conn.execute('SELECT * FROM bots ORDER BY created_at DESC').fetchall()
    conn.close()
    return rows

def count_user_bots(user_id):
    conn = get_conn()
    count = conn.execute('SELECT COUNT(*) FROM bots WHERE user_id=?', (user_id,)).fetchone()[0]
    conn.close()
    return count

def next_bot_id():
    conn = get_conn()
    count = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
    conn.close()
    return f"TZ-{count+1:04d}"

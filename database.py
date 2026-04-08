import sqlite3
import os
from config import DB_PATH, BASE_DIR

def init_db():
    try:
        os.makedirs(BASE_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS bots (
            bot_id TEXT PRIMARY KEY,
            user_id INTEGER,
            name TEXT,
            folder TEXT,
            status TEXT DEFAULT 'stopped',
            pid INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            started_at TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            banned INTEGER DEFAULT 0,
            joined_at TEXT DEFAULT (datetime('now'))
        )''')
        
        conn.commit()
        conn.close()
        print(f"✅ Database created: {DB_PATH}")
        return True
    except Exception as e:
        print(f"❌ DB Error: {e}")
        return False

def register_user(user_id, username, full_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)',
              (user_id, username, full_name))
    conn.commit()
    conn.close()

def is_banned(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT banned FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == 1

def get_user_bots(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM bots WHERE user_id = ?', (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{'bot_id': r[0], 'user_id': r[1], 'name': r[2], 'folder': r[3], 
             'status': r[4], 'pid': r[5], 'created_at': r[6], 'started_at': r[7]} for r in rows]

def get_bot(bot_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM bots WHERE bot_id = ?', (bot_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'bot_id': row[0], 'user_id': row[1], 'name': row[2], 'folder': row[3],
                'status': row[4], 'pid': row[5], 'created_at': row[6], 'started_at': row[7]}
    return None

def add_bot(bot_id, user_id, name, folder):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO bots (bot_id, user_id, name, folder) VALUES (?, ?, ?, ?)',
              (bot_id, user_id, name, folder))
    conn.commit()
    conn.close()

def delete_bot(bot_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM bots WHERE bot_id = ?', (bot_id,))
    conn.commit()
    conn.close()

def update_bot_status(bot_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE bots SET status = ? WHERE bot_id = ?', (status, bot_id))
    conn.commit()
    conn.close()

def rename_bot(bot_id, new_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE bots SET name = ? WHERE bot_id = ?', (new_name, bot_id))
    conn.commit()
    conn.close()

def count_user_bots(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM bots WHERE user_id = ?', (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def next_bot_id():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM bots')
    count = c.fetchone()[0] + 1
    conn.close()
    return f"TZ-{count:04d}"

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM users')
    rows = c.fetchall()
    conn.close()
    return [{'user_id': r[0], 'username': r[1], 'full_name': r[2], 'banned': r[3], 'joined_at': r[4]} for r in rows]

def get_all_bots():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM bots')
    rows = c.fetchall()
    conn.close()
    return [{'bot_id': r[0], 'user_id': r[1], 'name': r[2], 'folder': r[3],
             'status': r[4], 'pid': r[5], 'created_at': r[6], 'started_at': r[7]} for r in rows]

def ban_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET banned = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET banned = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
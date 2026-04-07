# database.py - সম্পূর্ণ ফাইলটি এরকম করুন

import sqlite3
import os
from config import BASE_DIR

DB_PATH = os.path.join(BASE_DIR, 'tachzone.db')

def get_db():
    """Database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db()
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            banned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Bots table
    c.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            bot_id TEXT PRIMARY KEY,
            user_id INTEGER,
            name TEXT,
            folder TEXT,
            status TEXT DEFAULT 'stopped',
            pid INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

def register_user(user_id, username, full_name):
    """Register or update user"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO users (user_id, username, full_name, banned)
        VALUES (?, ?, ?, COALESCE((SELECT banned FROM users WHERE user_id = ?), 0))
    ''', (user_id, username, full_name, user_id))
    conn.commit()
    conn.close()

def is_banned(user_id):
    """Check if user is banned"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row is not None and row['banned'] == 1

def ban_user(user_id):
    """Ban a user"""
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    """Unban a user"""
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_user_bots(user_id):
    """Get all bots of a user"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_bot(bot_id):
    """Get bot by ID"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM bots WHERE bot_id = ?", (bot_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def add_bot(bot_id, user_id, name, folder):
    """Add new bot"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO bots (bot_id, user_id, name, folder, status, pid)
        VALUES (?, ?, ?, ?, 'stopped', NULL)
    ''', (bot_id, user_id, name, folder))
    conn.commit()
    conn.close()

def delete_bot(bot_id):
    """Delete bot from database"""
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM bots WHERE bot_id = ?", (bot_id,))
    conn.commit()
    conn.close()

def update_bot_status(bot_id, status, pid=None):
    """Update bot status and PID"""
    conn = get_db()
    c = conn.cursor()
    if pid:
        c.execute('''
            UPDATE bots SET status = ?, pid = ? WHERE bot_id = ?
        ''', (status, pid, bot_id))
    else:
        c.execute('''
            UPDATE bots SET status = ?, pid = NULL WHERE bot_id = ?
        ''', (status, bot_id))
    conn.commit()
    conn.close()

def rename_bot(bot_id, new_name):
    """Rename bot"""
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE bots SET name = ? WHERE bot_id = ?", (new_name, bot_id))
    conn.commit()
    conn.close()

def count_user_bots(user_id):
    """Count bots of a user"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as count FROM bots WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row['count'] if row else 0

def next_bot_id():
    """Generate next bot ID (TZ-XXXX)"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT bot_id FROM bots ORDER BY bot_id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    
    if row:
        last_id = row['bot_id']
        num = int(last_id.split('-')[1]) + 1
    else:
        num = 1
    
    return f"TZ-{num:04d}"

def get_all_users():
    """Get all users (for admin)"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_bots():
    """Get all bots (for admin)"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM bots ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]
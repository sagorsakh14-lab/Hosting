# database.py - এই ফাংশনগুলো যোগ/আপডেট করুন

def update_bot_status(bot_id, status, pid=None):
    """Update bot status and PID"""
    conn = get_db()
    c = conn.cursor()
    if pid:
        c.execute(
            "UPDATE bots SET status = ?, pid = ? WHERE bot_id = ?",
            (status, pid, bot_id)
        )
    else:
        c.execute(
            "UPDATE bots SET status = ? WHERE bot_id = ?",
            (status, bot_id)
        )
    conn.commit()
    conn.close()

def get_bot(bot_id):
    """Get bot by ID with full details"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM bots WHERE bot_id = ?", (bot_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def add_bot(bot_id, user_id, name, folder):
    """Add new bot to database"""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO bots (bot_id, user_id, name, folder, status, pid, created_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        (bot_id, user_id, name, folder, 'stopped', None)
    )
    conn.commit()
    conn.close()
# core/database.py
import sqlite3
from pathlib import Path
from typing import Optional, Tuple, List
from config.settings import DB_PATH
from core.security import generate_salt, hash_pin, verify_pin
from core.qr_utils import make_qr_token

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_conn():
    try:
        return sqlite3.connect(DB_PATH)
    except Exception as e:
        from core.error_utils import log_error
        log_error(e, "Opening database connection")
        raise


# User management
def add_admin(username: str, password: str):
    salt = generate_salt()
    phash = hash_pin(password, salt)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO admins (username, pass_hash, pass_salt) VALUES (?, ?, ?)",
                (username, phash, salt))
    conn.commit()
    conn.close()

def check_admin_credentials(username: str, password: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT pass_hash, pass_salt FROM admins WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row: return False
    phash, salt = row
    return verify_pin(password, salt, phash)

def add_user(name, role, pin):
    salt = generate_salt()
    pin_hash = hash_pin(pin, salt)
    qr_token = make_qr_token()

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, role, pin_hash, pin_salt, status, qr_code) VALUES (?, ?, ?, ?, 'Active', ?)",
        (name, role, pin_hash, salt, qr_token)
    )
    conn.commit()
    conn.close()

    return qr_token


def list_users(limit: int = 100) -> List[Tuple]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, name, role, status, created_at FROM users ORDER BY user_id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_user_by_qr(qr_code: str) -> Optional[Tuple]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, name, role, pin_hash, pin_salt, status FROM users WHERE qr_code = ?", (qr_code,))
    row = cur.fetchone()
    conn.close()
    return row

def get_user_by_id(user_id: int) -> Optional[Tuple]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, name, role, qr_code, status FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

def set_user_pin(user_id: int, pin_hash: str, pin_salt: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET pin_hash = ?, pin_salt = ? WHERE user_id = ?", (pin_hash, pin_salt, user_id))
    conn.commit()
    conn.close()

# Logging
def log_access(user_id: int, action: str, location: str = "Gate"):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO access_logs (user_id, action, location) VALUES (?, ?, ?)", (user_id, action, location))
    conn.commit()
    conn.close()

def last_action_for_user(user_id: int) -> Optional[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT action FROM access_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def export_logs_csv(path: str):
    import pandas as pd
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM access_logs ORDER BY timestamp DESC", conn)
    df.to_csv(path, index=False)
    conn.close()

# --- Dashboard helpers ---
def get_current_inside():
    """
    Return list of (user_id, name, role, last_action_time)
    for users whose latest action is IN.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.user_id, u.name, u.role, MAX(l.timestamp)
        FROM users u
        JOIN access_logs l ON u.user_id = l.user_id
        WHERE l.action = 'IN'
        AND u.user_id NOT IN (
            SELECT user_id FROM access_logs WHERE action='OUT'
            AND timestamp > l.timestamp
        )
        GROUP BY u.user_id
        ORDER BY MAX(l.timestamp) DESC;
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_recent_logs(limit=100):
    """
    Return last <limit> log entries joined with usernames.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT l.log_id, u.name, l.action, l.timestamp, l.location
        FROM access_logs l
        JOIN users u ON l.user_id = u.user_id
        ORDER BY l.timestamp DESC
        LIMIT ?;
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_daily_counts(days=7):
    """Return tuples of (date, ins, outs) for the past <days> days."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DATE(timestamp) as day,
               SUM(CASE WHEN action='IN'  THEN 1 ELSE 0 END) as ins,
               SUM(CASE WHEN action='OUT' THEN 1 ELSE 0 END) as outs
        FROM access_logs
        GROUP BY day
        ORDER BY day DESC
        LIMIT ?;
    """, (days,))
    rows = cur.fetchall()
    conn.close()
    # reverse chronological order → oldest first
    return rows[::-1]

def get_total_inside():
    """Return total users currently inside."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT u.user_id
            FROM users u
            JOIN access_logs l ON u.user_id = l.user_id
            WHERE l.action='IN'
            AND u.user_id NOT IN (
                SELECT user_id FROM access_logs WHERE action='OUT' AND timestamp>l.timestamp
            )
            GROUP BY u.user_id
        );
    """)
    total = cur.fetchone()[0]
    conn.close()
    return total

def get_all_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, name, role, status FROM users ORDER BY user_id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_user(user_id, name, role, new_pin=None):
    from core.security import generate_salt, hash_pin
    conn = get_conn()
    cur = conn.cursor()
    if new_pin:
        salt = generate_salt()
        pin_hash = hash_pin(new_pin, salt)
        cur.execute("UPDATE users SET name=?, role=?, pin_hash=?, pin_salt=? WHERE user_id=?",
                    (name, role, pin_hash, salt, user_id))
    else:
        cur.execute("UPDATE users SET name=?, role=? WHERE user_id=?", (name, role, user_id))
    conn.commit()
    conn.close()

def set_user_status(user_id, status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status=? WHERE user_id=?", (status, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        from core.error_utils import log_error
        log_error(e, "delete_user()")
        raise


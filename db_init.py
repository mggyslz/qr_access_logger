# db_init.py
from pathlib import Path
import sqlite3

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
QRC_DIR = PROJECT_ROOT / "qrcodes"
EXPORT_DIR = DATA_DIR / "exports"

DATA_DIR.mkdir(exist_ok=True)
QRC_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "security_app.db"

CREATE_ADMINS = """
CREATE TABLE IF NOT EXISTS admins (
    admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    pass_hash TEXT,
    pass_salt TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'Staff',
    qr_code TEXT UNIQUE,
    pin_hash TEXT,
    pin_salt TEXT,
    status TEXT DEFAULT 'Active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_LOGS = """
CREATE TABLE IF NOT EXISTS access_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT CHECK(action IN ('IN','OUT')) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    location TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
"""

def init_db():
    conn = sqlite3.connect(DB_PATH.as_posix())
    cur = conn.cursor()
    cur.execute(CREATE_ADMINS)
    cur.execute(CREATE_USERS)
    cur.execute(CREATE_LOGS)
    conn.commit()
    conn.close()
    print(f"Initialized DB at {DB_PATH}")

if __name__ == "__main__":
    init_db()

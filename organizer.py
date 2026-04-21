import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
from config import ORGANIZED_ROOT

def ensure_db() -> sqlite3.Connection:
    db_path = ORGANIZED_ROOT / ".autopilot.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            original_path TEXT,
            new_path TEXT,
            category TEXT,
            action TEXT
        )
        """
    )
    conn.commit()
    return conn

def move_file(file_path: Path, category: str) -> Path:
    dest_dir = ORGANIZED_ROOT / category
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir / file_path.name
    counter = 1
    stem = file_path.stem
    suffix = file_path.suffix
    while dest_path.exists():
        dest_path = dest_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    shutil.move(str(file_path), str(dest_path))
    return dest_path

def log_action(conn: sqlite3.Connection, original: Path, new: Path, category: str):
    conn.execute(
        "INSERT INTO actions (timestamp, original_path, new_path, category, action) VALUES (?, ?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), str(original), str(new), category, "move"),
    )
    conn.commit()

def organize(file_path: Path, category: str) -> Path:
    conn = ensure_db()
    try:
        new_path = move_file(file_path, category)
        log_action(conn, file_path, new_path, category)
        return new_path
    finally:
        conn.close()

def get_recent_actions(limit: int = 20):
    conn = ensure_db()
    cursor = conn.execute(
        "SELECT timestamp, original_path, new_path, category FROM actions ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

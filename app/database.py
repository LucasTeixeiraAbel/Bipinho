import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.config import DB_PATH, DEFAULT_SETTINGS

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_db():
    conn = get_connection()
    with conn:
        # Items table (drawings / cartoons)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                date TEXT NOT NULL,
                media_type TEXT NOT NULL,
                filename TEXT NOT NULL,
                thumb_filename TEXT NOT NULL,
                view_count INTEGER DEFAULT 0,
                last_viewed TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Settings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Session state table (single row: id=1)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_scans INTEGER DEFAULT 0,
                is_paused INTEGER DEFAULT 0,
                pause_started_at TEXT,
                scanned_items_json TEXT DEFAULT '[]',
                last_scanned_code TEXT,
                last_scanned_at TEXT,
                current_item_id INTEGER
            )
        """)

        # Initialize default settings if not exists
        for key, val in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, str(val))
            )

        # Initialize session state row 1
        conn.execute("""
            INSERT OR IGNORE INTO session_state (
                id, current_scans, is_paused, pause_started_at,
                scanned_items_json, last_scanned_code, last_scanned_at, current_item_id
            ) VALUES (1, 0, 0, NULL, '[]', NULL, NULL, NULL)
        """)
    conn.close()

# ----------------- ITEMS CRUD ----------------- #

def get_all_items() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM items ORDER BY id DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_item_by_id(item_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_item_by_code(code: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    # Trim and match case-insensitively
    clean_code = code.strip().upper()
    cursor = conn.execute("SELECT * FROM items WHERE UPPER(code) = ?", (clean_code,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_random_item(exclude_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    if exclude_id is not None:
        cursor = conn.execute(
            "SELECT * FROM items WHERE id != ? ORDER BY RANDOM() LIMIT 1",
            (exclude_id,)
        )
    else:
        cursor = conn.execute("SELECT * FROM items ORDER BY RANDOM() LIMIT 1")
    row = cursor.fetchone()
    if not row and exclude_id is not None:
        # If there's only one item, allow picking it
        cursor = conn.execute("SELECT * FROM items LIMIT 1")
        row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_item(
    code: str,
    title: str,
    author: str,
    date: str,
    media_type: str,
    filename: str,
    thumb_filename: str
) -> int:
    conn = get_connection()
    with conn:
        cursor = conn.execute("""
            INSERT INTO items (code, title, author, date, media_type, filename, thumb_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (code.strip().upper(), title.strip(), author.strip(), date.strip(), media_type, filename, thumb_filename))
        new_id = cursor.lastrowid
    conn.close()
    return new_id

def update_item(
    item_id: int,
    code: str,
    title: str,
    author: str,
    date: str,
    filename: Optional[str] = None,
    thumb_filename: Optional[str] = None
) -> bool:
    conn = get_connection()
    with conn:
        if filename and thumb_filename:
            conn.execute("""
                UPDATE items
                SET code = ?, title = ?, author = ?, date = ?, filename = ?, thumb_filename = ?
                WHERE id = ?
            """, (code.strip().upper(), title.strip(), author.strip(), date.strip(), filename, thumb_filename, item_id))
        else:
            conn.execute("""
                UPDATE items
                SET code = ?, title = ?, author = ?, date = ?
                WHERE id = ?
            """, (code.strip().upper(), title.strip(), author.strip(), date.strip(), item_id))
    conn.close()
    return True

def delete_item(item_id: int) -> Optional[Dict[str, Any]]:
    item = get_item_by_id(item_id)
    if not item:
        return None
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.close()
    return item

def increment_item_views(item_id: int):
    now_iso = datetime.now().isoformat()
    conn = get_connection()
    with conn:
        conn.execute("""
            UPDATE items
            SET view_count = view_count + 1, last_viewed = ?
            WHERE id = ?
        """, (now_iso, item_id))
    conn.close()

def get_next_available_code() -> str:
    conn = get_connection()
    cursor = conn.execute("SELECT code FROM items WHERE code LIKE 'BIP-%'")
    codes = [row[0] for row in cursor.fetchall()]
    conn.close()
    max_num = 1000
    for c in codes:
        try:
            num_part = int(c.replace("BIP-", "").strip())
            if num_part > max_num:
                max_num = num_part
        except ValueError:
            pass
    return f"BIP-{max_num + 1}"

# ----------------- SETTINGS ----------------- #

def get_all_settings() -> Dict[str, str]:
    conn = get_connection()
    cursor = conn.execute("SELECT key, value FROM settings")
    settings = {row["key"]: row["value"] for row in cursor.fetchall()}
    conn.close()
    # Merge defaults for any missing key
    merged = dict(DEFAULT_SETTINGS)
    merged.update(settings)
    return merged

def get_setting(key: str, default: Optional[str] = None) -> str:
    conn = get_connection()
    cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["value"]
    return default if default is not None else DEFAULT_SETTINGS.get(key, "")

def set_setting(key: str, value: str):
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, str(value)))
    conn.close()

def set_settings(settings_dict: Dict[str, Any]):
    conn = get_connection()
    with conn:
        for k, v in settings_dict.items():
            conn.execute("""
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (k, str(v)))
    conn.close()

# ----------------- SESSION STATE ----------------- #

def get_session_state() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM session_state WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {
            "current_scans": 0,
            "is_paused": 0,
            "pause_started_at": None,
            "scanned_items": [],
            "last_scanned_code": None,
            "last_scanned_at": None,
            "current_item_id": None
        }
    data = dict(row)
    try:
        data["scanned_items"] = json.loads(data.get("scanned_items_json") or "[]")
    except Exception:
        data["scanned_items"] = []
    return data

def update_session_state(
    current_scans: Optional[int] = None,
    is_paused: Optional[int] = None,
    pause_started_at: Optional[str] = "KEEP",
    scanned_items: Optional[List[int]] = None,
    last_scanned_code: Optional[str] = "KEEP",
    last_scanned_at: Optional[str] = "KEEP",
    current_item_id: Optional[int] = "KEEP" # type: ignore
):
    current = get_session_state()
    new_scans = current["current_scans"] if current_scans is None else current_scans
    new_paused = current["is_paused"] if is_paused is None else is_paused
    new_pause_time = current["pause_started_at"] if pause_started_at == "KEEP" else pause_started_at
    new_items = current["scanned_items"] if scanned_items is None else scanned_items
    new_code = current["last_scanned_code"] if last_scanned_code == "KEEP" else last_scanned_code
    new_time = current["last_scanned_at"] if last_scanned_at == "KEEP" else last_scanned_at
    new_item_id = current["current_item_id"] if current_item_id == "KEEP" else current_item_id

    conn = get_connection()
    with conn:
        conn.execute("""
            UPDATE session_state
            SET current_scans = ?,
                is_paused = ?,
                pause_started_at = ?,
                scanned_items_json = ?,
                last_scanned_code = ?,
                last_scanned_at = ?,
                current_item_id = ?
            WHERE id = 1
        """, (
            new_scans,
            new_paused,
            new_pause_time,
            json.dumps(new_items),
            new_code,
            new_time,
            new_item_id
        ))
    conn.close()

def reset_session():
    conn = get_connection()
    with conn:
        conn.execute("""
            UPDATE session_state
            SET current_scans = 0,
                is_paused = 0,
                pause_started_at = NULL,
                scanned_items_json = '[]',
                last_scanned_code = NULL,
                last_scanned_at = NULL,
                current_item_id = NULL
            WHERE id = 1
        """)
    conn.close()

# ----------------- STATISTICS ----------------- #

def get_stats() -> Dict[str, Any]:
    conn = get_connection()
    total_items = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    total_views = conn.execute("SELECT COALESCE(SUM(view_count), 0) FROM items").fetchone()[0]
    
    # Favorites (top 10 most viewed)
    favorites_cur = conn.execute("""
        SELECT id, code, title, author, view_count, last_viewed, thumb_filename
        FROM items
        ORDER BY view_count DESC, id DESC
        LIMIT 10
    """)
    favorites = [dict(r) for r in favorites_cur.fetchall()]
    conn.close()

    return {
        "total_items": total_items,
        "total_views": total_views,
        "favorites": favorites
    }

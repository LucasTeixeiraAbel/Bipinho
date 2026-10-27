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
                current_item_id INTEGER,
                watched_seconds REAL DEFAULT 0
            )
        """)

        # Migration: Ensure watched_seconds exists in session_state
        cur_cols = [r[1] for r in conn.execute("PRAGMA table_info(session_state)").fetchall()]
        if "watched_seconds" not in cur_cols:
            conn.execute("ALTER TABLE session_state ADD COLUMN watched_seconds REAL DEFAULT 0")

        # Initialize default settings if not exists
        for key, val in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, str(val))
            )

        # Migration: Check if legacy plaintext admin_password exists and migrate to admin_password_hash
        cur = conn.execute("SELECT value FROM settings WHERE key = 'admin_password'")
        legacy_pwd_row = cur.fetchone()
        cur_hash = conn.execute("SELECT value FROM settings WHERE key = 'admin_password_hash'").fetchone()
        
        from app.services.auth_service import hash_password
        if legacy_pwd_row and legacy_pwd_row[0]:
            legacy_val = legacy_pwd_row[0]
            if not cur_hash or not cur_hash[0]:
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_password_hash', ?)",
                    (hash_password(legacy_val),)
                )
            # If the password was still default "bipinho123", ensure admin_password_changed is "0"
            if legacy_val == "bipinho123":
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_password_changed', '0')")
            else:
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_password_changed', '1')")
            # Remove legacy plaintext key
            conn.execute("DELETE FROM settings WHERE key = 'admin_password'")
        else:
            # If no hash exists at all, initialize with default "bipinho123" and changed="0"
            if not cur_hash or not cur_hash[0]:
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_password_hash', ?)",
                    (hash_password("bipinho123"),)
                )
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_password_changed', '0')")

        # Daily sessions tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                session_num INTEGER NOT NULL DEFAULT 1,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                total_watched_seconds REAL DEFAULT 0,
                scans_count INTEGER DEFAULT 0,
                items_json TEXT DEFAULT '[]'
            )
        """)

        # Viewing history / analytics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS view_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                item_code TEXT NOT NULL,
                item_title TEXT NOT NULL,
                viewed_at TEXT NOT NULL,
                watched_seconds REAL DEFAULT 0
            )
        """)

        # Movement challenges list
        conn.execute("""
            CREATE TABLE IF NOT EXISTS movement_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            )
        """)

        # Seed default movement challenges if table is empty
        count = conn.execute("SELECT COUNT(*) FROM movement_challenges").fetchone()[0]
        if count == 0:
            default_challenges = [
                "Dê 10 pulinhos!",
                "Gire como um bailarino!",
                "Imite um bichinho da sua escolha!",
                "Faça 5 agachamentos!",
                "Pule de um pé só por 10 segundos!",
                "Faça uma estrela com o corpo!",
                "Corra no lugar por 15 segundos!",
                "Imite um robô andando!",
                "Dê 5 cambalhotas imaginárias!",
                "Balance os braços como um pássaro!",
                "Pule feito um sapo 5 vezes!",
                "Toque nos pés sem dobrar os joelhos!",
                "Faça carinha de leão e ruja 3 vezes!",
                "Equilibre-se numa perna só por 10 segundos!",
                "Dance sua música favorita por 20 segundos!",
            ]
            for i, c in enumerate(default_challenges):
                conn.execute(
                    "INSERT INTO movement_challenges (challenge, enabled, sort_order) VALUES (?, 1, ?)",
                    (c, i)
                )

        # Initialize session state row 1
        conn.execute("""
            INSERT OR IGNORE INTO session_state (
                id, current_scans, is_paused, pause_started_at,
                scanned_items_json, last_scanned_code, last_scanned_at, current_item_id, watched_seconds
            ) VALUES (1, 0, 0, NULL, '[]', NULL, NULL, NULL, 0)
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
            "current_item_id": None,
            "watched_seconds": 0.0
        }
    data = dict(row)
    try:
        data["scanned_items"] = json.loads(data.get("scanned_items_json") or "[]")
    except Exception:
        data["scanned_items"] = []
    data["watched_seconds"] = float(data.get("watched_seconds") or 0.0)
    return data

def update_session_state(
    current_scans: Optional[int] = None,
    is_paused: Optional[int] = None,
    pause_started_at: Optional[str] = "KEEP",
    scanned_items: Optional[List[int]] = None,
    last_scanned_code: Optional[str] = "KEEP",
    last_scanned_at: Optional[str] = "KEEP",
    current_item_id: Optional[int] = "KEEP", # type: ignore
    watched_seconds: Optional[float] = None
):
    current = get_session_state()
    new_scans = current["current_scans"] if current_scans is None else current_scans
    new_paused = current["is_paused"] if is_paused is None else is_paused
    new_pause_time = current["pause_started_at"] if pause_started_at == "KEEP" else pause_started_at
    new_items = current["scanned_items"] if scanned_items is None else scanned_items
    new_code = current["last_scanned_code"] if last_scanned_code == "KEEP" else last_scanned_code
    new_time = current["last_scanned_at"] if last_scanned_at == "KEEP" else last_scanned_at
    new_item_id = current["current_item_id"] if current_item_id == "KEEP" else current_item_id
    new_watched = current["watched_seconds"] if watched_seconds is None else float(watched_seconds)

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
                current_item_id = ?,
                watched_seconds = ?
            WHERE id = 1
        """, (
            new_scans,
            new_paused,
            new_pause_time,
            json.dumps(new_items),
            new_code,
            new_time,
            new_item_id,
            new_watched
        ))
    conn.close()

def add_watched_seconds(seconds: float) -> float:
    """Adds elapsed seconds to the watched_seconds accumulator and returns new total."""
    conn = get_connection()
    with conn:
        conn.execute("""
            UPDATE session_state
            SET watched_seconds = COALESCE(watched_seconds, 0) + ?
            WHERE id = 1
        """, (float(seconds),))
    conn.close()
    state = get_session_state()
    return state.get("watched_seconds", 0.0)

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
                current_item_id = NULL,
                watched_seconds = 0
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

# ----------------- DAILY SESSIONS ----------------- #

def get_today_session_count(date_str: Optional[str] = None) -> int:
    """Returns the number of completed sessions for a given date (default: today)."""
    from datetime import date as dt_date
    if not date_str:
        date_str = dt_date.today().isoformat()
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM daily_sessions WHERE date = ?", (date_str,)
    ).fetchone()[0]
    conn.close()
    return count

def start_daily_session(date_str: str, session_num: int, started_at: str) -> int:
    """Creates a new daily session record. Returns its id."""
    conn = get_connection()
    with conn:
        cur = conn.execute(
            "INSERT INTO daily_sessions (date, session_num, started_at) VALUES (?, ?, ?)",
            (date_str, session_num, started_at)
        )
        row_id = cur.lastrowid
    conn.close()
    return row_id

def end_daily_session(session_id: int, ended_at: str, total_watched_seconds: float, scans_count: int, items_list: list):
    """Updates a daily session record when it ends (pause triggered)."""
    conn = get_connection()
    with conn:
        conn.execute("""
            UPDATE daily_sessions
            SET ended_at = ?, total_watched_seconds = ?, scans_count = ?, items_json = ?
            WHERE id = ?
        """, (ended_at, total_watched_seconds, scans_count, json.dumps(items_list), session_id))
    conn.close()

def get_history_by_date(date_str: str) -> Dict[str, Any]:
    """Returns aggregated history for a given date."""
    conn = get_connection()
    sessions = conn.execute(
        "SELECT * FROM daily_sessions WHERE date = ? ORDER BY started_at",
        (date_str,)
    ).fetchall()
    sessions_list = [dict(s) for s in sessions]

    # Most-viewed items that day
    top_items = conn.execute("""
        SELECT vh.item_code, vh.item_title, COUNT(*) as plays
        FROM view_history vh
        WHERE DATE(vh.viewed_at) = ?
        GROUP BY vh.item_code
        ORDER BY plays DESC
        LIMIT 5
    """, (date_str,)).fetchall()
    conn.close()

    total_watched = sum(float(s.get("total_watched_seconds") or 0) for s in sessions_list)
    return {
        "date": date_str,
        "session_count": len(sessions_list),
        "total_watched_seconds": total_watched,
        "sessions": sessions_list,
        "top_items": [dict(t) for t in top_items]
    }

def get_weekly_history(base_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns last 7 days of history."""
    from datetime import date as dt_date, timedelta
    if not base_date:
        base_date = dt_date.today().isoformat()
    today = dt_date.fromisoformat(base_date)
    result = []
    for delta in range(6, -1, -1):
        d = (today - timedelta(days=delta)).isoformat()
        result.append(get_history_by_date(d))
    return result

def record_view_history(item_id: int, item_code: str, item_title: str, watched_seconds: float = 0):
    """Records one viewing event in the history log."""
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO view_history (item_id, item_code, item_title, viewed_at, watched_seconds) VALUES (?, ?, ?, ?, ?)",
            (item_id, item_code, item_title, datetime.now().isoformat(), watched_seconds)
        )
    conn.close()

# ----------------- MOVEMENT CHALLENGES ----------------- #

def get_all_challenges() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM movement_challenges ORDER BY sort_order, id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_random_challenge() -> Optional[str]:
    conn = get_connection()
    row = conn.execute(
        "SELECT challenge FROM movement_challenges WHERE enabled = 1 ORDER BY RANDOM() LIMIT 1"
    ).fetchone()
    conn.close()
    return row["challenge"] if row else None

def set_challenges(challenges_list: List[Dict[str, Any]]):
    """Replace the entire challenges list."""
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM movement_challenges")
        for i, c in enumerate(challenges_list):
            conn.execute(
                "INSERT INTO movement_challenges (challenge, enabled, sort_order) VALUES (?, ?, ?)",
                (c.get("challenge", ""), 1 if c.get("enabled", True) else 0, i)
            )
    conn.close()

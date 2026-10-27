import asyncio
import json
from datetime import datetime, timezone, date as dt_date
from typing import Dict, Any, Optional, List

from app.database import (
    get_all_settings,
    get_setting,
    get_item_by_code,
    get_item_by_id,
    get_random_item,
    increment_item_views,
    get_session_state,
    update_session_state,
    reset_session,
    get_today_session_count,
    start_daily_session,
    end_daily_session,
    record_view_history,
    get_random_challenge,
)

# Active SSE client queues
_sse_clients: List[asyncio.Queue] = []

# Track the current daily session DB row id (in-memory; resets on server restart)
_current_daily_session_id: Optional[int] = None
_session_started_at: Optional[str] = None

def add_sse_client() -> asyncio.Queue:
    q = asyncio.Queue()
    _sse_clients.append(q)
    return q

def remove_sse_client(q: asyncio.Queue):
    if q in _sse_clients:
        _sse_clients.remove(q)

async def broadcast_event(event_type: str, data: Any):
    payload = json.dumps({"type": event_type, "data": data})
    for q in list(_sse_clients):
        try:
            await q.put(payload)
        except Exception:
            pass

def check_pause_status() -> Dict[str, Any]:
    """Check if current pause is still active or expired."""
    state = get_session_state()
    settings = get_all_settings()
    
    if not state.get("is_paused"):
        return {"is_paused": False, "remaining_seconds": 0}

    pause_minutes = int(settings.get("pause_minutes", 18))
    total_pause_seconds = pause_minutes * 60
    pause_started_str = state.get("pause_started_at")
    
    if not pause_started_str:
        return {"is_paused": False, "remaining_seconds": 0}

    try:
        pause_start = datetime.fromisoformat(pause_started_str)
        now = datetime.now()
        elapsed = (now - pause_start).total_seconds()
        remaining = max(0, int(total_pause_seconds - elapsed))
        
        unlock_mode = settings.get("pause_unlock_mode", "ambas")
        # If time expired and auto-unlock allowed
        if remaining <= 0 and unlock_mode in ("ambas", "tempo"):
            reset_session()
            return {"is_paused": False, "remaining_seconds": 0, "just_unlocked": True}
        
        return {
            "is_paused": True,
            "remaining_seconds": remaining,
            "total_pause_seconds": total_pause_seconds,
            "pause_minutes": pause_minutes,
            "unlock_mode": unlock_mode
        }
    except Exception as e:
        print(f"Error calculating pause status: {e}")
        return {"is_paused": False, "remaining_seconds": 0}

def get_current_session_info() -> Dict[str, Any]:
    """Returns complete state for child or admin screen."""
    pause_info = check_pause_status()
    state = get_session_state()
    settings = get_all_settings()
    
    current_item = None
    if state.get("current_item_id"):
        current_item = get_item_by_id(state["current_item_id"])

    return {
        "current_scans": state.get("current_scans", 0),
        "max_scans": int(settings.get("max_scans", 3)),
        "count_mode": settings.get("count_mode", "leituras"),
        "is_paused": pause_info.get("is_paused", False),
        "remaining_pause_seconds": pause_info.get("remaining_seconds", 0),
        "total_pause_seconds": pause_info.get("total_pause_seconds", 0),
        "pause_minutes": int(settings.get("pause_minutes", 18)),
        "current_item": current_item,
        "sound_enabled": settings.get("sound_enabled", "1") == "1",
        "title_display_seconds": int(settings.get("title_display_seconds", 30)),
        "reader_type": settings.get("reader_type", "USB"),
        "video_scan_behavior": settings.get("video_scan_behavior", "interrupt"),
        "watched_seconds": state.get("watched_seconds", 0.0),
        "watch_time_limit_minutes": int(settings.get("watch_time_limit_minutes", 15)),
        "mascot_enabled": settings.get("mascot_enabled", "1") == "1",
        "movement_challenges_enabled": settings.get("movement_challenges_enabled", "1") == "1",
    }

async def trigger_coloring_pause() -> Dict[str, Any]:
    """Transitions system into 'Hora de colorir!' pause and records daily session."""
    global _current_daily_session_id
    now = datetime.now()
    now_iso = now.isoformat()
    settings = get_all_settings()
    pause_minutes = int(settings.get("pause_minutes", 18))

    # Record session end in daily_sessions
    if _current_daily_session_id:
        state = get_session_state()
        end_daily_session(
            session_id=_current_daily_session_id,
            ended_at=now_iso,
            total_watched_seconds=float(state.get("watched_seconds", 0.0)),
            scans_count=int(state.get("current_scans", 0)),
            items_list=state.get("scanned_items", []),
        )
        _current_daily_session_id = None

    # Reset any exceptional unlock when session completes
    from app.database import set_setting
    set_setting("exceptional_unlock", "0")

    update_session_state(
        is_paused=1,
        pause_started_at=now_iso
    )

    # Pick a random movement challenge
    challenge = None
    if settings.get("movement_challenges_enabled", "1") == "1":
        challenge = get_random_challenge()

    data = {
        "is_paused": True,
        "pause_minutes": pause_minutes,
        "remaining_seconds": pause_minutes * 60,
        "total_pause_seconds": pause_minutes * 60,
        "challenge": challenge,
    }
    await broadcast_event("pause_started", data)
    return data

async def unlock_coloring_pause(by_parents: bool = False) -> Dict[str, Any]:
    """Unlocks pause and resets session counter."""
    global _current_daily_session_id
    _current_daily_session_id = None
    reset_session()
    data = {"is_paused": False, "by_parents": by_parents}
    await broadcast_event("pause_unlocked", data)
    return data

async def handle_barcode_scan(code: str, is_video_playing: bool = False) -> Dict[str, Any]:
    """
    Main business logic for processing barcode reads.
    Handles parent unlock, surprise code, debounce, drawing lookup,
    counting rules, and pause transitions.
    """
    clean_code = code.strip().upper()
    now = datetime.now()
    now_iso = now.isoformat()
    
    state = get_session_state()
    settings = get_all_settings()
    pause_status = check_pause_status()

    parent_unlock_code = settings.get("parent_unlock_code", "PAIS-LIBERAR-99").strip().upper()
    surprise_code = settings.get("surprise_code", "BIP-SURPRESA").strip().upper()
    surprise_enabled = settings.get("surprise_enabled", "1") == "1"
    debounce_sec = float(settings.get("repeat_debounce_seconds", 3))

    # 1. PARENT UNLOCK CODE
    if clean_code == parent_unlock_code:
        # Clear manual block and grant exceptional schedule access
        from app.database import set_setting
        set_setting("tv_blocked", "0")
        set_setting("exceptional_unlock", "1")
        await unlock_coloring_pause(by_parents=True)
        await broadcast_event("schedule_unlocked", {"status": "unlocked_by_parent"})
        return {
            "status": "parent_unlock",
            "message": "Pausa e bloqueios liberados pelos pais! TV liberada.",
            "session": get_current_session_info()
        }

    # 2. IF CURRENTLY IN PAUSE
    if pause_status.get("is_paused"):
        # Regular scans are ignored during coloring time
        return {
            "status": "in_pause",
            "message": "Hora de colorir! Bipes de desenhos estão pausados.",
            "remaining_seconds": pause_status.get("remaining_seconds", 0),
            "pause_minutes": pause_status.get("pause_minutes", 18)
        }

    # 2.5 VIDEO PLAYING IGNORED (if configured)
    if is_video_playing and settings.get("video_scan_behavior") == "ignore":
        return {
            "status": "video_playing_ignored",
            "message": "Desenho em reprodução. Aguarde terminar para bipar outro!"
        }

    # 3. REPEAT DEBOUNCE CHECK
    last_code = state.get("last_scanned_code")
    last_at_str = state.get("last_scanned_at")
    if last_code and last_code == clean_code and last_at_str:
        try:
            last_at = datetime.fromisoformat(last_at_str)
            if (now - last_at).total_seconds() < debounce_sec:
                return {
                    "status": "debounce_ignored",
                    "message": "Bipe repetido ignorado (aguarde alguns segundos)."
                }
        except Exception:
            pass

    # 4. SURPRISE BARCODE
    is_surprise = False
    target_item = None
    if surprise_enabled and clean_code == surprise_code:
        is_surprise = True
        target_item = get_random_item(exclude_id=state.get("current_item_id"))
        if not target_item:
            return {
                "status": "not_found",
                "message": "Nenhum desenho cadastrado para a surpresa!",
                "code": clean_code
            }
    else:
        # Normal drawing lookup
        target_item = get_item_by_code(clean_code)

    # 5. UNKNOWN CODE
    if not target_item:
        return {
            "status": "not_found",
            "message": "Ops, esse desenho não está aqui!",
            "code": clean_code
        }

    # 6. COUNTING & PROGRESSION
    item_id = target_item["id"]
    increment_item_views(item_id)
    target_item["view_count"] += 1

    current_scans = state.get("current_scans", 0)
    max_scans = int(settings.get("max_scans", 3))
    count_mode = settings.get("count_mode", "leituras")
    scanned_items = state.get("scanned_items", [])

    # --- Start a daily session record on first scan ---
    global _current_daily_session_id
    if current_scans == 0 and _current_daily_session_id is None:
        today_str = now.date().isoformat()
        today_count = get_today_session_count(today_str)
        _current_daily_session_id = start_daily_session(
            date_str=today_str,
            session_num=today_count + 1,
            started_at=now_iso,
        )

    # Record view history
    record_view_history(
        item_id=item_id,
        item_code=target_item["code"],
        item_title=target_item["title"],
    )

    increment = False
    if count_mode == "desenhos_diferentes":
        if item_id not in scanned_items:
            scanned_items.append(item_id)
            current_scans += 1
            increment = True
    else:
        # Default: count by readings (allows replaying same cartoon)
        current_scans += 1
        increment = True
        if item_id not in scanned_items:
            scanned_items.append(item_id)

    if count_mode == "tempo_assistido":
        watch_limit_sec = int(settings.get("watch_time_limit_minutes", 15)) * 60
        limit_reached = float(state.get("watched_seconds", 0.0)) >= watch_limit_sec
    else:
        limit_reached = current_scans >= max_scans

    # Save session state
    update_session_state(
        current_scans=current_scans,
        scanned_items=scanned_items,
        last_scanned_code=clean_code,
        last_scanned_at=now_iso,
        current_item_id=item_id
    )

    result_data = {
        "status": "success",
        "item": target_item,
        "is_surprise": is_surprise,
        "current_scans": current_scans,
        "max_scans": max_scans,
        "limit_reached": limit_reached,
        "sound_enabled": settings.get("sound_enabled", "1") == "1",
        "title_display_seconds": int(settings.get("title_display_seconds", 30))
    }

    # Broadcast to all TV screens
    await broadcast_event("play_drawing", result_data)

    return result_data

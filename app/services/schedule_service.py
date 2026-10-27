"""
schedule_service.py — Parental schedule and session limit enforcement.

Checks whether the TV is allowed to play cartoons based on:
- Time window (allowed_start_time / allowed_end_time)
- Allowed days of the week (0=Mon, 6=Sun)
- Max sessions per day
- Manual TV block by admin
"""
from datetime import datetime, time as dt_time
from typing import Dict, Any, Optional

from app.database import get_all_settings, get_today_session_count, get_setting


def _parse_time(s: str, fallback: dt_time) -> dt_time:
    try:
        parts = s.strip().split(":")
        return dt_time(int(parts[0]), int(parts[1]))
    except Exception:
        return fallback


def check_schedule_allowed(override_now: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Returns a dict describing whether the TV is currently allowed to operate.

    {
        "allowed": bool,
        "reason": str,   # human-readable Portuguese reason when blocked
        "tv_blocked": bool,
        "outside_hours": bool,
        "outside_days": bool,
        "sessions_exceeded": bool,
        "schedule_enabled": bool,
    }
    """
    settings = get_all_settings()
    schedule_enabled = settings.get("schedule_enabled", "0") == "1"

    # Manual admin block always wins (unless unlocked by parent key)
    tv_blocked = settings.get("tv_blocked", "0") == "1"
    if tv_blocked:
        return {
            "allowed": False,
            "reason": "A TV foi bloqueada manualmente pelos pais. 🔒",
            "tv_blocked": True,
            "outside_hours": False,
            "outside_days": False,
            "sessions_exceeded": False,
            "schedule_enabled": schedule_enabled,
        }

    # Exceptional unlock by parent key grants access for the current session
    exceptional_unlock = settings.get("exceptional_unlock", "0") == "1"
    if exceptional_unlock:
        return {
            "allowed": True,
            "reason": "",
            "tv_blocked": False,
            "outside_hours": False,
            "outside_days": False,
            "sessions_exceeded": False,
            "schedule_enabled": schedule_enabled,
            "exceptional_unlock": True,
        }

    # If schedule not enabled, everything is allowed
    if not schedule_enabled:
        return {
            "allowed": True,
            "reason": "",
            "tv_blocked": False,
            "outside_hours": False,
            "outside_days": False,
            "sessions_exceeded": False,
            "schedule_enabled": False,
        }

    now = override_now or datetime.now()
    today_weekday = now.weekday()  # 0=Mon, 6=Sun

    # Check allowed days
    allowed_days_str = settings.get("allowed_days", "0,1,2,3,4,5,6")
    try:
        allowed_days = [int(d.strip()) for d in allowed_days_str.split(",") if d.strip()]
    except Exception:
        allowed_days = list(range(7))

    outside_days = today_weekday not in allowed_days

    # Check time window
    start_time = _parse_time(settings.get("allowed_start_time", "07:00"), dt_time(7, 0))
    end_time = _parse_time(settings.get("allowed_end_time", "21:00"), dt_time(21, 0))
    current_time = now.time().replace(second=0, microsecond=0)
    outside_hours = not (start_time <= current_time <= end_time)

    # Check max sessions per day
    max_sessions = int(settings.get("max_sessions_per_day", "0"))
    sessions_exceeded = False
    if max_sessions > 0:
        today_count = get_today_session_count(now.date().isoformat())
        sessions_exceeded = today_count >= max_sessions

    blocked = outside_days or outside_hours or sessions_exceeded

    reason = ""
    if outside_days:
        day_names = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
        allowed_names = ", ".join(day_names[d] for d in sorted(allowed_days))
        reason = f"O Bipinho só funciona em: {allowed_names}. Hoje não é um dia permitido! 😴"
    elif outside_hours:
        reason = (
            f"O Bipinho funciona das {settings.get('allowed_start_time','07:00')} "
            f"às {settings.get('allowed_end_time','21:00')}. "
            f"Agora são {now.strftime('%H:%M')}. 😴"
        )
    elif sessions_exceeded:
        reason = f"Você já assistiu {today_count} vez(es) hoje! O limite do dia é {max_sessions}. 😴"

    return {
        "allowed": not blocked,
        "reason": reason,
        "tv_blocked": False,
        "outside_hours": outside_hours,
        "outside_days": outside_days,
        "sessions_exceeded": sessions_exceeded,
        "schedule_enabled": True,
    }

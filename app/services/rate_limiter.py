import time
from typing import Dict, Tuple

# In-memory dictionary: ip -> {"failures": int, "lockout_until": float}
_LOGIN_ATTEMPTS: Dict[str, Dict] = {}

def check_ip_lockout(ip: str) -> Tuple[bool, int]:
    """
    Checks if an IP is locked out.
    Returns: (is_locked, remaining_seconds)
    """
    entry = _LOGIN_ATTEMPTS.get(ip)
    if not entry:
        return False, 0
    now = time.time()
    lockout_until = entry.get("lockout_until", 0)
    if lockout_until > now:
        return True, int(lockout_until - now)
    elif lockout_until > 0 and lockout_until <= now:
        # Lockout expired, reset
        _LOGIN_ATTEMPTS.pop(ip, None)
        return False, 0
    return False, 0

def record_login_failure(ip: str, max_attempts: int = 5, lockout_minutes: int = 15) -> Tuple[int, bool, int]:
    """
    Records a failed login attempt for an IP.
    Returns: (failures_count, is_now_locked, lockout_seconds)
    """
    now = time.time()
    entry = _LOGIN_ATTEMPTS.setdefault(ip, {"failures": 0, "lockout_until": 0})
    entry["failures"] += 1
    
    if entry["failures"] >= max_attempts:
        lockout_duration = lockout_minutes * 60
        entry["lockout_until"] = now + lockout_duration
        return entry["failures"], True, lockout_duration
    
    return entry["failures"], False, 0

def record_login_success(ip: str):
    """Clears failed attempts on successful login."""
    _LOGIN_ATTEMPTS.pop(ip, None)

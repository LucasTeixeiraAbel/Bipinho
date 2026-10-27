import hashlib
import os
import secrets
from typing import Tuple

def hash_password(password: str, salt: bytes = None) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations and salt."""
    if salt is None:
        salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
    return f"pbkdf2:sha256:100000${salt.hex()}${key.hex()}"

def verify_password(plain_password: str, hashed: str) -> bool:
    """Verifies a plain password against a stored hash."""
    if not hashed:
        return False
    try:
        parts = hashed.split('$')
        if len(parts) != 3:
            return False
        algo_info, salt_hex, key_hex = parts
        salt = bytes.fromhex(salt_hex)
        expected_key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100_000)
        return secrets.compare_digest(expected_key.hex(), key_hex)
    except Exception:
        return False

import os
import socket
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"
MEDIA_DIR = BASE_DIR / "media"
UPLOADS_DIR = MEDIA_DIR / "uploads"
THUMBS_DIR = MEDIA_DIR / "thumbs"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "bipinho.db"

# Ensure runtime directories exist
for folder in [MEDIA_DIR, UPLOADS_DIR, THUMBS_DIR, DATA_DIR, STATIC_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Server Defaults
DEFAULT_PORT = 8000
DEFAULT_HOST = "0.0.0.0"

# Default application settings
DEFAULT_SETTINGS = {
    # Session & Limit
    "max_scans": "3",
    "pause_minutes": "18",
    "count_mode": "leituras",          # "leituras" or "desenhos_diferentes"
    "pause_unlock_mode": "ambas",       # "ambas", "tempo", "codigo_pais"
    
    # Timing & Audio
    "repeat_debounce_seconds": "3",
    "title_display_seconds": "30",
    "sound_enabled": "1",
    
    # Special Barcodes
    "parent_unlock_code": "PAIS-LIBERAR-99",
    "surprise_enabled": "1",
    "surprise_code": "BIP-SURPRESA",
    
    # Security
    "admin_password_hash": "",         # pbkdf2_sha256 hash
    "admin_password_changed": "0",      # "0" means still default, must change
    "admin_access_restriction": "all",  # "all" or "localhost_only"
    "login_max_attempts": "5",          # Failed attempts before lockout
    "login_lockout_minutes": "15",      # Lockout duration in minutes
    
    # Barcode Reader Profile (Active Type)
    "reader_type": "USB",              # "USB", "Bluetooth", "2.4G"
    
    # Reader Profile: USB
    "reader_usb_max_interchar_ms": "100",
    "reader_usb_terminator": "Enter",
    "reader_usb_prefix_strip": "",
    "reader_usb_suffix_strip": "",
    "reader_usb_min_length": "3",
    "reader_usb_timeout_ms": "500",
    
    # Reader Profile: Sem fio 2.4G
    "reader_24g_max_interchar_ms": "100",
    "reader_24g_terminator": "Enter",
    "reader_24g_prefix_strip": "",
    "reader_24g_suffix_strip": "",
    "reader_24g_min_length": "3",
    "reader_24g_timeout_ms": "500",
    
    # Reader Profile: Bluetooth
    "reader_bt_max_interchar_ms": "300",
    "reader_bt_terminator": "Enter",
    "reader_bt_prefix_strip": "",
    "reader_bt_suffix_strip": "",
    "reader_bt_min_length": "3",
    "reader_bt_timeout_ms": "1000",
}

READER_TIPS = {
    "USB": "Se nada acontecer ao bipar, desconecte e reconecte o cabo na TV.",
    "Bluetooth": "Se o leitor parar de responder, bipe uma vez para acordá-lo ou refaça o pareamento nas configurações da TV.",
    "2.4G": "Verifique se o receptor USB está bem encaixado na TV."
}

def get_lan_ip() -> str:
    """
    Detect the local LAN IP address of this computer so it can be typed
    on the Android TV browser (e.g. 192.168.1.15).
    """
    try:
        # Connect to a dummy external address (doesn't send any packets)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    try:
        # Fallback to hostname inspection
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"

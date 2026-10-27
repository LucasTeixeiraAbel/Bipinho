import os
import shutil
import subprocess
import sqlite3
from pathlib import Path
from typing import Dict, Any
from app.config import BASE_DIR, DB_PATH, DEFAULT_PORT, get_lan_ip

VERSION = "1.1.0"

def get_ffmpeg_info() -> Dict[str, Any]:
    """Finds ffmpeg path and returns version details."""
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        return {
            "found": False,
            "path": None,
            "version": None,
            "error": "ffmpeg não encontrado no PATH do sistema."
        }
    try:
        res = subprocess.run([ffmpeg_path, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        if res.returncode == 0:
            first_line = res.stdout.splitlines()[0] if res.stdout else "Desconhecido"
            return {
                "found": True,
                "path": str(ffmpeg_path),
                "version": first_line
            }
    except Exception as e:
        return {
            "found": False,
            "path": str(ffmpeg_path),
            "version": None,
            "error": str(e)
        }
    return {
        "found": False,
        "path": str(ffmpeg_path),
        "version": None,
        "error": "Falha ao executar ffmpeg"
    }

def get_disk_space() -> Dict[str, Any]:
    """Returns free, total and used space in GB for the disk hosting BASE_DIR."""
    try:
        usage = shutil.disk_usage(str(BASE_DIR))
        free_gb = round(usage.free / (1024 ** 3), 2)
        total_gb = round(usage.total / (1024 ** 3), 2)
        used_gb = round(usage.used / (1024 ** 3), 2)
        percent_free = round((usage.free / usage.total) * 100, 1)
        return {
            "free_gb": free_gb,
            "total_gb": total_gb,
            "used_gb": used_gb,
            "percent_free": percent_free
        }
    except Exception:
        return {
            "free_gb": 0, "total_gb": 0, "used_gb": 0, "percent_free": 0
        }

def get_database_status() -> Dict[str, Any]:
    """Checks database integrity and file size."""
    try:
        size_bytes = DB_PATH.stat().st_size if DB_PATH.exists() else 0
        size_kb = round(size_bytes / 1024, 1)
        
        # Check integrity
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check")
        row = cur.fetchone()
        integrity = row[0] if row else "unknown"
        
        cur.execute("SELECT COUNT(*) FROM items")
        items_count = cur.fetchone()[0]
        conn.close()
        
        return {
            "exists": DB_PATH.exists(),
            "size_kb": size_kb,
            "integrity": integrity,
            "items_count": items_count,
            "ok": integrity == "ok"
        }
    except Exception as e:
        return {
            "exists": False,
            "size_kb": 0,
            "integrity": f"Erro: {e}",
            "items_count": 0,
            "ok": False
        }

def get_windows_sleep_status() -> Dict[str, Any]:
    """Checks powercfg query on Windows to see if sleep/standby timeout is enabled."""
    if os.name != 'nt':
        return {"active": False, "details": "Sistema não é Windows"}
    try:
        # Run powercfg /q to get standby timeout AC
        cmd = ["powercfg", "/q", "SCHEME_CURRENT", "SUB_SLEEP", "STANDBYIDLE"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace", timeout=4)
        if res.returncode == 0:
            lines = res.stdout.splitlines()
            for line in lines:
                if "Configura" in line and "AC" in line or "Current AC Power Setting" in line or "Índice de Configuração de Alimentação CA Atual" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        val_hex = parts[-1].strip()
                        val_int = int(val_hex, 16)
                        if val_int == 0:
                            return {
                                "sleep_configured": False,
                                "timeout_minutes": 0,
                                "warning": False,
                                "message": "Suspensão desativada (Nunca suspender na tomada)."
                            }
                        else:
                            minutes = val_int // 60
                            return {
                                "sleep_configured": True,
                                "timeout_minutes": minutes,
                                "warning": True,
                                "message": f"Atenção: O Windows está configurado para suspender após {minutes} minutos na tomada. Isso pode derrubar o Bipinho para a TV."
                            }
        return {
            "sleep_configured": False,
            "timeout_minutes": None,
            "warning": False,
            "message": "Não foi possível verificar a suspensão ou ela está desativada."
        }
    except Exception:
        return {
            "sleep_configured": False,
            "timeout_minutes": None,
            "warning": False,
            "message": "Não foi possível consultar as configurações de energia."
        }

def get_full_diagnostics() -> Dict[str, Any]:
    """Aggregates all diagnostic data."""
    lan_ip = get_lan_ip()
    return {
        "version": VERSION,
        "ffmpeg": get_ffmpeg_info(),
        "disk": get_disk_space(),
        "database": get_database_status(),
        "sleep": get_windows_sleep_status(),
        "network": {
            "lan_ip": lan_ip,
            "port": DEFAULT_PORT,
            "tv_url": f"http://{lan_ip}:{DEFAULT_PORT}",
            "local_url": f"http://localhost:{DEFAULT_PORT}"
        }
    }

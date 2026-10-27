import os
import io
import zipfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

from app.config import (
    BASE_DIR, DATA_DIR, DB_PATH, MEDIA_DIR, UPLOADS_DIR, THUMBS_DIR
)
from app.database import init_db

def create_backup_zip() -> io.BytesIO:
    """
    Creates an in-memory zip file containing:
    - data/bipinho.db
    - media/uploads/*
    - media/thumbs/*
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add database
        if DB_PATH.exists():
            zf.write(str(DB_PATH), arcname="data/bipinho.db")

        # Add uploads
        if UPLOADS_DIR.exists():
            for file_path in UPLOADS_DIR.glob("*"):
                if file_path.is_file():
                    zf.write(str(file_path), arcname=f"media/uploads/{file_path.name}")

        # Add thumbs
        if THUMBS_DIR.exists():
            for file_path in THUMBS_DIR.glob("*"):
                if file_path.is_file():
                    zf.write(str(file_path), arcname=f"media/thumbs/{file_path.name}")

    buffer.seek(0)
    return buffer

def validate_backup_zip(zip_bytes: bytes) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates a zip file structure before restoring.
    Returns: (is_valid, error_message, metadata_dict)
    """
    try:
        buffer = io.BytesIO(zip_bytes)
        if not zipfile.is_zipfile(buffer):
            return False, "O arquivo enviado não é um arquivo .zip válido.", {}

        with zipfile.ZipFile(buffer, "r") as zf:
            namelist = zf.namelist()
            has_db = "data/bipinho.db" in namelist or any(n.endswith(".db") for n in namelist)
            
            # Security: Path traversal check
            for name in namelist:
                if name.startswith("/") or ".." in name or "\\" in name:
                    return False, f"Arquivo inseguro detectado no ZIP: {name}", {}

            uploads_count = sum(1 for n in namelist if n.startswith("media/uploads/") and not n.endswith("/"))
            thumbs_count = sum(1 for n in namelist if n.startswith("media/thumbs/") and not n.endswith("/"))

            if not has_db:
                return False, "O backup não contém o banco de dados (data/bipinho.db).", {}

            return True, "", {
                "has_db": has_db,
                "uploads_count": uploads_count,
                "thumbs_count": thumbs_count,
                "total_files": len(namelist)
            }
    except Exception as e:
        return False, f"Erro ao analisar o arquivo zip: {e}", {}

def restore_backup_zip(zip_bytes: bytes) -> Tuple[bool, str]:
    """
    Restores the backup zip into DATA_DIR and MEDIA_DIR safely.
    """
    is_valid, err, meta = validate_backup_zip(zip_bytes)
    if not is_valid:
        return False, err

    try:
        buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(buffer, "r") as zf:
            for member in zf.infolist():
                # Prevent directory traversal
                target_path = Path(BASE_DIR) / member.filename
                resolved = target_path.resolve()
                if not str(resolved).startswith(str(BASE_DIR.resolve())):
                    continue

                if member.is_dir():
                    resolved.mkdir(parents=True, exist_ok=True)
                else:
                    resolved.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as source, open(resolved, "wb") as target:
                        shutil.copyfileobj(source, target)

        # Re-initialize DB to ensure schema and migrations are current
        init_db()
        return True, "Backup restaurado com sucesso!"
    except Exception as e:
        return False, f"Falha ao restaurar arquivos: {e}"

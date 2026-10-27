import os
import secrets
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import (
    APIRouter, Request, Response, Form, UploadFile, File,
    HTTPException, Depends, status
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel

from app.config import (
    TEMPLATES_DIR, DEFAULT_PORT, get_lan_ip,
    READER_TIPS, UPLOADS_DIR, THUMBS_DIR
)
from app.database import (
    get_all_items, get_item_by_id, get_item_by_code,
    create_item, update_item, delete_item, get_next_available_code,
    get_all_settings, get_setting, set_setting, set_settings,
    get_stats, reset_session
)
from app.services.auth_service import hash_password, verify_password
from app.services.rate_limiter import check_ip_lockout, record_login_failure, record_login_success
from app.services.diagnostic_service import get_full_diagnostics, get_ffmpeg_info
from app.services.media_service import save_and_process_media, is_ffmpeg_installed
from app.services.session_manager import handle_barcode_scan, broadcast_event

router = APIRouter()

# In-memory admin session tokens (valid for server lifetime)
ACTIVE_ADMIN_SESSIONS = set()

def get_client_ip(request: Request) -> str:
    """Extracts client IP safely."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

def check_ip_restriction(request: Request):
    """Enforces localhost_only if configured in settings."""
    restriction = get_setting("admin_access_restriction", "all")
    if restriction == "localhost_only":
        client_ip = get_client_ip(request)
        if client_ip not in ("127.0.0.1", "::1", "localhost", "testclient"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso administrativo restrito exclusivamente ao computador local (localhost)."
            )

def is_authenticated(request: Request) -> bool:
    token = request.cookies.get("bipinho_admin_auth")
    return token in ACTIVE_ADMIN_SESSIONS if token else False

def require_auth(request: Request):
    check_ip_restriction(request)
    if not is_authenticated(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado"
        )

# ----------------- LOGIN / LOGOUT ----------------- #

@router.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request):
    check_ip_restriction(request)
    if is_authenticated(request):
        # If password still hasn't been changed, send to force-change
        if get_setting("admin_password_changed", "0") == "0":
            return RedirectResponse(url="/admin/trocar-senha-obrigatoria", status_code=303)
        return RedirectResponse(url="/admin", status_code=303)
    login_template = TEMPLATES_DIR / "login.html"
    return HTMLResponse(content=login_template.read_text(encoding="utf-8"))

@router.post("/admin/login")
async def do_login(request: Request, password: str = Form(...)):
    check_ip_restriction(request)
    client_ip = get_client_ip(request)
    
    # Check Rate Limiting lockout
    is_locked, remaining = check_ip_lockout(client_ip)
    if is_locked:
        mins = max(1, remaining // 60)
        template_text = (TEMPLATES_DIR / "login.html").read_text(encoding="utf-8")
        error_html = f"<div class='alert-error'>Muitas tentativas incorretas. Acesso bloqueado temporariamente por mais {mins} minuto(s).</div>"
        rendered = template_text.replace("<!-- ERROR_MESSAGE -->", error_html)
        return HTMLResponse(content=rendered, status_code=429)

    max_att = int(get_setting("login_max_attempts", "5"))
    lockout_mins = int(get_setting("login_lockout_minutes", "15"))

    saved_hash = get_setting("admin_password_hash", "")
    # Check password
    is_valid = verify_password(password, saved_hash)

    if is_valid:
        record_login_success(client_ip)
        token = secrets.token_hex(24)
        ACTIVE_ADMIN_SESSIONS.add(token)
        
        # Check if first-login change is required
        needs_change = get_setting("admin_password_changed", "0") == "0"
        dest_url = "/admin/trocar-senha-obrigatoria" if needs_change else "/admin"
        
        response = RedirectResponse(url=dest_url, status_code=303)
        response.set_cookie(
            key="bipinho_admin_auth",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=86400 * 7 # 7 days
        )
        return response
    else:
        fails, now_locked, lock_sec = record_login_failure(client_ip, max_attempts=max_att, lockout_minutes=lockout_mins)
        template_text = (TEMPLATES_DIR / "login.html").read_text(encoding="utf-8")
        if now_locked:
            error_html = f"<div class='alert-error'>Limite de {max_att} tentativas excedido! IP bloqueado por {lockout_mins} minutos.</div>"
            code = 429
        else:
            left = max_att - fails
            error_html = f"<div class='alert-error'>Senha incorreta. Restam {left} tentativa(s) antes do bloqueio temporário.</div>"
            code = 401
        rendered = template_text.replace("<!-- ERROR_MESSAGE -->", error_html)
        return HTMLResponse(content=rendered, status_code=code)

@router.get("/admin/trocar-senha-obrigatoria", response_class=HTMLResponse)
async def force_change_password_page(request: Request):
    require_auth(request)
    template_file = TEMPLATES_DIR / "force_password.html"
    return HTMLResponse(content=template_file.read_text(encoding="utf-8"))

@router.post("/admin/trocar-senha-obrigatoria")
async def do_force_change_password(
    request: Request,
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    require_auth(request)
    if new_password.strip() == "bipinho123":
        template_text = (TEMPLATES_DIR / "force_password.html").read_text(encoding="utf-8")
        rendered = template_text.replace("<!-- ERROR_MESSAGE -->", "<div class='alert-error'>A nova senha NÃO pode ser a senha padrão antiga (bipinho123). Escolha uma senha segura!</div>")
        return HTMLResponse(content=rendered, status_code=400)
    
    if len(new_password.strip()) < 4:
        template_text = (TEMPLATES_DIR / "force_password.html").read_text(encoding="utf-8")
        rendered = template_text.replace("<!-- ERROR_MESSAGE -->", "<div class='alert-error'>A nova senha deve ter no mínimo 4 caracteres.</div>")
        return HTMLResponse(content=rendered, status_code=400)

    if new_password.strip() != confirm_password.strip():
        template_text = (TEMPLATES_DIR / "force_password.html").read_text(encoding="utf-8")
        rendered = template_text.replace("<!-- ERROR_MESSAGE -->", "<div class='alert-error'>A confirmação da nova senha não confere.</div>")
        return HTMLResponse(content=rendered, status_code=400)

    # Save new password hash & mark changed
    new_hash = hash_password(new_password.strip())
    set_setting("admin_password_hash", new_hash)
    set_setting("admin_password_changed", "1")

    return RedirectResponse(url="/admin", status_code=303)

@router.get("/admin/logout")
async def logout(request: Request):
    token = request.cookies.get("bipinho_admin_auth")
    if token and token in ACTIVE_ADMIN_SESSIONS:
        ACTIVE_ADMIN_SESSIONS.remove(token)
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("bipinho_admin_auth")
    return response

# ----------------- ADMIN DASHBOARD ----------------- #

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    check_ip_restriction(request)
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    if get_setting("admin_password_changed", "0") == "0":
        return RedirectResponse(url="/admin/trocar-senha-obrigatoria", status_code=303)
    admin_template = TEMPLATES_DIR / "admin.html"
    return HTMLResponse(content=admin_template.read_text(encoding="utf-8"))

@router.get("/admin/imprimir", response_class=HTMLResponse)
async def print_cards_page(request: Request):
    check_ip_restriction(request)
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    print_template = TEMPLATES_DIR / "print_cards.html"
    return HTMLResponse(content=print_template.read_text(encoding="utf-8"))

# ----------------- ADMIN APIS ----------------- #

@router.get("/api/admin/diagnostics")
async def api_admin_diagnostics(request: Request):
    require_auth(request)
    return get_full_diagnostics()

@router.get("/api/admin/info")
async def api_admin_info(request: Request):
    require_auth(request)
    lan_ip = get_lan_ip()
    port = DEFAULT_PORT
    settings = get_all_settings()
    active_reader = settings.get("reader_type", "USB")
    ffmpeg_status = get_ffmpeg_info()
    
    return {
        "tv_url": f"http://{lan_ip}:{port}",
        "lan_ip": lan_ip,
        "port": port,
        "reader_type": active_reader,
        "reader_tip": READER_TIPS.get(active_reader, ""),
        "next_auto_code": get_next_available_code(),
        "ffmpeg_installed": ffmpeg_status["found"],
        "ffmpeg_version": ffmpeg_status.get("version"),
        "admin_access_restriction": settings.get("admin_access_restriction", "all")
    }

@router.get("/api/admin/items")
async def api_get_items(request: Request):
    require_auth(request)
    return get_all_items()

@router.post("/api/admin/items")
async def api_create_item(
    request: Request,
    title: str = Form(...),
    author: str = Form(...),
    date: str = Form(...),
    code: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    require_auth(request)
    if not title.strip():
        raise HTTPException(status_code=400, detail="Título é obrigatório")
    
    # Auto code if empty
    final_code = (code.strip().upper() if code and code.strip() else get_next_available_code())
    
    # Check duplicate code
    existing = get_item_by_code(final_code)
    if existing:
        raise HTTPException(status_code=400, detail=f"O código '{final_code}' já está em uso!")

    # Check ffmpeg if video is uploaded
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext in {".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"} and not is_ffmpeg_installed():
        raise HTTPException(
            status_code=400,
            detail="O ffmpeg não está instalado no computador. Não é possível converter vídeos que não sejam MP4 direto. Por favor instale o ffmpeg ou envie arquivos .mp4 prontos."
        )

    # Read bytes safely
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="O arquivo enviado está vazio")

    try:
        media_type, safe_name, thumb_name, warning = save_and_process_media(
            file_bytes=file_bytes,
            original_filename=file.filename or "media_file",
            title=title
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    item_id = create_item(
        code=final_code,
        title=title,
        author=author,
        date=date,
        media_type=media_type,
        filename=safe_name,
        thumb_filename=thumb_name
    )

    return {
        "status": "success",
        "item_id": item_id,
        "code": final_code,
        "media_type": media_type,
        "warning": warning
    }

@router.put("/api/admin/items/{item_id}")
async def api_update_item(
    item_id: int,
    request: Request,
    title: str = Form(...),
    author: str = Form(...),
    date: str = Form(...),
    code: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    require_auth(request)
    current = get_item_by_id(item_id)
    if not current:
        raise HTTPException(status_code=404, detail="Desenho não encontrado")

    clean_code = code.strip().upper()
    if clean_code != current["code"]:
        other = get_item_by_code(clean_code)
        if other and other["id"] != item_id:
            raise HTTPException(status_code=400, detail=f"O código '{clean_code}' já está em uso!")

    new_filename = None
    new_thumb = None
    warning = None

    if file and file.filename:
        file_bytes = await file.read()
        if file_bytes:
            media_type, new_filename, new_thumb, warning = save_and_process_media(
                file_bytes=file_bytes,
                original_filename=file.filename,
                title=title
            )

    update_item(
        item_id=item_id,
        code=clean_code,
        title=title,
        author=author,
        date=date,
        filename=new_filename,
        thumb_filename=new_thumb
    )

    return {"status": "success", "warning": warning}

@router.delete("/api/admin/items/{item_id}")
async def api_delete_item(item_id: int, request: Request):
    require_auth(request)
    item = delete_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Desenho não encontrado")

    # Clean up physical files
    try:
        (UPLOADS_DIR / item["filename"]).unlink(missing_ok=True)
        (THUMBS_DIR / item["thumb_filename"]).unlink(missing_ok=True)
    except Exception:
        pass

    return {"status": "success", "deleted_id": item_id}

@router.get("/api/admin/settings")
async def api_get_settings(request: Request):
    require_auth(request)
    settings = get_all_settings()
    # Mask password hash from settings response
    safe_settings = dict(settings)
    safe_settings.pop("admin_password_hash", None)
    return safe_settings

class SettingsUpdateRequest(BaseModel):
    settings: Dict[str, Any]

@router.post("/api/admin/settings")
async def api_update_settings(payload: SettingsUpdateRequest, request: Request):
    require_auth(request)
    new_settings = payload.settings
    
    # Don't allow updating password directly via this endpoint
    new_settings.pop("admin_password_hash", None)
    new_settings.pop("admin_password", None)
    
    # Save to database
    set_settings(new_settings)

    # Broadcast event to TV so reader profile or sound changes take effect instantly
    await broadcast_event("settings_updated", new_settings)

    active_reader = new_settings.get("reader_type", get_setting("reader_type", "USB"))
    return {
        "status": "success",
        "reader_type": active_reader,
        "reader_tip": READER_TIPS.get(active_reader, "")
    }

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/api/admin/change-password")
async def api_change_password(payload: ChangePasswordRequest, request: Request):
    require_auth(request)
    saved_hash = get_setting("admin_password_hash", "")
    if not verify_password(payload.current_password, saved_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    if len(payload.new_password.strip()) < 4:
        raise HTTPException(status_code=400, detail="A nova senha deve ter no mínimo 4 caracteres")

    new_hash = hash_password(payload.new_password.strip())
    set_setting("admin_password_hash", new_hash)
    set_setting("admin_password_changed", "1")
    return {"status": "success", "message": "Senha alterada com sucesso!"}

@router.get("/api/admin/stats")
async def api_get_stats(request: Request):
    require_auth(request)
    return get_stats()

class SimulateScanRequest(BaseModel):
    code: str

@router.post("/api/admin/simulate-scan")
async def api_simulate_scan(payload: SimulateScanRequest, request: Request):
    require_auth(request)
    if not payload.code or not payload.code.strip():
        raise HTTPException(status_code=400, detail="Código não informado")
    result = await handle_barcode_scan(payload.code)
    return result

@router.post("/api/admin/reset-session")
async def api_reset_session(request: Request):
    require_auth(request)
    reset_session()
    await broadcast_event("session_reset", {"status": "reset"})
    return {"status": "success", "message": "Sessão reiniciada com sucesso!"}

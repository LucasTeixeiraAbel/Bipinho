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
from app.services.media_service import save_and_process_media
from app.services.session_manager import handle_barcode_scan, broadcast_event

router = APIRouter()

# In-memory admin session tokens (valid for server lifetime)
ACTIVE_ADMIN_SESSIONS = set()

def is_authenticated(request: Request) -> bool:
    token = request.cookies.get("bipinho_admin_auth")
    return token in ACTIVE_ADMIN_SESSIONS if token else False

def require_auth(request: Request):
    if not is_authenticated(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado"
        )

# ----------------- LOGIN / LOGOUT ----------------- #

@router.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/admin", status_code=303)
    login_template = TEMPLATES_DIR / "login.html"
    return HTMLResponse(content=login_template.read_text(encoding="utf-8"))

@router.post("/admin/login")
async def do_login(password: str = Form(...)):
    current_password = get_setting("admin_password", "bipinho123")
    if password == current_password:
        token = secrets.token_hex(24)
        ACTIVE_ADMIN_SESSIONS.add(token)
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(
            key="bipinho_admin_auth",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=86400 * 7 # 7 days
        )
        return response
    else:
        # Return login page with error
        template_text = (TEMPLATES_DIR / "login.html").read_text(encoding="utf-8")
        error_html = "<div class='alert-error'>Senha incorreta. Tente novamente.</div>"
        rendered = template_text.replace("<!-- ERROR_MESSAGE -->", error_html)
        return HTMLResponse(content=rendered, status_code=401)

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
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    admin_template = TEMPLATES_DIR / "admin.html"
    return HTMLResponse(content=admin_template.read_text(encoding="utf-8"))

@router.get("/admin/imprimir", response_class=HTMLResponse)
async def print_cards_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    print_template = TEMPLATES_DIR / "print_cards.html"
    return HTMLResponse(content=print_template.read_text(encoding="utf-8"))

# ----------------- ADMIN APIS ----------------- #

@router.get("/api/admin/info")
async def api_admin_info(request: Request):
    require_auth(request)
    lan_ip = get_lan_ip()
    port = DEFAULT_PORT
    settings = get_all_settings()
    active_reader = settings.get("reader_type", "USB")
    
    return {
        "tv_url": f"http://{lan_ip}:{port}",
        "lan_ip": lan_ip,
        "port": port,
        "reader_type": active_reader,
        "reader_tip": READER_TIPS.get(active_reader, ""),
        "next_auto_code": get_next_available_code()
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
    existing = get_item_by_id(item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Desenho não encontrado")

    clean_code = code.strip().upper()
    other = get_item_by_code(clean_code)
    if other and other["id"] != item_id:
        raise HTTPException(status_code=400, detail=f"O código '{clean_code}' já pertence a outro desenho!")

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
    # Don't send plain password hash if not necessary, but this is a private local app
    return settings

class SettingsUpdateRequest(BaseModel):
    settings: Dict[str, Any]

@router.post("/api/admin/settings")
async def api_update_settings(payload: SettingsUpdateRequest, request: Request):
    require_auth(request)
    new_settings = payload.settings
    
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
    current_saved = get_setting("admin_password", "bipinho123")
    if payload.current_password != current_saved:
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    if len(payload.new_password.strip()) < 4:
        raise HTTPException(status_code=400, detail="A nova senha deve ter no mínimo 4 caracteres")

    set_setting("admin_password", payload.new_password.strip())
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

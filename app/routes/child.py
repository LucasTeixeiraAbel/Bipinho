import asyncio
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from app.config import TEMPLATES_DIR
from app.database import get_all_settings
from app.services.schedule_service import check_schedule_allowed
from app.services.session_manager import (
    handle_barcode_scan,
    get_current_session_info,
    trigger_coloring_pause,
    add_sse_client,
    remove_sse_client
)

router = APIRouter()

class ScanRequest(BaseModel):
    code: str
    is_video_playing: bool = False

class WatchTimeRequest(BaseModel):
    seconds: float

@router.get("/", response_class=HTMLResponse)
async def child_screen():
    template_file = TEMPLATES_DIR / "child.html"
    if not template_file.exists():
        raise HTTPException(status_code=500, detail="child.html não encontrado")
    return HTMLResponse(content=template_file.read_text(encoding="utf-8"))

@router.get("/api/schedule/status")
async def api_schedule_status():
    """Returns current schedule/restriction status for the TV screen."""
    return check_schedule_allowed()

@router.post("/api/scan")
async def api_scan_barcode(req: ScanRequest):
    if not req.code or not req.code.strip():
        raise HTTPException(status_code=400, detail="Código inválido")

    # Parent key can unlock exceptionally even if schedule is blocked
    settings = get_all_settings()
    parent_code = settings.get("parent_unlock_code", "PAIS-LIBERAR-99").strip().upper()
    is_parent_key = (req.code.strip().upper() == parent_code)

    # Schedule check: block scan if outside allowed window
    schedule = check_schedule_allowed()
    if not schedule["allowed"] and not is_parent_key:
        return {
            "status": "schedule_blocked",
            "reason": schedule["reason"],
            "tv_blocked": schedule.get("tv_blocked", False),
        }

    result = await handle_barcode_scan(req.code, is_video_playing=req.is_video_playing)
    return result

@router.post("/api/session/report-watch-time")
async def api_report_watch_time(req: WatchTimeRequest):
    from app.database import add_watched_seconds
    total_watched = add_watched_seconds(req.seconds)
    settings = get_all_settings()
    count_mode = settings.get("count_mode", "leituras")
    limit_minutes = int(settings.get("watch_time_limit_minutes", 15))
    limit_sec = limit_minutes * 60

    if count_mode == "tempo_assistido":
        if total_watched >= limit_sec:
            await trigger_coloring_pause()
            return {
                "watched_seconds": total_watched,
                "limit_reached": True,
                "is_paused": True
            }
        return {
            "watched_seconds": total_watched,
            "limit_reached": False,
            "is_paused": False
        }

    return {
        "watched_seconds": total_watched,
        "limit_reached": False,
        "is_paused": False
    }

@router.get("/api/session/status")
async def api_session_status():
    return get_current_session_info()

@router.post("/api/session/trigger-pause")
async def api_trigger_pause():
    result = await trigger_coloring_pause()
    return result

@router.get("/api/reader-profile")
async def api_reader_profile():
    settings = get_all_settings()
    active_type = settings.get("reader_type", "USB")

    # Map settings to profile
    if active_type == "Bluetooth":
        max_interchar = int(settings.get("reader_bt_max_interchar_ms", 300))
        terminator = settings.get("reader_bt_terminator", "Enter")
        prefix = settings.get("reader_bt_prefix_strip", "")
        suffix = settings.get("reader_bt_suffix_strip", "")
        min_len = int(settings.get("reader_bt_min_length", 3))
        timeout_ms = int(settings.get("reader_bt_timeout_ms", 1000))
    elif active_type == "2.4G":
        max_interchar = int(settings.get("reader_24g_max_interchar_ms", 100))
        terminator = settings.get("reader_24g_terminator", "Enter")
        prefix = settings.get("reader_24g_prefix_strip", "")
        suffix = settings.get("reader_24g_suffix_strip", "")
        min_len = int(settings.get("reader_24g_min_length", 3))
        timeout_ms = int(settings.get("reader_24g_timeout_ms", 500))
    else: # USB
        max_interchar = int(settings.get("reader_usb_max_interchar_ms", 100))
        terminator = settings.get("reader_usb_terminator", "Enter")
        prefix = settings.get("reader_usb_prefix_strip", "")
        suffix = settings.get("reader_usb_suffix_strip", "")
        min_len = int(settings.get("reader_usb_min_length", 3))
        timeout_ms = int(settings.get("reader_usb_timeout_ms", 500))

    return {
        "reader_type": active_type,
        "max_interchar_ms": max_interchar,
        "terminator": terminator,
        "prefix_strip": prefix,
        "suffix_strip": suffix,
        "min_length": min_len,
        "timeout_ms": timeout_ms
    }

@router.get("/api/events")
async def api_events(request: Request):
    """Server-Sent Events endpoint to keep TV synchronized in real-time."""
    queue = add_sse_client()

    async def event_generator():
        try:
            # Initial connection ping
            yield "event: connected\ndata: {\"status\": \"ok\"}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    # Wait for next event or send keepalive ping every 15s
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: message\ndata: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            remove_sse_client(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

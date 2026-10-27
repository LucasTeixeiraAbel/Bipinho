"""
Bipinho — Etapa 2 Test Suite: Confiabilidade na TV
Covers: SSE reconnection overlay, video scan behavior, watch time mode,
backup/restore zip, and count mode "tempo_assistido".
"""
import io
import zipfile
import time
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db, reset_session, set_setting, get_setting, add_watched_seconds
from app.seed import seed_sample_data
from app.services.backup_service import create_backup_zip, validate_backup_zip, restore_backup_zip
from app.services.auth_service import hash_password


def setup_authed_client():
    """Helper: returns authenticated TestClient with force-change bypass."""
    init_db()
    seed_sample_data()
    reset_session()
    # Ensure password is "changed" so we don't get redirected to force-change
    set_setting("admin_password_changed", "1")
    set_setting("admin_password_hash", hash_password("test_senha_123"))
    client = TestClient(app)
    r = client.post("/admin/login", data={"password": "test_senha_123"}, follow_redirects=False)
    assert r.status_code == 303, f"Login failed: {r.status_code}"
    return client


def test_video_scan_behavior_interrupt():
    """When behavior is 'interrupt', scan during video plays new item normally."""
    client = setup_authed_client()
    set_setting("video_scan_behavior", "interrupt")

    # Scan first item
    res = client.post("/api/scan", json={"code": "BIP-1001", "is_video_playing": False})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"

    # Scan second item while "video playing" — interrupt mode should allow it
    # Need to bypass debounce so scan different code
    time.sleep(0.1)
    res = client.post("/api/scan", json={"code": "BIP-1002", "is_video_playing": True})
    assert res.status_code == 200
    data = res.json()
    # In interrupt mode, the new code should play (not be blocked)
    assert data["status"] == "success"
    assert data["item"]["code"] == "BIP-1002"

    print("✓ test_video_scan_behavior_interrupt passed")


def test_video_scan_behavior_ignore():
    """When behavior is 'ignore', scan during video is blocked with status 'video_playing_ignored'."""
    init_db()
    seed_sample_data()
    reset_session()
    set_setting("video_scan_behavior", "ignore")
    set_setting("admin_password_changed", "1")
    set_setting("admin_password_hash", hash_password("test_senha_123"))

    client = TestClient(app)

    # First scan to set video playing state
    client.post("/api/scan", json={"code": "BIP-1001", "is_video_playing": False})
    # Now scan while video is playing — should be ignored
    time.sleep(0.1)
    res = client.post("/api/scan", json={"code": "BIP-1002", "is_video_playing": True})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "video_playing_ignored"
    assert "reprodução" in data["message"] or "Aguarde" in data["message"]

    print("✓ test_video_scan_behavior_ignore passed")


def test_watch_time_report_no_pause():
    """Report watch time below limit does not trigger pause."""
    init_db()
    seed_sample_data()
    reset_session()
    set_setting("count_mode", "tempo_assistido")
    set_setting("watch_time_limit_minutes", "10")

    client = TestClient(app)

    # Report 5 minutes (300 seconds) — below 10 min limit
    res = client.post("/api/session/report-watch-time", json={"seconds": 300.0})
    assert res.status_code == 200
    data = res.json()
    assert data["watched_seconds"] >= 300.0
    assert data["limit_reached"] is False
    assert data["is_paused"] is False

    print("✓ test_watch_time_report_no_pause passed")


def test_watch_time_report_triggers_pause():
    """Report watch time at/above limit triggers 'Hora de colorir!' pause."""
    init_db()
    seed_sample_data()
    reset_session()
    set_setting("count_mode", "tempo_assistido")
    set_setting("watch_time_limit_minutes", "1")

    client = TestClient(app)

    # Report 61 seconds — above 1 min (60 sec) limit
    res = client.post("/api/session/report-watch-time", json={"seconds": 61.0})
    assert res.status_code == 200
    data = res.json()
    assert data["limit_reached"] is True
    assert data["is_paused"] is True

    print("✓ test_watch_time_report_triggers_pause passed")


def test_backup_export_is_valid_zip():
    """Backup export creates a valid zip with database and media dirs."""
    init_db()
    seed_sample_data()

    buf = create_backup_zip()
    content = buf.read()
    assert len(content) > 100

    is_valid, err, meta = validate_backup_zip(content)
    assert is_valid, f"Backup zip should be valid: {err}"
    assert meta["has_db"] is True

    print("✓ test_backup_export_is_valid_zip passed")


def test_backup_restore_via_api():
    """Admin backup/restore endpoints work correctly (export returns zip, restore accepts it)."""
    client = setup_authed_client()

    # Export backup via API
    res = client.get("/api/admin/backup/export")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert "attachment" in res.headers.get("content-disposition", "")
    zip_bytes = res.content
    assert len(zip_bytes) > 100

    # Validate zip structure
    is_valid, err, meta = validate_backup_zip(zip_bytes)
    assert is_valid, f"Exported zip must be valid: {err}"

    # Restore via API
    restore_res = client.post(
        "/api/admin/backup/restore",
        files={"file": ("backup.zip", io.BytesIO(zip_bytes), "application/zip")}
    )
    assert restore_res.status_code == 200
    assert restore_res.json()["status"] == "success"

    print("✓ test_backup_restore_via_api passed")


def test_backup_invalid_zip_rejected():
    """Restore endpoint rejects a non-zip file with HTTP 400."""
    client = setup_authed_client()

    fake_content = b"this is not a zip file at all"
    res = client.post(
        "/api/admin/backup/restore",
        files={"file": ("bad.zip", io.BytesIO(fake_content), "application/zip")}
    )
    assert res.status_code == 400
    assert "zip" in res.json()["detail"].lower() or "válido" in res.json()["detail"].lower()

    print("✓ test_backup_invalid_zip_rejected passed")


def test_child_screen_has_connection_overlay():
    """Child TV screen HTML contains the reconnection overlay element."""
    init_db()
    seed_sample_data()
    client = TestClient(app)

    res = client.get("/")
    assert res.status_code == 200
    assert "connection-toast" in res.text
    assert "Bipinho já volta" in res.text

    print("✓ test_child_screen_has_connection_overlay passed")


def test_session_status_includes_new_fields():
    """/api/session/status returns video_scan_behavior and watch_time fields."""
    init_db()
    seed_sample_data()
    reset_session()
    client = TestClient(app)

    res = client.get("/api/session/status")
    assert res.status_code == 200
    data = res.json()
    assert "video_scan_behavior" in data
    assert "watch_time_limit_minutes" in data
    assert "watched_seconds" in data

    print("✓ test_session_status_includes_new_fields passed")


def test_etapa2_all():
    """Run all Etapa 2 tests."""
    print("=" * 50)
    print("RUNNING ETAPA 2 TEST SUITE")
    print("=" * 50)

    test_video_scan_behavior_interrupt()
    test_video_scan_behavior_ignore()
    test_watch_time_report_no_pause()
    test_watch_time_report_triggers_pause()
    test_backup_export_is_valid_zip()
    test_backup_restore_via_api()
    test_backup_invalid_zip_rejected()
    test_child_screen_has_connection_overlay()
    test_session_status_includes_new_fields()

    print("=" * 50)
    print("ALL 9 ETAPA 2 TESTS PASSED SUCCESSFULLY!")
    print("=" * 50)


if __name__ == "__main__":
    test_etapa2_all()

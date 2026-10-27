"""
Bipinho — Etapa 3 Test Suite: Controle dos Pais
Covers:
1. Schedule limits (hours, days of week, max sessions per day, manual block).
2. "O Bipinho está dormindo" & Parent key exceptional release.
3. Live admin panel APIs (live-status, TV block/release, end pause).
4. Viewing history & daily session tracking.
5. Movement challenges list & random challenge.
6. Bulk import from local directory.
7. Card printing separation of Parent Key.
"""
import io
import os
import shutil
import tempfile
from datetime import datetime, date, time as dt_time, timedelta
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.database import (
    init_db, reset_session, set_setting, get_setting,
    get_all_challenges, set_challenges, get_random_challenge,
    get_today_session_count, start_daily_session, end_daily_session,
    get_weekly_history, get_item_by_code
)
from app.seed import seed_sample_data
from app.services.auth_service import hash_password
from app.services.schedule_service import check_schedule_allowed


def setup_client():
    init_db()
    seed_sample_data()
    reset_session()
    set_setting("admin_password_changed", "1")
    set_setting("admin_password_hash", hash_password("test_senha_123"))
    set_setting("schedule_enabled", "0")
    set_setting("tv_blocked", "0")
    set_setting("exceptional_unlock", "0")
    client = TestClient(app)
    r = client.post("/admin/login", data={"password": "test_senha_123"}, follow_redirects=False)
    assert r.status_code == 303, f"Login failed: {r.status_code}"
    return client


def test_schedule_disabled_allows_all():
    """When schedule_enabled is 0, check_schedule_allowed returns True."""
    setup_client()
    set_setting("schedule_enabled", "0")
    set_setting("tv_blocked", "0")
    res = check_schedule_allowed()
    assert res["allowed"] is True
    print("✓ test_schedule_disabled_allows_all passed")


def test_schedule_manual_tv_block():
    """Manual tv_blocked=1 immediately blocks TV, regardless of schedule."""
    setup_client()
    set_setting("tv_blocked", "1")
    res = check_schedule_allowed()
    assert res["allowed"] is False
    assert res["tv_blocked"] is True
    assert "bloqueada" in res["reason"].lower()

    # Release TV
    set_setting("tv_blocked", "0")
    res2 = check_schedule_allowed()
    assert res2["allowed"] is True
    print("✓ test_schedule_manual_tv_block passed")


def test_schedule_hours_restriction():
    """Check schedule outside allowed hours is blocked."""
    setup_client()
    set_setting("schedule_enabled", "1")
    set_setting("allowed_days", "0,1,2,3,4,5,6")
    set_setting("allowed_start_time", "08:00")
    set_setting("allowed_end_time", "12:00")

    # Simulate 06:00 (outside)
    outside_dt = datetime(2026, 10, 26, 6, 0, 0)
    res = check_schedule_allowed(override_now=outside_dt)
    assert res["allowed"] is False
    assert res["outside_hours"] is True

    # Simulate 10:00 (inside)
    inside_dt = datetime(2026, 10, 26, 10, 0, 0)
    res2 = check_schedule_allowed(override_now=inside_dt)
    assert res2["allowed"] is True
    assert res2["outside_hours"] is False
    print("✓ test_schedule_hours_restriction passed")


def test_schedule_days_restriction():
    """Check schedule outside allowed days is blocked."""
    setup_client()
    set_setting("schedule_enabled", "1")
    # 2026-10-26 is Monday (weekday = 0)
    monday_dt = datetime(2026, 10, 26, 10, 0, 0)

    # Allow only weekends (5,6)
    set_setting("allowed_days", "5,6")
    set_setting("allowed_start_time", "00:00")
    set_setting("allowed_end_time", "23:59")

    res = check_schedule_allowed(override_now=monday_dt)
    assert res["allowed"] is False
    assert res["outside_days"] is True

    # Now allow Mondays (0)
    set_setting("allowed_days", "0,5,6")
    res2 = check_schedule_allowed(override_now=monday_dt)
    assert res2["allowed"] is True
    print("✓ test_schedule_days_restriction passed")


def test_scan_blocked_by_schedule_and_parent_unlock():
    """Scan is blocked when schedule is inactive; parent key unlocks exceptionally."""
    client = setup_client()
    set_setting("schedule_enabled", "1")
    set_setting("tv_blocked", "1")

    # Regular scan when blocked
    r = client.post("/api/scan", json={"code": "BIP-1001", "is_video_playing": False})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "schedule_blocked"
    assert "bloqueada" in data["reason"].lower()

    # Scan Parent Key code -> should unlock exceptionally
    parent_code = get_setting("parent_unlock_code", "PAIS-LIBERAR-99")
    r_parent = client.post("/api/scan", json={"code": parent_code, "is_video_playing": False})
    assert r_parent.status_code == 200
    data_parent = r_parent.json()
    assert data_parent["status"] == "parent_unlock"

    # Now TV is unblocked and exceptional unlock is granted
    assert get_setting("tv_blocked") == "0"
    assert get_setting("exceptional_unlock") == "1"

    # Normal scan now succeeds!
    r_after = client.post("/api/scan", json={"code": "BIP-1001", "is_video_playing": False})
    assert r_after.status_code == 200
    assert r_after.json()["status"] == "success"

    print("✓ test_scan_blocked_by_schedule_and_parent_unlock passed")


def test_movement_challenges_defaults_and_api():
    """Movement challenges are seeded (15 items) and editable via API."""
    client = setup_client()

    # Check seeded defaults
    challenges = get_all_challenges()
    assert len(challenges) >= 15
    assert any("pulinho" in c["challenge"].lower() for c in challenges)

    # Random challenge picker works
    rand = get_random_challenge()
    assert rand is not None
    assert len(rand) > 3

    # API get challenges
    r = client.get("/api/admin/challenges")
    assert r.status_code == 200
    assert len(r.json()["challenges"]) >= 15

    # API update challenges
    new_list = [
        {"challenge": "Pule 5 vezes como pipoca!", "enabled": True},
        {"challenge": "Gire os braços como moinho!", "enabled": True}
    ]
    r_post = client.post("/api/admin/challenges", json={"challenges": new_list})
    assert r_post.status_code == 200
    assert r_post.json()["count"] == 2

    # Verify updated
    updated = get_all_challenges()
    assert len(updated) == 2
    assert updated[0]["challenge"] == "Pule 5 vezes como pipoca!"

    print("✓ test_movement_challenges_defaults_and_api passed")


def test_live_panel_apis():
    """Live admin APIs (live-status, tv/block, tv/release, session/end-pause)."""
    client = setup_client()

    # Get live status
    r = client.get("/api/admin/live-status")
    assert r.status_code == 200
    d = r.json()
    assert "current_scans" in d
    assert "max_scans" in d
    assert "schedule" in d

    # Block TV via live API
    r_block = client.post("/api/admin/tv/block")
    assert r_block.status_code == 200
    assert r_block.json()["tv_blocked"] is True
    assert get_setting("tv_blocked") == "1"

    # Release TV via live API
    r_rel = client.post("/api/admin/tv/release")
    assert r_rel.status_code == 200
    assert r_rel.json()["tv_blocked"] is False
    assert get_setting("tv_blocked") == "0"

    # End pause via live API
    r_end = client.post("/api/admin/session/end-pause")
    assert r_end.status_code == 200
    assert r_end.json()["is_paused"] is False

    print("✓ test_live_panel_apis passed")


def test_history_tracking_and_api():
    """Daily session and viewing history tracking and /api/admin/history API."""
    client = setup_client()

    # Trigger a scan
    client.post("/api/scan", json={"code": "BIP-1001", "is_video_playing": False})

    # Trigger pause
    client.post("/api/session/trigger-pause")

    # Check history endpoint
    r = client.get("/api/admin/history?days=7")
    assert r.status_code == 200
    h_data = r.json()
    assert "history" in h_data
    assert len(h_data["history"]) == 7

    # Check specific date history
    today_str = date.today().isoformat()
    r_date = client.get(f"/api/admin/history/{today_str}")
    assert r_date.status_code == 200
    d_info = r_date.json()
    assert d_info["date"] == today_str
    assert d_info["session_count"] >= 1

    print("✓ test_history_tracking_and_api passed")


def test_bulk_import_from_folder():
    """Bulk import registers files from a directory, generating codes & titles."""
    client = setup_client()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create dummy image and dummy text file
        img1_path = Path(tmpdir) / "Desenho_do_Ursinho.png"
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        img.save(img1_path)

        img2_path = Path(tmpdir) / "Aventuras_na_Floresta.jpg"
        img2 = Image.new("RGB", (100, 100), color=(0, 255, 0))
        img2.save(img2_path)

        # Non-media file (should be ignored)
        (Path(tmpdir) / "notas.txt").write_text("anotações")

        r = client.post(
            "/api/admin/bulk-import",
            json={"folder_path": tmpdir, "author": "Estúdio Bipinho"}
        )
        assert r.status_code == 200
        res = r.json()
        assert res["status"] == "success"
        assert res["imported_count"] == 2
        assert res["error_count"] == 0

        # Check items were created
        imported_codes = [it["code"] for it in res["imported"]]
        for c in imported_codes:
            item = get_item_by_code(c)
            assert item is not None
            assert item["author"] == "Estúdio Bipinho"

    # Non-existent folder returns 400
    r_bad = client.post(
        "/api/admin/bulk-import",
        json={"folder_path": "C:\\PastaInexistente123_xyz", "author": "Teste"}
    )
    assert r_bad.status_code == 400

    print("✓ test_bulk_import_from_folder passed")


def test_print_cards_parent_key_separation():
    """Print cards template contains the separated parent key page markings."""
    client = setup_client()
    r = client.get("/admin/imprimir")
    assert r.status_code == 200
    html = r.text
    assert "NÃO COLOCAR NA PASTINHA DA CRIANÇA" in html
    assert "Chave dos Pais" in html
    assert "Desenho Surpresa" in html
    print("✓ test_print_cards_parent_key_separation passed")


def test_etapa3_all():
    print("=" * 50)
    print("RUNNING ETAPA 3 TEST SUITE: CONTROLE DOS PAIS")
    print("=" * 50)

    test_schedule_disabled_allows_all()
    test_schedule_manual_tv_block()
    test_schedule_hours_restriction()
    test_schedule_days_restriction()
    test_scan_blocked_by_schedule_and_parent_unlock()
    test_movement_challenges_defaults_and_api()
    test_live_panel_apis()
    test_history_tracking_and_api()
    test_bulk_import_from_folder()
    test_print_cards_parent_key_separation()

    print("=" * 50)
    print("ALL 10 ETAPA 3 TESTS PASSED SUCCESSFULLY!")
    print("=" * 50)


if __name__ == "__main__":
    test_etapa3_all()

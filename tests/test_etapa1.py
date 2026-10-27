import io
import time
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.database import (
    init_db, reset_session, set_setting, get_setting,
    get_all_items, create_item
)
from app.services.auth_service import hash_password, verify_password
from app.services.rate_limiter import _LOGIN_ATTEMPTS, check_ip_lockout, record_login_success
from app.services.diagnostic_service import get_full_diagnostics, get_ffmpeg_info

def setup_clean_db():
    init_db()
    reset_session()
    _LOGIN_ATTEMPTS.clear()
    # Ensure default password and unchanged state
    set_setting("admin_password_hash", hash_password("bipinho123"))
    set_setting("admin_password_changed", "0")
    set_setting("admin_access_restriction", "all")
    set_setting("login_max_attempts", "5")
    set_setting("login_lockout_minutes", "15")

# 1. test_password_hash_and_salt
def test_password_hash_and_salt():
    p1 = "minhaSenhaSuperSegura_99"
    h1 = hash_password(p1)
    h2 = hash_password(p1)

    # Different salts produce different hashes
    assert h1 != h2, "Hashes with independent random salts must be different"
    assert h1.startswith("pbkdf2:sha256:100000$"), "Must use PBKDF2 with 100k iterations"

    # Verification
    assert verify_password(p1, h1) is True
    assert verify_password(p1, h2) is True
    assert verify_password("senhaErrada", h1) is False
    assert verify_password("", h1) is False
    assert verify_password(p1, "") is False
    assert verify_password(p1, "invalid_hash_string") is False
    print("✓ test_password_hash_and_salt passed")

# 2. test_first_login_forces_change
def test_first_login_forces_change():
    setup_clean_db()
    client = TestClient(app)

    # Login with initial default password
    res = client.post("/admin/login", data={"password": "bipinho123"}, follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/admin/trocar-senha-obrigatoria"
    assert "bipinho_admin_auth" in res.cookies

    # Trying to access /admin directly while admin_password_changed == "0" redirects to force-change
    res = client.get("/admin", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/admin/trocar-senha-obrigatoria"

    # Attempting to reuse old default password "bipinho123" must be rejected (400)
    res = client.post(
        "/admin/trocar-senha-obrigatoria",
        data={"new_password": "bipinho123", "confirm_password": "bipinho123"}
    )
    assert res.status_code == 400
    assert "bipinho123" in res.text

    # Attempting password shorter than 4 chars rejected (400)
    res = client.post(
        "/admin/trocar-senha-obrigatoria",
        data={"new_password": "abc", "confirm_password": "abc"}
    )
    assert res.status_code == 400

    # Changing to a strong new password
    new_pwd = "NovaSenhaForte2026!"
    res = client.post(
        "/admin/trocar-senha-obrigatoria",
        data={"new_password": new_pwd, "confirm_password": new_pwd},
        follow_redirects=False
    )
    assert res.status_code == 303
    assert res.headers["location"] == "/admin"

    # Verify database state
    assert get_setting("admin_password_changed") == "1"
    assert verify_password(new_pwd, get_setting("admin_password_hash")) is True

    # Now /admin is unlocked and accessible
    res = client.get("/admin")
    assert res.status_code == 200
    assert "Bipinho" in res.text
    print("✓ test_first_login_forces_change passed")

# 3. test_login_rate_limiting
def test_login_rate_limiting():
    setup_clean_db()
    _LOGIN_ATTEMPTS.clear()
    set_setting("login_max_attempts", "5")
    set_setting("login_lockout_minutes", "15")

    client = TestClient(app)
    ip_header = {"X-Forwarded-For": "192.168.1.188"}

    # 5 consecutive failed attempts
    for i in range(1, 6):
        res = client.post("/admin/login", data={"password": f"senha_errada_{i}"}, headers=ip_header)
        if i < 5:
            assert res.status_code == 401
            assert "Restam" in res.text
        else:
            # 5th failure triggers lockout
            assert res.status_code == 429
            assert "bloqueado" in res.text.lower()

    # 6th attempt is blocked with 429
    res = client.post("/admin/login", data={"password": "qualquer_coisa"}, headers=ip_header)
    assert res.status_code == 429
    assert "Muitas tentativas incorretas" in res.text or "bloqueado" in res.text.lower()

    # Different IP is not blocked
    other_ip = {"X-Forwarded-For": "192.168.1.199"}
    res = client.post("/admin/login", data={"password": "senha_incorreta"}, headers=other_ip)
    assert res.status_code == 401

    _LOGIN_ATTEMPTS.clear()
    print("✓ test_login_rate_limiting passed")

# 4. test_admin_access_restriction
def test_admin_access_restriction():
    setup_clean_db()
    set_setting("admin_access_restriction", "localhost_only")

    client = TestClient(app)

    # External IP request is forbidden (403)
    ext_header = {"X-Forwarded-For": "192.168.1.50"}
    res = client.get("/admin", headers=ext_header)
    assert res.status_code == 403
    assert "restrito exclusivamente ao computador local" in res.text

    res = client.get("/admin/login", headers=ext_header)
    assert res.status_code == 403

    # Localhost requests are permitted
    local_header = {"X-Forwarded-For": "127.0.0.1"}
    res = client.get("/admin/login", headers=local_header, follow_redirects=False)
    assert res.status_code == 200

    # Reset to all
    set_setting("admin_access_restriction", "all")
    res = client.get("/admin/login", headers=ext_header, follow_redirects=False)
    assert res.status_code == 200
    print("✓ test_admin_access_restriction passed")

# 5. test_diagnostics_api
def test_diagnostics_api():
    setup_clean_db()
    set_setting("admin_password_changed", "1")
    client = TestClient(app)

    # Login to acquire session cookie
    client.post("/admin/login", data={"password": "bipinho123"}, follow_redirects=False)

    res = client.get("/api/admin/diagnostics")
    assert res.status_code == 200
    data = res.json()

    assert data["version"] == "1.1.0"
    assert "disk" in data
    assert "free_gb" in data["disk"]
    assert "total_gb" in data["disk"]
    assert "database" in data
    assert data["database"]["ok"] is True
    assert "ffmpeg" in data
    assert "sleep" in data
    assert "network" in data
    assert "tv_url" in data["network"]
    print("✓ test_diagnostics_api passed")

# 6. test_ffmpeg_missing_alert
def test_ffmpeg_missing_alert():
    setup_clean_db()
    set_setting("admin_password_changed", "1")
    client = TestClient(app)
    client.post("/admin/login", data={"password": "bipinho123"}, follow_redirects=False)

    # 1. When ffmpeg is missing, uploading non-MP4 video raises 400 with friendly message
    with patch("app.routes.admin.is_ffmpeg_installed", return_value=False):
        fake_mkv = io.BytesIO(b"\x1a\x45\xdf\xa3fake_mkv_data")
        res = client.post(
            "/api/admin/items",
            data={
                "title": "Desenho Formato MKV",
                "author": "Papai",
                "date": "2026-10-18",
                "code": "BIP-TEST-MKV"
            },
            files={"file": ("video.mkv", fake_mkv, "video/x-matroska")}
        )
        assert res.status_code == 400
        detail = res.json()["detail"].lower()
        assert "ffmpeg não está instalado" in detail or "não é possível converter" in detail

    # 2. When ffmpeg is missing, diagnostic service reflects found=False and informative error
    with patch("shutil.which", return_value=None):
        info = get_ffmpeg_info()
        assert info["found"] is False
        assert "error" in info
        assert "não encontrado" in info["error"].lower()

    print("✓ test_ffmpeg_missing_alert passed")

def run_all_etapa1_tests():
    print("=" * 50)
    print("RUNNING ETAPA 1 TEST SUITE")
    print("=" * 50)
    test_password_hash_and_salt()
    test_first_login_forces_change()
    test_login_rate_limiting()
    test_admin_access_restriction()
    test_diagnostics_api()
    test_ffmpeg_missing_alert()
    print("=" * 50)
    print("ALL 6 ETAPA 1 TESTS PASSED SUCCESSFULLY!")
    print("=" * 50)

if __name__ == "__main__":
    run_all_etapa1_tests()

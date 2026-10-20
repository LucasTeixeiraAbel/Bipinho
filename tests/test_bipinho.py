import time
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, reset_session, set_setting, get_setting
from app.seed import seed_sample_data

def test_full_bipinho_flow():
    init_db()
    seed_sample_data()
    reset_session()

    client = TestClient(app)

    # 1. Child Screen (GET /)
    res = client.get("/")
    assert res.status_code == 200
    assert "Bipinho" in res.text
    assert "barcode-input" in res.text

    # 2. Barcode SVG Generation
    res = client.get("/api/barcode/BIP-1001.svg")
    assert res.status_code == 200
    assert "image/svg+xml" in res.headers["content-type"]
    assert "<svg" in res.text

    # 3. HTTP Range Requests (Video Streaming RFC 7233)
    res = client.get("/media/uploads/sample_colors.mp4", headers={"Range": "bytes=0-99"})
    assert res.status_code == 206
    assert "bytes 0-99/" in res.headers.get("content-range", "")
    assert len(res.content) == 100

    # 4. Reader Profile API
    res = client.get("/api/reader-profile")
    assert res.status_code == 200
    data = res.json()
    assert "reader_type" in data
    assert "max_interchar_ms" in data

    # 5. Scan 1st Drawing (BIP-1001)
    res = client.post("/api/scan", json={"code": "BIP-1001"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["item"]["code"] == "BIP-1001"
    assert data["current_scans"] == 1
    assert data["limit_reached"] is False

    # 6. Debounce test (immediate repeat)
    res = client.post("/api/scan", json={"code": "BIP-1001"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "debounce_ignored"

    # 7. Scan Unknown Code
    res = client.post("/api/scan", json={"code": "CODIGO-INEXISTENTE-999"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "not_found"
    assert "Ops" in data["message"]

    # 8. Scan 2nd Drawing (BIP-1002)
    res = client.post("/api/scan", json={"code": "BIP-1002"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["current_scans"] == 2

    # 9. Scan 3rd Drawing (BIP-1003) -> Limit Reached!
    res = client.post("/api/scan", json={"code": "BIP-1003"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["current_scans"] == 3
    assert data["limit_reached"] is True

    # 10. Trigger Pause ("Hora de colorir!")
    res = client.post("/api/session/trigger-pause")
    assert res.status_code == 200
    data = res.json()
    assert data["is_paused"] is True
    assert data["remaining_seconds"] > 0

    # 11. During Pause, regular drawings are ignored
    res = client.post("/api/scan", json={"code": "BIP-1001"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "in_pause"

    # 12. Unlock with Parent Secret Code
    parent_code = get_setting("parent_unlock_code", "PAIS-LIBERAR-99")
    res = client.post("/api/scan", json={"code": parent_code})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "parent_unlock"

    # Check session state reset
    res = client.get("/api/session/status")
    data = res.json()
    assert data["is_paused"] is False
    assert data["current_scans"] == 0

    # 13. Surprise Code
    surprise_code = get_setting("surprise_code", "BIP-SURPRESA")
    res = client.post("/api/scan", json={"code": surprise_code})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["is_surprise"] is True
    assert data["item"] is not None

    # 14. Admin Security
    # Access without auth -> redirect to /admin/login
    res = client.get("/admin", follow_redirects=False)
    assert res.status_code == 303
    assert "/admin/login" in res.headers["location"]

    # Wrong password -> 401
    res = client.post("/admin/login", data={"password": "senha_errada"})
    assert res.status_code == 401

    # Correct password -> login success with cookie
    res = client.post("/admin/login", data={"password": "bipinho123"}, follow_redirects=False)
    assert res.status_code == 303
    assert "bipinho_admin_auth" in res.cookies

    # Access /admin with cookie
    res = client.get("/admin")
    assert res.status_code == 200
    assert "Bipinho" in res.text

    # Print A4 page
    res = client.get("/admin/imprimir")
    assert res.status_code == 200
    assert "Folha de Códigos" in res.text

    # 15. Switch Reader Profile to Bluetooth in Admin
    res = client.post("/api/admin/settings", json={"settings": {"reader_type": "Bluetooth"}})
    assert res.status_code == 200

    # Verify TV reads updated Bluetooth profile (300ms)
    res = client.get("/api/reader-profile")
    assert res.status_code == 200
    data = res.json()
    assert data["reader_type"] == "Bluetooth"
    assert data["max_interchar_ms"] == 300

    print("ALL 15 TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_full_bipinho_flow()

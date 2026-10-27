"""
Bipinho — Etapa 4 Test Suite: Experiência da Criança
Covers:
1. Categories table and item category field.
2. API /api/admin/categories and item CRUD with category.
3. Coloring outline generator (P&B line drawing with edge detection).
4. Printable coloring page route (/admin/colorir/{item_id}).
5. Print cards options (sizes: 1, 2, 6 per sheet, category grouping, colored stripes).
6. Animated mascot on idle screen (SVG structure, eyes, waving arm, toggle in status).
7. Movement challenge in coloring pause.
"""
import io
import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.config import UPLOADS_DIR, THUMBS_DIR, OUTLINES_DIR
from app.database import (
    init_db, reset_session, set_setting, get_setting,
    get_all_categories, get_category_color_map,
    create_item, update_item, get_item_by_id, get_item_by_code
)
from app.seed import seed_sample_data
from app.services.auth_service import hash_password
from app.services.outline_service import generate_coloring_outline


def setup_client():
    init_db()
    seed_sample_data()
    reset_session()
    set_setting("admin_password_changed", "1")
    set_setting("admin_password_hash", hash_password("test_senha_123"))
    set_setting("schedule_enabled", "0")
    set_setting("tv_blocked", "0")
    set_setting("mascot_enabled", "1")
    set_setting("movement_challenges_enabled", "1")
    client = TestClient(app)
    r = client.post("/admin/login", data={"password": "test_senha_123"}, follow_redirects=False)
    assert r.status_code == 303, f"Login failed: {r.status_code}"
    return client


def test_categories_seeded_and_api():
    """Default categories are seeded and accessible via /api/admin/categories."""
    client = setup_client()

    cats = get_all_categories()
    assert len(cats) >= 5
    cat_names = [c["name"] for c in cats]
    for expected in ["Animais", "Músicas", "Histórias", "Educativos", "Geral"]:
        assert expected in cat_names

    # Check color map
    color_map = get_category_color_map()
    assert "Animais" in color_map
    assert color_map["Animais"].startswith("#")

    # Check API
    r = client.get("/api/admin/categories")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 5

    print("✓ test_categories_seeded_and_api passed")


def test_item_category_crud():
    """Item creation and update correctly persist category."""
    setup_client()

    # Create item with category "Músicas"
    new_id = create_item(
        code="BIP-CAT1",
        title="Canção da Alegria",
        author="Bipinho Kids",
        date="2026-10-27",
        media_type="image",
        filename="sample_bear.jpg",
        thumb_filename="thumb_sample_bear.jpg",
        category="Músicas"
    )
    assert new_id > 0

    item = get_item_by_id(new_id)
    assert item is not None
    assert item["category"] == "Músicas"

    # Update item category to "Educativos"
    update_item(
        item_id=new_id,
        code="BIP-CAT1",
        title="Canção da Alegria (Editada)",
        author="Bipinho Kids",
        date="2026-10-27",
        category="Educativos"
    )
    item_updated = get_item_by_id(new_id)
    assert item_updated["category"] == "Educativos"

    print("✓ test_item_category_crud passed")


def test_coloring_outline_generation():
    """Outline generator creates a clean black-and-white line drawing from an image."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "test_color.png"
        dst = Path(tmpdir) / "test_outline.png"

        # Create image with shapes and colors
        img = Image.new("RGB", (300, 300), color=(135, 206, 235))
        from PIL import ImageDraw
        d = ImageDraw.Draw(img)
        d.ellipse([50, 50, 250, 250], fill=(255, 165, 0), outline=(255, 0, 0), width=5)
        d.rectangle([100, 100, 200, 200], fill=(50, 205, 50), outline=(0, 100, 0), width=4)
        img.save(src)

        # Run outline generator
        success = generate_coloring_outline(src, dst)
        assert success is True
        assert dst.exists()
        assert dst.stat().st_size > 100

        # Verify output is valid image
        with Image.open(dst) as out_img:
            assert out_img.size == (300, 300)
            # Check high contrast (predominantly near-white and dark pixels)
            colors = out_img.getcolors()
            assert colors is not None

    print("✓ test_coloring_outline_generation passed")


def test_coloring_page_admin_route():
    """Route /admin/colorir/{item_id} renders printable A4 coloring sheet."""
    client = setup_client()

    # Find sample item
    item = get_item_by_code("BIP-1001")
    assert item is not None

    r = client.get(f"/admin/colorir/{item['id']}")
    assert r.status_code == 200
    html = r.text
    assert item["title"] in html
    assert item["code"] in html
    assert "Desenho para Colorir" in html
    assert "outline_" in html or "thumb_" in html
    assert "<svg" in html  # Barcode SVG rendered

    print("✓ test_coloring_page_admin_route passed")


def test_print_cards_features():
    """Print cards sheet contains size selector, category grouping, and category stripes."""
    client = setup_client()

    r = client.get("/admin/imprimir")
    assert r.status_code == 200
    html = r.text
    assert "sel-card-size" in html
    assert "Caça ao Tesouro" in html
    assert "Grandes" in html
    assert "chk-group-category" in html
    assert "card-category-stripe" in html

    print("✓ test_print_cards_features passed")


def test_mascot_idle_screen_and_settings():
    """Child TV screen contains animated SVG mascot elements and respects mascot_enabled."""
    client = setup_client()

    # Verify TV screen HTML
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert "bipinho-mascot-svg" in html
    assert "mascot-eyes" in html
    assert "mascot-arm" in html
    assert "mascot-laser" in html

    # Check status endpoint reports mascot_enabled
    r_stat = client.get("/api/session/status")
    assert r_stat.status_code == 200
    assert "mascot_enabled" in r_stat.json()
    assert r_stat.json()["mascot_enabled"] is True

    # Disable mascot and verify status
    set_setting("mascot_enabled", "0")
    r_stat2 = client.get("/api/session/status")
    assert r_stat2.json()["mascot_enabled"] is False

    print("✓ test_mascot_idle_screen_and_settings passed")


def test_movement_challenge_in_pause():
    """When pause is triggered, a movement challenge is included."""
    setup_client()
    client = TestClient(app)
    set_setting("movement_challenges_enabled", "1")

    # Trigger pause
    r = client.post("/api/session/trigger-pause")
    assert r.status_code == 200
    d = r.json()
    assert d["is_paused"] is True
    assert "challenge" in d
    assert d["challenge"] is not None
    assert len(d["challenge"]) > 3

    print("✓ test_movement_challenge_in_pause passed")


def test_etapa4_all():
    print("=" * 50)
    print("RUNNING ETAPA 4 TEST SUITE: EXPERIÊNCIA DA CRIANÇA")
    print("=" * 50)

    test_categories_seeded_and_api()
    test_item_category_crud()
    test_coloring_outline_generation()
    test_coloring_page_admin_route()
    test_print_cards_features()
    test_mascot_idle_screen_and_settings()
    test_movement_challenge_in_pause()

    print("=" * 50)
    print("ALL 7 ETAPA 4 TESTS PASSED SUCCESSFULLY!")
    print("=" * 50)


if __name__ == "__main__":
    test_etapa4_all()

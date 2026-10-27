import os
import sys
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.config import UPLOADS_DIR, THUMBS_DIR, DB_PATH
from app.database import init_db, get_all_items, create_item
from app.services.media_service import generate_image_thumbnail, extract_video_thumbnail, is_ffmpeg_installed

def create_sample_bear() -> Path:
    path = UPLOADS_DIR / "sample_bear.jpg"
    img = Image.new("RGB", (1280, 720), (254, 243, 199))
    draw = ImageDraw.Draw(img)
    # Bright sun
    draw.ellipse([1000, 40, 1160, 200], fill=(251, 191, 36), outline=(245, 158, 11), width=6)
    # Rolling green hills
    draw.ellipse([-200, 460, 1500, 1100], fill=(52, 211, 153))
    draw.ellipse([300, 500, 1600, 1100], fill=(16, 185, 129))
    # Bear body
    draw.ellipse([540, 320, 740, 560], fill=(180, 83, 9))
    # Bear head
    draw.ellipse([560, 200, 720, 360], fill=(217, 119, 6))
    # Ears
    draw.ellipse([545, 175, 605, 235], fill=(180, 83, 9))
    draw.ellipse([675, 175, 735, 235], fill=(180, 83, 9))
    draw.ellipse([560, 190, 590, 220], fill=(254, 215, 170))
    draw.ellipse([690, 190, 720, 220], fill=(254, 215, 170))
    # Eyes
    draw.ellipse([595, 245, 620, 275], fill=(15, 23, 42))
    draw.ellipse([660, 245, 685, 275], fill=(15, 23, 42))
    draw.ellipse([605, 250, 615, 260], fill=(255, 255, 255))
    draw.ellipse([670, 250, 680, 260], fill=(255, 255, 255))
    # Snout
    draw.ellipse([600, 275, 680, 325], fill=(254, 215, 170))
    draw.ellipse([625, 285, 655, 305], fill=(15, 23, 42))
    # Smile
    draw.arc([620, 300, 660, 320], start=0, end=180, fill=(15, 23, 42), width=3)
    img.save(path, quality=90)
    return path

def create_sample_rocket() -> Path:
    path = UPLOADS_DIR / "sample_rocket.jpg"
    img = Image.new("RGB", (1280, 720), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    # Stars in space
    import random
    rng = random.Random(42)
    for _ in range(80):
        x = rng.randint(20, 1260)
        y = rng.randint(20, 700)
        r = rng.randint(2, 5)
        color = rng.choice([(254, 240, 138), (255, 255, 255), (147, 197, 253)])
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
    # Big planet
    draw.ellipse([900, 420, 1300, 820], fill=(236, 72, 153), outline=(219, 39, 119), width=8)
    draw.arc([800, 580, 1400, 660], start=0, end=360, fill=(244, 114, 182), width=10)
    # Rocket body
    draw.polygon([(640, 150), (560, 450), (720, 450)], fill=(239, 68, 68))
    # Fins
    draw.polygon([(560, 390), (480, 480), (560, 470)], fill=(37, 99, 235))
    draw.polygon([(720, 390), (800, 480), (720, 470)], fill=(37, 99, 235))
    # Window
    draw.ellipse([600, 260, 680, 340], fill=(224, 242, 254), outline=(148, 163, 184), width=6)
    # Fire exhaust
    draw.polygon([(580, 450), (640, 560), (700, 450)], fill=(245, 158, 11))
    draw.polygon([(600, 450), (640, 520), (680, 450)], fill=(254, 240, 138))
    img.save(path, quality=90)
    return path

def create_sample_fish() -> Path:
    path = UPLOADS_DIR / "sample_fish.jpg"
    img = Image.new("RGB", (1280, 720), (14, 165, 233))
    draw = ImageDraw.Draw(img)
    # Ocean floor
    draw.ellipse([-100, 620, 1380, 900], fill=(245, 158, 11))
    # Corals / Seaweed
    for x in [100, 160, 220, 1100, 1160, 1200]:
        draw.arc([x - 40, 460, x + 40, 660], start=90, end=270, fill=(16, 185, 129), width=14)
        draw.arc([x - 20, 380, x + 60, 580], start=270, end=90, fill=(5, 150, 105), width=14)
    # Bubbles
    for bx, by, br in [(300, 400, 12), (320, 320, 18), (310, 200, 24), (800, 300, 15)]:
        draw.ellipse([bx - br, by - br, bx + br, by + br], outline=(255, 255, 255), width=3)
    # Fish Body
    draw.ellipse([460, 260, 800, 460], fill=(249, 115, 22))
    # Tail
    draw.polygon([(480, 360), (360, 250), (360, 470)], fill=(234, 88, 12))
    # Fin
    draw.polygon([(600, 340), (660, 390), (590, 410)], fill=(251, 146, 60))
    # Eye
    draw.ellipse([700, 300, 740, 340], fill=(255, 255, 255))
    draw.ellipse([715, 310, 735, 330], fill=(15, 23, 42))
    # Smile
    draw.arc([720, 350, 760, 380], start=45, end=160, fill=(15, 23, 42), width=3)
    img.save(path, quality=90)
    return path

def create_sample_video() -> Path:
    path = UPLOADS_DIR / "sample_colors.mp4"
    if not is_ffmpeg_installed():
        return None
    # Generate 6 seconds of vibrant color test with moving ball
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        "testsrc=duration=6:size=1280x720:rate=30",
        "-f", "lavfi", "-i",
        "sine=frequency=523.25:duration=6",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart",
        str(path)
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        if res.returncode == 0 and path.exists():
            return path
    except Exception as e:
        print(f"Sample video creation note: {e}")
    return None

def seed_sample_data():
    init_db()
    items = get_all_items()
    if len(items) > 0:
        return

    print("Generating starter sample drawings...")

    # 1. Bear
    bear_path = create_sample_bear()
    thumb_bear = THUMBS_DIR / f"thumb_{bear_path.stem}.jpg"
    generate_image_thumbnail(bear_path, thumb_bear)
    create_item(
        code="BIP-1001",
        title="O Ursinho Bipinho",
        author="Família Bipinho",
        date="2026-10-18",
        media_type="image",
        filename=bear_path.name,
        thumb_filename=thumb_bear.name,
        category="Animais"
    )

    # 2. Rocket
    rocket_path = create_sample_rocket()
    thumb_rocket = THUMBS_DIR / f"thumb_{rocket_path.stem}.jpg"
    generate_image_thumbnail(rocket_path, thumb_rocket)
    create_item(
        code="BIP-1002",
        title="O Foguete nas Estrelas",
        author="Aventuras Espaciais",
        date="2026-10-18",
        media_type="image",
        filename=rocket_path.name,
        thumb_filename=thumb_rocket.name,
        category="Histórias"
    )

    # 3. Fish
    fish_path = create_sample_fish()
    thumb_fish = THUMBS_DIR / f"thumb_{fish_path.stem}.jpg"
    generate_image_thumbnail(fish_path, thumb_fish)
    create_item(
        code="BIP-1003",
        title="O Peixinho Aventureiro",
        author="Fundo do Mar Kids",
        date="2026-10-18",
        media_type="image",
        filename=fish_path.name,
        thumb_filename=thumb_fish.name,
        category="Animais"
    )

    # 4. Animated Video
    vid_path = create_sample_video()
    if vid_path and vid_path.exists():
        thumb_vid = THUMBS_DIR / f"thumb_{vid_path.stem}.jpg"
        extract_video_thumbnail(vid_path, thumb_vid)
        create_item(
            code="BIP-1004",
            title="Dança das Cores (Vídeo)",
            author="Animações Bipinho",
            date="2026-10-18",
            media_type="video",
            filename=vid_path.name,
            thumb_filename=thumb_vid.name,
            category="Músicas"
        )

    print("Starter sample drawings created successfully!")

if __name__ == "__main__":
    seed_sample_data()

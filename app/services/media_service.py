import os
import re
import uuid
import shutil
import subprocess
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image

from app.config import UPLOADS_DIR, THUMBS_DIR

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}

def sanitize_filename(original_name: str) -> str:
    """Safely sanitizes filename, preventing path traversal and invalid characters."""
    base = Path(original_name).name
    # Keep alphanumeric, hyphen, underscore
    name_stem = re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(base).stem)[:40]
    ext = Path(base).suffix.lower()
    uid = uuid.uuid4().hex[:8]
    return f"{name_stem}_{uid}{ext}"

def is_ffmpeg_installed() -> bool:
    try:
        res = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
        return res.returncode == 0
    except Exception:
        return False

def probe_video(video_path: Path) -> dict:
    """Probes video duration, width, height and codec using ffprobe if available."""
    info = {"duration": None, "width": None, "height": None, "codec": None}
    if not is_ffmpeg_installed():
        return info
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=width,height,codec_name",
            "-of", "default=noprint_wrappers=1", str(video_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8, text=True)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    if k == "duration":
                        try:
                            info["duration"] = float(v)
                        except ValueError:
                            pass
                    elif k == "width":
                        try:
                            info["width"] = int(v)
                        except ValueError:
                            pass
                    elif k == "height":
                        try:
                            info["height"] = int(v)
                        except ValueError:
                            pass
                    elif k == "codec_name" and not info["codec"]:
                        info["codec"] = v
    except Exception:
        pass
    return info

def extract_video_thumbnail(video_path: Path, thumb_path: Path) -> bool:
    """Extract a thumbnail from video at 1s mark."""
    if not is_ffmpeg_installed():
        return False
    try:
        # Try at 1s
        cmd = [
            "ffmpeg", "-y", "-ss", "00:00:01", "-i", str(video_path),
            "-vframes", "1", "-vf", "scale=360:-1", "-q:v", "3", str(thumb_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        if res.returncode == 0 and thumb_path.exists():
            return True
        # If video is < 1s, try at 0s
        cmd[2] = "00:00:00"
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        return res.returncode == 0 and thumb_path.exists()
    except Exception as e:
        print(f"Error extracting video thumbnail: {e}")
        return False

def convert_video_to_mp4(src_path: Path, dst_path: Path) -> bool:
    """Convert non-mp4 or unsupported video to standard H.264 MP4."""
    if not is_ffmpeg_installed():
        return False
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(src_path),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(dst_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        return res.returncode == 0 and dst_path.exists()
    except Exception as e:
        print(f"Error converting video to MP4: {e}")
        return False

def generate_image_thumbnail(src_path: Path, thumb_path: Path) -> bool:
    """Generate resized thumbnail for an image."""
    try:
        with Image.open(src_path) as img:
            img = img.convert("RGB")
            img.thumbnail((360, 360), Image.Resampling.LANCZOS)
            img.save(thumb_path, "JPEG", quality=85)
            return True
    except Exception as e:
        print(f"Error generating image thumbnail: {e}")
        return False

def create_default_placeholder_thumb(thumb_path: Path, title: str, media_type: str):
    """Generates a pleasant vector-like colored thumbnail if video/image thumbnail failed."""
    from PIL import ImageDraw, ImageFont
    img = Image.new("RGB", (360, 240), color=(74, 144, 226) if media_type == "video" else (92, 184, 92))
    draw = ImageDraw.Draw(img)
    # Draw simple frame and text
    draw.rectangle([10, 10, 350, 230], outline=(255, 255, 255), width=3)
    display_text = title[:24]
    draw.text((20, 100), display_text, fill=(255, 255, 255))
    draw.text((20, 140), f"[{media_type.upper()}]", fill=(240, 240, 240))
    img.save(thumb_path, "JPEG", quality=85)

def save_and_process_media(
    file_bytes: bytes,
    original_filename: str,
    title: str
) -> Tuple[str, str, str, Optional[str]]:
    """
    Saves and processes an uploaded file.
    Returns: (media_type, final_filename, thumb_filename, warning_message)
    """
    ext = Path(original_filename).suffix.lower()
    safe_name = sanitize_filename(original_filename)
    
    if ext in IMAGE_EXTENSIONS:
        media_type = "image"
        dest_path = UPLOADS_DIR / safe_name
        dest_path.write_bytes(file_bytes)
        
        thumb_name = f"thumb_{Path(safe_name).stem}.jpg"
        thumb_path = THUMBS_DIR / thumb_name
        
        success = generate_image_thumbnail(dest_path, thumb_path)
        if not success:
            create_default_placeholder_thumb(thumb_path, title, media_type)
            
        return media_type, safe_name, thumb_name, None

    elif ext in VIDEO_EXTENSIONS:
        media_type = "video"
        temp_dest = UPLOADS_DIR / safe_name
        temp_dest.write_bytes(file_bytes)
        warning = None

        final_filename = safe_name
        # If not MP4, convert with ffmpeg or warn
        if ext != ".mp4":
            mp4_name = f"{Path(safe_name).stem}.mp4"
            mp4_path = UPLOADS_DIR / mp4_name
            if is_ffmpeg_installed():
                converted = convert_video_to_mp4(temp_dest, mp4_path)
                if converted:
                    final_filename = mp4_name
                    # Remove original raw file
                    try:
                        temp_dest.unlink()
                    except Exception:
                        pass
                else:
                    warning = "Não foi possível converter o vídeo para MP4. Pode haver problemas de compatibilidade na TV."
            else:
                warning = f"Vídeo no formato {ext}. Para melhor compatibilidade com a TV Android, recomenda-se MP4 (H.264)."
        
        final_path = UPLOADS_DIR / final_filename
        thumb_name = f"thumb_{Path(final_filename).stem}.jpg"
        thumb_path = THUMBS_DIR / thumb_name
        
        thumb_ok = extract_video_thumbnail(final_path, thumb_path)
        if not thumb_ok:
            create_default_placeholder_thumb(thumb_path, title, media_type)

        # Video diagnostics & warnings (duration, resolution)
        warnings_list = []
        if warning:
            warnings_list.append(warning)
        info = probe_video(final_path)
        if info.get("duration") and info["duration"] > 1800:
            mins = int(info["duration"] // 60)
            warnings_list.append(f"Vídeo longo ({mins} min). Vídeos curtos facilitam o controle de tela e intervalos.")
        if info.get("width") and (info["width"] > 1920 or (info.get("height") and info["height"] > 1080)):
            warnings_list.append(f"Resolução alta detectada ({info['width']}x{info.get('height')}). Na TV pode causar lentidão.")

        final_warning = " • ".join(warnings_list) if warnings_list else None
        return media_type, final_filename, thumb_name, final_warning

    else:
        raise ValueError(f"Formato de arquivo não suportado ({ext}). Envie imagens ou vídeos.")

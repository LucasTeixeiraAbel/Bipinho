"""
outline_service.py — Black-and-white coloring book outline generator.
Converts any cartoon image or video thumbnail into a crisp, high-contrast
line drawing optimized for home printing (P&B) and coloring with crayons or pencils.
"""
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps, ImageEnhance


def generate_coloring_outline(src_image_path: Path, output_path: Path) -> bool:
    """
    Generates a clean black & white contour drawing from an image or thumbnail.
    Returns True if successfully generated and saved.
    """
    try:
        if not src_image_path.exists():
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with Image.open(src_image_path) as img:
            # Convert to RGB then Grayscale
            rgb = img.convert("RGB")
            gray = ImageOps.grayscale(rgb)

            # Apply slight smoothing to eliminate minor noise and video compression artifacts
            smoothed = gray.filter(ImageFilter.SMOOTH)

            # Find edges using FIND_EDGES
            edges = smoothed.filter(ImageFilter.FIND_EDGES)

            # Invert so background is pure white and lines are dark
            inverted = ImageOps.invert(edges)

            # Boost contrast significantly to make outlines sharp and crisp
            contrast = ImageEnhance.Contrast(inverted).enhance(2.8)

            # Threshold: near-white becomes pure white (255), outlines become solid black (0)
            thresholded = contrast.point(lambda p: 255 if p > 195 else 0)

            # Convert to 1-bit or high-quality L grayscale PNG
            result = thresholded.convert("L")
            result.save(output_path, "PNG", optimize=True)
            return True
    except Exception as e:
        print(f"Error generating coloring outline: {e}")
        return False

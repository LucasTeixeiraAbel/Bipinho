import io
import barcode
from barcode.writer import SVGWriter

def generate_code128_svg(code_text: str, write_text: bool = True) -> str:
    """
    Generates an SVG barcode string for Code128.
    Clean, vectorized, crisp at all zoom levels, 100% offline.
    """
    clean_code = code_text.strip()
    rv = io.BytesIO()
    code_obj = barcode.get("code128", clean_code, writer=SVGWriter())
    options = {
        "module_height": 16.0,
        "module_width": 0.38,
        "font_size": 11,
        "text_distance": 4.0,
        "quiet_zone": 4.0,
        "write_text": write_text
    }
    code_obj.write(rv, options=options)
    svg_str = rv.getvalue().decode("utf-8")
    
    # Strip XML declaration and doctype if present for clean inline embedding
    if "<svg" in svg_str:
        svg_str = "<svg" + svg_str.split("<svg", 1)[1]
    return svg_str

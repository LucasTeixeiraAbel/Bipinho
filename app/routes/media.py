from pathlib import Path
from fastapi import APIRouter, HTTPException, Response
from starlette.responses import FileResponse

from app.config import UPLOADS_DIR, THUMBS_DIR, OUTLINES_DIR
from app.services.barcode_service import generate_code128_svg

router = APIRouter()

@router.get("/media/uploads/{filename}")
async def get_uploaded_media(filename: str):
    # Path traversal protection
    safe_path = (UPLOADS_DIR / filename).resolve()
    if not str(safe_path).startswith(str(UPLOADS_DIR.resolve())) or not safe_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de mídia não encontrado")
    
    # FileResponse in Starlette automatically handles HTTP Range (status 206)
    return FileResponse(
        safe_path,
        headers={"Accept-Ranges": "bytes", "Cache-Control": "public, max-age=3600"}
    )

@router.get("/media/thumbs/{filename}")
async def get_thumbnail(filename: str):
    safe_path = (THUMBS_DIR / filename).resolve()
    if not str(safe_path).startswith(str(THUMBS_DIR.resolve())) or not safe_path.exists():
        raise HTTPException(status_code=404, detail="Miniatura não encontrada")
    return FileResponse(safe_path, headers={"Cache-Control": "public, max-age=86400"})

@router.get("/media/outlines/{filename}")
async def get_outline(filename: str):
    safe_path = (OUTLINES_DIR / filename).resolve()
    if not str(safe_path).startswith(str(OUTLINES_DIR.resolve())) or not safe_path.exists():
        raise HTTPException(status_code=404, detail="Desenho para colorir não encontrado")
    return FileResponse(safe_path, headers={"Cache-Control": "public, max-age=86400"})

@router.get("/api/barcode/{code}.svg")
async def get_barcode_svg(code: str, write_text: bool = True):
    try:
        svg_content = generate_code128_svg(code, write_text=write_text)
        return Response(content=svg_content, media_type="image/svg+xml")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro gerando código de barras: {str(e)}")

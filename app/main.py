import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import (
    STATIC_DIR, DEFAULT_HOST, DEFAULT_PORT, get_lan_ip
)
from app.database import init_db, get_all_items
from app.seed import seed_sample_data
from app.routes.child import router as child_router
from app.routes.admin import router as admin_router
from app.routes.media import router as media_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure SQLite database and tables exist
    init_db()
    seed_sample_data()
    lan_ip = get_lan_ip()
    print("=" * 60)
    print("  * * * BIPINHO ESTA PRONTO E RODANDO! * * *")
    print(f"  Tela da Crianca (TV):  http://{lan_ip}:{DEFAULT_PORT}")
    print(f"  Area Administrativa:   http://{lan_ip}:{DEFAULT_PORT}/admin")
    print(f"  Acesso Local no PC:    http://localhost:{DEFAULT_PORT}")
    print("=" * 60)
    yield
    # Shutdown

app = FastAPI(
    title="Bipinho",
    description="Servidor de desenhos infantis acionados por código de barras",
    docs_url=None,   # Don't expose Swagger docs to child
    redoc_url=None,
    lifespan=lifespan
)

# Mount static files (CSS, JS, Sounds)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Register routers
app.include_router(child_router)
app.include_router(admin_router)
app.include_router(media_router)

def run():
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
        log_level="info"
    )

if __name__ == "__main__":
    run()

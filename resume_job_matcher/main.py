from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import router as api_router
from app.utils.config import settings


FRONTEND_DIR = Path(__file__).parent / "frontend"


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI-Powered Resume–Job Matching & Skill Gap Analysis",
        version="1.0.0",
    )
    
    # CORS for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # API routes
    app.include_router(api_router, prefix=settings.api_prefix)
    
    # Serve frontend static files
    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
        
        @app.get("/")
        async def serve_frontend():
            return FileResponse(FRONTEND_DIR / "index.html")
    
    return app


app = create_app()



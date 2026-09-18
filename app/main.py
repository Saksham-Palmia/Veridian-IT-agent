"""FastAPI application entry point for Veridian IT Service Agent."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config.settings import get_settings
from app.core.exceptions import VeridianBaseError
from app.db.database import init_db

from app.api import auth, chat, requests, tickets, audit, notifications, policies

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB and seed data."""
    logger.info("🚀 Veridian IT Service Agent starting up...")
    init_db()
    logger.info("✅ Database ready. LLM enabled: %s", settings.llm_enabled)
    yield
    logger.info("👋 Veridian IT Service Agent shutting down.")


app = FastAPI(
    title="Veridian IT Service Agent",
    description="Internal IT support agent for Veridian Corp employees.",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url=None,
)

# CORS — allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(VeridianBaseError)
async def veridian_error_handler(request: Request, exc: VeridianBaseError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "data": None, "error": exc.detail},
    )


# ── API routers ───────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(requests.router)
app.include_router(tickets.router)
app.include_router(audit.router)
app.include_router(notifications.router)
app.include_router(policies.router)


# ── Scalar API Reference Documentation ─────────────────────────────────────────

@app.get("/docs", include_in_schema=False)
async def scalar_html():
    return HTMLResponse("""
    <!doctype html>
    <html>
      <head>
        <title>Veridian IT Service Agent — API Reference</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" type="image/svg+xml" href="https://scalar.com/favicon.svg" />
        <style>
          body {
            margin: 0;
          }
        </style>
      </head>
      <body>
        <script
          id="api-reference"
          data-url="/openapi.json"
          data-configuration='{"theme": "purple"}'>
        </script>
        <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
      </body>
    </html>
    """)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "llm_enabled": settings.llm_enabled,
    }


# ── Serve frontend ────────────────────────────────────────────────────────────

employee_frontend = FRONTEND_DIR / "employee"
admin_frontend = FRONTEND_DIR / "admin"

if employee_frontend.exists():
    app.mount("/static/employee", StaticFiles(directory=str(employee_frontend)), name="employee-static")

if admin_frontend.exists():
    app.mount("/static/admin", StaticFiles(directory=str(admin_frontend)), name="admin-static")


@app.get("/", include_in_schema=False)
async def serve_employee_ui():
    index = employee_frontend / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"message": "Veridian IT Service Agent — API running. Frontend not found."})


@app.get("/admin", include_in_schema=False)
async def serve_admin_ui():
    index = admin_frontend / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"message": "Admin dashboard not yet built."})


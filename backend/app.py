"""
Pacfully Cost Intelligence — FastAPI application entry point.
Initialises the SQLite database on startup and mounts all API routes.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db, SessionLocal
from routes import router
from auth import router as auth_router, seed_users

app = FastAPI(
    title    = "Pacfully Cost Intelligence API",
    version  = "1.0.0",
    docs_url = "/docs",
)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api")   # /api/auth/...
app.include_router(router,      prefix="/api")   # /api/estimates/... etc.

# ── Static PDFs ───────────────────────────────────────────────
PDF_DIR = Path(__file__).resolve().parent.parent / "data" / "pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/pdfs", StaticFiles(directory=str(PDF_DIR)), name="pdfs")

# ── Startup ───────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    init_db()                     # create all tables
    db = SessionLocal()
    try:
        seed_users(db)            # insert default users once
    finally:
        db.close()


@app.get("/")
def root():
    return {"service": "Pacfully Cost Intelligence", "status": "ready", "docs": "/docs"}

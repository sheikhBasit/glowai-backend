import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

load_dotenv()

from database import Base, engine
from routers import account, auth, diary, generate, glow_journey, looks, profile, recommendations, routine, scan, scans, score, tutorials

# Create all tables on startup
Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="GlowAI API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(account.router)
app.include_router(generate.router)
app.include_router(profile.router)
app.include_router(diary.router)
app.include_router(looks.router)
app.include_router(scans.router)
app.include_router(score.router)
app.include_router(scan.router)
app.include_router(recommendations.router)
app.include_router(tutorials.router)
app.include_router(glow_journey.router)
app.include_router(routine.router)


# ── Static file serving for uploads ──────────────────────────────────────────
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))

@app.get("/uploads/{file_path:path}")
def serve_upload(file_path: str):
    full = UPLOAD_DIR / file_path
    if not full.exists() or not full.is_file():
        raise HTTPException(404, "File not found")
    # Safety: ensure path stays within UPLOAD_DIR (no path traversal)
    try:
        full.resolve().relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(403, "Forbidden")
    return FileResponse(full)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "gemini": bool(os.getenv("GOOGLE_API_KEY")),
        "vision": "gemini" if os.getenv("GOOGLE_API_KEY") else ("groq" if os.getenv("GROQ_API_KEY") else "none"),
    }

"""
FastAPI application entry point for SourceSage.

Configures CORS, registers all routers, and sets up the
application lifespan (temp directory creation).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import analyze, docs, health

# ── Logging ──────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler.

    On startup: create the temporary directory used for cloned repos.
    On shutdown: (no-op — repos are cleaned up after each request).
    """
    settings.temp_path.mkdir(parents=True, exist_ok=True)
    logger.info("Temp directory ready: %s", settings.temp_path)
    yield
    logger.info("SourceSage shutting down.")


# ── App factory ──────────────────────────────────────────────

app = FastAPI(
    title="SourceSage API",
    description=(
        "AI-powered code review and documentation generator. "
        "Analyses GitHub repositories using Google Gemini and "
        "streams results in real-time via SSE."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(docs.router)


# ── Root redirect ────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root() -> dict:
    """Redirect to API docs."""
    return {
        "message": "Welcome to SourceSage API",
        "docs": "/docs",
        "health": "/api/health",
    }

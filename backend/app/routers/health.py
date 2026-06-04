"""
Health-check router for SourceSage API.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Return service health status.

    Returns:
        JSON with ``status`` and ``version`` keys.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
    }

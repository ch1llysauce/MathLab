"""Health check route."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok", "environment": settings.app_env}

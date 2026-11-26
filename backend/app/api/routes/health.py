"""Health check route."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.api_route("/health", methods=["GET", "HEAD"])
def health_check() -> dict[str, str]:
    """Return service health status for GET and UptimeRobot-style HEAD probes."""
    return {"status": "ok", "environment": settings.app_env}

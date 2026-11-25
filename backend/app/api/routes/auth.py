"""Authentication status route."""

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import AuthenticatedUser, get_optional_user
from app.core.config import settings
from app.core.exceptions import UnauthorizedError

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me")
def get_me(user: AuthenticatedUser | None = Depends(get_optional_user)) -> dict[str, object]:
    """Return the currently authenticated Supabase user or guest status."""
    if user is None:
        if settings.auth_required:
            raise UnauthorizedError("Authentication required.")
        return {"authenticated": False, "user": None}
    return {
        "authenticated": True,
        "user": {"id": user.id, "email": user.email},
    }

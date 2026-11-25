"""Authentication dependencies using Supabase Auth token verification."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header
import httpx

from app.core.config import settings
from app.core.exceptions import UnauthorizedError


@dataclass(frozen=True)
class AuthenticatedUser:
    """Verified user identity extracted from a Supabase Auth JWT."""

    id: str
    email: str | None = None


def verify_supabase_token(token: str) -> AuthenticatedUser:
    """Verify a Supabase Auth access token via the Supabase Auth /user endpoint."""
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise UnauthorizedError("Supabase Auth is not configured on the backend.")

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.supabase_anon_key,
                },
            )
    except httpx.HTTPError as exc:
        raise UnauthorizedError("Failed to contact authentication service.") from exc

    if resp.status_code != 200:
        raise UnauthorizedError("Invalid or expired authentication token.")

    payload = resp.json()
    user_id = payload.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise UnauthorizedError("Authentication token did not contain a valid user id.")

    return AuthenticatedUser(id=user_id, email=payload.get("email"))


def get_optional_user(
    authorization: str | None = Header(default=None),
) -> AuthenticatedUser | None:
    """Resolve the current user if a Bearer token is supplied, or enforce when AUTH_REQUIRED=true."""
    if not authorization:
        if settings.auth_required:
            raise UnauthorizedError("Bearer token required.")
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise UnauthorizedError("Authorization header must use Bearer token format.")

    return verify_supabase_token(token.strip())

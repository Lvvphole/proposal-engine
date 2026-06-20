"""Authentication — verify Supabase-issued JWTs.

When ``AUTH_ENABLED`` is false (the default, for local dev and tests), requests
are not authenticated and run as a synthetic ``dev`` principal. When enabled,
every request must carry a valid Supabase access token in an
``Authorization: Bearer <jwt>`` header; we verify its signature (HS256 with the
project's JWT secret), audience, and expiry, and derive the user from ``sub``.
"""

from __future__ import annotations

import jwt
from fastapi import HTTPException, Request, status
from pydantic import BaseModel

from core.config import get_config


class Principal(BaseModel):
    """The authenticated caller."""

    user_id: str
    email: str | None = None
    role: str = "authenticated"


# Identity used when auth is disabled. Tenancy scoping is also disabled in that
# mode, so this id is never used to filter rows.
DEV_PRINCIPAL = Principal(user_id="dev", email=None, role="dev")


def tenancy_owner(principal: Principal) -> str | None:
    """The owner id to scope a query/resource by, or ``None`` when tenancy is off.

    Used both to stamp ``owner_id`` on new rows and to filter/authorize reads.
    Returns ``None`` when ``AUTH_ENABLED`` is false so existing single-tenant
    behavior (and tests) is preserved.
    """
    return principal.user_id if get_config().auth_enabled else None


def _bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.strip()


async def get_current_principal(request: Request) -> Principal:
    """FastAPI dependency: resolve the caller, enforcing JWT auth when enabled."""
    config = get_config()
    if not config.auth_enabled:
        return DEV_PRINCIPAL

    token = _bearer_token(request)
    try:
        claims = jwt.decode(
            token,
            config.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=config.supabase_jwt_audience,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject (sub) claim",
        )
    return Principal(
        user_id=str(sub),
        email=claims.get("email"),
        role=claims.get("role", "authenticated"),
    )

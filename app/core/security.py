"""
Authentication helpers.

Identity itself is delegated to a self-hosted Supabase instance (GoTrue).
This module is only responsible for *verifying* the JWT that Supabase
issued and turning it into an internal `AuthContext`, and for issuing
short-lived, scoped API keys for the Developer Platform / SDK.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthContext:
    """Resolved identity for the current request."""

    user_id: str
    organization_id: str
    role: str
    scopes: tuple[str, ...] = ()


def create_api_key_token(*, organization_id: str, scopes: list[str], expires_minutes: int = 0) -> str:
    """Issue a scoped, signed API token for the Developer Platform.

    `expires_minutes=0` produces a long-lived server-to-server token, which
    is appropriate for API keys that customers store in their own backend.
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": organization_id,
        "scopes": scopes,
        "iat": now,
        "type": "api_key",
    }
    if expires_minutes:
        payload["exp"] = now + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_supabase_jwt(token: str) -> dict[str, Any]:
    """Verify and decode a Supabase-issued end-user JWT."""
    try:
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        ) from exc


async def get_current_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthContext:
    """FastAPI dependency that resolves the caller's identity and tenant."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials.")

    claims = decode_supabase_jwt(credentials.credentials)
    organization_id = claims.get("organization_id") or claims.get("sub")
    if not organization_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing tenant claim.")

    return AuthContext(
        user_id=claims.get("sub", ""),
        organization_id=organization_id,
        role=claims.get("role", "member"),
        scopes=tuple(claims.get("scopes", [])),
    )


def require_scopes(*required: str):
    """Dependency factory enforcing that an API key token carries given scopes."""

    async def _checker(ctx: AuthContext = Depends(get_current_auth_context)) -> AuthContext:
        missing = set(required) - set(ctx.scopes)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope(s): {', '.join(sorted(missing))}",
            )
        return ctx

    return _checker

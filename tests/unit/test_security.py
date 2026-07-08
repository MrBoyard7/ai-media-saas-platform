"""Unit tests for `app.core.security`: JWT issuance/verification and the
FastAPI dependencies built on top of it.

These call `get_current_auth_context` / `require_scopes` directly as plain
Python functions rather than through a running app -- they're ordinary
`async def`s under FastAPI's `Depends()` sugar, so nothing but pytest is
needed to exercise them.
"""
from __future__ import annotations

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.security import (
    create_api_key_token,
    decode_supabase_jwt,
    get_current_auth_context,
    require_scopes,
    settings,
)


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _sign_supabase_token(**claims) -> str:
    return jwt.encode(claims, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


def test_create_api_key_token_round_trips_scopes():
    token = create_api_key_token(organization_id="org-42", scopes=["generation:write", "credits:read"])

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == "org-42"
    assert payload["scopes"] == ["generation:write", "credits:read"]
    assert payload["type"] == "api_key"
    assert "exp" not in payload  # expires_minutes=0 -> long-lived server-to-server token


def test_create_api_key_token_with_expiry_sets_exp_claim():
    token = create_api_key_token(organization_id="org-42", scopes=[], expires_minutes=15)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert "exp" in payload


def test_decode_supabase_jwt_roundtrip():
    token = _sign_supabase_token(sub="user-1", organization_id="org-1", role="admin")
    claims = decode_supabase_jwt(token)
    assert claims["sub"] == "user-1"
    assert claims["organization_id"] == "org-1"


def test_decode_supabase_jwt_rejects_invalid_token():
    with pytest.raises(HTTPException) as exc_info:
        decode_supabase_jwt("this.is.not-a-valid-jwt")
    assert exc_info.value.status_code == 401


def test_decode_supabase_jwt_rejects_wrong_signature():
    forged = jwt.encode({"sub": "attacker"}, "wrong-secret", algorithm="HS256")
    with pytest.raises(HTTPException) as exc_info:
        decode_supabase_jwt(forged)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_auth_context_missing_credentials_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        await get_current_auth_context(credentials=None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_auth_context_resolves_from_valid_token():
    token = _sign_supabase_token(sub="user-1", organization_id="org-9", role="owner", scopes=["a", "b"])

    ctx = await get_current_auth_context(credentials=_bearer(token))

    assert ctx.user_id == "user-1"
    assert ctx.organization_id == "org-9"
    assert ctx.role == "owner"
    assert ctx.scopes == ("a", "b")


@pytest.mark.asyncio
async def test_get_current_auth_context_falls_back_to_sub_as_tenant():
    """A token with no explicit `organization_id` claim (e.g. a personal
    account not yet in an org) falls back to `sub` as the tenant id."""
    token = _sign_supabase_token(sub="org-and-user-same-id")
    ctx = await get_current_auth_context(credentials=_bearer(token))
    assert ctx.organization_id == "org-and-user-same-id"


@pytest.mark.asyncio
async def test_get_current_auth_context_rejects_token_without_any_tenant_claim():
    token = jwt.encode({"role": "member"}, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_auth_context(credentials=_bearer(token))
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_scopes_passes_when_all_scopes_present():
    token = _sign_supabase_token(sub="user-1", organization_id="org-1", scopes=["generation:write", "credits:read"])
    ctx = await get_current_auth_context(credentials=_bearer(token))

    checker = require_scopes("generation:write")
    result = await checker(ctx=ctx)

    assert result is ctx


@pytest.mark.asyncio
async def test_require_scopes_raises_403_when_scope_missing():
    token = _sign_supabase_token(sub="user-1", organization_id="org-1", scopes=["credits:read"])
    ctx = await get_current_auth_context(credentials=_bearer(token))

    checker = require_scopes("generation:write")
    with pytest.raises(HTTPException) as exc_info:
        await checker(ctx=ctx)

    assert exc_info.value.status_code == 403
    assert "generation:write" in exc_info.value.detail

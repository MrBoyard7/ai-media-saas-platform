"""Integration tests for the Organizations endpoints, exercised end-to-end
through the ASGI app (routing, dependency injection, DB, serialization)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.wallet import Wallet

pytestmark = pytest.mark.asyncio


async def test_create_organization_seeds_signup_credits(client, db_session):
    response = await client.post("/api/v1/organizations", json={"name": "Nova Records"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Nova Records"
    assert body["slug"] == "nova-records"
    assert body["plan"] == "free"

    # The authenticated test client is pinned to `seeded_organization` (see
    # conftest.py), so the new org's balance is checked directly against
    # the shared test session rather than through `/credits/balance`.
    result = await db_session.execute(select(Wallet).where(Wallet.organization_id == uuid.UUID(body["id"])))
    wallet = result.scalar_one()
    assert wallet.balance == 100  # DEFAULT_SIGNUP_CREDITS


async def test_get_organization_returns_seeded_fixture(client, seeded_organization):
    response = await client.get(f"/api/v1/organizations/{seeded_organization.id}")

    assert response.status_code == 200
    assert response.json()["slug"] == "acme-studio"


async def test_get_unknown_organization_returns_404(client):
    response = await client.get("/api/v1/organizations/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_enable_white_label_updates_branding(client, seeded_organization):
    response = await client.put(
        f"/api/v1/organizations/{seeded_organization.id}/white-label",
        json={"custom_domain": "studio.novarecords.com", "branding": {"primary_color": "#111827"}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_white_label"] is True
    assert body["custom_domain"] == "studio.novarecords.com"

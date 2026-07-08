"""Integration tests for `POST /generate` and `GET /jobs/{id}`: the full
credits -> entitlement -> provider -> job pipeline, exercised over HTTP with
the Celery broker stubbed out (see `no_real_celery_broker` in conftest)."""
from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def test_generation_request_reserves_credits_and_queues_job(client, seeded_organization):
    balance_before = (await client.get("/api/v1/credits/balance")).json()["balance"]

    response = await client.post(
        "/api/v1/generate",
        json={
            "capability": "lyrics",
            "prompt": "an upbeat song about summer",
            "parameters": {"line_count": 8},
            "idempotency_key": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["kind"] == "lyrics"
    assert body["credits_reserved"] > 0

    balance_after = (await client.get("/api/v1/credits/balance")).json()["balance"]
    assert balance_after == balance_before - body["credits_reserved"]


async def test_generation_request_is_idempotent(client, seeded_organization):
    idempotency_key = str(uuid.uuid4())
    payload = {
        "capability": "lyrics",
        "prompt": "a rainy day ballad",
        "parameters": {"line_count": 4},
        "idempotency_key": idempotency_key,
    }

    first = await client.post("/api/v1/generate", json=payload)
    balance_after_first = (await client.get("/api/v1/credits/balance")).json()["balance"]

    # A client retry with the same idempotency key must not double-charge,
    # even though it creates a second job row.
    second = await client.post("/api/v1/generate", json=payload)
    balance_after_second = (await client.get("/api/v1/credits/balance")).json()["balance"]

    assert first.status_code == second.status_code == 202
    assert balance_after_first == balance_after_second


async def test_get_job_returns_404_for_unknown_job(client, seeded_organization):
    response = await client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_get_job_after_generation_request(client, seeded_organization):
    create_response = await client.post(
        "/api/v1/generate",
        json={
            "capability": "music",
            "prompt": "lofi hip-hop beat",
            "parameters": {"duration_seconds": 20},
            "idempotency_key": str(uuid.uuid4()),
        },
    )
    job_id = create_response.json()["id"]

    get_response = await client.get(f"/api/v1/jobs/{job_id}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == job_id
    assert get_response.json()["status"] == "queued"  # worker hasn't run; only enqueued in this test

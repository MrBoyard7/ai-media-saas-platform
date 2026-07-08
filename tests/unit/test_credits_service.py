"""Unit tests for `CreditsService`: the financial core of the platform.

These tests run against the in-memory SQLite session from `conftest.py`
rather than a fake repository, because the idempotency guarantee is only
meaningful when it is exercised against the real unique constraint on
`(wallet_id, idempotency_key)`.
"""
from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import IdempotencyConflictError, InsufficientCreditsError
from app.models.wallet import TransactionType
from app.repositories.wallet_repository import WalletRepository
from app.services.credits_service import CreditsService

pytestmark = pytest.mark.asyncio


async def _service(db_session) -> CreditsService:
    return CreditsService(WalletRepository(db_session))


async def test_credit_creates_wallet_when_missing(db_session):
    service = await _service(db_session)
    org_id = uuid.uuid4()

    entry = await service.credit(
        org_id, amount=100, type_=TransactionType.PROMOTIONAL_GRANT, idempotency_key="grant-1"
    )

    assert entry.balance_after == 100
    assert await service.get_balance(org_id) == 100


async def test_debit_reduces_balance(db_session):
    service = await _service(db_session)
    org_id = uuid.uuid4()
    await service.credit(org_id, amount=50, type_=TransactionType.TOP_UP, idempotency_key="topup-1")

    await service.debit(org_id, amount=20, idempotency_key="debit-1")

    assert await service.get_balance(org_id) == 30


async def test_debit_raises_when_insufficient_funds(db_session):
    service = await _service(db_session)
    org_id = uuid.uuid4()
    await service.credit(org_id, amount=10, type_=TransactionType.TOP_UP, idempotency_key="topup-1")

    with pytest.raises(InsufficientCreditsError):
        await service.debit(org_id, amount=11, idempotency_key="debit-1")

    # Balance must be unchanged after a rejected debit.
    assert await service.get_balance(org_id) == 10


async def test_debit_is_idempotent_on_replay(db_session):
    service = await _service(db_session)
    org_id = uuid.uuid4()
    await service.credit(org_id, amount=100, type_=TransactionType.TOP_UP, idempotency_key="topup-1")

    first = await service.debit(org_id, amount=30, idempotency_key="job-42")
    second = await service.debit(org_id, amount=30, idempotency_key="job-42")  # replay, e.g. client retry

    assert first.id == second.id
    assert await service.get_balance(org_id) == 70  # debited only once


async def test_replaying_idempotency_key_with_different_amount_conflicts(db_session):
    service = await _service(db_session)
    org_id = uuid.uuid4()
    await service.credit(org_id, amount=100, type_=TransactionType.TOP_UP, idempotency_key="topup-1")
    await service.debit(org_id, amount=30, idempotency_key="job-42")

    with pytest.raises(IdempotencyConflictError):
        await service.debit(org_id, amount=99, idempotency_key="job-42")


async def test_refund_credits_the_wallet_back(db_session):
    service = await _service(db_session)
    org_id = uuid.uuid4()
    await service.credit(org_id, amount=100, type_=TransactionType.TOP_UP, idempotency_key="topup-1")
    await service.debit(org_id, amount=40, idempotency_key="job-1")

    await service.refund(org_id, amount=40, idempotency_key="refund:job-1", reference="job-1")

    assert await service.get_balance(org_id) == 100

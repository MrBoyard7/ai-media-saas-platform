"""Repository for Wallet and CreditTransaction.

`get_for_update` takes a `SELECT ... FOR UPDATE` row lock so two concurrent
generation requests from the same organization cannot both read the same
starting balance and overspend -- see `app.services.credits_service` for
how this is used inside a single DB transaction.

SQLite (used by the test suite, see `tests/conftest.py`) has no `FOR
UPDATE` support and no meaningful concurrent-writer story to begin with
(SQLAlchemy's SQLite dialect will happily emit invalid SQL if asked), so
the lock is only applied on dialects that actually support it. This keeps
the exact same repository code correct against both SQLite in tests and
PostgreSQL in production.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.wallet import CreditTransaction, Wallet
from app.repositories.base import BaseRepository

_DIALECTS_SUPPORTING_ROW_LOCKS = {"postgresql", "mysql", "oracle"}


class WalletRepository(BaseRepository[Wallet]):
    model = Wallet

    async def get_by_organization(self, organization_id: uuid.UUID) -> Wallet | None:
        result = await self.session.execute(select(Wallet).where(Wallet.organization_id == organization_id))
        return result.scalar_one_or_none()

    async def get_for_update(self, organization_id: uuid.UUID) -> Wallet | None:
        query = select(Wallet).where(Wallet.organization_id == organization_id)
        if self.session.bind.dialect.name in _DIALECTS_SUPPORTING_ROW_LOCKS:
            query = query.with_for_update()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def find_transaction_by_idempotency_key(
        self, wallet_id: uuid.UUID, idempotency_key: str
    ) -> CreditTransaction | None:
        result = await self.session.execute(
            select(CreditTransaction).where(
                CreditTransaction.wallet_id == wallet_id,
                CreditTransaction.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

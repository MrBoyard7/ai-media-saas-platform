"""
Credits & Wallet service.

This is the financial core of the platform: every AI generation debits a
wallet, every top-up or subscription renewal credits it, and every single
movement is idempotent and produces an immutable ledger row. No code path
outside this service is allowed to mutate `Wallet.balance`.
"""

from __future__ import annotations

import uuid

from app.core.exceptions import IdempotencyConflictError, InsufficientCreditsError
from app.models.wallet import CreditTransaction, TransactionType, Wallet
from app.repositories.wallet_repository import WalletRepository


class CreditsService:
    def __init__(self, wallet_repository: WalletRepository) -> None:
        self._wallets = wallet_repository

    async def get_balance(self, organization_id: uuid.UUID) -> int:
        wallet = await self._wallets.get_by_organization(organization_id)
        return wallet.balance if wallet else 0

    async def _find_replay(
        self, wallet: Wallet, *, amount: int, type_: TransactionType, idempotency_key: str
    ) -> CreditTransaction | None:
        """Look up a prior transaction for this idempotency key.

        Checked *before* any balance mutation or sufficiency check in both
        `credit()` and `debit()`: whether a request is a safe replay is a
        property of the request itself, independent of the wallet's
        current balance, so it must never be shadowed by an
        `InsufficientCreditsError` raised from stale/inconsistent retry
        logic on the caller's side.
        """
        existing = await self._wallets.find_transaction_by_idempotency_key(wallet.id, idempotency_key)
        if existing is None:
            return None
        if existing.amount != amount or existing.type != type_:
            raise IdempotencyConflictError(
                f"idempotency_key {idempotency_key!r} was already used with a different transaction."
            )
        return existing  # safe replay: return the original result, do not double-apply

    async def _insert_ledger_entry(
        self,
        *,
        wallet: Wallet,
        amount: int,
        type_: TransactionType,
        idempotency_key: str,
        reference: str | None = None,
        metadata: dict | None = None,
    ) -> CreditTransaction:
        wallet.balance += amount
        entry = CreditTransaction(
            wallet_id=wallet.id,
            amount=amount,
            balance_after=wallet.balance,
            type=type_,
            reference=reference,
            idempotency_key=idempotency_key,
            metadata_=metadata or {},
        )
        self._wallets.session.add(entry)
        await self._wallets.session.flush()
        return entry

    async def credit(
        self,
        organization_id: uuid.UUID,
        *,
        amount: int,
        type_: TransactionType,
        idempotency_key: str,
        reference: str | None = None,
        metadata: dict | None = None,
    ) -> CreditTransaction:
        if amount <= 0:
            raise ValueError("credit() amount must be positive; use debit() to subtract credits.")

        wallet = await self._wallets.get_for_update(organization_id)
        if wallet is None:
            wallet = Wallet(organization_id=organization_id, balance=0)
            await self._wallets.add(wallet)
        else:
            replay = await self._find_replay(
                wallet, amount=amount, type_=type_, idempotency_key=idempotency_key
            )
            if replay is not None:
                return replay

        return await self._insert_ledger_entry(
            wallet=wallet,
            amount=amount,
            type_=type_,
            idempotency_key=idempotency_key,
            reference=reference,
            metadata=metadata,
        )

    async def debit(
        self,
        organization_id: uuid.UUID,
        *,
        amount: int,
        idempotency_key: str,
        reference: str | None = None,
        metadata: dict | None = None,
    ) -> CreditTransaction:
        """Debit `amount` credits, raising `InsufficientCreditsError` if the
        wallet balance would go negative. Always call this *before*
        dispatching a generation job to a GPU worker, never after."""
        if amount <= 0:
            raise ValueError("debit() amount must be positive.")

        wallet = await self._wallets.get_for_update(organization_id)
        if wallet is None:
            raise InsufficientCreditsError(f"Insufficient credits: requested {amount}, available 0.")

        replay = await self._find_replay(
            wallet, amount=-amount, type_=TransactionType.GENERATION_DEBIT, idempotency_key=idempotency_key
        )
        if replay is not None:
            return replay

        if wallet.balance < amount:
            raise InsufficientCreditsError(
                f"Insufficient credits: requested {amount}, available {wallet.balance}."
            )

        return await self._insert_ledger_entry(
            wallet=wallet,
            amount=-amount,
            type_=TransactionType.GENERATION_DEBIT,
            idempotency_key=idempotency_key,
            reference=reference,
            metadata=metadata,
        )

    async def refund(
        self, organization_id: uuid.UUID, *, amount: int, idempotency_key: str, reference: str | None = None
    ) -> CreditTransaction:
        """Refund credits for a job that was reserved but failed/was canceled."""
        return await self.credit(
            organization_id,
            amount=amount,
            type_=TransactionType.REFUND,
            idempotency_key=idempotency_key,
            reference=reference,
        )

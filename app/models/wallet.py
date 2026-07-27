"""Credits & Wallet: the single source of truth for how many credits an
organization has, and a fully auditable, append-only ledger of every
movement (top-up, generation debit, refund, promotional grant)."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import GUID, PortableJSON, StrEnum

if TYPE_CHECKING:
    from app.models.organization import Organization


class TransactionType(str, enum.Enum):
    TOP_UP = "top_up"
    SUBSCRIPTION_GRANT = "subscription_grant"
    GENERATION_DEBIT = "generation_debit"
    REFUND = "refund"
    PROMOTIONAL_GRANT = "promotional_grant"
    ADMIN_ADJUSTMENT = "admin_adjustment"


class Wallet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One wallet per organization. `balance` is a materialized, cached value
    that must always equal SUM(credit_transactions.amount) for that wallet --
    it exists purely to avoid summing the whole ledger on every read, and is
    only ever mutated inside the same DB transaction as its ledger entry."""

    __tablename__ = "wallets"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    balance: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    currency_credits_per_usd: Mapped[int] = mapped_column(BigInteger, default=100, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="wallet")
    transactions: Mapped[list["CreditTransaction"]] = relationship(back_populates="wallet", cascade="all, delete-orphan")


class CreditTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Append-only ledger entry. `amount` is signed: positive for
    credits/refunds, negative for generation debits."""

    __tablename__ = "credit_transactions"
    __table_args__ = (
        UniqueConstraint("wallet_id", "idempotency_key", name="uq_wallet_idempotency_key"),
        Index("ix_credit_transactions_wallet_created", "wallet_id", "created_at"),
    )

    wallet_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[TransactionType] = mapped_column(StrEnum(TransactionType, name="transaction_type"), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)  # e.g. job_id, invoice_id
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", PortableJSON(), default=dict, nullable=False)

    wallet: Mapped["Wallet"] = relationship(back_populates="transactions")

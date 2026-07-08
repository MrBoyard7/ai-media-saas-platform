"""Pydantic request/response schemas for the Credits & Wallet API."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.wallet import TransactionType


class WalletBalanceRead(BaseModel):
    balance: int


class TopUpRequest(BaseModel):
    amount: int = Field(gt=0, description="Number of credits to add.")
    idempotency_key: str = Field(min_length=8, max_length=255)
    reference: str | None = None


class CreditTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: int
    balance_after: int
    type: TransactionType
    reference: str | None
    created_at: datetime

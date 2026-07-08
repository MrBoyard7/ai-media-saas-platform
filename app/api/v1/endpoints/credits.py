"""Credits & Wallet API."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.deps import get_credits_service
from app.core.security import AuthContext, get_current_auth_context
from app.models.wallet import TransactionType
from app.schemas.credits import CreditTransactionRead, TopUpRequest, WalletBalanceRead
from app.services.credits_service import CreditsService

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/balance", response_model=WalletBalanceRead)
async def get_balance(
    ctx: AuthContext = Depends(get_current_auth_context),
    credits: CreditsService = Depends(get_credits_service),
) -> WalletBalanceRead:
    balance = await credits.get_balance(uuid.UUID(ctx.organization_id))
    return WalletBalanceRead(balance=balance)


@router.post("/top-up", response_model=CreditTransactionRead, status_code=201)
async def top_up(
    payload: TopUpRequest,
    ctx: AuthContext = Depends(get_current_auth_context),
    credits: CreditsService = Depends(get_credits_service),
) -> CreditTransactionRead:
    # NOTE: in production this endpoint is called from a payment-provider
    # webhook handler *after* the charge has settled, never directly from an
    # unauthenticated client -- see docs/architecture.md#billing.
    entry = await credits.credit(
        uuid.UUID(ctx.organization_id),
        amount=payload.amount,
        type_=TransactionType.TOP_UP,
        idempotency_key=payload.idempotency_key,
        reference=payload.reference,
    )
    return CreditTransactionRead.model_validate(entry)

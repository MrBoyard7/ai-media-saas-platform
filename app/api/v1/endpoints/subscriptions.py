"""Subscriptions API: current plan and feature entitlement lookup."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.deps import get_entitlement_service
from app.core.exceptions import FeatureNotEntitledError
from app.core.security import AuthContext, get_current_auth_context
from app.services.entitlement_service import EntitlementService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/entitlements/{feature_key}")
async def check_entitlement(
    feature_key: str,
    ctx: AuthContext = Depends(get_current_auth_context),
    entitlements: EntitlementService = Depends(get_entitlement_service),
) -> dict:
    """Lightweight endpoint the frontend can call to decide whether to show
    a feature (e.g. gray out the "Generate Video" button) before the user
    even attempts the action."""
    organization_id = uuid.UUID(ctx.organization_id)
    try:
        await entitlements.check(organization_id, feature_key)
        entitled = True
    except FeatureNotEntitledError:
        entitled = False

    limit = await entitlements.get_monthly_limit(organization_id, feature_key)
    return {"feature": feature_key, "entitled": entitled, "monthly_limit": limit}

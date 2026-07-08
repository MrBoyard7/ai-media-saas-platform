"""
Feature-Based Subscription / Entitlement Engine.

Answers exactly one question -- "is organization X allowed to do Y right
now, and how much of it?" -- by combining the organization's current plan
with the data-driven `plan_features` table. Nothing else in the codebase
is allowed to special-case a plan name; every gate goes through
`EntitlementService.check`.
"""
from __future__ import annotations

import uuid

from app.core.exceptions import FeatureNotEntitledError
from app.models.organization import OrganizationPlan
from app.repositories.subscription_repository import FeatureRepository, SubscriptionRepository


class EntitlementService:
    def __init__(self, subscriptions: SubscriptionRepository, features: FeatureRepository) -> None:
        self._subscriptions = subscriptions
        self._features = features

    async def _resolve_plan(self, organization_id: uuid.UUID) -> OrganizationPlan:
        subscription = await self._subscriptions.get_by_organization(organization_id)
        return subscription.plan if subscription else OrganizationPlan.FREE

    async def check(self, organization_id: uuid.UUID, feature_key: str) -> None:
        """Raise `FeatureNotEntitledError` if the org's plan does not include
        `feature_key`. Returns None (i.e. does not raise) when entitled."""
        plan = await self._resolve_plan(organization_id)
        plan_feature = await self._features.get_plan_feature(plan, feature_key)

        if plan_feature is None or not plan_feature.enabled:
            raise FeatureNotEntitledError(
                f"Feature {feature_key!r} is not included in the {plan.value!r} plan."
            )

    async def get_monthly_limit(self, organization_id: uuid.UUID, feature_key: str) -> int | None:
        """Return the monthly usage limit for a feature, or None if unlimited.
        Callers should combine this with a usage counter (e.g. in Redis) to
        enforce the limit; this service only resolves *what* the limit is."""
        plan = await self._resolve_plan(organization_id)
        plan_feature = await self._features.get_plan_feature(plan, feature_key)
        if plan_feature is None:
            return 0
        return plan_feature.monthly_limit

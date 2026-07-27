"""Repository for Subscription, Feature and PlanFeature."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.organization import OrganizationPlan
from app.models.subscription import Feature, PlanFeature, Subscription
from app.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    model = Subscription

    async def get_by_organization(self, organization_id: uuid.UUID) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription).where(Subscription.organization_id == organization_id)
        )
        return result.scalar_one_or_none()


class FeatureRepository(BaseRepository[Feature]):
    model = Feature

    async def get_by_key(self, key: str) -> Feature | None:
        result = await self.session.execute(select(Feature).where(Feature.key == key))
        return result.scalar_one_or_none()

    async def get_plan_feature(self, plan: OrganizationPlan, feature_key: str) -> PlanFeature | None:
        result = await self.session.execute(
            select(PlanFeature).join(Feature).where(PlanFeature.plan == plan, Feature.key == feature_key)
        )
        return result.scalar_one_or_none()

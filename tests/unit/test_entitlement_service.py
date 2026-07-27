"""Unit tests for `EntitlementService`."""

from __future__ import annotations

import pytest

from app.core.exceptions import FeatureNotEntitledError
from app.models.organization import Organization, OrganizationPlan
from app.models.subscription import Feature, PlanFeature, Subscription, SubscriptionStatus
from app.repositories.subscription_repository import FeatureRepository, SubscriptionRepository
from app.services.entitlement_service import EntitlementService

pytestmark = pytest.mark.asyncio


async def _make_org_with_plan(db_session, plan: OrganizationPlan) -> Organization:
    organization = Organization(name="Test Org", slug=f"test-org-{plan.value}", plan=plan)
    db_session.add(organization)
    await db_session.flush()
    db_session.add(Subscription(organization_id=organization.id, plan=plan, status=SubscriptionStatus.ACTIVE))
    await db_session.commit()
    return organization


async def _grant_feature(db_session, plan: OrganizationPlan, key: str, monthly_limit: int | None) -> None:
    feature = Feature(key=key, name=key, description="")
    db_session.add(feature)
    await db_session.flush()
    db_session.add(PlanFeature(plan=plan, feature_id=feature.id, enabled=True, monthly_limit=monthly_limit))
    await db_session.commit()


async def test_check_passes_for_entitled_feature(db_session):
    org = await _make_org_with_plan(db_session, OrganizationPlan.PRO)
    await _grant_feature(db_session, OrganizationPlan.PRO, "video.generate", monthly_limit=None)

    service = EntitlementService(SubscriptionRepository(db_session), FeatureRepository(db_session))
    await service.check(org.id, "video.generate")  # must not raise


async def test_check_raises_for_unentitled_feature(db_session):
    org = await _make_org_with_plan(db_session, OrganizationPlan.FREE)

    service = EntitlementService(SubscriptionRepository(db_session), FeatureRepository(db_session))
    with pytest.raises(FeatureNotEntitledError):
        await service.check(org.id, "video.generate")


async def test_organization_without_subscription_defaults_to_free_plan(db_session):
    organization = Organization(name="No Sub Org", slug="no-sub-org", plan=OrganizationPlan.FREE)
    db_session.add(organization)
    await db_session.commit()

    await _grant_feature(db_session, OrganizationPlan.FREE, "lyrics.generate", monthly_limit=20)

    service = EntitlementService(SubscriptionRepository(db_session), FeatureRepository(db_session))
    await service.check(organization.id, "lyrics.generate")  # falls back to FREE plan defaults
    assert await service.get_monthly_limit(organization.id, "lyrics.generate") == 20


async def test_get_monthly_limit_returns_zero_for_unknown_feature(db_session):
    org = await _make_org_with_plan(db_session, OrganizationPlan.STARTER)
    service = EntitlementService(SubscriptionRepository(db_session), FeatureRepository(db_session))
    assert await service.get_monthly_limit(org.id, "nonexistent.feature") == 0

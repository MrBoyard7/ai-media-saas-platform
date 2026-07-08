"""
FastAPI dependency wiring.

This module is the composition root: it is the only place in the API layer
that knows how to construct a service from its repositories. Endpoints only
ever depend on a service (e.g. `CreditsService`), never on a repository or
the raw DB session, which keeps the HTTP layer thin and the business logic
independently testable.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.providers.registry import ProviderRegistry, build_default_registry
from app.repositories.organization_repository import (
    OrganizationMemberRepository,
    OrganizationRepository,
)
from app.repositories.subscription_repository import FeatureRepository, SubscriptionRepository
from app.repositories.wallet_repository import WalletRepository
from app.services.credits_service import CreditsService
from app.services.entitlement_service import EntitlementService
from app.services.generation_service import GenerationJobRepository, GenerationService
from app.services.organization_service import OrganizationService

# The provider registry is process-wide and stateless: one instance is
# shared by every request instead of being rebuilt per-dependency-injection.
_provider_registry = build_default_registry()


def get_provider_registry() -> ProviderRegistry:
    return _provider_registry


def get_credits_service(session: AsyncSession = Depends(get_db)) -> CreditsService:
    return CreditsService(WalletRepository(session))


def get_entitlement_service(session: AsyncSession = Depends(get_db)) -> EntitlementService:
    return EntitlementService(SubscriptionRepository(session), FeatureRepository(session))


def get_organization_service(
    session: AsyncSession = Depends(get_db),
    credits: CreditsService = Depends(get_credits_service),
) -> OrganizationService:
    return OrganizationService(
        OrganizationRepository(session),
        OrganizationMemberRepository(session),
        credits,
    )


def get_generation_service(
    session: AsyncSession = Depends(get_db),
    credits: CreditsService = Depends(get_credits_service),
    entitlements: EntitlementService = Depends(get_entitlement_service),
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> GenerationService:
    return GenerationService(GenerationJobRepository(session), credits, entitlements, registry)

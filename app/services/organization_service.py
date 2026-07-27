"""Organization service: tenant lifecycle and white-label configuration."""

from __future__ import annotations

import re
import uuid

from app.core.exceptions import OrganizationNotFoundError
from app.models.organization import MemberRole, Organization, OrganizationMember
from app.models.wallet import TransactionType
from app.repositories.organization_repository import OrganizationMemberRepository, OrganizationRepository
from app.services.credits_service import CreditsService

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    return _SLUG_RE.sub("-", name.lower()).strip("-")


class OrganizationService:
    def __init__(
        self,
        organizations: OrganizationRepository,
        members: OrganizationMemberRepository,
        credits: CreditsService,
        *,
        signup_credits: int = 100,
    ) -> None:
        self._organizations = organizations
        self._members = members
        self._credits = credits
        self._signup_credits = signup_credits

    async def create_organization(self, *, name: str, owner_user_id: str) -> Organization:
        """Create a new tenant, grant the founding member the `owner` role,
        and seed their wallet with the free signup credit grant."""
        organization = Organization(name=name, slug=slugify(name))
        await self._organizations.add(organization)

        await self._members.add(
            OrganizationMember(organization_id=organization.id, user_id=owner_user_id, role=MemberRole.OWNER)
        )

        await self._credits.credit(
            organization.id,
            amount=self._signup_credits,
            type_=TransactionType.PROMOTIONAL_GRANT,
            idempotency_key=f"signup-grant:{organization.id}",
            reference="signup_bonus",
        )
        return organization

    async def get_or_404(self, organization_id: uuid.UUID) -> Organization:
        organization = await self._organizations.get_by_id(organization_id)
        if organization is None:
            raise OrganizationNotFoundError(f"Organization {organization_id} not found.")
        return organization

    async def enable_white_label(
        self, organization_id: uuid.UUID, *, custom_domain: str, branding: dict
    ) -> Organization:
        organization = await self.get_or_404(organization_id)
        organization.is_white_label = True
        organization.custom_domain = custom_domain
        organization.branding = branding
        return organization

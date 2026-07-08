"""Repository for Organization and OrganizationMember."""
from __future__ import annotations

from sqlalchemy import select

from app.models.organization import Organization, OrganizationMember
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.session.execute(select(Organization).where(Organization.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_custom_domain(self, domain: str) -> Organization | None:
        result = await self.session.execute(select(Organization).where(Organization.custom_domain == domain))
        return result.scalar_one_or_none()


class OrganizationMemberRepository(BaseRepository[OrganizationMember]):
    model = OrganizationMember

    async def list_for_organization(self, organization_id) -> list[OrganizationMember]:
        result = await self.session.execute(
            select(OrganizationMember).where(OrganizationMember.organization_id == organization_id)
        )
        return list(result.scalars().all())

    async def get_membership(self, organization_id, user_id: str) -> OrganizationMember | None:
        result = await self.session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

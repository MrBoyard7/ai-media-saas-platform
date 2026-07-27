"""Direct unit tests for `OrganizationRepository` / `OrganizationMemberRepository`
query methods that aren't already exercised indirectly through the service layer."""

from __future__ import annotations

import pytest

from app.models.organization import MemberRole, Organization, OrganizationMember
from app.repositories.organization_repository import OrganizationMemberRepository, OrganizationRepository

pytestmark = pytest.mark.asyncio


async def test_get_by_slug_finds_existing_organization(db_session):
    org = Organization(name="Acme", slug="acme")
    db_session.add(org)
    await db_session.commit()

    found = await OrganizationRepository(db_session).get_by_slug("acme")

    assert found is not None
    assert found.id == org.id


async def test_get_by_slug_returns_none_when_missing(db_session):
    found = await OrganizationRepository(db_session).get_by_slug("does-not-exist")
    assert found is None


async def test_get_by_custom_domain_finds_white_labeled_org(db_session):
    org = Organization(name="Acme", slug="acme", is_white_label=True, custom_domain="studio.acme.com")
    db_session.add(org)
    await db_session.commit()

    found = await OrganizationRepository(db_session).get_by_custom_domain("studio.acme.com")

    assert found is not None
    assert found.slug == "acme"


async def test_get_by_custom_domain_returns_none_for_unmapped_host(db_session):
    found = await OrganizationRepository(db_session).get_by_custom_domain("unknown.example.com")
    assert found is None


async def test_list_for_organization_returns_all_members(db_session):
    org = Organization(name="Acme", slug="acme")
    db_session.add(org)
    await db_session.flush()
    db_session.add(OrganizationMember(organization_id=org.id, user_id="user-1", role=MemberRole.OWNER))
    db_session.add(OrganizationMember(organization_id=org.id, user_id="user-2", role=MemberRole.MEMBER))
    await db_session.commit()

    members = await OrganizationMemberRepository(db_session).list_for_organization(org.id)

    assert {m.user_id for m in members} == {"user-1", "user-2"}


async def test_get_membership_finds_specific_user(db_session):
    org = Organization(name="Acme", slug="acme")
    db_session.add(org)
    await db_session.flush()
    db_session.add(OrganizationMember(organization_id=org.id, user_id="user-1", role=MemberRole.ADMIN))
    await db_session.commit()

    membership = await OrganizationMemberRepository(db_session).get_membership(org.id, "user-1")

    assert membership is not None
    assert membership.role == MemberRole.ADMIN


async def test_get_membership_returns_none_for_non_member(db_session):
    org = Organization(name="Acme", slug="acme")
    db_session.add(org)
    await db_session.commit()

    membership = await OrganizationMemberRepository(db_session).get_membership(org.id, "ghost-user")

    assert membership is None

"""Shared pytest fixtures.

The whole suite runs against an in-memory SQLite database via `aiosqlite`
-- no Docker, no network, no external services required. `app.models.types`
is what makes this possible (see that module's docstring): the exact same
model definitions that run on PostgreSQL in production compile cleanly
against SQLite here.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import AuthContext, get_current_auth_context
from app.main import app
from app.models.organization import Organization, OrganizationPlan
from app.models.subscription import Feature, PlanFeature, Subscription, SubscriptionStatus
from app.models.wallet import Wallet


@pytest_asyncio.fixture
async def session_factory():
    """An `async_sessionmaker` bound to a fresh in-memory SQLite database.

    `poolclass=StaticPool` is required for an in-memory SQLite database in
    tests: without it, every new connection checkout gets its own separate
    (and empty) `:memory:` database, so the schema created below would be
    invisible to any session opened after this fixture returns -- including
    the ad-hoc sessions `TenantResolutionMiddleware` opens per-request (see
    the `client` fixture below, which points `app.state.db_sessionmaker` at
    this exact factory).
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def seeded_organization(db_session: AsyncSession) -> Organization:
    """An organization on the PRO plan with a funded wallet and every
    feature flag needed by the integration tests already entitled."""
    organization = Organization(name="Acme Studio", slug="acme-studio", plan=OrganizationPlan.PRO)
    db_session.add(organization)
    await db_session.flush()

    db_session.add(Wallet(organization_id=organization.id, balance=1_000))
    db_session.add(Subscription(organization_id=organization.id, plan=OrganizationPlan.PRO, status=SubscriptionStatus.ACTIVE))

    for key in ("lyrics.generate", "music.generate", "voice.generate", "video.generate"):
        feature = Feature(key=key, name=key, description="")
        db_session.add(feature)
        await db_session.flush()
        db_session.add(PlanFeature(plan=OrganizationPlan.PRO, feature_id=feature.id, enabled=True, monthly_limit=None))

    await db_session.commit()
    await db_session.refresh(organization)
    return organization


@pytest_asyncio.fixture
async def client(session_factory, db_session: AsyncSession, seeded_organization: Organization) -> AsyncIterator[AsyncClient]:
    """An httpx AsyncClient wired to the FastAPI app, with the DB and auth
    dependencies overridden so no real Postgres or Supabase is required."""

    async def _override_get_db():
        yield db_session

    async def _override_auth() -> AuthContext:
        return AuthContext(
            user_id=str(uuid.uuid4()),
            organization_id=str(seeded_organization.id),
            role="owner",
            scopes=("*",),
        )

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_auth_context] = _override_auth
    # TenantResolutionMiddleware isn't part of FastAPI's Depends graph, so
    # it can't be overridden via dependency_overrides -- point it at the
    # same in-memory engine directly (see app/middleware/tenant.py).
    app.state.db_sessionmaker = session_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def no_real_celery_broker():
    """Tests never talk to a real Redis broker: `send_task` is stubbed so the
    HTTP layer can be exercised end-to-end without a running Celery stack."""
    with patch("app.api.v1.endpoints.generation.celery_app.send_task") as mock_send_task:
        yield mock_send_task

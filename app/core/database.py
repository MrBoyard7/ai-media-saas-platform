"""
Async SQLAlchemy engine and session management.

The platform is multi-tenant at the *row* level (an `organization_id` column
on every tenant-scoped table) rather than schema-per-tenant. This keeps
migrations simple while still allowing a move to schema- or
database-per-tenant later for large enterprise customers, since the
repository layer is the only place that knows about this decision.
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a request-scoped async session.

    Follows the unit-of-work-per-request pattern: the transaction opened by
    this session is committed once the endpoint (and every dependency
    layered on top of it) has returned successfully, and rolled back if
    anything raised. Endpoints and services should never call
    `session.commit()` themselves -- only this dependency and
    `session_scope()` (its Celery/script equivalent) do.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Context manager for use outside of FastAPI (Celery tasks, scripts)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

"""Shared mixins for every ORM model in the platform."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.types import GUID


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TenantScopedMixin:
    """Mixin applied to every table that belongs to a single organization.

    Row-level multi-tenancy: every query in the repository layer MUST filter
    on `organization_id`. See docs/adr/0002-multi-tenancy-strategy.md for why
    this was chosen over schema-per-tenant.
    """

    @staticmethod
    def organization_fk():
        return mapped_column(
            GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
        )

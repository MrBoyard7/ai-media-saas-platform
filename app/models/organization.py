"""Organization = tenant. Every other resource in the platform is scoped to one."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import GUID, PortableJSON, StrEnum

if TYPE_CHECKING:
    # Import-time-only: Organization, Wallet and Subscription reference each
    # other, so a real (non-guarded) import here would be circular. The
    # string forward references below (`Mapped["Wallet"]`) are what
    # SQLAlchemy actually resolves at runtime, via its mapper registry --
    # this block exists purely so mypy/ruff can resolve those same strings
    # statically instead of flagging them as undefined names.
    from app.models.subscription import Subscription
    from app.models.wallet import Wallet


class OrganizationPlan(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class MemberRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    BILLING = "billing"


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A tenant account. Doubles as the white-label unit: every organization
    can carry its own branding config, custom domain and feature flags."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    plan: Mapped[OrganizationPlan] = mapped_column(
        StrEnum(OrganizationPlan, name="organization_plan"), default=OrganizationPlan.FREE, nullable=False
    )

    # --- White-label configuration -----------------------------------------
    is_white_label: Mapped[bool] = mapped_column(default=False, nullable=False)
    custom_domain: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    branding: Mapped[dict] = mapped_column(PortableJSON(), default=dict, nullable=False)
    # e.g. {"logo_url": "...", "primary_color": "#111827", "product_name": "Acme Studio"}

    members: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    wallet: Mapped["Wallet"] = relationship(
        back_populates="organization", uselist=False, cascade="all, delete-orphan"
    )
    subscription: Mapped["Subscription"] = relationship(
        back_populates="organization", uselist=False, cascade="all, delete-orphan"
    )


class OrganizationMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Join table linking a Supabase-authenticated user to an organization."""

    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_member"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # Supabase auth.users.id
    role: Mapped[MemberRole] = mapped_column(
        StrEnum(MemberRole, name="member_role"), default=MemberRole.MEMBER
    )

    organization: Mapped["Organization"] = relationship(back_populates="members")

"""Feature-based subscription & entitlement models.

Rather than hard-coding "what plan X can do" in application code, features
are data: a `Feature` is a capability key (e.g. `video.generate`,
`voice.clone`, `api.rate_limit_tier_2`) and a `PlanFeature` row says which
plans include it and with what limits. This lets Sales/Product ship a new
pricing tier or run an A/B experiment without a deploy.
"""
import enum
import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.organization import Organization, OrganizationPlan
from app.models.types import GUID, StrEnum


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    plan: Mapped[OrganizationPlan] = mapped_column(StrEnum(OrganizationPlan, name="subscription_plan"), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        StrEnum(SubscriptionStatus, name="subscription_status"), default=SubscriptionStatus.TRIALING
    )
    external_billing_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Stripe/Paddle subscription id

    organization: Mapped[Organization] = relationship(back_populates="subscription")


class Feature(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single, independently-toggleable platform capability."""

    __tablename__ = "features"

    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)  # e.g. "video.generate"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="")


class PlanFeature(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Associates a Feature with a Plan, plus an optional numeric limit
    (e.g. max generations/month). Absence of a row == not entitled."""

    __tablename__ = "plan_features"
    __table_args__ = (UniqueConstraint("plan", "feature_id", name="uq_plan_feature"),)

    plan: Mapped[OrganizationPlan] = mapped_column(StrEnum(OrganizationPlan, name="plan_feature_plan"), nullable=False)
    feature_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("features.id", ondelete="CASCADE"), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    monthly_limit: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # None == unlimited

    feature: Mapped["Feature"] = relationship()

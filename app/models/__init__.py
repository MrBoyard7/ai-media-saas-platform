"""Import every model here so `Base.metadata` is complete for Alembic
autogeneration and for the `scripts/seed_demo_data.py` bootstrap script."""
from app.models.job import GenerationJob, JobKind, JobStatus  # noqa: F401
from app.models.organization import (  # noqa: F401
    MemberRole,
    Organization,
    OrganizationMember,
    OrganizationPlan,
)
from app.models.subscription import (  # noqa: F401
    Feature,
    PlanFeature,
    Subscription,
    SubscriptionStatus,
)
from app.models.wallet import CreditTransaction, TransactionType, Wallet  # noqa: F401

__all__ = [
    "GenerationJob",
    "JobKind",
    "JobStatus",
    "MemberRole",
    "Organization",
    "OrganizationMember",
    "OrganizationPlan",
    "Feature",
    "PlanFeature",
    "Subscription",
    "SubscriptionStatus",
    "CreditTransaction",
    "TransactionType",
    "Wallet",
]

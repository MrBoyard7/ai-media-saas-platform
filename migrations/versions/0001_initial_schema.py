"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-01-01 00:00:00
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

# NOTE: written for PostgreSQL (production target). The test suite instead
# builds the schema directly from the ORM metadata against SQLite
# (see tests/conftest.py), so this file is exercised by `alembic upgrade
# head` against a real Postgres instance, not by pytest.


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "plan",
            sa.Enum("free", "starter", "pro", "enterprise", name="organization_plan"),
            nullable=False,
            server_default="free",
        ),
        sa.Column("is_white_label", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("custom_domain", sa.String(255), unique=True, nullable=True),
        sa.Column("branding", postgresql.JSONB(), nullable=False, server_default="{}"),
    )

    op.create_table(
        "organization_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("owner", "admin", "member", "billing", name="member_role"), nullable=False, server_default="member"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
    )
    op.create_index("ix_org_members_org_id", "organization_members", ["organization_id"])
    op.create_index("ix_org_members_user_id", "organization_members", ["user_id"])

    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("balance", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("currency_credits_per_usd", sa.BigInteger(), nullable=False, server_default="100"),
    )

    op.create_table(
        "credit_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column(
            "type",
            sa.Enum("top_up", "subscription_grant", "generation_debit", "refund", "promotional_grant", "admin_adjustment", name="transaction_type"),
            nullable=False,
        ),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.UniqueConstraint("wallet_id", "idempotency_key", name="uq_wallet_idempotency_key"),
    )
    op.create_index("ix_credit_transactions_wallet_created", "credit_transactions", ["wallet_id", "created_at"])

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("plan", sa.Enum("free", "starter", "pro", "enterprise", name="subscription_plan"), nullable=False),
        sa.Column("status", sa.Enum("active", "trialing", "past_due", "canceled", name="subscription_status"), nullable=False, server_default="trialing"),
        sa.Column("external_billing_id", sa.String(255), nullable=True),
    )

    op.create_table(
        "features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), server_default=""),
    )

    op.create_table(
        "plan_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("plan", sa.Enum("free", "starter", "pro", "enterprise", name="plan_feature_plan"), nullable=False),
        sa.Column("feature_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("features.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("monthly_limit", sa.BigInteger(), nullable=True),
        sa.UniqueConstraint("plan", "feature_id", name="uq_plan_feature"),
    )

    op.create_table(
        "generation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by_user_id", sa.String(255), nullable=False),
        sa.Column("kind", sa.Enum("lyrics", "music", "voice", "video", name="job_kind"), nullable=False),
        sa.Column("provider_name", sa.String(100), nullable=False),
        sa.Column("status", sa.Enum("queued", "running", "succeeded", "failed", "canceled", name="job_status"), nullable=False, server_default="queued"),
        sa.Column("input_payload", postgresql.JSONB(), nullable=False),
        sa.Column("output_payload", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.String(2000), nullable=True),
        sa.Column("credits_reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
    )
    op.create_index("ix_generation_jobs_organization_id", "generation_jobs", ["organization_id"])
    op.create_index("ix_generation_jobs_celery_task_id", "generation_jobs", ["celery_task_id"])


def downgrade() -> None:
    op.drop_table("generation_jobs")
    op.drop_table("plan_features")
    op.drop_table("features")
    op.drop_table("subscriptions")
    op.drop_table("credit_transactions")
    op.drop_table("wallets")
    op.drop_table("organization_members")
    op.drop_table("organizations")

    for enum_name in (
        "job_status",
        "job_kind",
        "plan_feature_plan",
        "subscription_status",
        "subscription_plan",
        "transaction_type",
        "member_role",
        "organization_plan",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)

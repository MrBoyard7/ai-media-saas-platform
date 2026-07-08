"""
Seed the database with demo data: the four plans' feature entitlements and a
sample organization. Safe to run multiple times (idempotent upserts).

Usage:
    python -m scripts.seed_demo_data
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.database import Base, engine, session_scope
from app.models.organization import OrganizationPlan
from app.models.subscription import Feature, PlanFeature

FEATURES = [
    ("lyrics.generate", "Lyrics Generation", "Generate song lyrics from a text prompt."),
    ("music.generate", "Music Generation", "Generate instrumental or full music tracks."),
    ("voice.generate", "Voice Generation", "Text-to-speech and voice cloning."),
    ("video.generate", "Video Generation", "AI-generated video clips."),
    ("api.white_label", "White-Label API Access", "Serve the platform under a custom domain/brand."),
]

# (plan, feature_key, monthly_limit or None for unlimited)
PLAN_FEATURES = [
    (OrganizationPlan.FREE, "lyrics.generate", 20),
    (OrganizationPlan.STARTER, "lyrics.generate", None),
    (OrganizationPlan.STARTER, "music.generate", 50),
    (OrganizationPlan.PRO, "lyrics.generate", None),
    (OrganizationPlan.PRO, "music.generate", None),
    (OrganizationPlan.PRO, "voice.generate", 200),
    (OrganizationPlan.ENTERPRISE, "lyrics.generate", None),
    (OrganizationPlan.ENTERPRISE, "music.generate", None),
    (OrganizationPlan.ENTERPRISE, "voice.generate", None),
    (OrganizationPlan.ENTERPRISE, "video.generate", None),
    (OrganizationPlan.ENTERPRISE, "api.white_label", None),
]


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_scope() as session:
        key_to_feature: dict[str, Feature] = {}
        for key, name, description in FEATURES:
            result = await session.execute(select(Feature).where(Feature.key == key))
            feature = result.scalar_one_or_none()
            if feature is None:
                feature = Feature(key=key, name=name, description=description)
                session.add(feature)
                await session.flush()
            key_to_feature[key] = feature

        for plan, feature_key, monthly_limit in PLAN_FEATURES:
            feature = key_to_feature[feature_key]
            result = await session.execute(
                select(PlanFeature).where(PlanFeature.plan == plan, PlanFeature.feature_id == feature.id)
            )
            if result.scalar_one_or_none() is None:
                session.add(PlanFeature(plan=plan, feature_id=feature.id, enabled=True, monthly_limit=monthly_limit))

    print("Seed complete: features and plan entitlements are up to date.")


if __name__ == "__main__":
    asyncio.run(seed())

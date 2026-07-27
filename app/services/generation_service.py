"""
Generation service: the orchestration layer that ties everything together.

Request lifecycle for every lyrics/music/voice/video generation:

    1. Check feature entitlement for the organization's plan.
    2. Ask the target provider adapter for a cost estimate.
    3. Debit the wallet for that estimate (idempotent on `idempotency_key`).
    4. Persist a `GenerationJob` row with status=QUEUED.
    5. Enqueue a Celery task (see `app.workers.tasks`) and return the job id.

If step 3 fails (insufficient credits) no job row is ever created and no
GPU worker is ever touched -- the platform never spends compute it hasn't
already been paid for.
"""

from __future__ import annotations

import uuid

from app.models.job import GenerationJob, JobKind, JobStatus
from app.providers.base import Capability, GenerationRequest
from app.providers.registry import ProviderRegistry
from app.repositories.base import BaseRepository
from app.services.credits_service import CreditsService
from app.services.entitlement_service import EntitlementService

_FEATURE_KEY_BY_CAPABILITY: dict[Capability, str] = {
    Capability.LYRICS: "lyrics.generate",
    Capability.MUSIC: "music.generate",
    Capability.VOICE: "voice.generate",
    Capability.VIDEO: "video.generate",
}

_KIND_BY_CAPABILITY: dict[Capability, JobKind] = {
    Capability.LYRICS: JobKind.LYRICS,
    Capability.MUSIC: JobKind.MUSIC,
    Capability.VOICE: JobKind.VOICE,
    Capability.VIDEO: JobKind.VIDEO,
}


class GenerationJobRepository(BaseRepository[GenerationJob]):
    model = GenerationJob


class GenerationService:
    def __init__(
        self,
        jobs: GenerationJobRepository,
        credits: CreditsService,
        entitlements: EntitlementService,
        registry: ProviderRegistry,
    ) -> None:
        self._jobs = jobs
        self._credits = credits
        self._entitlements = entitlements
        self._registry = registry

    async def request_generation(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: str,
        capability: Capability,
        prompt: str,
        parameters: dict | None = None,
        reference_asset_url: str | None = None,
        provider_name: str | None = None,
        idempotency_key: str,
    ) -> GenerationJob:
        parameters = parameters or {}

        feature_key = _FEATURE_KEY_BY_CAPABILITY[capability]
        await self._entitlements.check(organization_id, feature_key)

        adapter = self._registry.get(capability, provider_name)

        job = GenerationJob(
            organization_id=organization_id,
            requested_by_user_id=user_id,
            kind=_KIND_BY_CAPABILITY[capability],
            provider_name=adapter.name,
            status=JobStatus.QUEUED,
            input_payload={
                "prompt": prompt,
                "parameters": parameters,
                "reference_asset_url": reference_asset_url,
            },
        )

        probe_request = GenerationRequest(
            organization_id=str(organization_id),
            job_id="estimate",  # cost estimation never needs a real job id
            capability=capability,
            prompt=prompt,
            parameters=parameters,
            reference_asset_url=reference_asset_url,
        )
        estimated_cost = adapter.estimate_cost_credits(probe_request)

        await self._jobs.add(job)  # flush to obtain job.id before debiting

        await self._credits.debit(
            organization_id,
            amount=estimated_cost,
            idempotency_key=idempotency_key,
            reference=str(job.id),
            metadata={"job_id": str(job.id), "capability": capability.value},
        )
        job.credits_reserved = estimated_cost

        # NOTE: the actual `celery_app.send_task(...)` enqueue call is issued
        # by the API endpoint (see app.api.v1.endpoints.generation) right
        # after this method returns, once the DB transaction has committed --
        # enqueuing *before* commit risks a worker picking up a job the
        # database doesn't know about yet if the transaction later rolls back.
        return job

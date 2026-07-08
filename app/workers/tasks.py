"""
Celery tasks: the GPU-worker-facing side of the AI Job Queue.

Each task loads the `GenerationJob` row, resolves the right adapter from
the provider registry, runs the (potentially GPU-bound) generation, and
writes the result back. On failure, credits are refunded automatically so
customers are never charged for a job that didn't produce output.

In production these tasks are consumed by GPU-backed Celery workers
(`queue=gpu.music`, `gpu.voice`, `gpu.video`) running on RunPod serverless
GPU instances, while the lightweight `lyrics` queue can run on plain CPU
workers alongside the API.
"""
from __future__ import annotations

import asyncio
import uuid

from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.core.database import session_scope
from app.models.job import JobStatus
from app.providers.base import Capability, GenerationRequest, ProviderError
from app.providers.registry import build_default_registry
from app.repositories.wallet_repository import WalletRepository
from app.services.credits_service import CreditsService
from app.services.generation_service import GenerationJobRepository

logger = get_task_logger(__name__)

# Built once per worker process; adapters here are cheap, stateless objects.
_registry = build_default_registry()

_CAPABILITY_BY_KIND = {
    "lyrics": Capability.LYRICS,
    "music": Capability.MUSIC,
    "voice": Capability.VOICE,
    "video": Capability.VIDEO,
}


async def _run_generation_job(job_id: str) -> None:
    async with session_scope() as session:
        jobs = GenerationJobRepository(session)
        job = await jobs.get_by_id(uuid.UUID(job_id))
        if job is None:
            logger.warning("generation job %s not found, skipping", job_id)
            return

        job.status = JobStatus.RUNNING
        await session.flush()

        capability = _CAPABILITY_BY_KIND[job.kind.value]
        adapter = _registry.get(capability, job.provider_name)

        request = GenerationRequest(
            organization_id=str(job.organization_id),
            job_id=str(job.id),
            capability=capability,
            prompt=job.input_payload["prompt"],
            parameters=job.input_payload.get("parameters", {}),
            reference_asset_url=job.input_payload.get("reference_asset_url"),
        )

        try:
            result = await adapter.generate(request)
        except ProviderError as exc:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            wallets = WalletRepository(session)
            credits = CreditsService(wallets)
            if job.credits_reserved:
                await credits.refund(
                    job.organization_id,
                    amount=job.credits_reserved,
                    idempotency_key=f"refund:{job.id}",
                    reference=str(job.id),
                )
            logger.error("generation job %s failed: %s", job_id, exc)
            return

        job.status = JobStatus.SUCCEEDED
        job.output_payload = {
            "output_url": result.output_url,
            "duration_seconds": result.duration_seconds,
            "provider_metadata": result.raw_provider_metadata,
        }


def _run_async(coro) -> None:
    """Celery workers are synchronous; each task gets its own event loop."""
    asyncio.run(coro)


@celery_app.task(name="app.workers.tasks.generate_lyrics_task", bind=True, max_retries=3)
def generate_lyrics_task(self, job_id: str) -> None:
    _run_async(_run_generation_job(job_id))


@celery_app.task(name="app.workers.tasks.generate_music_task", bind=True, max_retries=3)
def generate_music_task(self, job_id: str) -> None:
    _run_async(_run_generation_job(job_id))


@celery_app.task(name="app.workers.tasks.generate_voice_task", bind=True, max_retries=3)
def generate_voice_task(self, job_id: str) -> None:
    _run_async(_run_generation_job(job_id))


@celery_app.task(name="app.workers.tasks.generate_video_task", bind=True, max_retries=3)
def generate_video_task(self, job_id: str) -> None:
    _run_async(_run_generation_job(job_id))

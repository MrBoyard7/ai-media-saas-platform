"""AI Generation API: the single entry point for lyrics, music, voice and video jobs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.deps import get_generation_service
from app.core.celery_app import celery_app
from app.core.security import AuthContext, get_current_auth_context
from app.models.job import JobKind
from app.schemas.generation import GenerationCreateRequest, GenerationJobRead
from app.services.generation_service import GenerationService

router = APIRouter(prefix="/generate", tags=["generation"])

_TASK_NAME_BY_KIND = {
    JobKind.LYRICS: "app.workers.tasks.generate_lyrics_task",
    JobKind.MUSIC: "app.workers.tasks.generate_music_task",
    JobKind.VOICE: "app.workers.tasks.generate_voice_task",
    JobKind.VIDEO: "app.workers.tasks.generate_video_task",
}


@router.post("", response_model=GenerationJobRead, status_code=202)
async def create_generation(
    payload: GenerationCreateRequest,
    ctx: AuthContext = Depends(get_current_auth_context),
    generation: GenerationService = Depends(get_generation_service),
) -> GenerationJobRead:
    """Reserve credits, persist the job, and enqueue it for a GPU worker.

    Returns HTTP 202 with the job in `queued` status; clients poll
    `GET /jobs/{id}` or subscribe to the job's webhook for the result.
    """
    job = await generation.request_generation(
        organization_id=uuid.UUID(ctx.organization_id),
        user_id=ctx.user_id,
        capability=payload.capability,
        prompt=payload.prompt,
        parameters=payload.parameters,
        reference_asset_url=payload.reference_asset_url,
        provider_name=payload.provider_name,
        idempotency_key=payload.idempotency_key,
    )

    celery_app.send_task(_TASK_NAME_BY_KIND[job.kind], args=[str(job.id)])
    return GenerationJobRead.model_validate(job)

"""Jobs API: poll the status of an asynchronous generation job."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import JobNotFoundError
from app.schemas.generation import GenerationJobRead
from app.services.generation_service import GenerationJobRepository

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=GenerationJobRead)
async def get_job(job_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> GenerationJobRead:
    job = await GenerationJobRepository(session).get_by_id(job_id)
    if job is None:
        raise JobNotFoundError(f"Job {job_id} not found.")
    return GenerationJobRead.model_validate(job)

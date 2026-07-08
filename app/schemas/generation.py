"""Pydantic request/response schemas for the AI Generation API."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.job import JobKind, JobStatus
from app.providers.base import Capability


class GenerationCreateRequest(BaseModel):
    capability: Capability
    prompt: str = Field(min_length=1, max_length=4000)
    parameters: dict = Field(default_factory=dict)
    reference_asset_url: str | None = None
    provider_name: str | None = Field(default=None, description="Force a specific provider; omit to use the plan default.")
    idempotency_key: str = Field(min_length=8, max_length=255)


class GenerationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: JobKind
    provider_name: str
    status: JobStatus
    credits_reserved: int
    output_payload: dict | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

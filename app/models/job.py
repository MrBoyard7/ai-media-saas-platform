"""GenerationJob: the durable record behind every asynchronous AI job.

The row is created synchronously (so the API can return a `job_id`
immediately) and then updated by a Celery worker as the job moves through
the GPU pipeline. This table is what powers webhook notifications, the
user dashboard's "My Generations" view and SDK polling.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import GUID, PortableJSON, StrEnum


class JobKind(str, enum.Enum):
    LYRICS = "lyrics"
    MUSIC = "music"
    VOICE = "voice"
    VIDEO = "video"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class GenerationJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "generation_jobs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[JobKind] = mapped_column(StrEnum(JobKind, name="job_kind"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "audiocraft", "openvoice"
    status: Mapped[JobStatus] = mapped_column(StrEnum(JobStatus, name="job_status"), default=JobStatus.QUEUED, nullable=False)

    input_payload: Mapped[dict] = mapped_column(PortableJSON(), nullable=False)
    output_payload: Mapped[dict | None] = mapped_column(PortableJSON(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    credits_reserved: Mapped[int] = mapped_column(default=0, nullable=False)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

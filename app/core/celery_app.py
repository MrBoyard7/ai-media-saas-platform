"""
Celery application factory.

Background AI generation jobs (lyrics, music, voice, video) are long-running
and GPU-bound, so they are never executed inline on the request/response
cycle. The API only ever *enqueues* a job and returns a job id; a pool of
GPU workers (see `app.workers.tasks`) picks the job up asynchronously.
"""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_media_saas_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # fair dispatch across GPU workers
    task_routes={
        "app.workers.tasks.generate_lyrics_task": {"queue": "lyrics"},
        "app.workers.tasks.generate_music_task": {"queue": "gpu.music"},
        "app.workers.tasks.generate_voice_task": {"queue": "gpu.voice"},
        "app.workers.tasks.generate_video_task": {"queue": "gpu.video"},
    },
)

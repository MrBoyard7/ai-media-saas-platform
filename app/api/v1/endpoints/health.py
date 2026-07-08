"""Liveness/readiness endpoint used by Docker, Kubernetes and uptime checks."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}

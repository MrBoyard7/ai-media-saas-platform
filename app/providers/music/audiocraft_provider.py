"""
Reference adapter for a Meta AudioCraft-style music generation backend.

NOTE ON SCOPE: this adapter *simulates* an AudioCraft GPU worker call
(latency, output shape, failure modes) rather than shelling out to a real
model checkpoint, since that requires a CUDA GPU and multi-gigabyte model
weights that don't belong in an architecture-reference repository. In a
real deployment this class's `generate()` body would be replaced with an
RPC call to the GPU worker pool (see `docs/architecture.md#gpu-workers`),
typically via RunPod's serverless API. The adapter contract, the retry /
timeout policy and the cost model below are production-shaped.
"""
from __future__ import annotations

import asyncio
import random

from app.providers.base import (
    AIProviderAdapter,
    Capability,
    GenerationRequest,
    GenerationResult,
    ProviderError,
)

_MAX_DURATION_SECONDS = 300
_CREDITS_PER_SECOND = 2


class AudioCraftMusicProvider(AIProviderAdapter):
    name = "audiocraft"
    capability = Capability.MUSIC

    def __init__(self, *, simulated_failure_rate: float = 0.0) -> None:
        # Exposed for tests that want to exercise the retry/error path.
        self._simulated_failure_rate = simulated_failure_rate

    async def health_check(self) -> bool:
        # A real implementation would ping the RunPod endpoint / GPU worker pool.
        return True

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        duration = int(request.parameters.get("duration_seconds", 30))
        if duration <= 0 or duration > _MAX_DURATION_SECONDS:
            raise ProviderError(f"duration_seconds must be between 1 and {_MAX_DURATION_SECONDS}.")

        await asyncio.sleep(min(duration / 60, 2.0))  # simulate proportional GPU render time

        if random.random() < self._simulated_failure_rate:
            raise ProviderError("Simulated AudioCraft worker timeout.")

        output_url = f"https://storage.example.com/music/{request.organization_id}/{request.job_id}.wav"
        return GenerationResult(
            output_url=output_url,
            provider_name=self.name,
            duration_seconds=float(duration),
            raw_provider_metadata={
                "model": "musicgen-melody-large (reference)",
                "sample_rate_hz": 32000,
                "genre_hint": request.parameters.get("genre"),
            },
        )

    def estimate_cost_credits(self, request: GenerationRequest) -> int:
        duration = int(request.parameters.get("duration_seconds", 30))
        return max(1, duration * _CREDITS_PER_SECOND)

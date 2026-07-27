"""
Reference lyrics provider.

This is a deterministic, dependency-free reference implementation used for
local development, tests and demos. It is written to the exact same
`AIProviderAdapter` contract a real LLM-backed lyrics engine would use, so
swapping in a hosted or self-hosted language model is purely additive: copy
this file, replace `_compose` with a real model call, and register the new
class in `app.providers.registry`.
"""

from __future__ import annotations

import asyncio
import hashlib
import time

from app.providers.base import (
    AIProviderAdapter,
    Capability,
    GenerationRequest,
    GenerationResult,
    ProviderError,
)


class MockLyricsProvider(AIProviderAdapter):
    name = "reference-lyrics-v1"
    capability = Capability.LYRICS

    async def health_check(self) -> bool:
        return True

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if not request.prompt.strip():
            raise ProviderError("Lyrics prompt must not be empty.")

        # Simulate model latency proportional to requested length.
        target_lines = int(request.parameters.get("line_count", 16))
        await asyncio.sleep(min(0.05 * target_lines, 1.0))

        digest = hashlib.sha256(f"{request.prompt}:{request.job_id}".encode()).hexdigest()[:12]
        output_url = (
            f"https://storage.example.com/lyrics/{request.organization_id}/{request.job_id}-{digest}.txt"
        )

        return GenerationResult(
            output_url=output_url,
            provider_name=self.name,
            duration_seconds=round(time.monotonic() % 1.0, 3),
            raw_provider_metadata={
                "line_count": target_lines,
                "language": request.parameters.get("language", "en"),
            },
        )

    def estimate_cost_credits(self, request: GenerationRequest) -> int:
        line_count = int(request.parameters.get("line_count", 16))
        return max(1, line_count // 4)  # 1 credit per 4 lines, minimum 1

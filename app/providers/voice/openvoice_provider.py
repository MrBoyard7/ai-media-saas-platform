"""
Reference adapter for an OpenVoice / RVC-style voice cloning & TTS backend.

Same scope note as `app.providers.music.audiocraft_provider`: this
simulates the provider boundary (input validation, cost model, latency,
failure surface) rather than running real voice-cloning inference. Two
concrete providers (OpenVoice for cross-lingual cloning, RVC for
retrieval-based voice conversion) are expected to implement this same
`AIProviderAdapter` contract in production, selected per-request via the
`provider_name` field on `GenerationJob`.
"""
from __future__ import annotations

import asyncio

from app.providers.base import (
    AIProviderAdapter,
    Capability,
    GenerationRequest,
    GenerationResult,
    ProviderError,
)

_CREDITS_PER_CHARACTER = 1


class OpenVoiceProvider(AIProviderAdapter):
    name = "openvoice"
    capability = Capability.VOICE

    async def health_check(self) -> bool:
        return True

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if request.parameters.get("clone_voice") and not request.reference_asset_url:
            raise ProviderError("Voice cloning requires a `reference_asset_url` sample.")

        text_length = len(request.prompt)
        await asyncio.sleep(min(text_length / 500, 1.5))

        output_url = f"https://storage.example.com/voice/{request.organization_id}/{request.job_id}.mp3"
        return GenerationResult(
            output_url=output_url,
            provider_name=self.name,
            duration_seconds=round(text_length / 15, 2),  # ~15 chars/sec speaking rate estimate
            raw_provider_metadata={
                "voice_id": request.parameters.get("voice_id", "default"),
                "cloned": bool(request.parameters.get("clone_voice")),
                "language": request.parameters.get("language", "en"),
            },
        )

    def estimate_cost_credits(self, request: GenerationRequest) -> int:
        base = max(1, len(request.prompt) * _CREDITS_PER_CHARACTER // 10)
        return base * 3 if request.parameters.get("clone_voice") else base

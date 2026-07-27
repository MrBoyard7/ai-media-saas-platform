"""
Reference adapter for a ComfyUI-style image/video generation pipeline.

Same scope note as the other reference adapters in this package: this
simulates a ComfyUI workflow execution (queueing a prompt graph, polling
for completion, retrieving the output) rather than running one, since that
requires a running ComfyUI instance with GPU-backed checkpoints. The shape
below -- `workflow_id` selecting a pre-built ComfyUI graph, async polling
semantics -- mirrors ComfyUI's real `/prompt` + `/history` API.
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

_CREDITS_PER_SECOND_OF_VIDEO = 8


class ComfyUIVideoProvider(AIProviderAdapter):
    name = "comfyui"
    capability = Capability.VIDEO

    async def health_check(self) -> bool:
        return True

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        workflow_id = request.parameters.get("workflow_id", "text-to-video-default")
        duration = float(request.parameters.get("duration_seconds", 4))
        if duration <= 0 or duration > 30:
            raise ProviderError("Video duration_seconds must be between 0 and 30 for this workflow tier.")

        # Simulate queueing + rendering a ComfyUI workflow graph.
        await asyncio.sleep(min(duration / 4, 3.0))

        output_url = f"https://storage.example.com/video/{request.organization_id}/{request.job_id}.mp4"
        return GenerationResult(
            output_url=output_url,
            provider_name=self.name,
            duration_seconds=duration,
            raw_provider_metadata={
                "workflow_id": workflow_id,
                "resolution": request.parameters.get("resolution", "768x768"),
                "fps": request.parameters.get("fps", 24),
            },
        )

    def estimate_cost_credits(self, request: GenerationRequest) -> int:
        duration = float(request.parameters.get("duration_seconds", 4))
        return max(5, int(duration * _CREDITS_PER_SECOND_OF_VIDEO))

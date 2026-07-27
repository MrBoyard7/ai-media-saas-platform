"""
Provider Adapter Layer.

This module is the single most important architectural decision in the
platform: **business logic never talks to AudioCraft, OpenVoice, RVC or
ComfyUI directly.** It talks to one of these small `Protocol` interfaces.

Adding a new AI provider -- or swapping a commercial API in for an
open-source model -- means writing one new adapter class and registering
it in `app.providers.registry`. Nothing in `app.services`, `app.api` or
`app.workers` ever changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class Capability(str, Enum):
    """The four generation capabilities exposed by the platform today.

    New capabilities (e.g. `IMAGE`, `AVATAR`) can be added without touching
    any existing adapter.
    """

    LYRICS = "lyrics"
    MUSIC = "music"
    VOICE = "voice"
    VIDEO = "video"


@dataclass(frozen=True)
class GenerationRequest:
    """Provider-agnostic request envelope.

    `parameters` intentionally stays a loosely-typed dict: each adapter is
    responsible for validating and translating the subset of parameters it
    understands into its own provider's native call. This keeps the
    envelope stable even as individual providers evolve their parameter
    surface.
    """

    organization_id: str
    job_id: str
    capability: Capability
    prompt: str
    parameters: dict[str, Any] = field(default_factory=dict)
    reference_asset_url: str | None = None  # e.g. a voice sample to clone, an image to animate


@dataclass(frozen=True)
class GenerationResult:
    """Provider-agnostic result envelope returned by every adapter."""

    output_url: str
    provider_name: str
    duration_seconds: float | None = None
    raw_provider_metadata: dict[str, Any] = field(default_factory=dict)


class ProviderError(Exception):
    """Raised by an adapter when the underlying provider fails.

    Adapters should catch their own provider-specific exceptions (HTTP
    errors, CUDA OOM, timeouts, ...) and re-raise as `ProviderError` so the
    orchestration layer only ever needs to handle one exception type.
    """


@runtime_checkable
class AIProviderAdapter(Protocol):
    """The contract every AI provider integration must satisfy."""

    #: Unique, stable identifier used in the `generation_jobs.provider_name` column.
    name: str
    #: The single capability this adapter implements.
    capability: Capability

    async def health_check(self) -> bool:
        """Return True if the provider is reachable and able to accept work."""
        ...

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Run the generation and return a result. Must raise `ProviderError`
        (never a provider-specific exception) on failure."""
        ...

    def estimate_cost_credits(self, request: GenerationRequest) -> int:
        """Return how many credits this request will cost, computed *before*
        the job runs so the caller's wallet can be debited up front."""
        ...

"""
Provider Registry.

A small, dependency-free registry mapping `(capability, provider_name)` to
a concrete adapter instance. The registry -- not application code -- is the
only place that decides which concrete provider handles a given capability,
which is what makes the platform "provider independent" and "model
agnostic": routing a job to a different provider is a configuration change,
not a code change.
"""
from __future__ import annotations

from app.providers.base import AIProviderAdapter, Capability, ProviderError


class ProviderRegistry:
    """In-memory registry of provider adapters, keyed by capability."""

    def __init__(self) -> None:
        self._adapters: dict[Capability, dict[str, AIProviderAdapter]] = {c: {} for c in Capability}
        self._default_provider: dict[Capability, str] = {}

    def register(self, adapter: AIProviderAdapter, *, is_default: bool = False) -> None:
        self._adapters[adapter.capability][adapter.name] = adapter
        if is_default or adapter.capability not in self._default_provider:
            self._default_provider[adapter.capability] = adapter.name

    def get(self, capability: Capability, provider_name: str | None = None) -> AIProviderAdapter:
        provider_name = provider_name or self._default_provider.get(capability)
        adapters_for_capability = self._adapters.get(capability, {})
        if not provider_name or provider_name not in adapters_for_capability:
            raise ProviderError(
                f"No adapter registered for capability={capability.value!r} "
                f"provider={provider_name!r}."
            )
        return adapters_for_capability[provider_name]

    def list_providers(self, capability: Capability) -> list[str]:
        return list(self._adapters.get(capability, {}).keys())

    def default_provider_name(self, capability: Capability) -> str | None:
        return self._default_provider.get(capability)


def build_default_registry() -> ProviderRegistry:
    """Wire up the registry used by the running application.

    Every adapter registered here is a *reference/mock implementation*
    (see each module's docstring) that simulates provider latency and
    output so the whole request -> credits -> job -> webhook pipeline can be
    exercised end-to-end without a GPU. Swapping in the real AudioCraft /
    OpenVoice / RVC / ComfyUI calls means editing only these ~10 lines.
    """
    from app.providers.lyrics.mock_provider import MockLyricsProvider
    from app.providers.music.audiocraft_provider import AudioCraftMusicProvider
    from app.providers.video.comfyui_provider import ComfyUIVideoProvider
    from app.providers.voice.openvoice_provider import OpenVoiceProvider

    registry = ProviderRegistry()
    registry.register(MockLyricsProvider(), is_default=True)
    registry.register(AudioCraftMusicProvider(), is_default=True)
    registry.register(OpenVoiceProvider(), is_default=True)
    registry.register(ComfyUIVideoProvider(), is_default=True)
    return registry

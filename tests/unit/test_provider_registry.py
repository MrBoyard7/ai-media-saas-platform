"""Unit tests for the Provider Adapter Layer.

These tests need no database and no network: the registry and every
reference adapter are pure, dependency-free Python.
"""
from __future__ import annotations

import pytest

from app.providers.base import Capability, GenerationRequest, ProviderError
from app.providers.lyrics.mock_provider import MockLyricsProvider
from app.providers.music.audiocraft_provider import AudioCraftMusicProvider
from app.providers.registry import ProviderRegistry, build_default_registry


def _request(capability: Capability, **parameters) -> GenerationRequest:
    return GenerationRequest(
        organization_id="org-1",
        job_id="job-1",
        capability=capability,
        prompt="a test prompt",
        parameters=parameters,
    )


async def test_registry_routes_to_default_provider():
    registry = ProviderRegistry()
    registry.register(MockLyricsProvider(), is_default=True)

    adapter = registry.get(Capability.LYRICS)

    assert adapter.name == "reference-lyrics-v1"


def test_registry_raises_for_unregistered_capability():
    registry = ProviderRegistry()
    with pytest.raises(ProviderError):
        registry.get(Capability.VIDEO)


async def test_default_registry_wires_all_four_capabilities():
    registry = build_default_registry()
    for capability in Capability:
        assert registry.default_provider_name(capability) is not None
        adapter = registry.get(capability)
        assert await adapter.health_check() is True


async def test_lyrics_provider_generates_deterministic_output_url():
    provider = MockLyricsProvider()
    result = await provider.generate(_request(Capability.LYRICS, line_count=8))
    assert result.output_url.startswith("https://storage.example.com/lyrics/org-1/")
    assert result.provider_name == "reference-lyrics-v1"


async def test_lyrics_provider_rejects_empty_prompt():
    provider = MockLyricsProvider()
    empty_request = GenerationRequest(organization_id="org-1", job_id="job-1", capability=Capability.LYRICS, prompt="   ")
    with pytest.raises(ProviderError):
        await provider.generate(empty_request)


async def test_music_provider_rejects_out_of_range_duration():
    provider = AudioCraftMusicProvider()
    with pytest.raises(ProviderError):
        await provider.generate(_request(Capability.MUSIC, duration_seconds=99999))


def test_cost_estimate_scales_with_requested_duration():
    provider = AudioCraftMusicProvider()
    short = provider.estimate_cost_credits(_request(Capability.MUSIC, duration_seconds=10))
    long = provider.estimate_cost_credits(_request(Capability.MUSIC, duration_seconds=100))
    assert long > short

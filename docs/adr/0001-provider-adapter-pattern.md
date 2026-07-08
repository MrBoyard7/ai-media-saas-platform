# ADR 0001: Provider Adapter Pattern for AI Generation

**Status:** Accepted

## Context

The platform must integrate multiple, heterogeneous AI providers
(AudioCraft, Amphion, OpenVoice, RVC, ComfyUI today; unnamed future
providers, potentially including commercial APIs, tomorrow) across four
capabilities (lyrics, music, voice, video). The brief explicitly requires
the architecture to be "Provider Independent" and "Model Agnostic," and
states that "business logic must never depend on a specific AI provider."

## Decision

Define every provider integration behind a single `AIProviderAdapter`
`Protocol` (`app/providers/base.py`) with four methods: `health_check`,
`generate`, `estimate_cost_credits`, plus `name` and `capability`
attributes. A `ProviderRegistry` (`app/providers/registry.py`) maps
`(capability, provider_name) -> adapter instance`. `GenerationService`
(`app/services/generation_service.py`) depends only on the registry and
the protocol, never on a concrete adapter class.

## Consequences

**Positive**

- New providers are additive: one new adapter file + one registry line.
- Swapping the default provider for a capability (e.g. moving music
  generation from AudioCraft to a commercial API) is a configuration
  change.
- Adapters are independently unit-testable (see
  `tests/unit/test_provider_registry.py`) without a GPU or network access.
- `estimate_cost_credits` living on the adapter means each provider owns
  its own pricing model (per-second, per-character, per-line, ...) without
  `CreditsService` needing to know about any of them.

**Negative / tradeoffs**

- The `GenerationRequest.parameters` dict is intentionally loosely typed,
  which trades compile-time safety for adapter-to-adapter flexibility.
  Each adapter is responsible for validating the subset of parameters it
  understands and raising `ProviderError` on bad input.
- A capability's adapters must agree on a shared `GenerationResult` shape
  (`output_url`, `duration_seconds`, `raw_provider_metadata`), which means
  some provider-specific richness only surfaces via the free-form
  `raw_provider_metadata` field rather than typed fields.

## Alternatives considered

- **Direct SDK calls from services.** Rejected: couples business logic to
  a specific vendor's API shape and error model; makes provider swaps a
  multi-file change.
- **A single mega-adapter with `if provider == "audiocraft"` branches.**
  Rejected: violates open/closed principle, and mixes four providers'
  error handling and retry logic in one class.

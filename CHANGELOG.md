# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-01

### Added

- AI Gateway (FastAPI) exposing Organizations, Credits & Wallet,
  Subscriptions/Entitlements, Generation, and Jobs APIs.
- Provider Adapter Layer with reference adapters for lyrics, music
  (AudioCraft-style), voice (OpenVoice-style) and video (ComfyUI-style)
  generation, plus a provider registry for capability routing.
- Feature-based subscription & entitlement engine driven by data
  (`features` / `plan_features` tables), not hardcoded plan checks.
- Idempotent, append-only Credits & Wallet ledger with row-locking for
  safe concurrent debits.
- Row-level multi-tenant Organization model with white-label support
  (custom domain + branding) and tenant-resolution middleware.
- Async AI Job Queue via Celery + Redis, with per-capability queues and
  automatic credit refunds on provider failure.
- Python SDK (`sdk/python/`) for the Developer Platform.
- Alembic migrations, Docker Compose stack (api, worker, postgres, redis),
  and a demo data seed script.
- Unit and integration test suite (SQLite in-memory, no external services
  required) with coverage reporting.
- CI (lint, type-check, multi-version test matrix, Docker build) and
  CodeQL security scanning via GitHub Actions.

[1.0.0]: https://github.com/MrBoyard7/ai-media-saas-platform/releases/tag/v1.0.0

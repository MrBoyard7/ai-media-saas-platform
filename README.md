# AI Media SaaS Platform

**Enterprise-grade, multi-tenant, white-label AI SaaS platform for Lyrics,
Music, Voice and Video generation, built on a provider-independent AI
Gateway.**

[![CI](https://github.com/MrBoyard7/ai-media-saas-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/MrBoyard7/ai-media-saas-platform/actions/workflows/ci.yml)
[![CodeQL](https://github.com/MrBoyard7/ai-media-saas-platform/actions/workflows/codeql.yml/badge.svg)](https://github.com/MrBoyard7/ai-media-saas-platform/actions/workflows/codeql.yml)
[![codecov](https://codecov.io/gh/MrBoyard7/ai-media-saas-platform/branch/main/graph/badge.svg)](https://codecov.io/gh/MrBoyard7/ai-media-saas-platform)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg?logo=docker&logoColor=white)](docker-compose.yml)

---

## Why this repository exists

This is a **reference implementation** of the architecture behind a
production AI SaaS platform: an AI Gateway that fronts multiple AI
providers through a provider-independent adapter layer, a credits/wallet
billing core, a feature-based subscription engine, multi-tenant
white-labeling, and an async GPU job pipeline -- the pattern used by modern
AI infrastructure platforms.

**Scope note:** the four generation adapters (`app/providers/{lyrics,music,
voice,video}/`) are deterministic reference/simulation implementations --
they model real provider latency, cost and failure behavior against the
exact interface a production AudioCraft / OpenVoice / RVC / ComfyUI
integration would use, without requiring a GPU or model weights to run
this repository. See each adapter's docstring and
[`docs/adr/0001-provider-adapter-pattern.md`](docs/adr/0001-provider-adapter-pattern.md)
for what swapping in a real model call involves (it's small, by design).

## Features

- 🧩 **Provider-independent AI Gateway** -- lyrics, music, voice and video
  generation behind one adapter interface; add a provider without touching
  business logic.
- 🏢 **Multi-tenant & white-label** -- row-level tenant isolation, custom
  domains, per-organization branding.
- 💳 **Credits & Wallet** -- idempotent, append-only ledger; safe
  concurrent debits via row locking; automatic refunds on job failure.
- 🎚️ **Feature-based subscription engine** -- entitlements are data
  (`features` / `plan_features` tables), not hardcoded plan checks.
- ⚙️ **Async AI Job Queue** -- Celery + Redis, per-capability GPU queues,
  designed for a RunPod serverless GPU worker pool.
- 🔑 **Developer Platform** -- REST API + a minimal Python SDK
  (`sdk/python/`).
- 🔐 **Auth** -- Supabase-issued JWTs, RBAC roles, scoped API keys.
- ✅ **Tested** -- unit + integration tests run against in-memory SQLite,
  zero external services required.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for component and
sequence diagrams, and [`docs/database-schema.md`](docs/database-schema.md)
for the data model. Key decisions are recorded as ADRs in
[`docs/adr/`](docs/adr/).

```
Client (Next.js / SDK / Admin Portal)
        │
        ▼
  AI Gateway (FastAPI)  ──▶  Entitlement Engine ──▶ Credits & Wallet (Postgres ledger)
        │
        ▼
  Provider Registry ──▶ Lyrics / Music / Voice / Video Adapters
        │
        ▼
  Celery + Redis ──▶ GPU Worker Pool (RunPod) ──▶ Object Storage
```

## Project structure

```
ai-media-saas-platform/
├── app/
│   ├── main.py                  # FastAPI application entrypoint
│   ├── core/                    # config, database, redis, celery, security, logging
│   ├── models/                  # SQLAlchemy ORM models (+ portable UUID/JSON types)
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── repositories/            # data access layer (one query surface per aggregate)
│   ├── services/                # business logic: credits, entitlements, orgs, generation
│   ├── providers/                # AI Gateway adapter layer
│   │   ├── base.py              # AIProviderAdapter protocol
│   │   ├── registry.py          # capability -> adapter routing
│   │   ├── lyrics/ music/ voice/ video/
│   ├── workers/                 # Celery tasks (GPU job execution)
│   ├── middleware/               # tenant resolution (white-label custom domains)
│   └── api/v1/endpoints/         # FastAPI routers
├── sdk/python/                   # Developer Platform Python SDK
├── migrations/                   # Alembic migrations
├── scripts/seed_demo_data.py     # seed plans/features for local dev
├── tests/{unit,integration}/     # pytest suite (SQLite in-memory)
├── docs/{architecture,database-schema}.md, docs/adr/
├── docker-compose.yml, Dockerfile, Makefile
└── .github/workflows/{ci,codeql}.yml
```

## Quickstart

### Option A -- Docker Compose (recommended)

```bash
git clone https://github.com/MrBoyard7/ai-media-saas-platform.git
cd ai-media-saas-platform
cp .env.example .env

make up          # starts postgres, redis, api (reload), worker
make migrate      # in a second terminal: alembic upgrade head
make seed         # seed demo plans & features
```

The API is now at `http://localhost:8000`, interactive docs at
`http://localhost:8000/docs`.

### Option B -- local Python environment

```bash
git clone https://github.com/MrBoyard7/ai-media-saas-platform.git
cd ai-media-saas-platform
python -m venv .venv && source .venv/bin/activate
make install
cp .env.example .env               # point DATABASE_URL / REDIS_URL at local services

uvicorn app.main:app --reload      # API
celery -A app.core.celery_app.celery_app worker --loglevel=info   # worker, separate terminal
```

## Testing

The full test suite runs against an in-memory SQLite database -- no Docker,
Postgres, Redis or network access required:

```bash
make install        # installs pytest, pytest-asyncio, aiosqlite, etc.
make test           # pytest --cov=app --cov-report=term-missing
```

Run a single file or test:

```bash
pytest tests/unit/test_credits_service.py -v
pytest tests/integration/test_generation_endpoint.py::test_generation_request_is_idempotent -v
```

Lint, format and type-check:

```bash
make lint           # ruff check .
make format         # black . && isort .
make typecheck      # mypy app
```

## Example: calling the API

```bash
curl -X POST http://localhost:8000/api/v1/organizations \
  -H "Authorization: Bearer <supabase_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Nova Records"}'

curl -X POST http://localhost:8000/api/v1/generate \
  -H "Authorization: Bearer <supabase_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
        "capability": "music",
        "prompt": "uplifting lofi hip-hop beat, 90 bpm",
        "parameters": {"duration_seconds": 30},
        "idempotency_key": "8f14e45f-ceea-4b19"
      }'
```

Or with the Python SDK:

```python
from ai_media_saas_sdk import PlatformClient

with PlatformClient(api_key="sk_live_...", base_url="http://localhost:8000/api/v1") as client:
    job = client.generate_music("uplifting lofi hip-hop beat, 90 bpm", duration_seconds=30)
    print(job["id"], job["status"])
```

## Technology stack

| Layer          | Choice                                             |
| -------------- | --------------------------------------------------- |
| API             | Python, FastAPI                                     |
| Database        | PostgreSQL, SQLAlchemy 2.0 (async), Alembic          |
| Queue / cache   | Redis, Celery                                        |
| Auth            | Self-hosted Supabase (JWT), RBAC                      |
| AI providers    | AudioCraft, Amphion, OpenVoice, RVC, ComfyUI (adapters) |
| GPU infra       | RunPod serverless GPU workers                          |
| Infra           | Docker, Docker Compose                                |
| Testing         | pytest, pytest-asyncio, aiosqlite, httpx               |
| CI/CD           | GitHub Actions, CodeQL, Codecov                         |

## Roadmap

- [ ] Postgres Row-Level Security policies as defense-in-depth for
      multi-tenancy (see ADR 0002)
- [ ] TypeScript SDK generated from the OpenAPI schema
- [ ] Usage-based rate limiting per `plan_features.monthly_limit`
- [ ] Real GPU worker deployment scripts for RunPod serverless

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please also read our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Security

See [SECURITY.md](SECURITY.md) for how to report a vulnerability.

## License

MIT © 2026 [Prince Boyard MBOUNGOU NGOMA](https://github.com/MrBoyard7). See
[LICENSE](LICENSE).

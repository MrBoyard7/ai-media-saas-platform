# Architecture Overview

## Goals

The platform is designed around seven non-negotiable properties (see the
project brief): **provider independent, model agnostic, multi-tenant,
white-label ready, enterprise ready, scalable, secure.** Every architectural
decision below exists to serve one or more of these.

## High-level component diagram

```mermaid
flowchart LR
    subgraph Clients
        WEB[Next.js User Dashboard]
        ADMIN[Admin / Super Admin Portal]
        SDK[Customer apps via SDK]
    end

    subgraph ControlPlane["Control Plane (FastAPI)"]
        GATEWAY[AI Gateway / REST API]
        ORG[Organization Service]
        CREDITS[Credits & Wallet Service]
        ENTITLE[Entitlement Engine]
        GEN[Generation Orchestrator]
    end

    subgraph AIPlane["AI Plane"]
        REGISTRY[Provider Registry]
        LYRICS[Lyrics Adapter]
        MUSIC[Music Adapter - AudioCraft]
        VOICE[Voice Adapter - OpenVoice / RVC]
        VIDEO[Video Adapter - ComfyUI]
    end

    subgraph AsyncInfra["Async Infrastructure"]
        REDIS[(Redis)]
        CELERY[Celery Workers]
        GPU[GPU Worker Pool - RunPod]
    end

    subgraph Data
        PG[(PostgreSQL)]
        STORAGE[(Object Storage)]
    end

    WEB --> GATEWAY
    ADMIN --> GATEWAY
    SDK --> GATEWAY

    GATEWAY --> ORG
    GATEWAY --> CREDITS
    GATEWAY --> ENTITLE
    GATEWAY --> GEN

    GEN --> REGISTRY
    REGISTRY --> LYRICS
    REGISTRY --> MUSIC
    REGISTRY --> VOICE
    REGISTRY --> VIDEO

    GEN --> REDIS
    REDIS --> CELERY
    CELERY --> GPU
    MUSIC -. real deployment .-> GPU
    VOICE -. real deployment .-> GPU
    VIDEO -. real deployment .-> GPU

    ORG --> PG
    CREDITS --> PG
    ENTITLE --> PG
    GEN --> PG
    GPU --> STORAGE
```

## Request lifecycle: a single generation job

```mermaid
sequenceDiagram
    participant Client
    participant API as AI Gateway (FastAPI)
    participant Ent as Entitlement Engine
    participant Wallet as Credits Service
    participant DB as PostgreSQL
    participant Queue as Celery / Redis
    participant Worker as GPU Worker
    participant Provider as Provider Adapter

    Client->>API: POST /generate {capability, prompt, idempotency_key}
    API->>Ent: check(org_id, feature_key)
    Ent-->>API: entitled
    API->>Wallet: debit(org_id, estimated_cost, idempotency_key)
    Wallet->>DB: SELECT ... FOR UPDATE / INSERT ledger row
    DB-->>Wallet: ok
    API->>DB: INSERT generation_jobs (status=queued)
    API->>Queue: send_task(job_id)
    API-->>Client: 202 Accepted {job_id, status: queued}

    Queue->>Worker: deliver task
    Worker->>Provider: generate(request)
    Provider-->>Worker: GenerationResult | ProviderError
    alt success
        Worker->>DB: UPDATE job status=succeeded, output_payload
    else failure
        Worker->>Wallet: refund(org_id, reserved_amount)
        Worker->>DB: UPDATE job status=failed, error_message
    end

    Client->>API: GET /jobs/{job_id}
    API-->>Client: job status + output_url (when ready)
```

## Why an Adapter Pattern for AI providers

Business logic (`app.services`, `app.api`) never imports `audiocraft`,
`openvoice`, `rvc` or `comfyui` packages directly. It only knows the
`AIProviderAdapter` protocol defined in `app/providers/base.py`. Concrete
adapters live in `app/providers/{lyrics,music,voice,video}/` and are wired
up in `app/providers/registry.py`.

Consequences:

- Adding a new provider (a commercial API, a newer open-source model) is a
  new adapter class plus one line in the registry -- no change to services,
  routers, or the job schema.
- A/B testing two providers for the same capability, or offering
  enterprise customers a choice of provider, is a `provider_name` field on
  the request, not a code branch.
- The reference adapters shipped in this repository (see each module's
  docstring) simulate GPU latency and output shape so the full
  credits → entitlement → job → webhook pipeline is exercisable and
  testable without a GPU; swapping in real inference is intentionally
  isolated to those files.

## Multi-tenancy

Row-level multi-tenancy: every tenant-owned table carries an
`organization_id` foreign key, and the repository layer is the only place
allowed to query these tables -- every query filters by tenant. See
[`docs/adr/0002-multi-tenancy-strategy.md`](./adr/0002-multi-tenancy-strategy.md)
for the tradeoffs against schema-per-tenant and database-per-tenant, and
when the platform would need to graduate to one of those for very large
enterprise customers.

## White-label

An `Organization` can set `is_white_label=True`, a `custom_domain`, and a
`branding` JSON blob (logo, colors, product name). `TenantResolutionMiddleware`
resolves incoming requests by `Host` header to the right organization so a
white-labeled customer's own domain transparently serves the same API and
(via the Next.js frontend, out of scope for this repository) the same
dashboard with their branding.

## Credits & billing

See [`docs/adr/0001-provider-adapter-pattern.md`](./adr/0001-provider-adapter-pattern.md)
for the adapter pattern rationale and
[`app/services/credits_service.py`](../app/services/credits_service.py)
for the ledger implementation: every balance change is an idempotent,
append-only `CreditTransaction` row, and `Wallet.balance` is a cached
projection that is only ever mutated in the same DB transaction as its
ledger entry.

## Background AI Job Processing

Celery + Redis, with one queue per GPU-bound capability
(`gpu.music`, `gpu.voice`, `gpu.video`) plus a lightweight `lyrics` queue
that can run on CPU-only workers. `worker_prefetch_multiplier=1` and
`task_acks_late=True` are set so a crashed GPU worker's in-flight job is
requeued rather than lost. See `app/core/celery_app.py`.

## Developer Platform / SDK

`sdk/python/` ships a minimal, dependency-light client (`PlatformClient`)
that wraps the REST API. The same request/response contracts back
generated SDKs in other languages in a production rollout (TypeScript,
Go), since the API is the single source of truth.

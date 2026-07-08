# Contributing

Thanks for your interest in improving the AI Media SaaS Platform reference
architecture.

## Getting set up

```bash
git clone https://github.com/MrBoyard7/ai-media-saas-platform.git
cd ai-media-saas-platform
python -m venv .venv && source .venv/bin/activate
make install
cp .env.example .env
make up        # starts postgres, redis, api, worker
make migrate
make seed
```

## Development workflow

1. Create a branch: `git checkout -b feat/short-description`.
2. Make your change, with tests. `app/` code changes should almost always
   come with a corresponding test in `tests/unit/` or `tests/integration/`.
3. Run the full local check before opening a PR:
   ```bash
   make format
   make lint
   make typecheck
   make test
   ```
4. Open a PR against `main` using the PR template. CI must be green
   (lint, type-check, tests on Python 3.9/3.11/3.12, Docker build) before
   review.

## Code style

- Formatting: [black](https://github.com/psf/black) (line length 110) +
  [isort](https://pycqa.github.io/isort/). Run `make format`.
- Linting: [ruff](https://docs.astral.sh/ruff/). Run `make lint`.
- Type hints are required on public function signatures in `app/services`
  and `app/providers`; `mypy app` runs in CI.
- Business logic belongs in `app/services/`, never in `app/api/` route
  handlers -- routers should stay thin (parse request -> call service ->
  serialize response).
- New AI providers implement `AIProviderAdapter`
  (`app/providers/base.py`) and are registered in
  `app/providers/registry.py`; see
  [`docs/adr/0001-provider-adapter-pattern.md`](docs/adr/0001-provider-adapter-pattern.md).

## Commit messages

Conventional commits are appreciated but not enforced:
`feat: add RVC voice provider adapter`, `fix: correct wallet idempotency race`,
`docs: expand multi-tenancy ADR`.

## Reporting bugs / requesting features

Please use the issue templates under `.github/ISSUE_TEMPLATE/`.

## Code of Conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).

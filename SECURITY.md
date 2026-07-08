# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, report it privately via GitHub's
["Report a vulnerability"](https://github.com/MrBoyard7/ai-media-saas-platform/security/advisories/new)
feature on this repository. Include:

- A description of the vulnerability and its potential impact
- Steps to reproduce (or a proof of concept)
- Any known mitigations

You should expect an initial response within 5 business days. Please allow
a reasonable disclosure window before publishing details publicly so a fix
can be released first.

## Security Practices in This Repository

- Dependencies are scanned via GitHub CodeQL (`.github/workflows/codeql.yml`)
  on every push to `main` and weekly on a schedule.
- Authentication tokens are verified server-side (`app/core/security.py`)
  and never trusted from client-supplied claims without signature
  verification.
- Secrets (`SECRET_KEY`, `SUPABASE_JWT_SECRET`, `RUNPOD_API_KEY`, ...) are
  read from environment variables only; `.env` is git-ignored and
  `.env.example` contains no real credentials.
- Tenant data isolation is enforced at the repository layer -- see
  [`docs/adr/0002-multi-tenancy-strategy.md`](docs/adr/0002-multi-tenancy-strategy.md).

# ADR 0002: Row-Level Multi-Tenancy

**Status:** Accepted

## Context

The platform must support multi-tenant organizations, white-labeling, and
eventually large enterprise customers with stricter isolation
expectations. Three common strategies exist:

1. **Row-level (shared schema):** one set of tables, every tenant-owned
   row carries an `organization_id`.
2. **Schema-per-tenant:** one Postgres schema per organization, same
   table structure repeated.
3. **Database-per-tenant:** a fully separate database (or cluster) per
   organization.

## Decision

Start with **row-level multi-tenancy** for all plans. Every tenant-scoped
table (`wallets`, `subscriptions`, `generation_jobs`, ...) has a
non-nullable `organization_id` foreign key, indexed, and the repository
layer (`app/repositories/`) is the only code allowed to issue queries
against these tables -- every query it issues filters by
`organization_id`.

## Consequences

**Positive**

- Single connection pool, single migration path, single set of Alembic
  revisions -- operationally simple at low-to-medium scale.
- Cross-tenant analytics (e.g. admin dashboards, platform-wide usage
  reporting) are simple joins, not fan-out queries across N databases.
- New tenants are a row insert, not a provisioning workflow.

**Negative / tradeoffs**

- A missed `WHERE organization_id = ...` filter is a data leak, not a
  compile error. Mitigations: (a) the repository pattern centralizes every
  query so this is a small, reviewable surface area, and (b) enterprise
  deployments should additionally enable PostgreSQL Row-Level Security
  policies on tenant tables as defense in depth (not yet implemented in
  this reference repo -- tracked as a follow-up for the Enterprise tier).
- Noisy-neighbor risk: one tenant's heavy query load can affect others
  sharing the same database. Acceptable at the target scale; revisit if a
  single tenant's write volume dominates.

## Migration path for large enterprise customers

Nothing above precludes moving a specific large customer to
schema-per-tenant or database-per-tenant later: because every query
already goes through the repository layer and is already scoped by
`organization_id`, the migration is a routing change in
`app/core/database.py` (picking a connection/schema based on tenant),
not a rewrite of business logic.

## Alternatives considered

- **Schema-per-tenant from day one.** Rejected for v1: Alembic migrations
  must fan out across every tenant schema, which is significant
  operational overhead for a platform targeting fast-moving SMB and
  mid-market customers first, with a small number of enterprise accounts
  later.

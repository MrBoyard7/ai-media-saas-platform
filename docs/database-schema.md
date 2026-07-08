# Database Schema

PostgreSQL in production; the same SQLAlchemy models compile against
SQLite for the test suite (see `app/models/types.py`).

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ ORGANIZATION_MEMBERS : has
    ORGANIZATIONS ||--|| WALLETS : owns
    ORGANIZATIONS ||--|| SUBSCRIPTIONS : has
    ORGANIZATIONS ||--o{ GENERATION_JOBS : requests
    WALLETS ||--o{ CREDIT_TRANSACTIONS : ledger
    FEATURES ||--o{ PLAN_FEATURES : "included in"

    ORGANIZATIONS {
        uuid id PK
        string name
        string slug
        enum plan
        bool is_white_label
        string custom_domain
        jsonb branding
    }
    ORGANIZATION_MEMBERS {
        uuid id PK
        uuid organization_id FK
        string user_id
        enum role
    }
    WALLETS {
        uuid id PK
        uuid organization_id FK
        bigint balance
    }
    CREDIT_TRANSACTIONS {
        uuid id PK
        uuid wallet_id FK
        bigint amount
        bigint balance_after
        enum type
        string idempotency_key
        jsonb metadata
    }
    SUBSCRIPTIONS {
        uuid id PK
        uuid organization_id FK
        enum plan
        enum status
        string external_billing_id
    }
    FEATURES {
        uuid id PK
        string key
        string name
    }
    PLAN_FEATURES {
        uuid id PK
        enum plan
        uuid feature_id FK
        bool enabled
        bigint monthly_limit
    }
    GENERATION_JOBS {
        uuid id PK
        uuid organization_id FK
        string requested_by_user_id
        enum kind
        string provider_name
        enum status
        jsonb input_payload
        jsonb output_payload
        int credits_reserved
    }
```

## Notes

- **`credit_transactions` is append-only.** No code path ever `UPDATE`s or
  `DELETE`s a row here; corrections are new rows (`REFUND`,
  `ADMIN_ADJUSTMENT`). This is what makes the ledger auditable.
- **`(wallet_id, idempotency_key)` is a unique constraint**, not just an
  application-level check -- it is the mechanism that makes
  `CreditsService.debit`/`credit` safe to retry.
- **`plan_features` is data, not code.** Changing what the `pro` plan
  includes is a row insert, not a deploy. See
  [`scripts/seed_demo_data.py`](../scripts/seed_demo_data.py) for the
  starter data set.
- Migrations are managed with Alembic (`migrations/`); see
  [`migrations/versions/0001_initial_schema.py`](../migrations/versions/0001_initial_schema.py)
  for the full column-level definition of every table above.

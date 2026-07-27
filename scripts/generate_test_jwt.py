"""
Mint a short-lived, locally-signed JWT for manual smoke-testing the API.

This is NOT for production use -- it exists so the platform can be
exercised end-to-end (curl / Swagger UI / Postman) without standing up a
real Supabase instance first. It signs a token with the same
`SUPABASE_JWT_SECRET` the running API validates against (read from your
`.env`), so the token is accepted exactly like a real Supabase-issued one.

Usage:
    python -m scripts.generate_test_jwt
    python -m scripts.generate_test_jwt --organization-id <uuid> --role owner
"""

from __future__ import annotations

import argparse
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", default=str(uuid.uuid4()), help="Subject / Supabase user id.")
    parser.add_argument(
        "--organization-id",
        default=None,
        help="Tenant id. Omit to use a fresh random org id (you'll need to POST /organizations "
        "first, or pass the id of one you already created).",
    )
    parser.add_argument("--role", default="owner", choices=["owner", "admin", "member", "billing"])
    parser.add_argument("--scopes", nargs="*", default=["*"])
    parser.add_argument("--expires-minutes", type=int, default=120)
    args = parser.parse_args()

    settings = get_settings()
    organization_id = args.organization_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": args.user_id,
            "organization_id": organization_id,
            "role": args.role,
            "scopes": args.scopes,
            "iat": now,
            "exp": now + timedelta(minutes=args.expires_minutes),
        },
        settings.SUPABASE_JWT_SECRET,
        algorithm="HS256",
    )

    print(f"user_id:         {args.user_id}")
    print(f"organization_id: {organization_id}")
    print(f"role:            {args.role}")
    print(f"expires in:      {args.expires_minutes} minutes")
    print()
    print(token)


if __name__ == "__main__":
    main()

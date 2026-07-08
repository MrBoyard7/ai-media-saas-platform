"""
Tenant resolution middleware.

For white-labeled organizations, the platform is reachable on the
customer's own domain (e.g. `studio.acme.com`) rather than a shared
`app.ourplatform.com/<org-slug>` path. This middleware inspects the `Host`
header, resolves it to an `Organization`, and stashes it on
`request.state.resolved_organization_slug` so downstream code can enforce
tenant isolation without knowing whether the request arrived via the
shared domain or a white-label one.

Starlette middleware runs outside FastAPI's `Depends` graph, so it cannot
receive `get_db` like a route handler can. It instead opens its own
short-lived session via `request.app.state.db_sessionmaker` -- a plain
`async_sessionmaker` set on the app in `app.main.create_app()` (production)
or overridden in `tests/conftest.py` to point at the in-memory test
database, so this middleware never has to reach for a hardcoded engine.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.repositories.organization_repository import OrganizationRepository

# Requests to these paths never need tenant resolution. `/docs`, `/redoc`
# and `/openapi.json` are mounted at the app root by FastAPI regardless of
# API_V1_PREFIX; the health check lives under the versioned API prefix.
_EXEMPT_SUFFIXES = ("/health", "/docs", "/openapi.json", "/redoc")

# Hosts that never carry a white-labeled custom domain: the platform's own
# internal service-to-service hostname, and the hostnames used by local
# development and the test suite (httpx's ASGITransport defaults to
# "testserver").
_NON_TENANT_HOSTS = {"testserver", "localhost", "127.0.0.1"}


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path.endswith(_EXEMPT_SUFFIXES):
            return await call_next(request)

        host = request.headers.get("host", "").split(":")[0]
        request.state.resolved_organization_slug = None

        # Shared-domain requests (e.g. api.platform.com) carry the tenant in
        # the JWT instead, so custom-domain lookup is purely additive here.
        if host and host not in _NON_TENANT_HOSTS:
            session_factory = request.app.state.db_sessionmaker
            async with session_factory() as session:
                organizations = OrganizationRepository(session)
                organization = await organizations.get_by_custom_domain(host)
                if organization is not None:
                    request.state.resolved_organization_slug = organization.slug
                    request.state.white_label_branding = organization.branding

        return await call_next(request)

"""
Tenant resolution middleware.

For white-labeled organizations, the platform is reachable on the
customer's own domain (e.g. `studio.acme.com`) rather than a shared
`app.ourplatform.com/<org-slug>` path. This middleware inspects the `Host`
header, resolves it to an `Organization`, and stashes it on
`request.state.organization_id` so every downstream dependency (including
`get_current_auth_context`) can enforce tenant isolation without knowing
whether the request arrived via the shared domain or a white-label one.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import session_scope
from app.repositories.organization_repository import OrganizationRepository

# Requests to these paths never need tenant resolution.
_EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        host = request.headers.get("host", "").split(":")[0]
        request.state.resolved_organization_slug = None

        # Shared domain requests (e.g. api.platform.com) carry the tenant in
        # the JWT instead, so custom-domain lookup is purely additive here.
        if host and not host.endswith("platform.internal"):
            async with session_scope() as session:
                organizations = OrganizationRepository(session)
                organization = await organizations.get_by_custom_domain(host)
                if organization is not None:
                    request.state.resolved_organization_slug = organization.slug
                    request.state.white_label_branding = organization.branding

        return await call_next(request)

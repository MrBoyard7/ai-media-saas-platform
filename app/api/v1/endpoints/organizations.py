"""Organizations API: tenant creation and white-label configuration."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.deps import get_organization_service
from app.core.security import AuthContext, get_current_auth_context
from app.schemas.organization import OrganizationCreate, OrganizationRead, WhiteLabelConfig
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationRead, status_code=201)
async def create_organization(
    payload: OrganizationCreate,
    ctx: AuthContext = Depends(get_current_auth_context),
    organizations: OrganizationService = Depends(get_organization_service),
) -> OrganizationRead:
    organization = await organizations.create_organization(name=payload.name, owner_user_id=ctx.user_id)
    return OrganizationRead.model_validate(organization)


@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_organization(
    organization_id: uuid.UUID,
    organizations: OrganizationService = Depends(get_organization_service),
) -> OrganizationRead:
    organization = await organizations.get_or_404(organization_id)
    return OrganizationRead.model_validate(organization)


@router.put("/{organization_id}/white-label", response_model=OrganizationRead)
async def configure_white_label(
    organization_id: uuid.UUID,
    payload: WhiteLabelConfig,
    organizations: OrganizationService = Depends(get_organization_service),
) -> OrganizationRead:
    organization = await organizations.enable_white_label(
        organization_id, custom_domain=payload.custom_domain, branding=payload.branding
    )
    return OrganizationRead.model_validate(organization)

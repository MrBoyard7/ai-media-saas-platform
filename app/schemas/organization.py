"""Pydantic request/response schemas for the Organizations API."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.organization import OrganizationPlan


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class WhiteLabelConfig(BaseModel):
    custom_domain: str
    branding: dict = Field(default_factory=dict)


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan: OrganizationPlan
    is_white_label: bool
    custom_domain: str | None
    created_at: datetime

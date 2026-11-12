# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas._base import StrictInputSchema

from ..models.bibframe import AuthoritySource
from ..models.local_authority import LocalAuthorityStatus, LocalAuthorityType


class ExternalCrosswalk(BaseModel):
    source: AuthoritySource
    authority_id: str = Field(..., max_length=100)
    uri: Optional[str] = Field(None, max_length=500)
    label: Optional[str] = Field(None, max_length=500)


class RelatedAuthority(BaseModel):
    label: str = Field(..., max_length=500)
    relationship: Optional[str] = Field(None, max_length=50, description="e.g. broader, narrower, related")
    local_authority_id: Optional[int] = None


class LocalAuthorityBase(BaseModel):
    authority_type: LocalAuthorityType
    label: str = Field(..., min_length=1, max_length=500)
    status: LocalAuthorityStatus = LocalAuthorityStatus.provisional
    scope_note: Optional[str] = None
    source_notes: Optional[str] = None
    variants: Optional[list[str]] = None
    related_authorities: Optional[list[RelatedAuthority]] = None
    external_links: Optional[list[ExternalCrosswalk]] = None
    use_instead_id: Optional[int] = None
    library_system_id: Optional[int] = None


class LocalAuthorityCreate(StrictInputSchema, LocalAuthorityBase):
    pass


class LocalAuthorityUpdate(StrictInputSchema):
    authority_type: Optional[LocalAuthorityType] = None
    label: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[LocalAuthorityStatus] = None
    scope_note: Optional[str] = None
    source_notes: Optional[str] = None
    variants: Optional[list[str]] = None
    related_authorities: Optional[list[RelatedAuthority]] = None
    external_links: Optional[list[ExternalCrosswalk]] = None
    use_instead_id: Optional[int] = None


class LocalAuthorityResponse(LocalAuthorityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label_normalized: str
    created_by_id: Optional[int] = None
    updated_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class LocalAuthorityListResponse(BaseModel):
    total: int
    items: list[LocalAuthorityResponse]


class LocalAuthorityLinkRequest(StrictInputSchema):
    work_id: Optional[int] = None
    instance_id: Optional[int] = None
    item_id: Optional[int] = None
    contributor_id: Optional[int] = None
    subject_id: Optional[int] = None
    link_type: str = "sameAs"

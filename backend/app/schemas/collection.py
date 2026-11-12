# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas._base import StrictInputSchema

from ..models.collection import ArchivalLevel


class CollectionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    position: int = 0
    level: Optional[ArchivalLevel] = None

    # DACS Identity & Context
    reference_code: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=500)
    date_creation: Optional[str] = Field(None, max_length=255)
    date_accumulation: Optional[str] = Field(None, max_length=255)
    extent: Optional[str] = Field(None, max_length=255)
    creator: Optional[str] = Field(None, max_length=500)

    biographical_history: Optional[str] = None
    archival_history: Optional[str] = None
    acquisition_source: Optional[str] = None

    scope_content: Optional[str] = None
    appraisal: Optional[str] = None
    accruals: Optional[str] = None
    arrangement: Optional[str] = None

    access_conditions: Optional[str] = None
    reproduction_conditions: Optional[str] = None
    languages: Optional[str] = Field(None, max_length=255)
    physical_access: Optional[str] = None
    technical_access: Optional[str] = None
    finding_aids: Optional[str] = None

    originals_location: Optional[str] = None
    copies_location: Optional[str] = None
    related_materials: Optional[str] = None
    publication_note: Optional[str] = None

    notes: Optional[str] = None

    description_rules: Optional[str] = Field(None, max_length=255)
    description_status: Optional[str] = Field(None, max_length=50)
    described_by: Optional[str] = Field(None, max_length=255)


class CollectionCreate(StrictInputSchema, CollectionBase):
    pass


class CollectionUpdate(StrictInputSchema):

    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    position: Optional[int] = None
    level: Optional[ArchivalLevel] = None

    reference_code: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=500)
    date_creation: Optional[str] = Field(None, max_length=255)
    date_accumulation: Optional[str] = Field(None, max_length=255)
    extent: Optional[str] = Field(None, max_length=255)
    creator: Optional[str] = Field(None, max_length=500)

    biographical_history: Optional[str] = None
    archival_history: Optional[str] = None
    acquisition_source: Optional[str] = None

    scope_content: Optional[str] = None
    appraisal: Optional[str] = None
    accruals: Optional[str] = None
    arrangement: Optional[str] = None

    access_conditions: Optional[str] = None
    reproduction_conditions: Optional[str] = None
    languages: Optional[str] = Field(None, max_length=255)
    physical_access: Optional[str] = None
    technical_access: Optional[str] = None
    finding_aids: Optional[str] = None

    originals_location: Optional[str] = None
    copies_location: Optional[str] = None
    related_materials: Optional[str] = None
    publication_note: Optional[str] = None

    notes: Optional[str] = None

    description_rules: Optional[str] = Field(None, max_length=255)
    description_status: Optional[str] = Field(None, max_length=50)
    described_by: Optional[str] = Field(None, max_length=255)


class CollectionResponse(CollectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    described_at: Optional[datetime] = None


class CollectionTreeNode(CollectionResponse):
    children: list["CollectionTreeNode"] = Field(default_factory=list)
    item_count: int = 0


CollectionTreeNode.model_rebuild()


class CollectionItemAdd(BaseModel):
    catalog_item_id: int
    position: int = 0
    component_label: Optional[str] = Field(None, max_length=255)
    note: Optional[str] = None


class CollectionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    catalog_item_id: int
    position: int
    component_label: Optional[str] = None
    note: Optional[str] = None
    added_at: Optional[datetime] = None
    catalog_item_title: Optional[str] = None
    catalog_item_author: Optional[str] = None


class CollectionMoveRequest(StrictInputSchema):
    new_parent_id: Optional[int] = None
    position: int = 0

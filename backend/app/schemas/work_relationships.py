# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema

from ..models.work_relationships import RelationshipType, RelationshipDirection


class WorkRelationshipCreate(StrictInputSchema):
    source_work_id: int = Field(..., description="Source work ID")
    target_work_id: int = Field(..., description="Target work ID")
    relationship_type: RelationshipType = Field(..., description="Type of relationship")
    direction: Optional[RelationshipDirection] = Field(
        RelationshipDirection.forward, description="Direction of relationship"
    )
    title: Optional[str] = Field(None, description="Display title for relationship")
    description: Optional[str] = Field(None, description="Description of relationship")
    is_official: Optional[bool] = Field(True, description="Is official adaptation")
    adaptation_fidelity: Optional[str] = Field(None, description="How faithful is adaptation")
    adaptation_year: Optional[int] = Field(None, description="Year of adaptation")
    announcement_date: Optional[datetime] = Field(None, description="When adaptation announced")
    release_date: Optional[datetime] = Field(None, description="When adapted work released")
    is_complete: Optional[bool] = Field(False, description="Is adaptation complete")
    show_in_discovery: Optional[bool] = Field(True, description="Show in discovery suggestions")
    recommendation_reason: Optional[str] = Field(None, description="Why we recommend this")
    source_authority: Optional[str] = Field(None, description="Authority source")
    authority_id: Optional[str] = Field(None, description="ID in authority source")
    authority_uri: Optional[str] = Field(None, description="URI in authority source")


class WorkRelationshipUpdate(StrictInputSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    is_official: Optional[bool] = None
    adaptation_fidelity: Optional[str] = None
    adaptation_year: Optional[int] = None
    announcement_date: Optional[datetime] = None
    release_date: Optional[datetime] = None
    is_complete: Optional[bool] = None
    show_in_discovery: Optional[bool] = None
    recommendation_reason: Optional[str] = None
    verified: Optional[bool] = None


class WorkRelationshipResponse(BaseModel):
    id: int
    source_work_id: int
    target_work_id: int
    relationship_type: RelationshipType
    direction: RelationshipDirection
    title: Optional[str]
    description: Optional[str]
    is_official: bool
    is_complete: bool
    adaptation_fidelity: Optional[str]
    adaptation_year: Optional[int]
    announcement_date: Optional[datetime]
    release_date: Optional[datetime]
    show_in_discovery: bool
    recommendation_reason: Optional[str]
    verified: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class FormatSuggestionCreate(StrictInputSchema):
    source_work_id: int = Field(..., description="Source work ID")
    target_work_id: int = Field(..., description="Target work ID")
    suggestion_text: str = Field(
        ..., description="Text of suggestion (e.g., 'If you liked the anime, read the manga')"
    )
    suggestion_icon: Optional[str] = Field(None, description="Icon for suggestion")
    confidence_score: Optional[int] = Field(50, description="Confidence score 0-100")
    is_global: Optional[bool] = Field(True, description="Is global suggestion")


class FormatSuggestionResponse(BaseModel):
    id: int
    source_work_id: int
    target_work_id: int
    suggestion_text: str
    suggestion_icon: Optional[str]
    confidence_score: int
    is_global: bool
    is_active: bool
    suggested_count: int
    clicked_count: int
    conversion_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


class RelatedWorkItem(BaseModel):
    work_id: int
    title: str
    work_type: str
    relationship_type: RelationshipType
    relationship_id: int


class RelatedWorksResponse(BaseModel):
    work_id: int
    related_as_source: List[RelatedWorkItem] = Field(
        description="Works that this work adapts/relates to"
    )
    related_as_target: List[RelatedWorkItem] = Field(
        description="Works that adapt/relate to this work"
    )


class CrossFormatDiscoveryResponse(BaseModel):
    id: int
    primary_work_id: int
    series_name: str
    series_slug: Optional[str]
    format_counts: dict = Field(description="Count of each format type")
    available_formats: List[str] = Field(description="List of available format types")
    related_work_ids: List[int] = Field(description="IDs of all related works")
    relationship_types: dict = Field(description="Relationship types and their work IDs")
    is_trending: bool = Field(description="Is this trending")
    last_updated: datetime

    class Config:
        from_attributes = True

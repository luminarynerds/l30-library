# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date, datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas._base import StrictInputSchema


class DirectionBetter(StrEnum):
    up = "up"
    down = "down"


class Cadence(StrEnum):
    monthly = "monthly"
    quarterly = "quarterly"
    semi_annual = "semi_annual"
    annual = "annual"


class GeographicScopeType(StrEnum):
    census_tract = "census_tract"
    school_district = "school_district"
    zip = "zip"
    county = "county"
    service_area = "service_area"
    custom = "custom"


class EvidenceStrength(StrEnum):
    theoretical = "theoretical"
    program_aligned = "program_aligned"
    outcome_correlated = "outcome_correlated"
    quasi_experimental = "quasi_experimental"
    experimental = "experimental"


# ---------------------------------------------------------------------
# OutcomeIndicator
# ---------------------------------------------------------------------


class OutcomeIndicatorCreate(StrictInputSchema):

    slug: str = Field(min_length=3, max_length=120, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    unit: str = Field(min_length=1, max_length=40)
    direction_better: DirectionBetter
    cadence: Cadence
    geographic_scope_type: GeographicScopeType
    primary_source: Optional[str] = Field(default=None, max_length=255)
    source_url: Optional[str] = Field(default=None, max_length=500)
    requires_board_approval: bool = False


class OutcomeIndicatorApprove(BaseModel):

    board_decision_link_id: Optional[int] = None


class OutcomeIndicatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str
    unit: str
    direction_better: str
    cadence: str
    geographic_scope_type: str
    primary_source: Optional[str]
    source_url: Optional[str]
    is_active: bool
    requires_board_approval: bool
    approved_at: Optional[datetime]
    approved_by_user_id: Optional[int]
    board_decision_link_id: Optional[int]
    created_by_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------
# TheoryOfChangeClaim
# ---------------------------------------------------------------------


class ClaimCreate(StrictInputSchema):

    outcome_indicator_id: int
    contributing_program_id: Optional[int] = None
    contributing_initiative_id: Optional[int] = None
    mechanism_short: str = Field(min_length=1, max_length=280)
    mechanism_detail: str = Field(min_length=1)
    evidence_strength: EvidenceStrength = EvidenceStrength.theoretical
    evidence_citations: Optional[str] = None
    intended_dose: Optional[str] = Field(default=None, max_length=255)
    expected_lag: Optional[str] = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def _exactly_one_attribution(self) -> "ClaimCreate":
        has_program = self.contributing_program_id is not None
        has_initiative = self.contributing_initiative_id is not None
        if has_program == has_initiative:
            raise ValueError(
                "Exactly one of contributing_program_id or "
                "contributing_initiative_id must be set."
            )
        return self


class ClaimReview(BaseModel):

    notes: Optional[str] = None


class ClaimPromote(BaseModel):

    evidence_strength: EvidenceStrength
    board_decision_link_id: Optional[int] = None
    evidence_citations: Optional[str] = None


class ClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    outcome_indicator_id: int
    contributing_program_id: Optional[int]
    contributing_initiative_id: Optional[int]
    mechanism_short: str
    mechanism_detail: str
    evidence_strength: str
    evidence_citations: Optional[str]
    intended_dose: Optional[str]
    expected_lag: Optional[str]
    reviewed_at: Optional[datetime]
    reviewed_by_user_id: Optional[int]
    next_review_due: Optional[date]
    board_decision_link_id: Optional[int]
    is_active: bool
    retired_at: Optional[datetime]
    retired_reason: Optional[str]
    created_by_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime

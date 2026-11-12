# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ConsentStatus = Literal["granted", "revoked", "not_requested"]


class FamilySnapshotMember(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    first_name_revealed: str = Field(
        ...,
        description="Either initial-with-period (redacted) or full first "
        "name (revealed). Field name reflects 'what's revealed at this "
        "moment', not 'always revealed'.",
    )
    age_range: str = Field(
        ...,
        description="One of '0-5', '6-8', '9-12', '13-17' (matches "
        "``program_family.AgeRange``).",
    )
    is_parent: bool = False


class FamilySnapshotResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    patron_id: int
    consent_status: ConsentStatus
    consent_recorded_at: Optional[datetime] = None
    language_preference: Optional[str] = Field(
        None, description="BCP-47-ish code (e.g. 'en', 'es', 'vi')."
    )
    language_preference_label: Optional[str] = Field(
        None,
        description="Human-facing autonym of ``language_preference`` "
        "(e.g. 'Español'). Falls back to the code when no label is known.",
    )
    household_size: Optional[int] = Field(
        None,
        description="Total adults+children including the patron. Null when "
        "consent has not been granted (size leaks sensitive info too).",
    )
    household_members: List[FamilySnapshotMember] = Field(
        default_factory=list,
        description="Empty list when consent has not been granted.",
    )
    household_notes_summary: Optional[str] = Field(
        None,
        description="A short summary of ``family_situation_notes`` from "
        "the most recent session. Null when consent missing or when notes "
        "are empty.",
    )
    baby_age_months: Optional[int] = Field(
        None,
        description="Mirror of ``parent_onboarding_session.baby_age_months`` "
        "for the session referenced in the URL. Visible when consent is "
        "granted; null otherwise.",
    )
    sensitive_fields_hidden: bool = Field(
        ...,
        description="True when names + notes are redacted or omitted. "
        "Defaults to True until the staff caller clicks Reveal.",
    )


class PatronConsentDecision(BaseModel):

    model_config = ConfigDict(extra="forbid")

    granted: bool = Field(
        ...,
        description="True records a new active consent; False creates a "
        "row with ``revoked_at = now()`` that supersedes any active row.",
    )
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional free-text note captured at the point of "
        "consent (e.g. 'verbal consent recorded during session #42').",
    )


class PatronConsentRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int
    patron_id: int
    consent_type: str
    granted: bool
    recorded_by_staff_id: Optional[int]
    recorded_at: datetime
    revoked_at: Optional[datetime]
    notes: Optional[str]


class PatronConsentStatusResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    patron_id: int
    consent_status: ConsentStatus
    consent_recorded_at: Optional[datetime] = None
    recorded_by_staff_id: Optional[int] = None

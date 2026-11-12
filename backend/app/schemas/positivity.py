# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class PositivityEntryCreate(StrictInputSchema):
    entry_type: str = Field(..., description="Type of positivity entry")
    text: str = Field(..., min_length=1, max_length=5000, description="Entry text content")


class PositivityEntryUpdate(StrictInputSchema):
    entry_type: Optional[str] = None
    text: Optional[str] = Field(None, min_length=1, max_length=5000)


class PositivityEntryResponse(BaseModel):
    id: int
    entry_type: str
    text: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_name: Optional[str] = None

    model_config = {"from_attributes": True}


class PositivityEntryFullResponse(BaseModel):
    id: int
    entry_type: str
    text: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_name: Optional[str] = None
    source: str = "staff"
    patron_name: Optional[str] = None
    patron_email: Optional[str] = None
    flagged_for_advocacy: bool = False
    flagged_at: Optional[datetime] = None
    flagged_by_name: Optional[str] = None
    moderation_status: str = "approved"
    moderated_at: Optional[datetime] = None
    moderated_by_name: Optional[str] = None
    moderation_note: Optional[str] = None

    model_config = {"from_attributes": True}


class PositivityEntriesListResponse(BaseModel):
    entries: List[PositivityEntryFullResponse]
    total: int
    page: int
    per_page: int
    pages: int


class PositivityDigestResponse(BaseModel):
    feedback: int = 0
    win: int = 0
    program: int = 0
    thank_you: int = 0
    compliment: int = 0
    story: int = 0
    appreciation: int = 0
    total: int = 0
    advocacy_flagged: int = 0
    patron_submissions: int = 0
    pending_moderation: int = 0


# --- Patron Submission Schemas ---

class PatronPositivitySubmission(BaseModel):
    entry_type: str = Field(..., description="Type: feedback, thank-you, or story")
    text: str = Field(..., min_length=10, max_length=5000, description="The experience text")
    patron_name: Optional[str] = Field(None, max_length=255, description="Optional patron name")
    patron_email: Optional[str] = Field(None, max_length=255, description="Optional patron email")


class PatronSubmissionResponse(BaseModel):
    message: str
    id: int


# --- Advocacy Schemas ---

class AdvocacyFlagRequest(StrictInputSchema):
    flagged: bool


class AdvocacyEntriesResponse(BaseModel):
    entries: List[PositivityEntryFullResponse]
    count: int
    period_days: int


# --- Moderation Schemas ---

class ModerationActionRequest(StrictInputSchema):
    action: str = Field(..., description="'approve' or 'reject'")
    note: Optional[str] = Field(None, max_length=1000, description="Optional moderation note")

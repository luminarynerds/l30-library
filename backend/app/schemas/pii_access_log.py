# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas._base import StrictInputSchema

# Validated client-side and at the service layer. Kept narrow on purpose --
# new actions should be added deliberately, not by free-text drift.
PIIAccessAction = Literal["read", "reveal", "export", "print"]


class PIIAccessLogCreate(StrictInputSchema):

    patron_id: int = Field(
        ...,
        ge=1,
        description="Patron whose PII was accessed (users.id with role=PATRON, "
        "but FK is users.id so any user record is technically valid).",
    )
    subject_type: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Free-text resource label (e.g. 'patron_profile', "
        "'home_address', 'session_intake', 'minor_data').",
    )
    subject_id: Optional[int] = Field(
        None,
        description="Resource row id when applicable; null when the access is "
        "for the patron record itself or the resource has no row id.",
    )
    action: PIIAccessAction = Field(
        ...,
        description="What the staff member did with the PII. 'read' = "
        "passive view, 'reveal' = unmasked a redacted field, 'export' = "
        "downloaded, 'print' = sent to printer.",
    )
    reason: Optional[str] = Field(
        None,
        max_length=1000,
        description="Free-text reason captured at the point of access; "
        "nullable because not every surface prompts.",
    )


class PIIAccessLogRead(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    patron_id: Optional[int]
    subject_type: Optional[str]
    subject_id: Optional[int]
    action: Optional[str]
    reason: Optional[str]
    accessed_at: datetime = Field(..., validation_alias="timestamp")

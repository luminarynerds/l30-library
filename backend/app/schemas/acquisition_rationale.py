# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas._base import StrictInputSchema

from app.models.acquisition_rationale import SignalType, WeedingCondition
from app.models.book_challenge import ChallengeReason


_VALID_CHALLENGE_REASONS = {r.value for r in ChallengeReason}


class _RationaleBase(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    signal_type: SignalType
    signal_ref_table: Optional[str] = Field(default=None, max_length=50)
    signal_ref_id: Optional[int] = None
    signal_note: Optional[str] = None

    policy_clause: Optional[str] = Field(default=None, max_length=100)

    primary_use_case_slug: str = Field(min_length=1, max_length=64)
    secondary_use_case_slugs: list[str] = Field(default_factory=list)

    weeding_condition: WeedingCondition = WeedingCondition.CURRENT_5YR
    weeding_signal_note: Optional[str] = None

    anticipated_challenge_reasons: list[str] = Field(default_factory=list)
    anticipated_challenge_acknowledged: bool = False

    patron_visible: bool = False
    public_summary: Optional[str] = None

    @model_validator(mode='after')
    def _validate_signal_ref(self):
        if (self.signal_ref_table is None) != (self.signal_ref_id is None):
            raise ValueError(
                'signal_ref_table and signal_ref_id must both be set or both be null'
            )
        return self

    @model_validator(mode='after')
    def _validate_challenge_reasons(self):
        bad = [r for r in self.anticipated_challenge_reasons if r not in _VALID_CHALLENGE_REASONS]
        if bad:
            raise ValueError(f'invalid challenge reasons: {bad}')
        return self


class AcquisitionRationaleCreate(StrictInputSchema, _RationaleBase):
    pass


class AcquisitionRationaleUpdate(StrictInputSchema, _RationaleBase):
    pass


class AcquisitionRationaleRead(_RationaleBase):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: int
    catalog_item_id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class BehaviorTagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    label: str
    category: str
    description: Optional[str] = None
    sort_order: int

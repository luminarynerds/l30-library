# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator

from ._base import MoneyDecimal, StrictInputSchema

from ..models.catalog import ItemType
from ..models.circulation_policy import BookBinding
from ..models.user import UserRole


# Knobs (loan_period_days, max_renewals, ...) are stored separately because we
# need to know which ones the caller explicitly set in PATCH-style updates and
# to validate "at least one knob" on create.
_KNOB_FIELDS = (
    "loan_period_days",
    "max_renewals",
    "overdue_fine_per_day",
    "max_fine",
    "grace_period_days",
    "hold_pickup_days",
    "fine_free",
)


class _PolicyKnobs(BaseModel):

    loan_period_days: Optional[int] = Field(default=None, ge=0, le=365)
    max_renewals: Optional[int] = Field(default=None, ge=0, le=20)
    overdue_fine_per_day: Optional[MoneyDecimal] = Field(default=None, ge=0)
    max_fine: Optional[MoneyDecimal] = Field(default=None, ge=0)
    grace_period_days: Optional[int] = Field(default=None, ge=0, le=30)
    hold_pickup_days: Optional[int] = Field(default=None, ge=0, le=30)
    fine_free: Optional[bool] = None


class _PolicyScope(BaseModel):

    role: Optional[UserRole] = None
    item_type: Optional[ItemType] = None
    binding: Optional[BookBinding] = None
    collection_id: Optional[int] = None


def _validate_binding_against_item_type(
    item_type: Optional[ItemType], binding: Optional[BookBinding]
) -> None:
    if binding is not None and item_type is not None and item_type != ItemType.book:
        raise ValueError(
            "binding can only be set when item_type is 'book' or NULL "
            f"(got item_type={item_type.value!r})"
        )


class CirculationPolicyCreate(StrictInputSchema, _PolicyScope, _PolicyKnobs):

    library_system_id: Optional[int] = Field(
        default=None,
        description=(
            "If omitted, defaults to the only configured library_system_id "
            "(single-system deploys). Caller can override for multi-system."
        ),
    )
    active: bool = True
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _validate(self) -> "CirculationPolicyCreate":
        _validate_binding_against_item_type(self.item_type, self.binding)
        if not any(getattr(self, f) is not None for f in _KNOB_FIELDS):
            raise ValueError(
                "At least one policy knob must be set "
                f"(one of: {', '.join(_KNOB_FIELDS)})"
            )
        return self


class CirculationPolicyUpdate(StrictInputSchema, _PolicyKnobs):

    role: Optional[UserRole] = None
    item_type: Optional[ItemType] = None
    binding: Optional[BookBinding] = None
    collection_id: Optional[int] = None
    active: Optional[bool] = None
    notes: Optional[str] = None

    # Note: binding-vs-item_type cross-field validation happens in the router
    # after we merge the update onto the existing row, since either field may
    # be omitted in a partial update.


class CirculationPolicyResponse(BaseModel):

    id: int
    library_system_id: int

    role: Optional[UserRole] = None
    item_type: Optional[ItemType] = None
    binding: Optional[BookBinding] = None
    collection_id: Optional[int] = None

    loan_period_days: Optional[int] = None
    max_renewals: Optional[int] = None
    overdue_fine_per_day: Optional[MoneyDecimal] = None
    max_fine: Optional[MoneyDecimal] = None
    grace_period_days: Optional[int] = None
    hold_pickup_days: Optional[int] = None
    fine_free: Optional[bool] = None

    active: bool
    notes: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProvenanceEntry(BaseModel):

    source: str = Field(description="'policy' | 'system_settings' | 'default'")
    policy_id: Optional[int] = Field(
        default=None,
        description="The policy row that supplied this value, when source=='policy'.",
    )
    scope: str = Field(
        description=(
            "Human-readable scope of the source row, e.g. "
            "'role=patron, item_type=dvd' or 'system_settings' or 'hardcoded default'."
        )
    )


class ResolvedPolicyResponse(BaseModel):

    loan_period_days: int
    max_renewals: int
    overdue_fine_per_day: MoneyDecimal
    max_fine: MoneyDecimal
    grace_period_days: int
    hold_pickup_days: int
    fine_free: bool

    provenance: dict[str, ProvenanceEntry]

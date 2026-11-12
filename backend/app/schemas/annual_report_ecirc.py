# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Strict input schema for third-party electronic circulation (PLS e-circ).

PLS electronic circulation must include vendor e-platform usage (OverDrive/Libby,
Hoopla, e-audio, ...), which L30 does not model natively. Staff enter the per-platform
counts by hand, so the input is strict (``extra="forbid"``): an unexpected top-level
key is a data-entry mistake and should 422 rather than be silently dropped.
"""
from pydantic import BaseModel, ConfigDict, Field
from pydantic.types import conint


class ElectronicCirculationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Platform name -> circulation count. Platform names are open-ended, so the
    # forbid guard is on this wrapper, not on the dict keys; counts must be >= 0.
    by_platform: dict[str, conint(ge=0)] = Field(default_factory=dict)


class ElectronicCirculationResponse(BaseModel):
    report_id: int
    third_party_electronic_circulation: int
    electronic_circulation_by_platform: dict[str, int]
    electronic_circulation: int
    total_circulation: int

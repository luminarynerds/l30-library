# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime

from pydantic import BaseModel

from app.schemas._base import StrictInputSchema


class PLSDataElement(BaseModel):
    code: str  # PLS field code (e.g., "TOTCIR", "BKVOL")
    label: str
    category: str  # collection, circulation, programs, staffing, finance, facilities
    value: int | float | str | None
    source: str  # auto, manual_override, manual_required
    notes: str | None = None


class PLSPreviewResponse(BaseModel):
    fiscal_year: int
    library_name: str
    fscs_id: str | None  # Federal-State Cooperative System ID
    elements: list[PLSDataElement]
    auto_calculated: int
    manual_overrides: int
    missing: int
    fields_requiring_manual_input: list[str] = []


class PLSOverrideRequest(StrictInputSchema):
    overrides: dict[str, int | float | str]  # code -> value


class PLSExportHistoryItem(BaseModel):
    id: int
    fiscal_year: int
    generated_at: datetime
    generated_by_name: str | None
    element_count: int
    override_count: int


class PLSExportHistoryResponse(BaseModel):
    items: list[PLSExportHistoryItem]
    total: int

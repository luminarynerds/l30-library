# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Strict input schema for director-entered annual report finance (Phase 3.2).

PLS finance is entered by hand by the director, not derived, so the input is
strict (``extra="forbid"``): an unexpected key is a data-entry mistake and
should 422 rather than be silently dropped.
"""
from decimal import Decimal
from app.schemas._base import MoneyDecimal

from pydantic import BaseModel, ConfigDict, Field


class RevenueLines(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local: MoneyDecimal = Field(ge=0)
    state: MoneyDecimal = Field(ge=0)
    federal: MoneyDecimal = Field(ge=0)
    other: MoneyDecimal = Field(ge=0)


class ExpenditureLines(BaseModel):
    model_config = ConfigDict(extra="forbid")

    salaries: MoneyDecimal = Field(ge=0)
    benefits: MoneyDecimal = Field(ge=0)
    print: MoneyDecimal = Field(ge=0)  # print collection materials
    electronic: MoneyDecimal = Field(ge=0)  # electronic collection materials
    other: MoneyDecimal = Field(ge=0)  # other operating expenditure


class FinanceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_operating_revenue: MoneyDecimal = Field(ge=0)
    revenue: RevenueLines
    total_operating_expenditure: MoneyDecimal = Field(ge=0)
    expenditure: ExpenditureLines
    capital_outlay: MoneyDecimal = Field(ge=0, default=Decimal(0))
    capital_revenue: RevenueLines | None = None


class FinanceEntryResponse(BaseModel):
    report_id: int
    total_operating_revenue: MoneyDecimal
    total_operating_expenditure: MoneyDecimal
    capital_outlay: MoneyDecimal
    data_source: str

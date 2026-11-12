# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from decimal import Decimal
from app.schemas._base import MoneyDecimal
from pydantic import BaseModel, Field


class CostFactor(BaseModel):
    name: str
    description: str
    low_estimate: MoneyDecimal
    high_estimate: MoneyDecimal
    unit: str = Field(default="per item", description="Unit of measurement")
    notes: str | None = None


class MaterialFormatCosts(BaseModel):
    format_type: str
    format_name: str
    description: str
    acquisition_cost: CostFactor
    processing_cost: CostFactor
    storage_cost: CostFactor
    maintenance_cost: CostFactor
    licensing_model: str | None = Field(
        default=None,
        description="For digital: perpetual, subscription, metered, etc."
    )
    typical_lifespan_years: int | None = None
    simultaneous_users: str = Field(
        default="1",
        description="How many patrons can use simultaneously"
    )
    environmental_notes: str | None = None
    advantages: list[str] = []
    limitations: list[str] = []


class CostComparisonCategory(BaseModel):
    category_name: str
    category_description: str
    formats: list[MaterialFormatCosts]


class MaterialCostComparisonResponse(BaseModel):
    last_updated: str
    data_sources: list[str]
    methodology_note: str
    categories: list[CostComparisonCategory]


class CostComparisonSummary(BaseModel):
    format_type: str
    format_name: str
    avg_total_cost_per_circulation: MoneyDecimal
    typical_circulations_per_copy: int
    cost_per_simultaneous_user: MoneyDecimal

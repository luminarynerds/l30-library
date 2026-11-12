# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from ._base import StrictInputSchema


class EbookCardPurchaseRequest(StrictInputSchema):
    tier: str = Field(default="standard", description="Subscription tier: basic, standard, or unlimited")
    home_state: Optional[str] = Field(None, description="Applicant's home state")
    home_zip: Optional[str] = Field(None, description="Applicant's home ZIP code")
    auto_renew: bool = Field(default=False, description="Enable automatic annual renewal")


class EbookCardResponse(BaseModel):
    id: int
    card_number: str
    tier: str
    status: str
    annual_fee: float
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    max_concurrent_borrows: int
    max_monthly_borrows: int
    borrows_this_month: int
    total_borrows: int
    auto_renew: bool
    can_borrow: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class EbookCardTierInfo(BaseModel):
    tier: str
    display_name: str
    description: Optional[str] = None
    annual_fee: float
    max_concurrent_borrows: int
    max_monthly_borrows: int
    is_available: bool


class EbookCardStatsResponse(BaseModel):
    total_cards_issued: int
    active_cards: int
    expired_cards: int
    cancelled_cards: int
    total_revenue: float
    revenue_this_year: float
    cards_by_tier: dict
    top_states: list


class EbookCardRenewRequest(StrictInputSchema):
    tier: Optional[str] = Field(None, description="Change tier on renewal (optional)")

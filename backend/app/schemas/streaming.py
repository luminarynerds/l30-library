# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas._base import MoneyDecimal, StrictInputSchema

from ..models.streaming import (
    StreamingCheckoutStatus,
    StreamingContentType,
    StreamingService,
)


# ============================================================================
# Service Configuration Schemas
# ============================================================================


class StreamingServiceConfigBase(BaseModel):
    service: StreamingService
    is_active: bool = True
    api_base_url: str
    library_id: str | None = None
    cost_per_checkout: MoneyDecimal = Decimal("0.00")
    app_deep_link_template: str | None = None
    web_deep_link_template: str | None = None


class StreamingServiceConfigCreate(StrictInputSchema, StreamingServiceConfigBase):
    api_key: str | None = None
    api_secret: str | None = None


class StreamingServiceConfigUpdate(StrictInputSchema):
    is_active: bool | None = None
    api_base_url: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    library_id: str | None = None
    cost_per_checkout: MoneyDecimal | None = None
    app_deep_link_template: str | None = None
    web_deep_link_template: str | None = None


class StreamingServiceConfigResponse(StreamingServiceConfigBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Budget Schemas
# ============================================================================


class StreamingBudgetCreate(StrictInputSchema):
    service_config_id: int
    fiscal_year: int
    fiscal_month: int | None = None
    allocated_amount: MoneyDecimal
    max_checkouts: int | None = None


class StreamingBudgetUpdate(StrictInputSchema):
    allocated_amount: MoneyDecimal | None = None
    max_checkouts: int | None = None


class StreamingBudgetResponse(BaseModel):
    id: int
    service_config_id: int
    service_name: str | None = None
    fiscal_year: int
    fiscal_month: int | None = None
    allocated_amount: MoneyDecimal
    spent_amount: MoneyDecimal
    remaining_amount: MoneyDecimal
    max_checkouts: int | None = None
    current_checkouts: int
    remaining_checkouts: int | None = None
    utilization_percentage: float = 0.0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Patron Limit Schemas
# ============================================================================


class PatronStreamingLimitCreate(StrictInputSchema):
    user_id: int
    service_config_id: int
    monthly_limit: int = 5


class PatronStreamingLimitUpdate(StrictInputSchema):
    monthly_limit: int | None = None


class PatronStreamingLimitResponse(BaseModel):
    id: int
    user_id: int
    service_config_id: int
    service_name: str | None = None
    monthly_limit: int
    current_month_checkouts: int
    remaining_checkouts: int
    limit_reset_date: datetime

    class Config:
        from_attributes = True


class DefaultPatronStreamingLimitCreate(StrictInputSchema):
    service_config_id: int
    user_role: str
    monthly_limit: int = 5


class DefaultPatronStreamingLimitResponse(BaseModel):
    id: int
    service_config_id: int
    user_role: str
    monthly_limit: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


# ============================================================================
# Catalog Item Schemas
# ============================================================================


class StreamingCatalogItemBase(BaseModel):
    external_id: str
    title: str
    author: str | None = None
    description: str | None = None
    content_type: StreamingContentType
    isbn: str | None = None
    duration_minutes: int | None = None
    release_year: int | None = None
    genres: str | None = None
    cover_url: str | None = None
    rating: str | None = None
    is_available: bool = True
    available_until: datetime | None = None


class StreamingCatalogItemCreate(StrictInputSchema, StreamingCatalogItemBase):
    service_config_id: int
    catalog_item_id: int | None = None


class StreamingCatalogItemResponse(StreamingCatalogItemBase):
    id: int
    service_config_id: int
    service_name: str | None = None
    catalog_item_id: int | None = None
    last_synced_at: datetime
    created_at: datetime | None = None
    # Deep links
    app_deep_link: str | None = None
    web_deep_link: str | None = None

    class Config:
        from_attributes = True


class StreamingSearchResult(BaseModel):
    items: list[StreamingCatalogItemResponse]
    total_count: int
    services_searched: list[str]
    query: str


# ============================================================================
# Checkout Schemas
# ============================================================================


class StreamingCheckoutCreate(StrictInputSchema):
    streaming_item_id: int


class StreamingCheckoutResponse(BaseModel):
    id: int
    user_id: int | None = None
    service_config_id: int
    service_name: str | None = None
    streaming_item_id: int | None = None
    external_checkout_id: str | None = None
    status: StreamingCheckoutStatus
    checked_out_at: datetime
    expires_at: datetime | None = None
    returned_at: datetime | None = None
    cost: MoneyDecimal
    item_title: str | None = None
    item_content_type: StreamingContentType | None = None
    cover_url: str | None = None

    # Deep links for accessing content
    app_deep_link: str | None = None
    web_deep_link: str | None = None

    class Config:
        from_attributes = True


class StreamingCheckoutReturn(BaseModel):
    checkout_id: int


# ============================================================================
# Patron Dashboard Schemas
# ============================================================================


class PatronStreamingOverview(BaseModel):
    service: StreamingService
    service_name: str
    monthly_limit: int
    current_month_checkouts: int
    remaining_checkouts: int
    limit_reset_date: datetime
    active_checkouts: list[StreamingCheckoutResponse]
    is_available: bool = True


class PatronStreamingDashboard(BaseModel):
    services: list[PatronStreamingOverview]
    total_active_checkouts: int
    recent_checkouts: list[StreamingCheckoutResponse]


# ============================================================================
# Analytics and Reporting Schemas
# ============================================================================


class StreamingUsageStatsCreate(StrictInputSchema):
    service_config_id: int
    stat_date: datetime
    total_checkouts: int = 0
    unique_patrons: int = 0
    total_cost: MoneyDecimal = Decimal("0.00")
    checkouts_by_type: str | None = None
    top_items: str | None = None


class StreamingUsageStatsResponse(BaseModel):
    id: int
    service_config_id: int
    service_name: str | None = None
    stat_date: datetime
    total_checkouts: int
    unique_patrons: int
    total_cost: MoneyDecimal
    cost_per_checkout: MoneyDecimal = Decimal("0.00")
    checkouts_by_type: dict | None = None
    top_items: list[dict] | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class StreamingDashboardStats(BaseModel):
    # Overall stats
    total_checkouts_this_month: int
    total_cost_this_month: MoneyDecimal
    unique_patrons_this_month: int
    average_cost_per_checkout: MoneyDecimal

    # Per-service breakdown
    service_stats: list[dict]

    # Budget utilization
    total_budget_allocated: MoneyDecimal
    total_budget_spent: MoneyDecimal
    budget_utilization_percentage: float

    # Trending
    top_titles: list[dict]
    checkouts_by_content_type: dict
    checkouts_trend: list[dict]  # Daily/weekly trend data


class CollectionDevelopmentReport(BaseModel):
    report_period_start: datetime
    report_period_end: datetime

    # Most watched content
    most_watched_titles: list[dict]
    most_watched_genres: list[dict]
    most_active_content_types: list[dict]

    # Cost analysis
    total_cost: MoneyDecimal
    cost_by_service: dict
    cost_by_content_type: dict
    cost_per_checkout_by_service: dict

    # Patron engagement
    total_unique_patrons: int
    patron_engagement_by_service: dict
    repeat_user_rate: float

    # Availability insights
    titles_frequently_unavailable: list[dict]
    recommended_additions: list[dict]


# ============================================================================
# Search Schemas
# ============================================================================


class UnifiedSearchQuery(BaseModel):
    query: str
    content_types: list[StreamingContentType] | None = None
    services: list[StreamingService] | None = None
    include_unavailable: bool = False
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class UnifiedSearchResponse(BaseModel):
    items: list[StreamingCatalogItemResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    services_searched: list[str]
    query: str


# ============================================================================
# Catalog Integration Schemas
# ============================================================================


class CatalogStreamingAvailability(BaseModel):
    catalog_item_id: int
    catalog_item_title: str
    streaming_options: list[StreamingCatalogItemResponse]
    has_streaming: bool


class BulkStreamingAvailability(BaseModel):
    items: list[CatalogStreamingAvailability]


# ============================================================================
# Deep Link Schemas
# ============================================================================


class DeepLinkResponse(BaseModel):
    streaming_item_id: int
    service: StreamingService
    title: str
    app_deep_link: str | None = None
    web_deep_link: str | None = None
    requires_checkout: bool = True
    is_checked_out: bool = False


# ============================================================================
# Paginated Response Schemas
# ============================================================================


class PaginatedStreamingCheckoutsResponse(BaseModel):
    items: list[StreamingCheckoutResponse] = Field(..., description="List of streaming checkouts")
    total: int = Field(..., ge=0, description="Total number of checkouts")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

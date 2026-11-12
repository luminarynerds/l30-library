# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TrendDirection(StrEnum):

    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class TimeWindow(StrEnum):

    TODAY = "today"
    WEEK = "7d"
    MONTH = "30d"
    QUARTER = "90d"
    YEAR = "365d"
    ALL_TIME = "all"


class TrendData(BaseModel):

    direction: TrendDirection = Field(
        ..., description="Trend direction: up, down, or stable"
    )
    change_percentage: float = Field(
        ..., description="Percentage change from previous period"
    )
    previous_value: float = Field(..., description="Value from previous period")
    current_value: float = Field(..., description="Current period value")

    @classmethod
    def calculate(
        cls,
        current: int | float | Decimal,
        previous: int | float | Decimal,
        threshold: float = 1.0,
    ) -> "TrendData":
        current_float = float(current)
        previous_float = float(previous)

        if previous_float == 0:
            # Avoid division by zero
            if current_float == 0:
                direction = TrendDirection.STABLE
                change_pct = 0.0
            else:
                # If previous was 0 and current is positive, it's UP
                direction = TrendDirection.UP
                change_pct = 100.0  # Show 100% increase
        else:
            change_pct = ((current_float - previous_float) / previous_float) * 100
            if abs(change_pct) <= threshold:
                direction = TrendDirection.STABLE
            elif change_pct > 0:
                direction = TrendDirection.UP
            else:
                direction = TrendDirection.DOWN

        return cls(
            direction=direction,
            change_percentage=round(change_pct, 2),
            previous_value=previous_float,
            current_value=current_float,
        )


class StatsMetadata(BaseModel):

    generated_at: datetime = Field(..., description="When the stats were generated")
    cached: bool = Field(
        default=False, description="Whether this response was served from cache"
    )
    cache_ttl: int = Field(default=300, description="Cache TTL in seconds")
    time_window: str = Field(..., description="Time window for the stats (e.g. 30d)")


# ============================================================================
# Circulation Analytics Schemas
# ============================================================================


class CirculationStats(BaseModel):

    # Counts
    total_checkouts: int = Field(..., description="Total checkouts in period")
    active_checkouts: int = Field(..., description="Currently checked out items")
    checkouts_today: int = Field(..., description="Checkouts today")
    returns_today: int = Field(..., description="Returns today")
    overdue_count: int = Field(..., description="Overdue items")

    # Trends
    checkout_trend: Optional[TrendData] = Field(
        None, description="Checkout trend vs previous period"
    )
    overdue_trend: Optional[TrendData] = Field(
        None, description="Overdue trend vs previous period"
    )

    # Metrics
    unique_patrons: int = Field(..., description="Unique patrons who checked out items")
    avg_daily_checkouts: float = Field(..., description="Average checkouts per day")
    turnover_rate: float = Field(..., description="Collection turnover rate (%)")

    # Metadata
    metadata: StatsMetadata


class PopularItem(BaseModel):

    catalog_item_id: int
    title: str
    author: Optional[str] = None
    checkout_count: int
    item_type: Optional[str] = None


class PopularItemsResponse(BaseModel):

    items: List[PopularItem]
    period_days: int
    total_unique_items: int


class TrendDataPoint(BaseModel):

    date: str
    checkouts: int
    returns: Optional[int] = None


class CirculationTrendsResponse(BaseModel):

    data: List[TrendDataPoint]
    period_days: int
    avg_checkouts: float
    peak_day: Optional[str] = None
    peak_count: Optional[int] = None


# ============================================================================
# Reading Analytics Schemas
# ============================================================================


class ReadingStats(BaseModel):

    # Totals
    total_minutes_read: int = Field(
        ..., description="Total minutes read (all time or period)"
    )
    total_books_completed: int = Field(..., description="Total books completed")
    total_pages_read: int = Field(..., description="Total pages read")
    total_participants: int = Field(..., description="Number of active readers")

    # Averages
    avg_minutes_per_session: float = Field(
        ..., description="Average minutes per reading session"
    )
    avg_pages_per_session: float = Field(..., description="Average pages per session")
    avg_rating: Optional[float] = Field(None, description="Average book rating (1-5)")

    # Trends
    minutes_trend: Optional[TrendData] = Field(None, description="Reading time trend")
    books_trend: Optional[TrendData] = Field(None, description="Books completed trend")

    # Metadata
    metadata: StatsMetadata


class TopReader(BaseModel):

    user_id: int
    user_name: str
    total_minutes: int
    total_books: int
    reading_streak: Optional[int] = None


class TopReadersResponse(BaseModel):

    readers: List[TopReader]
    period_days: int
    total_readers: int


# ============================================================================
# Patron Engagement Analytics Schemas
# ============================================================================


class PatronEngagementStats(BaseModel):

    # Counts
    total_patrons: int = Field(..., description="Total patron accounts")
    active_patrons: int = Field(..., description="Patrons active in period")
    new_patrons: int = Field(..., description="New patron registrations in period")
    dormant_patrons: int = Field(..., description="Patrons inactive 180+ days")

    # Engagement metrics
    engagement_rate: float = Field(..., description="% patrons active in period")
    avg_checkouts_per_patron: float = Field(
        ..., description="Average checkouts per active patron"
    )
    retention_rate: float = Field(
        ..., description="% patrons returning from previous period"
    )

    # Trends
    engagement_trend: Optional[TrendData] = Field(
        None, description="Engagement rate trend"
    )
    new_patrons_trend: Optional[TrendData] = Field(None, description="New patron trend")

    # Metadata
    metadata: StatsMetadata


# ============================================================================
# Collection Health Analytics Schemas
# ============================================================================


class DormancyBreakdown(BaseModel):

    active_count: int = Field(..., description="Items with checkout < 90 days ago")
    active_percentage: float
    drifting_count: int = Field(..., description="Items with checkout 90-180 days ago")
    drifting_percentage: float
    dormant_count: int = Field(..., description="Items with no checkout 180+ days")
    dormant_percentage: float


class CollectionHealthStats(BaseModel):

    # Total items
    total_items: int = Field(..., description="Total items in collection")
    total_available: int = Field(..., description="Items available for checkout")

    # Dormancy analysis
    dormancy: DormancyBreakdown

    # Utilization
    utilization_rate: float = Field(..., description="% of collection currently in use")
    avg_checkouts_per_item: float = Field(..., description="Average checkouts per item")

    # Problem items
    never_checked_out: int = Field(..., description="Items never checked out")
    damaged_items: int = Field(..., description="Items marked as damaged")
    missing_items: int = Field(..., description="Items marked as missing")

    # Metadata
    metadata: StatsMetadata


class DriftingItem(BaseModel):

    catalog_item_id: int
    title: str
    author: Optional[str] = None
    days_since_checkout: int
    #         last_checkout_date: Optional[datetime] = None
    copy_count: int


class DriftingItemsResponse(BaseModel):

    items: List[DriftingItem]
    total_drifting: int


# ============================================================================
# Fine Analytics Schemas
# ============================================================================


class FineStats(BaseModel):

    # Outstanding
    outstanding_total: float = Field(..., description="Total outstanding fines")
    patrons_with_fines: int = Field(
        ..., description="Number of patrons with outstanding fines"
    )

    # Collections
    paid_this_month: float = Field(..., description="Fines paid this month")
    waived_this_month: float = Field(..., description="Fines waived this month")
    collection_rate: float = Field(..., description="% of fines collected vs issued")

    # Trends
    outstanding_trend: Optional[TrendData] = Field(
        None, description="Outstanding fines trend"
    )

    # Metadata
    metadata: StatsMetadata


# ============================================================================
# Unified Dashboard Response
# ============================================================================


# ============================================================================
# Social Sharing Analytics Schemas
# ============================================================================


class SharedResource(BaseModel):

    resource_id: int
    resource_type: str
    title: str
    author: Optional[str] = None
    share_count: int


class PlatformBreakdown(BaseModel):

    platform: str
    share_count: int
    percentage: float


class TopSharer(BaseModel):

    user_id: int
    user_name: str
    email: str
    total_shares: int
    favorite_platform: Optional[str] = None


class ShareTrendDataPoint(BaseModel):

    date: str
    total_shares: int
    unique_sharers: int


class SharingDashboardResponse(BaseModel):

    # Top resources
    top_shared_resources: List[SharedResource] = Field(
        ..., description="Top 10 most shared resources (books, events, lists)"
    )

    # Platform breakdown
    platform_breakdown: List[PlatformBreakdown] = Field(
        ..., description="Share count by platform with percentages"
    )

    # Metrics
    total_shares: int = Field(..., description="Total number of shares in period")
    unique_sharers: int = Field(..., description="Number of unique users who shared")
    avg_shares_per_user: float = Field(
        ..., description="Average shares per active sharer"
    )

    # Top sharers
    top_sharers: List[TopSharer] = Field(
        ..., description="Top 10 most active sharers"
    )

    # Trends
    share_trends: List[ShareTrendDataPoint] = Field(
        ..., description="Share activity trends over specified period"
    )
    shares_trend: Optional[TrendData] = Field(
        None, description="Overall shares trend vs previous period"
    )

    # Most popular platform
    top_platform: str = Field(..., description="Most used sharing platform")
    top_platform_percentage: float = Field(
        ..., description="% of total shares for top platform"
    )

    # Metadata
    metadata: StatsMetadata


class AnalyticsDashboardResponse(BaseModel):

    circulation: CirculationStats
    reading: ReadingStats
    patron_engagement: PatronEngagementStats
    collection_health: CollectionHealthStats
    fines: FineStats
    metadata: StatsMetadata

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema
from typing import List, Optional
from datetime import datetime
from enum import Enum


class CirculationSnapshot(BaseModel):

    active_checkouts: int = Field(..., description="Items currently checked out")
    returned_total: int = Field(..., description="Total items returned")
    overdue_items: int = Field(..., description="Items currently overdue")
    checked_out_today: int = Field(..., description="Items checked out in past 24h")
    returned_today: int = Field(..., description="Items returned in past 24h")
    active_holds: int = Field(..., description="Items on hold")
    circulation_rate: float = Field(..., description="Active checkouts as % of collection")

    class Config:
        json_schema_extra = {
            "example": {
                "active_checkouts": 45,
                "returned_total": 234,
                "overdue_items": 12,
                "checked_out_today": 3,
                "returned_today": 5,
                "active_holds": 8,
                "circulation_rate": 6.84,
            }
        }


class OverdueItemDetail(BaseModel):

    checkout_id: int
    due_date: datetime
    checked_out_at: datetime
    item_title: str
    item_author: Optional[str]
    item_isbn: Optional[str]
    item_type: str
    patron_id: int
    patron_name: str
    patron_email: Optional[str]
    patron_phone: Optional[str]
    fine_amount: float
    fine_status: str
    days_overdue: int


class OverdueItemsResponse(BaseModel):

    items: List[OverdueItemDetail]
    total: int
    skip: int
    limit: int


class PopularItem(BaseModel):

    item_id: int
    title: str
    author: Optional[str]
    item_type: str
    isbn: Optional[str]
    subjects: List[str]
    checkout_count: int
    hold_count: int


class PopularItemsResponse(BaseModel):

    items: List[PopularItem]
    days_range: int
    total: int


class ThemeMetric(BaseModel):

    theme: str
    checkout_count: int
    unique_items: int
    utilization_rate: float = Field(..., description="% of items currently checked out")
    turnover_ratio: float = Field(..., description="Checkouts per item")
    velocity_score: float = Field(..., description="Combined velocity metric")


class ThemeVelocityResponse(BaseModel):

    metrics: List[ThemeMetric]
    days_range: int


class HoldQueueStatus(BaseModel):

    total_pending: int
    ready_for_pickup: int
    expiring_soon_count: int = Field(..., description="Holds waiting 30+ days")
    average_wait_days: float
    longest_wait_days: int
    queue_health: str = Field(..., description="'healthy' or 'warning'")


class HealthComponent(BaseModel):

    name: str
    score: float = Field(..., ge=0, le=100)
    weight: int = Field(..., description="Weight in overall calculation (0-100)")


class CollectionHealthResponse(BaseModel):

    overall_score: float = Field(..., ge=0, le=100, description="Weighted health score")
    components: List[HealthComponent]
    status: str = Field(..., description="'Excellent', 'Good', 'Fair', or 'Poor'")


class SystemAlert(BaseModel):

    id: str
    priority: str = Field(..., description="'critical', 'warning', or 'info'")
    category: str = Field(
        ..., description="'circulation', 'holds', 'collection', 'fines', etc."
    )
    title: str
    message: str
    action_url: Optional[str] = Field(None, description="Link to take action")


class SystemAlertsResponse(BaseModel):

    alerts: List[SystemAlert]


class DashboardMetricsResponse(BaseModel):

    circulation_snapshot: CirculationSnapshot
    holds_queue: HoldQueueStatus
    overdue_count: int
    collection_health: CollectionHealthResponse
    timestamp: str = Field(..., description="ISO format timestamp")


class QuickActionRequest(StrictInputSchema):

    action_type: str = Field(
        ...,
        description="'mark_returned', 'send_overdue_notice', or 'waive_fine'",
    )
    target_id: int = Field(..., description="ID of checkout, hold, or fine")
    reason: Optional[str] = None


class QuickActionResponse(BaseModel):

    success: bool
    message: str

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema

from ..models.shelf_reading import (
    ScanResult,
    ScheduleFrequency,
    ShelfReadingStatus,
)


# ============ Session Schemas ============


class ShelfReadingSessionCreate(StrictInputSchema):
    name: str = Field(..., max_length=255)
    description: str | None = None
    branch_id: int
    location: str = Field(..., max_length=100)
    call_number_start: str | None = Field(None, max_length=100)
    call_number_end: str | None = Field(None, max_length=100)


class ShelfReadingSessionResponse(BaseModel):
    id: int
    name: str
    description: str | None
    branch_id: int
    location: str
    call_number_start: str | None
    call_number_end: str | None
    status: ShelfReadingStatus
    started_at: datetime
    completed_at: datetime | None
    paused_at: datetime | None
    total_items_scanned: int
    items_in_order: int
    items_out_of_order: int
    items_wrong_shelf: int
    accuracy_percentage: float
    points_earned: int
    created_by_id: int
    created_by_name: str | None = None
    branch_name: str | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ShelfReadingSessionListResponse(BaseModel):
    items: list[ShelfReadingSessionResponse]
    total: int
    page: int
    per_page: int


# ============ Scan Schemas ============


class ShelfReadingScanCreate(StrictInputSchema):
    barcode: str


class ShelfReadingScanResponse(BaseModel):
    id: int
    session_id: int
    item_copy_id: int
    scan_order: int
    scanned_call_number: str | None
    previous_call_number: str | None
    result: ScanResult
    expected_location: str | None
    correct_position_after: str | None
    scanned_at: datetime
    scanned_by_id: int
    barcode: str | None = None
    catalog_title: str | None = None
    catalog_author: str | None = None

    class Config:
        from_attributes = True


class ShelfReadingScanListResponse(BaseModel):
    items: list[ShelfReadingScanResponse]
    total: int
    session_accuracy: float


# ============ Schedule Schemas ============


class ShelfReadingScheduleCreate(StrictInputSchema):
    name: str = Field(..., max_length=255)
    description: str | None = None
    branch_id: int
    location: str = Field(..., max_length=100)
    call_number_start: str | None = Field(None, max_length=100)
    call_number_end: str | None = Field(None, max_length=100)
    frequency: ScheduleFrequency
    assigned_to_id: int | None = None
    next_due_at: datetime | None = None


class ShelfReadingScheduleUpdate(StrictInputSchema):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    frequency: ScheduleFrequency | None = None
    is_active: bool | None = None
    assigned_to_id: int | None = None
    next_due_at: datetime | None = None


class ShelfReadingScheduleResponse(BaseModel):
    id: int
    name: str
    description: str | None
    branch_id: int
    location: str
    call_number_start: str | None
    call_number_end: str | None
    frequency: ScheduleFrequency
    is_active: bool
    last_completed_at: datetime | None
    next_due_at: datetime | None
    assigned_to_id: int | None
    assigned_to_name: str | None = None
    created_by_id: int
    branch_name: str | None = None
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class ShelfReadingScheduleListResponse(BaseModel):
    items: list[ShelfReadingScheduleResponse]
    total: int
    page: int
    per_page: int


# ============ Report Schemas ============


class ShelfAccuracyReport(BaseModel):
    branch_id: int
    branch_name: str
    total_sessions: int
    total_items_scanned: int
    items_in_order: int
    items_out_of_order: int
    items_wrong_shelf: int
    overall_accuracy: float
    period_start: datetime
    period_end: datetime


class BranchAccuracySummary(BaseModel):
    branch_id: int
    branch_name: str
    sessions_completed: int
    average_accuracy: float
    last_session_at: datetime | None
    total_points_earned: int


class HistoricalAccuracyPoint(BaseModel):
    period: str  # e.g., "2026-01", "2026-W08"
    accuracy: float
    sessions: int
    items_scanned: int


class HistoricalAccuracyReport(BaseModel):
    branch_id: int
    branch_name: str
    data_points: list[HistoricalAccuracyPoint]


# ============ Gamification Schemas ============


class ShelfReadingLeaderboardEntry(BaseModel):
    user_id: int
    user_name: str
    total_points: int
    sessions_completed: int
    average_accuracy: float
    rank: int


class ShelfReadingLeaderboard(BaseModel):
    entries: list[ShelfReadingLeaderboardEntry]
    period: str  # "all_time", "monthly", "weekly"


# ============ Progress Schemas ============


class ShelfReadingProgress(BaseModel):
    session_id: int
    session_name: str
    status: ShelfReadingStatus
    total_items_scanned: int
    items_in_order: int
    items_out_of_order: int
    items_wrong_shelf: int
    accuracy_percentage: float
    last_scanned_call_number: str | None
    points_earned: int

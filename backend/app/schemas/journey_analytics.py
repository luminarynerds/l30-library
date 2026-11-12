# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


# ============================================================================
# JOURNEY STAGE & FUNNEL SCHEMAS
# ============================================================================

class FunnelStage(BaseModel):
    stage_name: str = Field(..., description="e.g., 'search_initiated', 'results_displayed'")
    event_count: int = Field(..., description="Number of events at this stage")
    unique_sessions: int = Field(..., description="Unique sessions reaching this stage")
    completion_rate: float = Field(..., description="Percentage of journeys completing this stage")
    avg_time_to_stage_ms: int = Field(..., description="Average time from journey start (milliseconds)")
    median_time_to_stage_ms: int = Field(..., description="Median time from journey start (milliseconds)")
    p95_time_to_stage_ms: int = Field(..., description="95th percentile time (milliseconds)")
    error_count: int = Field(0, description="Number of error events at this stage")
    error_rate: float = Field(0.0, description="Percentage of errors at this stage")

    class Config:
        json_schema_extra = {
            "example": {
                "stage_name": "search_initiated",
                "event_count": 1250,
                "unique_sessions": 1200,
                "completion_rate": 95.2,
                "avg_time_to_stage_ms": 150,
                "median_time_to_stage_ms": 120,
                "p95_time_to_stage_ms": 500,
                "error_count": 12,
                "error_rate": 1.0
            }
        }


class JourneyFunnelResponse(BaseModel):
    journey_type: str = Field(..., description="e.g., 'search_to_hold'")
    segment_key: Optional[str] = Field(None, description="Segment filter applied (device_mobile|user_returning|access_false)")
    total_sessions: int = Field(..., description="Total journeys started")
    completed_sessions: int = Field(..., description="Journeys completed")
    overall_completion_rate: float = Field(..., description="Percentage of journeys completed")
    avg_time_to_completion_ms: int = Field(..., description="Average completion time in milliseconds")
    stages: List[FunnelStage] = Field(..., description="All stages in order")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "journey_type": "search_to_hold",
                "segment_key": None,
                "total_sessions": 1250,
                "completed_sessions": 1100,
                "overall_completion_rate": 88.0,
                "avg_time_to_completion_ms": 2500,
                "stages": [
                    {
                        "stage_name": "search_initiated",
                        "event_count": 1250,
                        "unique_sessions": 1250,
                        "completion_rate": 100.0,
                        "avg_time_to_stage_ms": 0,
                        "median_time_to_stage_ms": 0,
                        "p95_time_to_stage_ms": 100,
                        "error_count": 0,
                        "error_rate": 0.0
                    }
                ],
                "timestamp": "2026-02-22T14:30:00Z"
            }
        }


# ============================================================================
# DROP-OFF ANALYSIS
# ============================================================================

class DropOffPoint(BaseModel):
    stage: str = Field(..., description="Stage where users dropped off")
    dropoff_count: int = Field(..., description="Number of users who abandoned at this stage")
    dropoff_rate: float = Field(..., description="Percentage of users dropping off here")
    time_at_stage_ms: int = Field(..., description="Average time spent at this stage before drop-off")
    primary_reason: Optional[str] = Field(None, description="Most common reason for drop-off")
    segment_breakdown: Dict[str, int] = Field(default_factory=dict, description="Drop-offs by device/user type")

    class Config:
        json_schema_extra = {
            "example": {
                "stage": "results_displayed",
                "dropoff_count": 75,
                "dropoff_rate": 6.0,
                "time_at_stage_ms": 3500,
                "primary_reason": "timeout",
                "segment_breakdown": {
                    "mobile": 45,
                    "desktop": 25,
                    "tablet": 5
                }
            }
        }


class JourneyDropOffResponse(BaseModel):
    journey_type: str
    total_dropoffs: int = Field(..., description="Total users who abandoned")
    overall_abandonment_rate: float = Field(..., description="Percentage of users abandoning")
    dropoff_points: List[DropOffPoint] = Field(..., description="Analysis by stage")
    most_problematic_stage: str = Field(..., description="Stage with highest abandonment")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# SEGMENTATION & METRICS
# ============================================================================

class SegmentMetrics(BaseModel):
    segment_name: str = Field(..., description="e.g., 'Mobile Returning Users with Accessibility'")
    segment_key: str = Field(..., description="Composite key for filtering")
    device_type: Optional[str] = None
    user_type: Optional[str] = None
    accessibility_mode: Optional[bool] = None

    total_sessions: int = Field(..., description="Sessions in this segment")
    completed_sessions: int = Field(..., description="Completed sessions")
    completion_rate: float = Field(..., description="Completion rate percentage")
    avg_completion_time_ms: int = Field(..., description="Average time to completion")
    error_rate: float = Field(..., description="Error rate percentage")
    abandonment_rate: float = Field(..., description="Abandonment rate percentage")

    class Config:
        json_schema_extra = {
            "example": {
                "segment_name": "Mobile Users",
                "segment_key": "device_mobile",
                "device_type": "mobile",
                "user_type": None,
                "accessibility_mode": None,
                "total_sessions": 500,
                "completed_sessions": 420,
                "completion_rate": 84.0,
                "avg_completion_time_ms": 3200,
                "error_rate": 2.5,
                "abandonment_rate": 16.0
            }
        }


class JourneyMetricsResponse(BaseModel):
    journey_type: str
    time_period: str = Field(..., description="'24_hours', '7_days', '28_days'")
    total_sessions: int
    completed_sessions: int
    completion_rate: float
    avg_time_to_completion_ms: int
    error_rate: float
    abandonment_rate: float
    segments: List[SegmentMetrics] = Field(..., description="Breakdown by segment")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# REAL-TIME UPDATES
# ============================================================================

class RealtimeUpdate(StrictInputSchema):
    journey_type: str
    timestamp: datetime
    metric_type: str = Field(..., description="'completion_rate', 'new_sessions', 'error_spike'")
    current_value: float
    previous_value: Optional[float] = None
    percent_change: Optional[float] = None
    segment_key: Optional[str] = None
    is_alert: bool = False


class RealtimeMetricsResponse(BaseModel):
    journeys: Dict[str, Dict[str, Any]] = Field(..., description="Current metrics per journey")
    last_updated: datetime
    next_update_in_seconds: int = 30


# ============================================================================
# ALERTS & REGRESSIONS
# ============================================================================

class RegressionAlert(BaseModel):
    alert_id: int
    journey_type: str
    alert_type: str = Field(..., description="'completion_rate_drop', 'error_rate_spike'")
    severity: str = Field(..., description="'low', 'medium', 'high'")
    current_value: float
    baseline_value: float
    percent_change: float = Field(..., description="Negative number for drops, positive for increases")
    description: str = Field(..., description="Human-readable alert message")
    segment_affected: Optional[str] = None
    created_at: datetime | None = None
    is_resolved: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "alert_id": 1,
                "journey_type": "search_to_hold",
                "alert_type": "completion_rate_drop",
                "severity": "high",
                "current_value": 78.5,
                "baseline_value": 88.0,
                "percent_change": -10.8,
                "description": "Search→Hold completion rate dropped 10.8% below 7-day average",
                "segment_affected": None,
                "created_at": "2026-02-22T14:30:00Z",
                "is_resolved": False
            }
        }


class AlertsResponse(BaseModel):
    active_alerts: List[RegressionAlert]
    total_count: int
    unresolved_count: int
    timestamp: datetime


# ============================================================================
# DASHBOARD RESPONSE (Combined)
# ============================================================================

class JourneyDashboardResponse(BaseModel):
    timestamp: datetime
    time_period: str = Field("24_hours")

    # Top 5 journeys
    journeys: Dict[str, JourneyFunnelResponse] = Field(...)

    # Segmented views
    segments: List[SegmentMetrics] = Field(...)

    # Drop-off analysis
    dropoffs: Dict[str, JourneyDropOffResponse] = Field(...)

    # Alerts
    alerts: List[RegressionAlert] = Field(default_factory=list)

    # Real-time status
    real_time_enabled: bool = True
    next_real_time_update_in_seconds: int = 30

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-02-22T14:30:00Z",
                "time_period": "24_hours",
                "journeys": {
                    "search_to_hold": {
                        "journey_type": "search_to_hold",
                        "total_sessions": 1250,
                        "completed_sessions": 1100,
                        "overall_completion_rate": 88.0,
                        "stages": []
                    }
                },
                "segments": [],
                "dropoffs": {},
                "alerts": [],
                "real_time_enabled": True,
                "next_real_time_update_in_seconds": 30
            }
        }


# ============================================================================
# HISTORICAL TRENDS
# ============================================================================

class TrendPoint(BaseModel):
    timestamp: datetime
    value: float
    sessions_count: Optional[int] = None


class HistoricalTrendResponse(BaseModel):
    journey_type: str
    metric: str = Field(..., description="'completion_rate', 'session_count', 'error_rate'")
    period_7_days: List[TrendPoint]
    period_28_days: List[TrendPoint]
    current_7_day_avg: float
    current_28_day_avg: float
    trend_direction: str = Field(..., description="'improving', 'declining', 'stable'")
    timestamp: datetime

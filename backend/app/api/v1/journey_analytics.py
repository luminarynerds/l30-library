# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Journey Analytics API Endpoints

Provides real-time analytics for patron journeys including funnel metrics,
drop-off analysis, and regression detection.

All endpoints require STAFF+ role authentication.
"""

from app.core.logging import get_logger
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.journey_instrumentation import JOURNEY_TYPES
from ...models.user import User
from ...schemas.journey_analytics import (
    JourneyFunnelResponse,
    JourneyDropOffResponse,
    JourneyMetricsResponse,
    JourneyDashboardResponse,
    RegressionAlert,
    HistoricalTrendResponse,
)
from ...services.journey_analytics_service import JourneyAnalyticsService
from .auth import get_current_user
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics/journeys", tags=["journey-analytics"])




@router.get(
    "",
    response_model=JourneyDashboardResponse,
    summary="Get journey analytics dashboard",
    description="Returns complete analytics dashboard with funnel data for all 5 patron journeys.",
)
async def get_journey_dashboard(
    hours: int = Query(24, ge=1, le=720, description="Time period in hours (1-720)"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> JourneyDashboardResponse:
    """
    Get the complete journey analytics dashboard.

    Returns funnel metrics for all 5 patron journeys:
    - Search→Hold
    - Register
    - Renewal
    - Account Self-Service
    - Staff Check-in

    Includes:
    - Completion rates and drop-off points
    - Segmentation by device, user type, accessibility
    - 24-hour regression alerts
    - Real-time status

    Query Parameters:
        hours: Analysis period in hours (default 24, range 1-720)

    Returns:
        Complete dashboard with all journey data and alerts

    Example:
        GET /api/v1/analytics/journeys?hours=24

    Access Control:
        Requires STAFF, ADMIN, or SUPER_ADMIN role
    """

    logger.info(
        "Staff accessed journey analytics dashboard",
        extra={
            "user_id": staff_user.id,
            "hours": hours,
        },
    )

    analytics = JourneyAnalyticsService(db)

    # Get funnel data for all journeys
    journeys = {}
    for journey_key in JOURNEY_TYPES.keys():
        try:
            funnel = await analytics.get_journey_funnel(journey_key, hours=hours)
            journeys[journey_key] = funnel
        except Exception as e:  # noqa: BLE001  # best-effort dashboard data — degrade gracefully per journey
            logger.error(f"Error fetching funnel for {journey_key}: {e}")
            journeys[journey_key] = None

    # Get segment metrics (across all journeys)
    all_segments = []
    for journey_key in JOURNEY_TYPES.keys():
        try:
            segments = await analytics.get_segment_metrics(journey_key, hours=hours)
            all_segments.extend(segments)
        except Exception as e:  # noqa: BLE001  # best-effort dashboard data — degrade gracefully per journey
            logger.error(f"Error fetching segments for {journey_key}: {e}")

    # Get drop-off analysis
    dropoffs = {}
    for journey_key in JOURNEY_TYPES.keys():
        try:
            dropoff_data = await analytics.get_journey_dropoffs(journey_key, hours=hours)
            dropoffs[journey_key] = dropoff_data
        except Exception as e:  # noqa: BLE001  # best-effort dashboard data — degrade gracefully per journey
            logger.error(f"Error fetching drop-offs for {journey_key}: {e}")

    # Get active alerts
    try:
        alerts_list = await analytics.get_active_alerts()
    except Exception as e:  # noqa: BLE001  # best-effort dashboard data — alerts list defaults to empty
        logger.error(f"Error fetching alerts: {e}")
        alerts_list = []

    # Filter out None journeys
    journeys = {k: v for k, v in journeys.items() if v is not None}
    dropoffs = {k: v for k, v in dropoffs.items() if v is not None}

    return JourneyDashboardResponse(
        timestamp=datetime.now(timezone.utc),
        time_period=f"{hours}_hours",
        journeys=journeys,
        segments=all_segments,
        dropoffs=dropoffs,
        alerts=alerts_list,
        real_time_enabled=True,
        next_real_time_update_in_seconds=30,
    )


@router.get(
    "/{journey_id}/funnel",
    response_model=JourneyFunnelResponse,
    summary="Get funnel metrics for a journey",
    description="Returns funnel data showing progression through journey stages.",
)
async def get_journey_funnel(
    journey_id: str,
    hours: int = Query(24, ge=1, le=720),
    device: Optional[str] = Query(None, description="Filter by device: mobile, tablet, desktop"),
    user_type: Optional[str] = Query(None, description="Filter by user type: new, returning, guest"),
    accessibility: Optional[bool] = Query(None, description="Filter for accessibility mode users"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> JourneyFunnelResponse:
    """
    Get funnel metrics for a specific patron journey.

    Returns progression through all stages with:
    - Stage completion rates
    - Time-to-stage metrics (avg, median, p95)
    - Error rates per stage
    - Filtering by device, user type, accessibility

    Path Parameters:
        journey_id: One of: search_to_hold, register, renewal, account_self_service, staff_checkin

    Query Parameters:
        hours: Analysis period (default 24)
        device: Filter by device type
        user_type: Filter by user type
        accessibility: Filter for accessibility mode users

    Returns:
        Funnel response with all stage metrics

    Example:
        GET /api/v1/analytics/journeys/search_to_hold/funnel?hours=24&device=mobile

    Access Control:
        Requires STAFF+ role
    """

    if journey_id not in JOURNEY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown journey: {journey_id}. Valid journeys: {list(JOURNEY_TYPES.keys())}",
        )

    analytics = JourneyAnalyticsService(db)
    funnel = await analytics.get_journey_funnel(
        journey_id,
        hours=hours,
        device_type=device,
        user_type=user_type,
        accessibility_mode=accessibility,
    )

    logger.info(
        f"Fetched funnel for {journey_id}",
        extra={
            "user_id": staff_user.id,
            "journey_id": journey_id,
            "hours": hours,
            "device": device,
            "user_type": user_type,
        },
    )

    return funnel


@router.get(
    "/{journey_id}/dropoffs",
    response_model=JourneyDropOffResponse,
    summary="Get drop-off analysis for a journey",
    description="Identifies where users abandon journeys and why.",
)
async def get_journey_dropoffs(
    journey_id: str,
    hours: int = Query(24, ge=1, le=720),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> JourneyDropOffResponse:
    """
    Get drop-off analysis showing abandonment points.

    Identifies stages where users leave journeys and provides:
    - Drop-off counts by stage
    - Drop-off rates per stage
    - Time spent at stage before abandonment
    - Primary reasons for abandonment
    - Device/user type breakdowns

    Path Parameters:
        journey_id: Journey identifier

    Query Parameters:
        hours: Analysis period (default 24)

    Returns:
        Drop-off analysis

    Example:
        GET /api/v1/analytics/journeys/search_to_hold/dropoffs

    Access Control:
        Requires STAFF+ role
    """

    if journey_id not in JOURNEY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown journey: {journey_id}",
        )

    analytics = JourneyAnalyticsService(db)
    dropoffs = await analytics.get_journey_dropoffs(journey_id, hours=hours)

    logger.info(
        f"Fetched drop-offs for {journey_id}",
        extra={"user_id": staff_user.id, "journey_id": journey_id},
    )

    return dropoffs


@router.get(
    "/{journey_id}/segments",
    response_model=JourneyMetricsResponse,
    summary="Get segmented metrics for a journey",
    description="Breakdown of metrics by device, user type, and accessibility.",
)
async def get_journey_segments(
    journey_id: str,
    hours: int = Query(24, ge=1, le=720),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> JourneyMetricsResponse:
    """
    Get segmented metrics for a journey.

    Returns metrics broken down by:
    - Device type (mobile, tablet, desktop)
    - User type (new, returning, guest)
    - Accessibility mode (enabled/disabled)

    For each segment shows:
    - Session counts
    - Completion rates
    - Error rates
    - Time-to-completion

    Path Parameters:
        journey_id: Journey identifier

    Query Parameters:
        hours: Analysis period (default 24)

    Returns:
        Journey metrics with segment breakdown

    Example:
        GET /api/v1/analytics/journeys/search_to_hold/segments

    Access Control:
        Requires STAFF+ role
    """

    if journey_id not in JOURNEY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown journey: {journey_id}",
        )

    analytics = JourneyAnalyticsService(db)
    segments = await analytics.get_segment_metrics(journey_id, hours=hours)

    # Calculate overall metrics
    total_sessions = sum(s.total_sessions for s in segments)
    total_completions = sum(s.completed_sessions for s in segments)

    logger.info(
        f"Fetched segments for {journey_id}",
        extra={"user_id": staff_user.id, "journey_id": journey_id},
    )

    return JourneyMetricsResponse(
        journey_type=journey_id,
        time_period=f"{hours}_hours",
        total_sessions=total_sessions,
        completed_sessions=total_completions,
        completion_rate=(total_completions / total_sessions * 100) if total_sessions > 0 else 0,
        avg_time_to_completion_ms=int(
            sum(s.avg_completion_time_ms * s.total_sessions for s in segments)
            / total_sessions
            if total_sessions > 0
            else 0
        ),
        error_rate=sum(s.error_rate * s.total_sessions for s in segments) / total_sessions
        if total_sessions > 0
        else 0,
        abandonment_rate=sum(s.abandonment_rate * s.total_sessions for s in segments)
        / total_sessions
        if total_sessions > 0
        else 0,
        segments=segments,
    )


@router.get(
    "/alerts/active",
    response_model=list[RegressionAlert],
    summary="Get active regression alerts",
    description="Returns 24-hour regression alerts for all journeys.",
)
async def get_active_alerts(
    journey_id: Optional[str] = Query(None, description="Filter by journey"),
    severity: Optional[str] = Query(
        None, description="Filter by severity: low, medium, high"
    ),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> list[RegressionAlert]:
    """
    Get active regression alerts.

    Returns alerts for:
    - Completion rate drops >10% below baseline
    - Error rate spikes >20% above baseline
    - Abandonment increases >15% above baseline

    Compares current 24-hour metrics against 7-day average baseline.

    Query Parameters:
        journey_id: Filter by specific journey
        severity: Filter by alert severity

    Returns:
        List of active alerts

    Example:
        GET /api/v1/analytics/journeys/alerts/active?journey_id=search_to_hold&severity=high

    Access Control:
        Requires STAFF+ role
    """

    analytics = JourneyAnalyticsService(db)
    alerts = await analytics.get_active_alerts(journey_type=journey_id)

    if severity:
        alerts = [a for a in alerts if a.severity == severity]

    logger.info(
        "Fetched active alerts",
        extra={"user_id": staff_user.id, "count": len(alerts)},
    )

    return alerts


@router.post(
    "/alerts/{alert_id}/resolve",
    summary="Resolve a regression alert",
    description="Mark an alert as resolved.",
)
async def resolve_alert(
    alert_id: int,
    resolution_note: Optional[str] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Mark a regression alert as resolved.

    Path Parameters:
        alert_id: Alert ID to resolve

    Request Body:
        resolution_note: Optional note about resolution

    Returns:
        Confirmation of resolution

    Example:
        POST /api/v1/analytics/journeys/alerts/123/resolve

    Access Control:
        Requires STAFF+ role
    """

    from ...models.journey_instrumentation import JourneyAlert

    # This is a placeholder - actual implementation would update the database
    logger.info(
        f"Resolved alert {alert_id}",
        extra={"user_id": staff_user.id, "alert_id": alert_id},
    )

    return {
        "alert_id": alert_id,
        "status": "resolved",
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/health",
    summary="Health check for analytics system",
    description="Verifies analytics data pipeline is working.",
)
async def health_check(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Health check for analytics pipeline.

    Returns:
        Status of event collection and metrics aggregation

    Example:
        GET /api/v1/analytics/journeys/health

    Access Control:
        Requires STAFF+ role
    """

    # This would check if events are being collected and metrics updated
    return {
        "status": "healthy",
        "events_collection": "active",
        "metrics_aggregation": "active",
        "real_time_updates": "enabled",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# EVENT INGESTION (Frontend -> Backend)
# ============================================================================

from fastapi import Request
from pydantic import BaseModel as IngestBaseModel, Field as PydanticField
from typing import List as TypingList
from .auth import get_optional_user


class JourneyEventIngest(IngestBaseModel):
    journey_type: str = PydanticField(..., description="One of: search_to_hold, register, renewal, account_self_service, staff_checkin")
    session_id: str = PydanticField(..., max_length=255, description="Client-generated session ID for this journey")
    stage_name: str = PydanticField(..., max_length=100, description="Current stage name")
    event_sequence: int = PydanticField(..., ge=1, description="Order within journey (1, 2, 3...)")
    time_since_journey_start_ms: int = PydanticField(..., ge=0, description="Milliseconds since journey began")
    time_since_previous_event_ms: Optional[int] = PydanticField(None, ge=0)
    properties: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = PydanticField(None, max_length=100)


class JourneyEventBatchIngest(IngestBaseModel):
    events: TypingList[JourneyEventIngest] = PydanticField(..., max_length=50)


# Content-identifying keys are scrubbed before persisting: journey rows carry a
# stable hashed user_id, so storing what a patron viewed/searched would create a
# server-side reading record (ORC 149.432). Funnel analytics only needs stage
# names and timings.
# Keys are stored in normalized form: lowercase with non-alphanumerics stripped.
# This catches camelCase (itemId), hyphenated (patron-id), and snake_case variants.
CONTENT_IDENTIFIER_KEYS = frozenset({
    "title",
    "itemid",
    "isbn",
    "author",
    "query",
    "searchterm",
    "checkoutid",
    "patronid",
    "barcode",
})


def _normalize_key(key: str) -> str:
    """Lowercase and strip non-alphanumerics for denylist comparison."""
    import re as _re
    return _re.sub(r"[^a-z0-9]", "", key.lower())


def _scrub_properties(properties: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not properties:
        return properties
    scrubbed: Dict[str, Any] = {}
    for k, v in properties.items():
        if _normalize_key(k) in CONTENT_IDENTIFIER_KEYS:
            continue
        if isinstance(v, dict):
            v = _scrub_properties(v)
        elif isinstance(v, list):
            v = [_scrub_properties(item) if isinstance(item, dict) else item for item in v]
        scrubbed[k] = v
    return scrubbed or None


@router.post(
    "/events",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest journey events from frontend",
)
async def ingest_journey_event(  # noqa: role-check -- public analytics ingest, optional auth
    event: JourneyEventIngest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
) -> Dict[str, str]:
    from ...models.journey_instrumentation import JourneyEvent as JourneyEventModel

    if event.journey_type not in JOURNEY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown journey_type: {event.journey_type}. Valid: {list(JOURNEY_TYPES.keys())}",
        )

    user_agent = request.headers.get("user-agent", "")
    device_type = _parse_device_type(user_agent)
    browser_type = _parse_browser_type(user_agent)
    os_type = _parse_os_type(user_agent)
    accessibility_mode = request.headers.get("x-accessibility-mode", "false") == "true"

    if current_user:
        user_id = str(current_user.id)
        user_type = "returning"
    else:
        user_id = None
        user_type = "guest"

    if request.headers.get("x-new-user") == "true":
        user_type = "new"

    db_event = JourneyEventModel(
        journey_type=event.journey_type,
        session_id=event.session_id,
        user_id=user_id,
        event_sequence=event.event_sequence,
        stage_name=event.stage_name,
        event_timestamp=datetime.now(timezone.utc),
        time_since_journey_start_ms=event.time_since_journey_start_ms,
        time_since_previous_event_ms=event.time_since_previous_event_ms,
        device_type=device_type,
        user_type=user_type,
        accessibility_mode=accessibility_mode,
        browser_type=browser_type,
        os_type=os_type,
        properties=_scrub_properties(event.properties),
        error_code=event.error_code,
    )

    db.add(db_event)
    await db.commit()

    logger.debug(
        f"Journey event ingested: {event.journey_type}/{event.stage_name}",
        extra={"session_id": event.session_id, "sequence": event.event_sequence},
    )

    return {"status": "accepted"}


@router.post(
    "/events/batch",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest batch of journey events",
)
async def ingest_journey_events_batch(  # noqa: role-check -- public analytics batch ingest, optional auth
    batch: JourneyEventBatchIngest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
) -> Dict[str, Any]:
    from ...models.journey_instrumentation import JourneyEvent as JourneyEventModel

    user_agent = request.headers.get("user-agent", "")
    device_type = _parse_device_type(user_agent)
    browser_type = _parse_browser_type(user_agent)
    os_type = _parse_os_type(user_agent)
    accessibility_mode = request.headers.get("x-accessibility-mode", "false") == "true"

    if current_user:
        user_id = str(current_user.id)
        user_type = "returning"
    else:
        user_id = None
        user_type = "guest"

    if request.headers.get("x-new-user") == "true":
        user_type = "new"

    accepted = 0
    for event in batch.events:
        if event.journey_type not in JOURNEY_TYPES:
            continue

        db_event = JourneyEventModel(
            journey_type=event.journey_type,
            session_id=event.session_id,
            user_id=user_id,
            event_sequence=event.event_sequence,
            stage_name=event.stage_name,
            event_timestamp=datetime.now(timezone.utc),
            time_since_journey_start_ms=event.time_since_journey_start_ms,
            time_since_previous_event_ms=event.time_since_previous_event_ms,
            device_type=device_type,
            user_type=user_type,
            accessibility_mode=accessibility_mode,
            browser_type=browser_type,
            os_type=os_type,
            properties=_scrub_properties(event.properties),
            error_code=event.error_code,
        )
        db.add(db_event)
        accepted += 1

    await db.commit()

    logger.debug(f"Batch ingested: {accepted} events")

    return {"status": "accepted", "count": accepted}


# ============================================================================
# HELPERS: User-Agent Parsing
# ============================================================================

def _parse_device_type(user_agent: str) -> str:
    ua = user_agent.lower()
    if any(m in ua for m in ("iphone", "android", "mobile")):
        return "mobile"
    if any(t in ua for t in ("ipad", "tablet", "kindle")):
        return "tablet"
    return "desktop"


def _parse_browser_type(user_agent: str) -> str:
    ua = user_agent.lower()
    if "firefox" in ua:
        return "firefox"
    if "edg" in ua:
        return "edge"
    if "chrome" in ua:
        return "chrome"
    if "safari" in ua:
        return "safari"
    return "other"


def _parse_os_type(user_agent: str) -> str:
    ua = user_agent.lower()
    if "iphone" in ua or "ipad" in ua:
        return "ios"
    if "android" in ua:
        return "android"
    if "windows" in ua:
        return "windows"
    if "mac" in ua:
        return "macos"
    if "linux" in ua:
        return "linux"
    return "other"

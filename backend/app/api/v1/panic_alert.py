# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff Panic Alert API routes.

Discreet panic alert system for staff safety. Provides endpoints for triggering,
acknowledging, and resolving panic alerts.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.panic_alert import (
    PanicAlertCreate,
    PanicAlertListResponse,
    PanicAlertNotificationPreferencesCreate,
    PanicAlertNotificationPreferencesResponse,
    PanicAlertResponse,
    PanicAlertUpdate,
    PanicAlertTimelineResponse,
    PanicAlertStatsResponse,
    BulkAcknowledgeRequest,
    BulkAcknowledgeResponse,
)
from ...services.panic_alert_service import PanicAlertService
from ...services.panic_alert_stats_service import PanicAlertStatsService
from ...validators.panic_alert_validators import PanicAlertValidator
from ...app_logging.panic_alert_logger import PanicAlertLogger

from .auth import get_current_user
from .dependencies import require_staff

router = APIRouter(prefix="/panic-alerts", tags=["panic-alerts"])
panic_logger = PanicAlertLogger()


# ============================================================================
# Panic Alert Endpoints (Staff)
# ============================================================================


@router.post("", response_model=PanicAlertResponse, status_code=status.HTTP_201_CREATED)
async def trigger_panic_alert(
    alert_data: PanicAlertCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Trigger a panic alert. Staff-only endpoint.

    This silently triggers a panic alert that notifies managers/security
    without any visible indication on the staff member's screen.

    Security features:
    - Rate limiting: Max 10 alerts per user per hour
    - Requires an authenticated staff session (Bearer token)
    - Input validation: Validates situation notes and metadata

    - **activation_source**: How the alert was triggered (keyboard, button, etc.)
    - **situation_notes**: Optional notes about the situation (max 500 chars, validated)
    - **metadata**: Device info, location data, etc. (validated)

    Returns: Created panic alert with ID and timestamp
    """
    try:
        # Validate input data
        validated_notes, validated_metadata = PanicAlertValidator.validate_alert_data(
            situation_notes=alert_data.situation_notes,
            metadata=alert_data.metadata,
        )

        # Create validated alert data
        validated_alert_data = PanicAlertCreate(
            activation_source=alert_data.activation_source,
            situation_notes=validated_notes,
            metadata=validated_metadata,
        )

        # Get branch_id from current user if available
        branch_id = getattr(current_user, "branch_id", None)

        alert = await PanicAlertService.trigger_alert(
            session=db,
            user_id=current_user.id,
            alert_data=validated_alert_data,
            branch_id=branch_id,
        )
        return alert
    except HTTPException:
        raise
    except ValueError as e:
        # Log validation error
        panic_logger.log_validation_error(
            field="alert_data",
            error_message=str(e),
            user_id=current_user.id,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        # Log API error
        panic_logger.log_api_error(
            endpoint="/api/v1/panic-alerts",
            error_message=str(e),
            user_id=current_user.id,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{alert_id}", response_model=PanicAlertResponse)
async def get_panic_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get details of a specific panic alert.

    Only staff members can view panic alerts.
    """
    alert = await PanicAlertService.get_alert(session=db, alert_id=alert_id)

    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    return alert


@router.get("", response_model=list[PanicAlertListResponse])
async def list_active_panic_alerts(
    branch_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get list of active panic alerts.

    Optional filters:
    - **branch_id**: Filter to specific branch

    Returns: List of active alerts
    """
    alerts = await PanicAlertService.get_active_alerts(
        session=db, branch_id=branch_id, limit=limit
    )
    return alerts


@router.get("/user/recent", response_model=list[PanicAlertListResponse])
async def get_user_recent_alerts(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get recent panic alerts triggered by the current user.

    Returns: List of recent alerts for this user
    """
    alerts = await PanicAlertService.get_recent_alerts(
        session=db, user_id=current_user.id, hours=hours, limit=limit
    )
    return alerts


@router.patch("/{alert_id}/acknowledge", response_model=PanicAlertResponse)
async def acknowledge_panic_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Acknowledge a panic alert (staff responding to help).

    Only staff members can acknowledge alerts.
    """
    try:
        alert = await PanicAlertService.acknowledge_alert(
            session=db, alert_id=alert_id, acknowledged_by_user_id=current_user.id
        )
        return alert
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.patch("/{alert_id}/resolve", response_model=PanicAlertResponse)
async def resolve_panic_alert(
    alert_id: int,
    update_data: PanicAlertUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Resolve a panic alert (situation handled).

    Only staff members can resolve alerts.
    """
    try:
        alert = await PanicAlertService.resolve_alert(
            session=db,
            alert_id=alert_id,
            resolution_notes=update_data.resolution_notes,
        )
        return alert
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# ============================================================================
# Notification Preference Endpoints
# ============================================================================


@router.get(
    "/preferences/me",
    response_model=Optional[PanicAlertNotificationPreferencesResponse],
)
async def get_my_notification_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get notification preferences for the current user.

    Returns user's panic alert notification preferences, or creates default preferences if not set.
    """
    prefs = await PanicAlertService.get_notification_preferences(
        session=db, user_id=current_user.id
    )
    if prefs is None:
        # Create and return default preferences for first-time users
        default_preferences = PanicAlertNotificationPreferencesCreate(
            receive_panic_alerts=True,
            notify_via_email=False,
            notify_via_sms=False,
            notify_via_in_app=True,
            notify_for_all_branches=True,
            branch_ids=None,
            sound_enabled=False,
            vibration_enabled=True,
        )
        prefs = await PanicAlertService.set_notification_preferences(
            session=db, user_id=current_user.id, preferences=default_preferences
        )
        await db.commit()
        await db.refresh(prefs)
    return prefs


@router.post(
    "/preferences/me",
    response_model=PanicAlertNotificationPreferencesResponse,
    status_code=status.HTTP_200_OK,
)
async def set_my_notification_preferences(
    preferences: PanicAlertNotificationPreferencesCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Set or update notification preferences for the current user.

    Configure how you want to be notified about panic alerts from colleagues:
    - **receive_panic_alerts**: Enable/disable notifications
    - **notify_via_email**: Receive email notifications
    - **notify_via_sms**: Receive SMS notifications
    - **notify_via_in_app**: Receive in-app notifications
    - **notify_for_all_branches**: Notify for all branches or specific ones
    - **branch_ids**: List of branch IDs if not all branches
    - **sound_enabled**: Play sound on notification
    - **vibration_enabled**: Vibrate on notification (mobile)

    Returns: Updated preferences
    """
    prefs = await PanicAlertService.set_notification_preferences(
        session=db, user_id=current_user.id, preferences=preferences
    )
    return PanicAlertNotificationPreferencesResponse.model_validate(prefs)


# ============================================================================
# Timeline and Statistics Endpoints
# ============================================================================


@router.get("/{alert_id}/timeline", response_model=PanicAlertTimelineResponse)
async def get_panic_alert_timeline(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get the complete timeline/history of a panic alert.

    Shows all state transitions and actions performed on the alert:
    - When it was triggered
    - Who acknowledged it and when
    - Any escalations
    - Resolution details

    Returns: Complete timeline with all history entries
    """
    timeline = await PanicAlertStatsService.get_alert_timeline(
        session=db, alert_id=alert_id
    )

    if not timeline or not timeline.get("entries"):
        # Check if alert exists
        alert = await PanicAlertService.get_alert(session=db, alert_id=alert_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )

    return PanicAlertTimelineResponse.model_validate(timeline)


@router.get("/stats/overview", response_model=PanicAlertStatsResponse)
async def get_panic_alert_statistics(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    branch_id: Optional[int] = Query(None, description="Filter by branch"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get statistics and analytics for panic alerts.

    Provides insights including:
    - Total alerts by status
    - Average response time
    - False alert rate
    - Most common situations
    - Alerts by branch
    - Alerts by time of day

    Query parameters:
    - **start_date**: Start of date range (defaults to 30 days ago)
    - **end_date**: End of date range (defaults to now)
    - **branch_id**: Filter to specific branch

    Returns: Comprehensive statistics
    """
    from datetime import datetime

    # Parse dates if provided
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    stats = await PanicAlertStatsService.get_statistics(
        session=db,
        start_date=start,
        end_date=end,
        branch_id=branch_id,
    )

    return PanicAlertStatsResponse.model_validate(stats)


# ============================================================================
# Bulk Operations
# ============================================================================


@router.post("/bulk/acknowledge", response_model=BulkAcknowledgeResponse)
async def bulk_acknowledge_panic_alerts(
    request: BulkAcknowledgeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Acknowledge multiple panic alerts at once.

    Useful for managers who need to acknowledge several alerts quickly.
    Only active alerts will be acknowledged; others will be skipped.

    Request body:
    - **alert_ids**: List of alert IDs to acknowledge (max 100)

    Returns:
    - **acknowledged_count**: Number of successfully acknowledged alerts
    - **failed_ids**: List of alert IDs that failed
    - **errors**: Map of alert ID to error message for failures
    """
    result = await PanicAlertStatsService.bulk_acknowledge(
        session=db,
        alert_ids=request.alert_ids,
        acknowledged_by_user_id=current_user.id,
    )

    return BulkAcknowledgeResponse.model_validate(result)

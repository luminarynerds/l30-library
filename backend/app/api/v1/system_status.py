# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
System Status Monitoring API

Transparent system health reporting for staff and patrons.
Honesty about tech problems reduces stress. Staff are notified before patrons ask.
Tech failures are never blamed on staff.

Endpoints:
- Public: Current status, status page, active issues
- Staff: Report/resolve issues, health metrics, staff notifications, paper backups
- Auto-save: Save and recover in-progress work
- Offline mode: Track offline sessions and sync status
- Recovery alerts: "We're back" notifications after outages
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from .dependencies import require_staff, require_admin, get_current_user, get_optional_user
from ...models.system_status import (
    AutoSaveEntry,
    IssueComponent,
    OfflineModeSession,
    PaperBackupProcedure,
    PaperBackupType,
    StaffNotificationType,
    StaffStatusNotification,
    SystemHealthMetrics,
    SystemStatus,
    SystemStatusLog,
)
from ...models.user import User
from app.core.datetime_utils import utc_now

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------

class ReportIssueRequest(BaseModel):
    status: SystemStatus
    title: str = Field(..., max_length=255)
    description: str
    component: Optional[IssueComponent] = None
    estimated_fix_time: Optional[datetime] = None
    is_scheduled: bool = False
    is_public: bool = True
    patron_message: Optional[str] = None
    technical_details: Optional[str] = None
    available_features: Optional[list] = None
    degraded_features: Optional[list] = None
    offline_alternatives: Optional[list] = None


class UpdateIssueRequest(BaseModel):
    status: Optional[SystemStatus] = None
    description: Optional[str] = None
    estimated_fix_time: Optional[datetime] = None
    patron_message: Optional[str] = None
    technical_details: Optional[str] = None
    available_features: Optional[list] = None
    degraded_features: Optional[list] = None


class ResolveIssueRequest(BaseModel):
    resolution_notes: str
    send_recovery_alert: bool = True


class AutoSaveRequest(BaseModel):
    context_type: str = Field(..., max_length=100)
    context_id: Optional[str] = Field(None, max_length=255)
    saved_data: dict


class PaperBackupRequest(BaseModel):
    backup_type: PaperBackupType
    title: str = Field(..., max_length=255)
    description: str
    instructions: str
    form_template: Optional[str] = None
    trigger_conditions: Optional[str] = None
    applicable_components: Optional[list] = None


# ---------------------------------------------------------------------------
# Public endpoints - anyone can check system status
# ---------------------------------------------------------------------------

@router.get("/system-status", tags=["system-status"])
async def get_current_status(
    db: AsyncSession = Depends(get_db),
):
    """
    Get current system status and active issues (public endpoint).

    Returns honest, transparent status information. When things are slow,
    we say so. When things are down, we say what's affected and when
    we expect to fix it.
    """
    result = await db.execute(
        select(SystemStatusLog).where(
            and_(
                SystemStatusLog.resolved_at.is_(None),
                SystemStatusLog.is_public == True,
            )
        ).order_by(SystemStatusLog.started_at.desc())
    )
    active_issues = result.scalars().all()

    # Determine overall status from highest severity
    if not active_issues:
        overall_status = SystemStatus.OPERATIONAL
        overall_message = "All systems are running normally."
    else:
        statuses = [issue.status for issue in active_issues]
        if SystemStatus.MAJOR_OUTAGE in statuses:
            overall_status = SystemStatus.MAJOR_OUTAGE
            overall_message = "We're experiencing a major outage. Staff can help you with paper forms."
        elif SystemStatus.PARTIAL_OUTAGE in statuses:
            overall_status = SystemStatus.PARTIAL_OUTAGE
            overall_message = "Some services are temporarily unavailable. Most features still work."
        elif SystemStatus.SLOW in statuses:
            overall_status = SystemStatus.SLOW
            overall_message = "Things are running slow today. We're aware and working on it."
        elif SystemStatus.DEGRADED in statuses:
            overall_status = SystemStatus.DEGRADED
            overall_message = "Some features may be slower than usual. We're on it."
        elif SystemStatus.MAINTENANCE in statuses:
            overall_status = SystemStatus.MAINTENANCE
            overall_message = "Scheduled maintenance is in progress. We'll be back soon."
        else:
            overall_status = SystemStatus.OPERATIONAL
            overall_message = "All systems are running normally."

    return {
        "status": overall_status,
        "message": overall_message,
        "active_issues": [
            {
                "id": issue.id,
                "component": issue.component,
                "title": issue.title,
                "description": issue.description,
                "patron_message": issue.patron_message,
                "status": issue.status,
                "started_at": issue.started_at.isoformat() if issue.started_at else None,
                "estimated_fix_time": issue.estimated_fix_time.isoformat() if issue.estimated_fix_time else None,
                "available_features": issue.available_features,
                "degraded_features": issue.degraded_features,
                "offline_alternatives": issue.offline_alternatives,
            }
            for issue in active_issues
        ],
        "offline_mode_recommended": overall_status in [
            SystemStatus.MAJOR_OUTAGE,
            SystemStatus.PARTIAL_OUTAGE,
        ],
    }


@router.get("/system-status/live", tags=["system-status"])
async def get_live_status():
    """
    Live service status from the uptime monitor (public endpoint).

    Real automated checks (every 60s) drive the per-service indicators and
    uptime shown on /status. If the monitor is unreachable, "available" is
    false and the frontend falls back to the staff-reported incident board.
    """
    from ...services.kuma_status_service import get_live_status as _get_live_status
    return await _get_live_status()


@router.get("/system-status/status-page", tags=["system-status"])
async def get_status_page(
    db: AsyncSession = Depends(get_db),
):
    """
    Simple public status page with clear indicators.

    Designed to be embedded anywhere - honest at a glance.
    """
    result = await db.execute(
        select(SystemStatusLog).where(
            and_(
                SystemStatusLog.resolved_at.is_(None),
                SystemStatusLog.is_public == True,
            )
        )
    )
    active_issues = result.scalars().all()

    if not active_issues:
        indicator = "green"
        message = "All Systems Operational"
        detail = "Everything is working as expected."
    else:
        statuses = [issue.status for issue in active_issues]
        if SystemStatus.MAJOR_OUTAGE in statuses:
            indicator = "red"
            message = "Major Outage"
            detail = "We know about it and are working to fix it. Paper backup procedures are available."
        elif SystemStatus.PARTIAL_OUTAGE in statuses:
            indicator = "orange"
            message = "Partial Outage"
            detail = "Some services are affected. Most features continue to work."
        elif SystemStatus.SLOW in statuses:
            indicator = "yellow"
            message = "Running Slow Today"
            detail = "We're aware things are slower than usual. Thank you for your patience."
        elif SystemStatus.MAINTENANCE in statuses:
            indicator = "blue"
            message = "Scheduled Maintenance"
            detail = "Planned maintenance in progress. Service will resume shortly."
        else:
            indicator = "yellow"
            message = "Degraded Performance"
            detail = "Some features may be slower. We're working on it."

    return {
        "indicator": indicator,
        "message": message,
        "detail": detail,
        "issue_count": len(active_issues),
        "issues": [
            {
                "title": issue.title,
                "component": issue.component,
                "status": issue.status,
                "patron_message": issue.patron_message or issue.description,
                "estimated_fix_time": issue.estimated_fix_time.isoformat() if issue.estimated_fix_time else None,
            }
            for issue in active_issues
        ],
    }


@router.get("/system-status/recent-recoveries", tags=["system-status"])
async def get_recent_recoveries(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recently resolved issues - the 'we're back' list.

    Shows patrons and staff what was fixed recently so they know
    things are working again.
    """
    from datetime import timedelta
    cutoff = utc_now() - timedelta(hours=hours)
    # Convert to naive datetime for database comparison with TIMESTAMP WITHOUT TIME ZONE
    if cutoff.tzinfo is not None:
        cutoff = cutoff.replace(tzinfo=None)

    result = await db.execute(
        select(SystemStatusLog).where(
            and_(
                SystemStatusLog.resolved_at.isnot(None),
                SystemStatusLog.resolved_at >= cutoff,
                SystemStatusLog.is_public == True,
            )
        ).order_by(desc(SystemStatusLog.resolved_at))
    )
    resolved_issues = result.scalars().all()

    return {
        "recoveries": [
            {
                "id": issue.id,
                "title": issue.title,
                "component": issue.component,
                "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
                "resolution_notes": issue.resolution_notes,
                "duration_minutes": (
                    int((issue.resolved_at - issue.started_at).total_seconds() / 60)
                    if issue.resolved_at and issue.started_at else None
                ),
            }
            for issue in resolved_issues
        ],
        "message": (
            "All clear! No recent issues." if not resolved_issues
            else f"{len(resolved_issues)} issue(s) resolved in the last {hours} hours."
        ),
    }


# ---------------------------------------------------------------------------
# Staff endpoints - issue management
# ---------------------------------------------------------------------------

@router.post("/system-status/issues", tags=["system-status"])
async def report_issue(
    request: ReportIssueRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Report a new system issue (staff only).

    Automatically generates a patron-friendly message if none is provided.
    Staff are notified immediately so they're prepared before patrons ask.
    """
    # Generate patron-friendly message if not provided
    patron_message = request.patron_message
    if not patron_message:
        patron_message = _generate_patron_message(request.status, request.component, request.title)

    issue = SystemStatusLog(
        organization_id=getattr(current_user, 'organization_id', 1),
        status=request.status,
        component=request.component,
        title=request.title,
        description=request.description,
        patron_message=patron_message,
        technical_details=request.technical_details,
        estimated_fix_time=request.estimated_fix_time,
        is_scheduled=request.is_scheduled,
        is_public=request.is_public,
        available_features=request.available_features,
        degraded_features=request.degraded_features,
        offline_alternatives=request.offline_alternatives,
        reported_by_id=current_user.id,
        notified_staff=True,
        staff_notified_at=utc_now(),
    )

    db.add(issue)
    await db.commit()
    await db.refresh(issue)

    # Create staff notification
    notification = StaffStatusNotification(
        organization_id=getattr(current_user, 'organization_id', 1),
        issue_id=issue.id,
        notification_type=_get_notification_type(request.status),
        title=f"System Alert: {request.title}",
        message=request.description,
        patron_talking_points=_generate_talking_points(request.status, request.component, request.title),
        workaround_instructions=_generate_workaround(request.status, request.component),
        channels=["dashboard"],
        sent_at=utc_now(),
    )
    db.add(notification)
    await db.commit()

    return {
        "message": "Issue reported and staff notified",
        "issue": {
            "id": issue.id,
            "status": issue.status,
            "component": issue.component,
            "title": issue.title,
            "started_at": issue.started_at.isoformat() if issue.started_at else None,
            "estimated_fix_time": issue.estimated_fix_time.isoformat() if issue.estimated_fix_time else None,
        },
    }


@router.put("/system-status/issues/{issue_id}", tags=["system-status"])
async def update_issue(
    issue_id: int,
    request: UpdateIssueRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update an existing issue with new information (staff only)."""
    issue = await get_or_404(db, SystemStatusLog, issue_id, "Issue not found")

    if request.status is not None:
        issue.status = request.status
    if request.description is not None:
        issue.description = request.description
    if request.estimated_fix_time is not None:
        issue.estimated_fix_time = request.estimated_fix_time
    if request.patron_message is not None:
        issue.patron_message = request.patron_message
    if request.technical_details is not None:
        issue.technical_details = request.technical_details
    if request.available_features is not None:
        issue.available_features = request.available_features
    if request.degraded_features is not None:
        issue.degraded_features = request.degraded_features

    await db.commit()

    # Notify staff of update
    notification = StaffStatusNotification(
        organization_id=getattr(current_user, 'organization_id', 1),
        issue_id=issue.id,
        notification_type=StaffNotificationType.ISSUE_UPDATED,
        title=f"Updated: {issue.title}",
        message=f"Issue updated by {current_user.first_name}. {request.description or ''}",
        channels=["dashboard"],
        sent_at=utc_now(),
    )
    db.add(notification)
    await db.commit()

    return {"message": "Issue updated", "issue_id": issue_id}


@router.post("/system-status/issues/{issue_id}/resolve", tags=["system-status"])
async def resolve_issue(
    issue_id: int,
    request: ResolveIssueRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Mark an issue as resolved and optionally send 'we're back' alert (staff only).

    When send_recovery_alert is True, staff and patrons are notified
    that the issue is resolved and things are back to normal.
    """
    issue = await get_or_404(db, SystemStatusLog, issue_id, "Issue not found")

    # resolved_at is a naive DateTime column; strip tzinfo so asyncpg can
    # bind it to TIMESTAMP WITHOUT TIME ZONE.
    issue.resolved_at = utc_now().replace(tzinfo=None)
    issue.resolution_notes = request.resolution_notes
    issue.resolved_by_id = current_user.id

    if request.send_recovery_alert:
        issue.recovery_alert_sent = True
        issue.recovery_alert_sent_at = utc_now()

        # Create "we're back" notification
        duration = ""
        if issue.started_at:
            minutes = int((utc_now() - issue.started_at).total_seconds() / 60)
            if minutes < 60:
                duration = f" (resolved in {minutes} minutes)"
            else:
                hours = minutes // 60
                duration = f" (resolved in {hours} hour{'s' if hours != 1 else ''})"

        notification = StaffStatusNotification(
            organization_id=getattr(current_user, 'organization_id', 1),
            issue_id=issue.id,
            notification_type=StaffNotificationType.RECOVERY_COMPLETE,
            title=f"Resolved: {issue.title}",
            message=f"The issue has been resolved{duration}. All systems are back to normal.",
            patron_talking_points="Good news - the system is back up and running normally. "
                                 "We apologize for any inconvenience.",
            channels=["dashboard"],
            sent_at=utc_now(),
        )
        db.add(notification)

    await db.commit()

    return {
        "message": "Issue resolved" + (" - recovery alert sent" if request.send_recovery_alert else ""),
        "issue_id": issue_id,
        "resolved_at": issue.resolved_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Staff notifications
# ---------------------------------------------------------------------------

@router.get("/system-status/staff-notifications", tags=["system-status"])
async def get_staff_notifications(
    unacknowledged_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get system status notifications for staff.

    Staff are always notified before patrons ask, so they can
    proactively help and never feel blindsided by questions about outages.
    """
    query = select(StaffStatusNotification).order_by(
        desc(StaffStatusNotification.id)
    ).limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()

    if unacknowledged_only:
        notifications = [
            n for n in notifications
            if not n.acknowledged_by or current_user.id not in n.acknowledged_by
        ]

    return {
        "notifications": [
            {
                "id": n.id,
                "type": n.notification_type,
                "title": n.title,
                "message": n.message,
                "patron_talking_points": n.patron_talking_points,
                "workaround_instructions": n.workaround_instructions,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "acknowledged": (
                    n.acknowledged_by and current_user.id in n.acknowledged_by
                ) if n.acknowledged_by else False,
            }
            for n in notifications
        ],
    }


@router.post("/system-status/staff-notifications/{notification_id}/acknowledge", tags=["system-status"])
async def acknowledge_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Acknowledge a staff notification (staff only)."""
    notification = await get_or_404(db, StaffStatusNotification, notification_id, "Notification not found")

    acknowledged = notification.acknowledged_by or []
    if current_user.id not in acknowledged:
        acknowledged.append(current_user.id)
        notification.acknowledged_by = acknowledged
        await db.commit()

    return {"message": "Notification acknowledged", "notification_id": notification_id}


# ---------------------------------------------------------------------------
# Health metrics
# ---------------------------------------------------------------------------

@router.get("/system-status/health-metrics", tags=["system-status"])
async def get_health_metrics(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get recent health metrics (staff only).

    Provides real-time system health data so staff can see exactly
    what's happening - no mystery, no guessing.
    """
    result = await db.execute(
        select(SystemHealthMetrics)
        .order_by(SystemHealthMetrics.recorded_at.desc())
        .limit(limit)
    )
    metrics = result.scalars().all()

    return {
        "metrics": [
            {
                "recorded_at": m.recorded_at.isoformat() if m.recorded_at else None,
                "response_time_p50_ms": m.response_time_p50_ms,
                "response_time_p95_ms": m.response_time_p95_ms,
                "response_time_p99_ms": m.response_time_p99_ms,
                "cpu_usage_percent": m.cpu_usage_percent,
                "memory_usage_percent": m.memory_usage_percent,
                "disk_usage_percent": m.disk_usage_percent,
                "db_connection_pool_used": m.db_connection_pool_used,
                "db_connection_pool_available": m.db_connection_pool_available,
                "db_query_latency_ms": m.db_query_latency_ms,
                "cache_hit_rate_percent": m.cache_hit_rate_percent,
                "cache_latency_ms": m.cache_latency_ms,
                "error_rate_percent": m.error_rate_percent,
                "is_degraded": m.is_degraded,
                "is_slow": m.is_slow,
                "slow_reason": m.slow_reason,
            }
            for m in metrics
        ],
    }


@router.get("/system-status/health-summary", tags=["system-status"])
async def get_health_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Quick health summary for the status banner (public).

    Returns a simple, honest summary that can be displayed on every page.
    """
    # Get the latest metric
    result = await db.execute(
        select(SystemHealthMetrics)
        .order_by(SystemHealthMetrics.recorded_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()

    # Get active issues count
    result = await db.execute(
        select(SystemStatusLog).where(
            and_(
                SystemStatusLog.resolved_at.is_(None),
                SystemStatusLog.is_public == True,
            )
        )
    )
    active_issues = result.scalars().all()

    is_slow = latest.is_slow if latest else False
    is_degraded = latest.is_degraded if latest else False
    has_outage = any(
        i.status in [SystemStatus.MAJOR_OUTAGE, SystemStatus.PARTIAL_OUTAGE]
        for i in active_issues
    )

    if has_outage:
        health = "outage"
        message = "Some services are currently unavailable. Staff can assist with alternatives."
    elif is_slow:
        health = "slow"
        message = f"Running slow today{': ' + latest.slow_reason if latest and latest.slow_reason else ''}. We're working on it."
    elif is_degraded:
        health = "degraded"
        message = "Performance is below normal. We're aware and investigating."
    else:
        health = "healthy"
        message = "All systems operational."

    return {
        "health": health,
        "message": message,
        "active_issue_count": len(active_issues),
        "response_time_ms": latest.response_time_p95_ms if latest else None,
        "last_checked": latest.recorded_at.isoformat() if latest and latest.recorded_at else None,
    }


# ---------------------------------------------------------------------------
# Paper backup procedures
# ---------------------------------------------------------------------------

@router.get("/system-status/paper-backups", tags=["system-status"])
async def get_paper_backups(
    component: Optional[IssueComponent] = None,
    backup_type: Optional[PaperBackupType] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get paper backup procedures (staff only).

    When technology fails, library service doesn't stop. These are
    the printable forms and manual procedures that keep things running.
    """
    query = select(PaperBackupProcedure).where(PaperBackupProcedure.is_active == True)

    if backup_type:
        query = query.where(PaperBackupProcedure.backup_type == backup_type)

    result = await db.execute(query.order_by(PaperBackupProcedure.backup_type))
    procedures = result.scalars().all()

    # Filter by component if specified
    if component:
        procedures = [
            p for p in procedures
            if p.applicable_components and component.value in p.applicable_components
        ]

    return {
        "procedures": [
            {
                "id": p.id,
                "backup_type": p.backup_type,
                "title": p.title,
                "description": p.description,
                "instructions": p.instructions,
                "form_template": p.form_template,
                "trigger_conditions": p.trigger_conditions,
                "applicable_components": p.applicable_components,
                "version": p.version,
                "last_reviewed_at": p.last_reviewed_at.isoformat() if p.last_reviewed_at else None,
            }
            for p in procedures
        ],
    }


@router.post("/system-status/paper-backups", tags=["system-status"])
async def create_paper_backup(
    request: PaperBackupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new paper backup procedure (admin only)."""
    procedure = PaperBackupProcedure(
        organization_id=getattr(current_user, 'organization_id', 1),
        backup_type=request.backup_type,
        title=request.title,
        description=request.description,
        instructions=request.instructions,
        form_template=request.form_template,
        trigger_conditions=request.trigger_conditions,
        applicable_components=request.applicable_components,
        reviewed_by_id=current_user.id,
        last_reviewed_at=utc_now(),
    )
    db.add(procedure)
    await db.commit()
    await db.refresh(procedure)

    return {
        "message": "Paper backup procedure created",
        "procedure": {
            "id": procedure.id,
            "backup_type": procedure.backup_type,
            "title": procedure.title,
        },
    }


@router.get("/system-status/paper-backups/{procedure_id}/print", tags=["system-status"])
async def get_printable_form(
    procedure_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get a printable version of a paper backup form (staff only).

    Returns the form template ready for printing so staff can
    immediately switch to paper procedures during an outage.
    """
    procedure = await get_or_404(db, PaperBackupProcedure, procedure_id, "Procedure not found")

    return {
        "title": procedure.title,
        "instructions": procedure.instructions,
        "form_template": procedure.form_template,
        "backup_type": procedure.backup_type,
        "version": procedure.version,
        "print_date": utc_now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Offline mode
# ---------------------------------------------------------------------------

@router.post("/system-status/offline-mode/start", tags=["system-status"])
async def start_offline_mode(
    reason: str = "",
    issue_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Start an offline mode session (staff only).

    When connectivity is lost or the system is down, staff can activate
    offline mode. All work is tracked for sync when connectivity returns.
    """
    session = OfflineModeSession(
        organization_id=getattr(current_user, 'organization_id', 1),
        started_by_id=current_user.id,
        trigger_issue_id=issue_id,
        trigger_reason=reason or "Manual activation by staff",
    )
    db.add(session)

    # Create staff notification
    notification = StaffStatusNotification(
        organization_id=getattr(current_user, 'organization_id', 1),
        issue_id=issue_id,
        notification_type=StaffNotificationType.OFFLINE_MODE_ACTIVATED,
        title="Offline Mode Activated",
        message=f"Offline mode activated by {current_user.first_name}. "
                "Use paper backup procedures for transactions. "
                "All work will sync when connectivity returns.",
        patron_talking_points="Our computer system is temporarily offline, but we can still "
                             "help you! We have paper forms for checkouts, returns, and other services.",
        workaround_instructions="Use paper backup forms from the front desk. "
                               "Record all transactions for later entry.",
        channels=["dashboard"],
        sent_at=utc_now(),
    )
    db.add(notification)

    await db.commit()
    await db.refresh(session)

    return {
        "message": "Offline mode activated",
        "session_id": session.id,
        "started_at": session.started_at.isoformat() if session.started_at else None,
    }


@router.post("/system-status/offline-mode/{session_id}/end", tags=["system-status"])
async def end_offline_mode(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """End an offline mode session and begin sync (staff only)."""
    session = await get_or_404(db, OfflineModeSession, session_id, "Offline session not found")

    session.ended_at = utc_now()

    # Create notification
    notification = StaffStatusNotification(
        organization_id=getattr(current_user, 'organization_id', 1),
        notification_type=StaffNotificationType.OFFLINE_MODE_DEACTIVATED,
        title="Offline Mode Ended - Systems Back Online",
        message="Connectivity restored. Please enter any paper transactions into the system. "
                "Auto-saved data will sync automatically.",
        channels=["dashboard"],
        sent_at=utc_now(),
    )
    db.add(notification)

    await db.commit()

    return {
        "message": "Offline mode ended",
        "session_id": session_id,
        "duration_minutes": (
            int((session.ended_at - session.started_at).total_seconds() / 60)
            if session.started_at else None
        ),
    }


@router.get("/system-status/offline-mode/active", tags=["system-status"])
async def get_active_offline_session(
    db: AsyncSession = Depends(get_db),
):
    """Check if offline mode is currently active (public)."""
    result = await db.execute(
        select(OfflineModeSession).where(
            OfflineModeSession.ended_at.is_(None)
        ).order_by(desc(OfflineModeSession.started_at)).limit(1)
    )
    session = result.scalar_one_or_none()

    if not session:
        return {"offline_mode_active": False}

    return {
        "offline_mode_active": True,
        "session_id": session.id,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "reason": session.trigger_reason,
        "pending_transactions": session.pending_transactions,
    }


# ---------------------------------------------------------------------------
# Auto-save
# ---------------------------------------------------------------------------

@router.post("/system-status/auto-save", tags=["system-status"])
async def auto_save(
    request: AutoSaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Auto-save work in progress.

    Everything is saved automatically so no one ever loses work.
    Replaces any existing auto-save for the same context.
    """
    # Check for existing auto-save for this context
    result = await db.execute(
        select(AutoSaveEntry).where(
            and_(
                AutoSaveEntry.user_id == current_user.id,
                AutoSaveEntry.context_type == request.context_type,
                AutoSaveEntry.context_id == request.context_id,
                AutoSaveEntry.recovered == False,
                AutoSaveEntry.expired == False,
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.saved_data = request.saved_data
        existing.saved_at = utc_now()
    else:
        entry = AutoSaveEntry(
            user_id=current_user.id,
            context_type=request.context_type,
            context_id=request.context_id,
            saved_data=request.saved_data,
        )
        db.add(entry)

    await db.commit()

    return {"message": "Auto-saved", "context_type": request.context_type}


@router.get("/system-status/auto-save/recover", tags=["system-status"])
async def recover_auto_saves(
    context_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recover auto-saved work for the current user.

    After a crash or outage, users can recover exactly where they left off.
    """
    query = select(AutoSaveEntry).where(
        and_(
            AutoSaveEntry.user_id == current_user.id,
            AutoSaveEntry.recovered == False,
            AutoSaveEntry.expired == False,
        )
    )

    if context_type:
        query = query.where(AutoSaveEntry.context_type == context_type)

    result = await db.execute(query.order_by(desc(AutoSaveEntry.saved_at)))
    entries = result.scalars().all()

    return {
        "recoverable_items": [
            {
                "id": e.id,
                "context_type": e.context_type,
                "context_id": e.context_id,
                "saved_data": e.saved_data,
                "saved_at": e.saved_at.isoformat() if e.saved_at else None,
            }
            for e in entries
        ],
    }


@router.post("/system-status/auto-save/{entry_id}/mark-recovered", tags=["system-status"])
async def mark_auto_save_recovered(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an auto-save entry as recovered (already restored by the user)."""
    result = await db.execute(
        select(AutoSaveEntry).where(
            and_(
                AutoSaveEntry.id == entry_id,
                AutoSaveEntry.user_id == current_user.id,
            )
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Auto-save entry not found")

    entry.recovered = True
    entry.recovered_at = utc_now()
    await db.commit()

    return {"message": "Auto-save marked as recovered", "entry_id": entry_id}


# ---------------------------------------------------------------------------
# Graceful degradation info
# ---------------------------------------------------------------------------

@router.get("/system-status/degradation-info", tags=["system-status"])
async def get_degradation_info(
    db: AsyncSession = Depends(get_db),
):
    """
    Get current graceful degradation status (public).

    Tells users exactly what works and what doesn't right now.
    No false promises, no vague 'experiencing issues' messages.
    """
    result = await db.execute(
        select(SystemStatusLog).where(
            SystemStatusLog.resolved_at.is_(None)
        ).order_by(SystemStatusLog.started_at.desc())
    )
    active_issues = result.scalars().all()

    if not active_issues:
        return {
            "degraded": False,
            "all_features_available": True,
            "message": "Everything is working normally.",
            "features": {},
        }

    # Build feature availability map
    all_degraded = set()
    all_available = set()
    all_alternatives = {}

    for issue in active_issues:
        if issue.degraded_features:
            all_degraded.update(issue.degraded_features)
        if issue.available_features:
            all_available.update(issue.available_features)
        if issue.offline_alternatives:
            for alt in issue.offline_alternatives:
                if isinstance(alt, dict):
                    all_alternatives[alt.get("feature", "")] = alt.get("alternative", "")

    return {
        "degraded": True,
        "all_features_available": False,
        "message": "Some features are affected. Here's what's working and what's not.",
        "degraded_features": list(all_degraded),
        "available_features": list(all_available),
        "alternatives": all_alternatives,
    }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _generate_patron_message(status: SystemStatus, component: Optional[IssueComponent], title: str) -> str:
    if status == SystemStatus.MAJOR_OUTAGE:
        return (
            "We're having a technical issue that's affecting our services. "
            "Our staff can help you with paper forms in the meantime. "
            "We're working to fix this as quickly as possible."
        )
    elif status == SystemStatus.PARTIAL_OUTAGE:
        component_name = _friendly_component_name(component)
        return (
            f"Our {component_name} is temporarily unavailable. "
            "Most other services are working normally. "
            "Please ask a staff member if you need help."
        )
    elif status == SystemStatus.SLOW:
        return (
            "Things are running slower than usual today. "
            "We're aware of it and working to speed things up. "
            "Thank you for your patience."
        )
    elif status == SystemStatus.DEGRADED:
        return (
            "Some features may be slower than normal right now. "
            "We're working on it. Please ask staff if you need assistance."
        )
    elif status == SystemStatus.MAINTENANCE:
        return (
            "We're doing some planned maintenance to improve our systems. "
            "Service will be back to normal shortly."
        )
    return f"We're experiencing a technical issue: {title}. Our team is working on it."


def _friendly_component_name(component: Optional[IssueComponent]) -> str:
    if not component:
        return "system"
    friendly_names = {
        IssueComponent.DATABASE: "catalog system",
        IssueComponent.CACHE: "system",
        IssueComponent.SEARCH: "search feature",
        IssueComponent.CIRCULATION: "checkout and returns system",
        IssueComponent.CATALOG: "book catalog",
        IssueComponent.AUTHENTICATION: "login system",
        IssueComponent.API: "system",
        IssueComponent.FRONTEND: "website",
        IssueComponent.PAYMENT_GATEWAY: "payment system",
        IssueComponent.EMAIL: "email notifications",
        IssueComponent.SMS: "text message notifications",
        IssueComponent.PRINTING: "printing service",
        IssueComponent.RFID: "self-checkout system",
        IssueComponent.NETWORK: "internet connection",
        IssueComponent.SELF_CHECKOUT: "self-checkout kiosk",
    }
    return friendly_names.get(component, "system")


def _get_notification_type(status: SystemStatus) -> StaffNotificationType:
    if status in [SystemStatus.MAJOR_OUTAGE, SystemStatus.PARTIAL_OUTAGE]:
        return StaffNotificationType.OUTAGE_ALERT
    elif status == SystemStatus.SLOW:
        return StaffNotificationType.DEGRADATION_WARNING
    elif status == SystemStatus.DEGRADED:
        return StaffNotificationType.DEGRADATION_WARNING
    elif status == SystemStatus.MAINTENANCE:
        return StaffNotificationType.MAINTENANCE_STARTING
    return StaffNotificationType.ISSUE_DETECTED


def _generate_talking_points(status: SystemStatus, component: Optional[IssueComponent], title: str) -> str:
    component_name = _friendly_component_name(component)

    if status == SystemStatus.MAJOR_OUTAGE:
        return (
            f"If patrons ask: 'Our {component_name} is temporarily down. "
            "This is a technical issue, not anything anyone did wrong. "
            "We can help you with paper forms right now, and everything "
            "will be entered into the system once it's back up.'"
        )
    elif status == SystemStatus.SLOW:
        return (
            "If patrons notice slowness: 'Yes, things are running a bit slow today. "
            "Our tech team knows about it and is working on it. "
            "Thank you for being patient with us.'"
        )
    elif status == SystemStatus.MAINTENANCE:
        return (
            "If patrons ask: 'We're doing some planned improvements to our system. "
            "It should be back shortly. I can help you with anything you need in the meantime.'"
        )
    return (
        f"If patrons notice issues: 'We're aware of a technical issue with our {component_name}. "
        "Our team is working on it. How can I help you right now?'"
    )


def _generate_workaround(status: SystemStatus, component: Optional[IssueComponent]) -> str:
    workarounds = {
        IssueComponent.CIRCULATION: "Use paper checkout forms. Record patron card number, item barcodes, and date. Enter into system when restored.",
        IssueComponent.CATALOG: "Use printed catalog reference sheets. Check shelf directly for availability.",
        IssueComponent.AUTHENTICATION: "Use manual patron verification (library card + photo ID). Note transactions for later entry.",
        IssueComponent.SEARCH: "Help patrons search by browsing shelves. Use printed catalog reference sheets.",
        IssueComponent.PRINTING: "Note print requests for processing when printing is restored.",
        IssueComponent.RFID: "Process all checkouts at the desk. Self-checkout is temporarily unavailable.",
        IssueComponent.PAYMENT_GATEWAY: "Accept cash payments only. Note card payments for later processing.",
        IssueComponent.SELF_CHECKOUT: "Direct patrons to the circulation desk for checkout.",
    }

    if component and component in workarounds:
        return workarounds[component]

    if status == SystemStatus.MAJOR_OUTAGE:
        return "Switch to paper backup procedures for all transactions. Retrieve forms from the backup supplies."

    return "Continue with available features. Use paper forms if needed."

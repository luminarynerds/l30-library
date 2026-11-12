# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Admin Monitoring and Alerting API Endpoints.

Provides endpoints for:
- Privacy change monitoring and alerts
- Moderation queue status and metrics
- HTTP 405 Method Not Allowed error tracking
- System health checks
- Alert management and acknowledgment

Requires admin authentication for all endpoints.
"""

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...core.performance_monitoring import get_monitor
from ...models.monitoring import (
    MonitoringAlertSeverity, AlertThreshold, ModerationAlert, PrivacyAlert,
    PrivacyChangeType, SystemHealth
)
from ...models.user import User, UserRole
from ...services.monitoring_service import (
    ModerationMonitoringService, PrivacyMonitoringService,
    SystemHealthService
)
from ...services.http_405_monitoring_service import HTTP405MonitoringService
from ...services.alert_notification_service import AlertNotificationService
from .auth import get_current_user
from .auth import get_current_user

logger = get_logger(__name__)
router = APIRouter(prefix="/admin/monitoring", tags=["admin-monitoring"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class AlertResponse(BaseModel):
    id: int
    severity: str
    description: str
    detected_at: datetime
    is_acknowledged: bool

    class Config:
        from_attributes = True


class PrivacyAlertResponse(AlertResponse):
    user_id: int
    alert_type: str
    change_count: int
    time_window_minutes: int
    resource_type: Optional[str] = None


class PrivacyAlertsResponse(BaseModel):
    total_alerts: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    alerts: List[PrivacyAlertResponse]


class ModerationAlertResponse(AlertResponse):
    alert_type: str
    pending_count: int
    overdue_count: int
    oldest_item_age_hours: int
    average_turnaround_hours: float


class ModerationQueueItem(BaseModel):
    type: str          # Type of item (event, book, etc.)
    count: int         # Number of items
    oldest_age_hours: int


class ModerationQueueStatus(BaseModel):
    pending: int
    approved: int
    rejected: int
    total_processed: int
    average_turnaround_hours: float
    oldest_pending_hours: int
    alerts: List[ModerationAlertResponse] = []


class SystemHealthMetric(BaseModel):
    name: str
    value: float
    unit: str
    status: str  # healthy, degraded, unhealthy
    threshold: Optional[float] = None


class SystemHealthSnapshot(BaseModel):
    status: str  # healthy, degraded, unhealthy
    status_reason: str
    share_events_last_hour: int
    share_events_last_24h: int
    db_connection_active: int
    db_connection_idle: int
    db_slow_queries: int
    db_query_avg_time_ms: float
    error_count_last_hour: int
    error_count_last_24h: int
    error_rate_percent: float
    api_response_p50_ms: float
    api_response_p95_ms: float
    api_response_p99_ms: float
    cache_hit_rate_percent: float
    created_at: datetime

    class Config:
        from_attributes = True


class SystemHealthResponse(BaseModel):
    current: Optional[SystemHealthSnapshot] = None
    trend_24h: List[SystemHealthSnapshot] = []


class MemoryEndpointMetric(BaseModel):
    endpoint: str
    method: str
    count: int
    avg_delta_bytes: float
    avg_delta_mb: Optional[float]
    min_delta_bytes: float
    min_delta_mb: Optional[float]
    max_delta_bytes: int
    max_delta_mb: Optional[float]
    max_peak_bytes: int
    max_peak_mb: Optional[float]
    p95_delta_bytes: Optional[float] = None
    p95_delta_mb: Optional[float] = None
    p99_delta_bytes: Optional[float] = None
    p99_delta_mb: Optional[float] = None
    error_count: int


class MemoryProfileResponse(BaseModel):
    total_tracked: int
    top_endpoints: List[MemoryEndpointMetric]
    focus_endpoints: List[MemoryEndpointMetric]


# ============================================================================
# HTTP 405 Error Monitoring Schemas
# ============================================================================

class ErrorEndpointMetric(BaseModel):
    endpoint: str
    method: str
    path: str
    error_count: int
    last_error: Optional[str] = None
    client_ips: List[str] = []
    sample_user_agents: List[str] = []


class ProblematicClientMetric(BaseModel):
    client_ip: str
    error_count: int
    unique_endpoints_tried: int
    unique_user_agents: int
    last_error: Optional[str] = None
    first_error: Optional[str] = None
    suspected_pattern: str


class ErrorTrendEntry(BaseModel):
    timestamp: str
    count: int


class HTTP405AlertStatus(BaseModel):
    status: str  # "ok", "warning", "firing"
    severity: str  # "low", "medium", "high", "critical"
    errors_last_hour: int
    threshold: int
    should_alert: bool
    alert_message: str


class HTTP405Summary(BaseModel):
    total_errors_24h: int
    total_errors_1h: int
    error_rate_per_hour: float
    peak_hour: Optional[str] = None
    unique_endpoints: int
    unique_clients: int


class HTTP405Metrics(BaseModel):
    summary: HTTP405Summary
    alert_status: HTTP405AlertStatus
    top_endpoints: List[ErrorEndpointMetric]
    problematic_clients: List[ProblematicClientMetric]


class HTTP405DebugContext(BaseModel):
    endpoint: str
    error_count: int
    first_occurrence: Optional[str] = None
    last_occurrence: Optional[str] = None
    client_ips: List[str] = []
    user_agents: List[str] = []
    user_ids_affected: List[int] = []
    sample_errors: List[Dict[str, Any]] = []
    remediation_suggestions: List[str] = []
    message: Optional[str] = None


class HTTP405HealthCheck(BaseModel):
    system_status: str
    events_tracked: int
    max_capacity: int
    capacity_utilization_percent: float
    total_unique_endpoints: int
    total_unique_clients: int
    errors_24h: int
    error_rate_per_hour: float


class AlertAcknowledgmentRequest(BaseModel):
    notes: Optional[str] = None


class AlertThresholdUpdate(BaseModel):
    warning_level: int = Field(..., ge=0)
    critical_level: int = Field(..., ge=0)
    enabled: bool = True


# ============================================================================
# Dependencies
# ============================================================================

async def _verify_admin_access(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR):
        logger.warning(
            "Unauthorized admin access attempt",
            extra={
                "user_id": current_user.id,
                "user_role": current_user.role,
                "endpoint": "monitoring",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


# ============================================================================
# Privacy Alerts Endpoints
# ============================================================================

@router.get(
    "/privacy-alerts",
    response_model=PrivacyAlertsResponse,
    summary="Get privacy change alerts",
    description="Retrieve alerts for suspicious privacy change patterns"
)
async def get_privacy_alerts(
    unacknowledged_only: bool = Query(False),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> PrivacyAlertsResponse:
    """
    Get privacy change alerts.

    Returns alerts for:
    - Bulk privacy changes (5+ changes in 1 hour)
    - Rapid toggle patterns
    - Large-scale public content changes (50+ items)
    - Suspicious visibility changes
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    query = select(PrivacyAlert).where(
        PrivacyAlert.detected_at >= cutoff_time
    )

    if unacknowledged_only:
        query = query.where(PrivacyAlert.is_acknowledged == False)

    query = query.order_by(
        PrivacyAlert.severity.desc(),
        PrivacyAlert.detected_at.desc()
    ).offset(offset).limit(limit)

    result = await db.execute(query)
    alerts = result.scalars().all()

    # Count by severity
    count_query = (
        select(PrivacyAlert.severity, func.count(PrivacyAlert.id))
        .where(PrivacyAlert.detected_at >= cutoff_time)
        .group_by(PrivacyAlert.severity)
    )
    count_result = await db.execute(count_query)
    severity_counts = {
        MonitoringAlertSeverity.CRITICAL: 0,
        MonitoringAlertSeverity.HIGH: 0,
        MonitoringAlertSeverity.MEDIUM: 0,
        MonitoringAlertSeverity.LOW: 0,
    }
    total_alerts = 0
    for severity, count in count_result.all():
        severity_counts[severity] = count
        total_alerts += count

    return PrivacyAlertsResponse(
        total_alerts=total_alerts,
        critical_alerts=severity_counts[MonitoringAlertSeverity.CRITICAL],
        high_alerts=severity_counts[MonitoringAlertSeverity.HIGH],
        medium_alerts=severity_counts[MonitoringAlertSeverity.MEDIUM],
        low_alerts=severity_counts[MonitoringAlertSeverity.LOW],
        alerts=[PrivacyAlertResponse.model_validate(a) for a in alerts]
    )


@router.post(
    "/privacy-alerts/{alert_id}/acknowledge",
    summary="Acknowledge a privacy alert"
)
async def acknowledge_privacy_alert(
    alert_id: int,
    request: AlertAcknowledgmentRequest,
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Acknowledge and mark a privacy alert as reviewed."""
    alert = await get_or_404(db, PrivacyAlert, alert_id, "Alert not found")

    alert.is_acknowledged = True
    alert.acknowledged_by_id = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledgment_notes = request.notes

    await db.commit()

    logger.info(
        "Privacy alert acknowledged",
        extra={"alert_id": alert_id, "user_id": current_user.id}
    )

    return {"message": "Alert acknowledged", "alert_id": alert_id}


# ============================================================================
# Moderation Queue Endpoints
# ============================================================================

@router.get(
    "/moderation-queue-status",
    response_model=ModerationQueueStatus,
    summary="Get moderation queue status"
)
async def get_moderation_queue_status(
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> ModerationQueueStatus:
    """Get comprehensive moderation queue status."""
    service = ModerationMonitoringService(db)

    status = await service.get_moderation_queue_status()

    # Check for active alerts
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    alert_result = await db.execute(
        select(ModerationAlert).where(
            and_(
                ModerationAlert.triggered_at >= cutoff,
                ModerationAlert.is_resolved == False
            )
        ).order_by(desc(ModerationAlert.severity))
    )
    alerts = alert_result.scalars().all()

    return ModerationQueueStatus(
        pending=status["pending"],
        approved=status["approved"],
        rejected=status["rejected"],
        total_processed=status["total_processed"],
        average_turnaround_hours=status["average_turnaround_hours"],
        oldest_pending_hours=status["oldest_pending_hours"],
        alerts=[
            ModerationAlertResponse(
                id=a.id,
                severity=str(a.severity),
                alert_type=a.alert_type,
                description=a.description,
                pending_count=a.pending_count,
                overdue_count=a.overdue_count,
                oldest_item_age_hours=a.oldest_item_age_hours,
                average_turnaround_hours=a.average_turnaround_hours,
                detected_at=a.triggered_at,
                is_acknowledged=a.is_resolved
            )
            for a in alerts
        ]
    )


@router.post(
    "/moderation-alerts/{alert_id}/resolve",
    summary="Resolve a moderation alert"
)
async def resolve_moderation_alert(
    alert_id: int,
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Mark a moderation alert as resolved."""
    alert = await get_or_404(db, ModerationAlert, alert_id, "Alert not found")

    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by_id = current_user.id

    await db.commit()

    logger.info(
        "Moderation alert resolved",
        extra={"alert_id": alert_id, "user_id": current_user.id}
    )

    return {"message": "Alert resolved", "alert_id": alert_id}


# ============================================================================
# System Health Endpoints
# ============================================================================

@router.get(
    "/system-health",
    response_model=SystemHealthResponse,
    summary="Get system health status"
)
async def get_system_health(
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> SystemHealthResponse:
    """
    Get system health metrics.

    Includes:
    - Database connection pool status
    - Share event tracking metrics
    - Error rates
    - API performance percentiles
    """
    service = SystemHealthService(db)
    current_health = await service.get_system_health()
    trend = await service.get_recent_health_history(hours=24)

    return SystemHealthResponse(
        current=SystemHealthSnapshot.model_validate(current_health),
        trend_24h=[SystemHealthSnapshot.model_validate(h) for h in trend]
    )


# ============================================================================
# Memory Profiling Endpoints
# ============================================================================

@router.get(
    "/memory-usage",
    response_model=MemoryProfileResponse,
    summary="Get endpoint memory allocation metrics",
)
async def get_memory_usage(
    limit: int = Query(20, ge=1, le=100),
    min_samples: int = Query(3, ge=1, le=1000),
    sort_by: str = Query("avg_delta_bytes", pattern="^(avg_delta_bytes|max_delta_bytes|max_peak_bytes)$"),
    current_user: User = Depends(_verify_admin_access),
) -> MemoryProfileResponse:
    """
    Get memory allocation metrics for endpoints.

    Focus list highlights common high-memory areas:
    - Catalog search
    - Reports
    - Bulk operations
    """
    monitor = get_monitor()
    focus_prefixes = [
        "/api/v1/catalog",
        "/api/v1/unified_search",
        "/api/v1/indie_discovery_search",
        "/api/v1/reports",
        "/api/v1/staff_reports",
        "/api/v1/financial_reports",
        "/api/v1/home_delivery_reports",
        "/api/v1/print_notices",
        "/api/v1/staff",
        "/api/v1/outreach",
        "/api/v1/patron_segmentation",
        "/api/v1/users",
    ]

    top_endpoints = monitor.get_top_memory_endpoints(
        limit=limit,
        min_samples=min_samples,
        sort_by=sort_by,
    )
    focus_endpoints = monitor.get_top_memory_endpoints(
        limit=limit,
        min_samples=min_samples,
        sort_by=sort_by,
        path_prefixes=focus_prefixes,
    )

    return MemoryProfileResponse(
        total_tracked=monitor.get_memory_endpoint_count(),
        top_endpoints=[MemoryEndpointMetric.model_validate(item) for item in top_endpoints],
        focus_endpoints=[MemoryEndpointMetric.model_validate(item) for item in focus_endpoints],
    )


# ============================================================================
# HTTP 405 Error Monitoring Endpoints
# ============================================================================

@router.get(
    "/http-405-metrics",
    response_model=HTTP405Metrics,
    summary="Get HTTP 405 error metrics",
    description="Comprehensive 405 error metrics including summary, alerts, top endpoints, and problematic clients"
)
async def get_http_405_metrics(
    current_user: User = Depends(_verify_admin_access),
) -> HTTP405Metrics:
    """
    Get comprehensive HTTP 405 error metrics.

    Returns:
    - Summary of 405 errors (24h, 1h, rate, peak)
    - Alert status and severity
    - Top 10 endpoints returning 405
    - Top 10 problematic clients
    """
    summary_data = HTTP405MonitoringService.get_errors_summary()
    alert_status = HTTP405MonitoringService.get_alert_status()
    top_endpoints = HTTP405MonitoringService.get_top_endpoints(limit=10)
    problematic_clients = HTTP405MonitoringService.get_problematic_clients(limit=10)

    summary = HTTP405Summary(**summary_data)
    alert = HTTP405AlertStatus(**alert_status)

    endpoints = [
        ErrorEndpointMetric(
            endpoint=ep["endpoint"],
            method=ep["method"],
            path=ep["path"],
            error_count=ep["error_count"],
            last_error=ep["last_error"],
            client_ips=ep["client_ips"],
            sample_user_agents=ep["sample_user_agents"],
        )
        for ep in top_endpoints
    ]

    clients = [
        ProblematicClientMetric(
            client_ip=c["client_ip"],
            error_count=c["error_count"],
            unique_endpoints_tried=c["unique_endpoints_tried"],
            unique_user_agents=c["unique_user_agents"],
            last_error=c["last_error"],
            first_error=c["first_error"],
            suspected_pattern=c["suspected_pattern"],
        )
        for c in problematic_clients
    ]

    return HTTP405Metrics(
        summary=summary,
        alert_status=alert,
        top_endpoints=endpoints,
        problematic_clients=clients,
    )


@router.get(
    "/http-405-trend",
    summary="Get HTTP 405 error trend over time"
)
async def get_http_405_trend(
    hours: int = Query(24, ge=1, le=168),
    bucket_minutes: int = Query(60, ge=5, le=1440),
    current_user: User = Depends(_verify_admin_access),
) -> Dict[str, Any]:
    """Get HTTP 405 error trend bucketed by time interval."""
    trend = HTTP405MonitoringService.get_error_trend(
        hours=hours,
        bucket_minutes=bucket_minutes
    )

    return {
        "hours": hours,
        "bucket_minutes": bucket_minutes,
        "buckets": [
            {
                "timestamp": timestamp,
                "count": count
            }
            for timestamp, count in trend.items()
        ]
    }


@router.get(
    "/http-405-debug/{method}/{path:path}",
    response_model=HTTP405DebugContext,
    summary="Get debugging context for 405 endpoint"
)
async def get_http_405_debug(
    method: str = Path(..., pattern="^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$"),
    path: str = Path(...),
    current_user: User = Depends(_verify_admin_access),
) -> HTTP405DebugContext:
    """
    Get detailed debugging context for a specific endpoint returning 405.

    Provides:
    - Error history and timestamps
    - Client IPs and user agents
    - Sample recent errors
    - Remediation suggestions
    """
    context = HTTP405MonitoringService.get_debugging_context(method, path)
    return HTTP405DebugContext(**context)


@router.get(
    "/http-405-health",
    response_model=HTTP405HealthCheck,
    summary="Get 405 monitoring system health"
)
async def get_http_405_health(
    current_user: User = Depends(_verify_admin_access),
) -> HTTP405HealthCheck:
    """Get health status of the 405 monitoring system."""
    health = HTTP405MonitoringService.get_health_check()
    return HTTP405HealthCheck(**health)


@router.post(
    "/http-405-test",
    summary="Test 405 monitoring (admin only)"
)
async def test_http_405_monitoring(
    current_user: User = Depends(_verify_admin_access),
) -> Dict[str, Any]:
    """
    Test endpoint that simulates a 405 error for testing monitoring.

    This endpoint is for testing purposes only and should only be callable
    by admin users.
    """
    # This endpoint will naturally return 405 since no method is defined
    # The middleware will catch and record it
    return {
        "message": "This endpoint should return 405",
        "testing": True
    }


# ============================================================================
# Alert Detection Endpoints
# ============================================================================

@router.post(
    "/check-privacy-alerts",
    summary="Manually trigger privacy alert check"
)
async def check_privacy_alerts(
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Manually trigger privacy alert detection."""
    try:
        service = PrivacyMonitoringService(db)
        alerts = await service.check_privacy_alerts()

        # Send notifications for high-severity alerts
        notification_service = AlertNotificationService(db)
        for alert in alerts:
            if alert.severity in (MonitoringAlertSeverity.HIGH, MonitoringAlertSeverity.CRITICAL):
                await notification_service.notify_privacy_alert(alert)

        logger.info(
            "Privacy alert check completed",
            extra={"alerts_detected": len(alerts), "user_id": current_user.id}
        )

        return {
            "message": "Privacy alert check completed",
            "alerts_detected": len(alerts),
            "high_severity": sum(1 for a in alerts if a.severity in (MonitoringAlertSeverity.HIGH, MonitoringAlertSeverity.CRITICAL))
        }
    except Exception as e:
        logger.error(f"Privacy alert check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Alert check failed"
        ) from e


@router.post(
    "/check-moderation-alerts",
    summary="Manually trigger moderation alert check"
)
async def check_moderation_alerts(
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Manually trigger moderation alert detection."""
    try:
        service = ModerationMonitoringService(db)
        alerts = await service.check_moderation_alerts()

        # Send notifications for high-severity alerts
        notification_service = AlertNotificationService(db)
        for alert in alerts:
            if alert.severity in (MonitoringAlertSeverity.HIGH, MonitoringAlertSeverity.CRITICAL):
                await notification_service.notify_moderation_alert(alert)

        logger.info(
            "Moderation alert check completed",
            extra={"alerts_detected": len(alerts), "user_id": current_user.id}
        )

        return {
            "message": "Moderation alert check completed",
            "alerts_detected": len(alerts),
            "high_severity": sum(1 for a in alerts if a.severity in (MonitoringAlertSeverity.HIGH, MonitoringAlertSeverity.CRITICAL))
        }
    except Exception as e:
        logger.error(f"Moderation alert check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Alert check failed"
        ) from e


@router.post(
    "/send-daily-digest",
    summary="Send daily alert digest"
)
async def send_daily_digest(
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Send daily digest of alerts to admin staff."""
    try:
        service = AlertNotificationService(db)
        success = await service.send_daily_digest()

        if success:
            logger.info(
                "Daily digest sent",
                extra={"user_id": current_user.id}
            )
            return {"message": "Daily digest sent successfully"}
        else:
            return {"message": "Daily digest send completed with warnings"}

    except Exception as e:
        logger.error(f"Failed to send daily digest: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Digest send failed"
        ) from e


# ============================================================================
# Alert Configuration Endpoints
# ============================================================================

@router.get(
    "/thresholds",
    summary="Get alert thresholds"
)
async def get_thresholds(
    category: Optional[str] = Query(None),
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get configured alert thresholds."""
    query = select(AlertThreshold)
    if category:
        query = query.where(AlertThreshold.category == category)

    result = await db.execute(query)
    thresholds = result.scalars().all()

    return {
        "thresholds": [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "warning_level": t.warning_level,
                "critical_level": t.critical_level,
                "time_window_minutes": t.time_window_minutes,
                "enabled": t.enabled,
            }
            for t in thresholds
        ]
    }


@router.put(
    "/thresholds/{threshold_id}",
    summary="Update alert threshold"
)
async def update_threshold(
    threshold_id: int,
    request: AlertThresholdUpdate,
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update alert threshold configuration."""
    threshold = await get_or_404(db, AlertThreshold, threshold_id, "Threshold not found")

    threshold.warning_level = request.warning_level
    threshold.critical_level = request.critical_level
    threshold.enabled = request.enabled

    await db.commit()

    logger.info(
        "Alert threshold updated",
        extra={
            "threshold_id": threshold_id,
            "user_id": current_user.id,
            "warning": request.warning_level,
            "critical": request.critical_level
        }
    )

    return {
        "message": "Threshold updated",
        "threshold_id": threshold_id
    }


# ============================================================================
# Application Metrics Endpoints (Monitoring Checklist Items)
# ============================================================================

@router.get(
    "/app-metrics",
    summary="Get application-level metrics for Prometheus scraping",
    description="Returns all counters and gauges from the monitoring checklist",
)
async def get_app_metrics(
    current_user: User = Depends(_verify_admin_access),
):
    """
    Return all application metrics for dashboards and alerting.

    Covers:
    #3  Job partial failure ratios
    #5  Cache/rate-limit fallback counters
    #6  Recommendation cache backend status
    #7  Circuit breaker states
    #9  Data parse error counters
    #26 Payment counters
    #30 External API call counters
    """
    from ...core.metrics import get_all_metrics
    from ...utils.circuit_breaker import circuit_breaker_manager

    metrics = get_all_metrics()
    metrics["circuit_breakers"] = circuit_breaker_manager.get_all_states()
    return metrics


@router.get(
    "/notification-dlq-status",
    summary="Get notification dead letter queue status",
    description="Shows pending, retrying, and abandoned notification failures",
)
async def get_notification_dlq_status(
    current_user: User = Depends(_verify_admin_access),
    db: AsyncSession = Depends(get_db),
):
    """
    Notification DLQ dashboard (#1, #2).

    Returns counts of failed notifications by status and channel.
    """
    from ...models.notification_failure import (
        FailedNotificationRecord,
        NotificationChannel,
        NotificationFailureStatus,
    )

    # Counts by status and channel
    stmt = (
        select(
            FailedNotificationRecord.channel,
            FailedNotificationRecord.status,
            func.count(FailedNotificationRecord.id),
        )
        .group_by(FailedNotificationRecord.channel, FailedNotificationRecord.status)
    )
    result = await db.execute(stmt)

    counts: dict = {}
    for channel, fstatus, count in result.all():
        ch = channel.value if channel else "unknown"
        st = fstatus.value if fstatus else "unknown"
        counts.setdefault(ch, {})[st] = count

    # Recent failures (last 24h)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_stmt = (
        select(func.count(FailedNotificationRecord.id))
        .where(FailedNotificationRecord.created_at >= cutoff)
    )
    recent_result = await db.execute(recent_stmt)
    recent_count = recent_result.scalar_one_or_none() or 0

    # Daily-cap suppressions specifically (subset of the email DLQ).
    # Surfaced as its own field so admins can distinguish cost-protection
    # suppressions from genuine provider/network failures.
    cap_pending_stmt = (
        select(func.count(FailedNotificationRecord.id))
        .where(
            FailedNotificationRecord.error_type == "daily_cap_exceeded",
            FailedNotificationRecord.status == NotificationFailureStatus.PENDING,
        )
    )
    cap_pending_result = await db.execute(cap_pending_stmt)
    cap_exceeded_pending = cap_pending_result.scalar_one_or_none() or 0

    return {
        "counts_by_channel_status": counts,
        "failures_last_24h": recent_count,
        "cap_exceeded_pending": cap_exceeded_pending,
    }

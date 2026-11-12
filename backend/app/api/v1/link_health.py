# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Link Health Monitoring API Endpoints.

Provides endpoints for:
- Viewing link health status and summaries
- Managing alerts
- Running manual checks
- Configuration management
"""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.link_health import LinkSource
from ...services.link_health_service import get_link_health_service
from .dependencies import require_admin, require_staff

router = APIRouter(prefix="/link-health", tags=["link-health"])


# ==================== Schemas ====================


class LinkHealthCheckResponse(BaseModel):

    id: int
    url: str
    status: str
    http_status_code: int | None
    response_time_ms: float | None
    error_message: str | None
    final_url: str | None
    redirect_count: int
    ssl_valid: bool | None
    ssl_expires_at: datetime | None
    checked_at: datetime

    class Config:
        from_attributes = True


class LinkHealthSummaryResponse(BaseModel):

    id: int
    url: str
    source: str
    source_id: int | None = None
    source_name: str | None
    current_status: str
    last_http_status: int | None
    last_error_message: str | None
    avg_response_time_ms: float | None
    last_response_time_ms: float | None
    total_checks: int
    successful_checks: int
    failed_checks: int
    uptime_percentage: float | None
    consecutive_failures: int
    last_successful_at: datetime | None
    last_failed_at: datetime | None
    last_checked_at: datetime | None
    is_monitored: bool
    alert_sent: bool

    class Config:
        from_attributes = True


class LinkHealthAlertResponse(BaseModel):

    id: int
    url: str
    source: str
    alert_type: str
    severity: str
    message: str
    status: str
    acknowledged_by: int | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    resolution_notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class LinkHealthStatsResponse(BaseModel):

    total_monitored: int
    by_status: dict[str, int]
    by_source: dict[str, int]
    open_alerts: int
    avg_uptime_percentage: float


class CheckUrlRequest(BaseModel):

    url: str = Field(..., min_length=1, max_length=2000)
    source: str = Field(default="other")
    source_name: str | None = None


class AcknowledgeAlertRequest(BaseModel):

    notes: str | None = None


class ResolveAlertRequest(BaseModel):

    notes: str | None = None


class UpdateConfigRequest(BaseModel):

    default_timeout_seconds: int | None = None
    default_check_interval_minutes: int | None = None
    max_redirects: int | None = None
    alert_on_consecutive_failures: int | None = None
    alert_on_response_time_ms: int | None = None
    degraded_response_time_ms: int | None = None
    keep_history_days: int | None = None
    monitoring_enabled: bool | None = None
    ssl_check_enabled: bool | None = None
    notify_on_broken: bool | None = None
    notify_on_recovered: bool | None = None
    notification_emails: list[str] | None = None


class UpdateMonitoringRequest(BaseModel):

    is_monitored: bool


class BulkCheckResponse(BaseModel):

    total: int
    healthy: int
    degraded: int
    broken: int
    errors: int


class PlatformStatusResponse(BaseModel):

    platforms: dict[str, dict[str, Any]]


# ==================== Dashboard & Stats ====================


@router.get("/stats", response_model=LinkHealthStatsResponse)
async def get_health_stats(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_staff),
):
    """Get overall link health statistics."""
    service = get_link_health_service(db)
    stats = await service.get_health_summary_stats()
    return stats


@router.get("/broken", response_model=list[LinkHealthSummaryResponse])
async def get_broken_links(
    source: str | None = Query(None, description="Filter by source"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    include_unmonitored: bool = Query(False, description="Include links with monitoring disabled"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_staff),
):
    """Get list of broken links."""
    service = get_link_health_service(db)

    source_enum = None
    if source:
        try:
            source_enum = LinkSource(source)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid source: {source}") from None

    links = await service.get_broken_links(
        source=source_enum, limit=limit, offset=offset, include_unmonitored=include_unmonitored
    )
    return links


@router.get("/degraded", response_model=list[LinkHealthSummaryResponse])
async def get_degraded_links(
    min_response_time_ms: float | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    include_unmonitored: bool = Query(False, description="Include links with monitoring disabled"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_staff),
):
    """Get links with degraded performance."""
    service = get_link_health_service(db)
    links = await service.get_degraded_links(
        min_response_time_ms=min_response_time_ms, limit=limit, include_unmonitored=include_unmonitored
    )
    return links


# ==================== Single URL Operations ====================


@router.post("/check", response_model=LinkHealthCheckResponse)
async def check_single_url(
    request: CheckUrlRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_staff),
):
    """Check health of a single URL."""
    service = get_link_health_service(db)

    try:
        source_enum = LinkSource(request.source)
    except ValueError:
        source_enum = LinkSource.other

    check = await service.check_url(
        url=request.url,
        source=source_enum,
        source_name=request.source_name,
    )
    return check


@router.get("/history", response_model=list[LinkHealthCheckResponse])
async def get_url_history(
    url: str = Query(..., min_length=1),
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_staff),
):
    """Get check history for a specific URL."""
    service = get_link_health_service(db)
    history = await service.get_check_history(url=url, days=days, limit=limit)
    return history


# ==================== Bulk Operations ====================


@router.post("/check/external-resources", status_code=status.HTTP_202_ACCEPTED)
async def check_all_external_resources(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin),
):
    """Start checking all external resource URLs in the background."""
    service = get_link_health_service(db)
    background_tasks.add_task(service.check_all_external_resources)
    return {"status": "started", "message": "External resource check running in background"}


@router.post("/check/lesson-resources", status_code=status.HTTP_202_ACCEPTED)
async def check_all_lesson_resources(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin),
):
    """Start checking all lesson resource URLs in the background."""
    service = get_link_health_service(db)
    background_tasks.add_task(service.check_all_lesson_resources)
    return {"status": "started", "message": "Lesson resource check running in background"}


@router.post("/check/catalog-links", status_code=status.HTTP_202_ACCEPTED)
async def check_all_catalog_links(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin),
):
    """Start checking all catalog 856 electronic-resource URLs in the background."""
    service = get_link_health_service(db)
    background_tasks.add_task(service.check_all_catalog_links)
    return {"status": "started", "message": "Catalog link check running in background"}


@router.post("/check/platforms", status_code=status.HTTP_202_ACCEPTED)
async def check_digital_platforms(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_staff),
):
    """Start checking digital platform endpoints (Palace Project) in the background."""
    service = get_link_health_service(db)
    background_tasks.add_task(service.check_digital_platform_endpoints)
    return {"status": "started", "message": "Platform check running in background"}


# ==================== Alerts ====================


@router.get("/alerts", response_model=list[LinkHealthAlertResponse])
async def get_open_alerts(
    severity: str | None = Query(None, description="Filter by severity"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_staff),
):
    """Get open link health alerts."""
    service = get_link_health_service(db)
    alerts = await service.get_open_alerts(severity=severity, limit=limit)
    return alerts


@router.post("/alerts/{alert_id}/acknowledge", response_model=LinkHealthAlertResponse)
async def acknowledge_alert(
    alert_id: int,
    request: AcknowledgeAlertRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    """Acknowledge a link health alert."""
    service = get_link_health_service(db)
    alert = await service.acknowledge_alert(
        alert_id=alert_id,
        user_id=current_user.id,
        notes=request.notes,
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/alerts/{alert_id}/resolve", response_model=LinkHealthAlertResponse)
async def resolve_alert(
    alert_id: int,
    request: ResolveAlertRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_staff),
):
    """Mark a link health alert as resolved."""
    service = get_link_health_service(db)
    alert = await service.resolve_alert(alert_id=alert_id, notes=request.notes)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


# ==================== Link Monitoring Toggle ====================


@router.patch("/links/{summary_id}", response_model=LinkHealthSummaryResponse)
async def update_link_monitoring(
    summary_id: int,
    request: UpdateMonitoringRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_staff),
):
    """Enable or disable monitoring for a specific link summary."""
    service = get_link_health_service(db)
    summary = await service.set_monitoring(summary_id=summary_id, is_monitored=request.is_monitored)
    if not summary:
        raise HTTPException(status_code=404, detail="Link summary not found")
    return summary


# ==================== Configuration ====================


@router.get("/config")
async def get_config(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin),
):
    """Get link health monitoring configuration."""
    service = get_link_health_service(db)
    config = await service.get_config()
    return {
        "default_timeout_seconds": config.default_timeout_seconds,
        "default_check_interval_minutes": config.default_check_interval_minutes,
        "max_redirects": config.max_redirects,
        "alert_on_consecutive_failures": config.alert_on_consecutive_failures,
        "alert_on_response_time_ms": config.alert_on_response_time_ms,
        "degraded_response_time_ms": config.degraded_response_time_ms,
        "keep_history_days": config.keep_history_days,
        "monitoring_enabled": config.monitoring_enabled,
        "ssl_check_enabled": config.ssl_check_enabled,
        "notify_on_broken": config.notify_on_broken,
        "notify_on_recovered": config.notify_on_recovered,
        "notification_emails": config.notification_emails,
        "max_concurrent_checks": config.max_concurrent_checks,
        "delay_between_checks_ms": config.delay_between_checks_ms,
    }


@router.patch("/config")
async def update_config(
    request: UpdateConfigRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin),
):
    """Update link health monitoring configuration."""
    service = get_link_health_service(db)

    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    config = await service.update_config(**update_data)

    return {"message": "Configuration updated", "config": config}


# ==================== Maintenance ====================


@router.post("/cleanup")
async def cleanup_old_data(
    days: int | None = Query(None, description="Days of history to keep"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_admin),
):
    """Clean up old check history records."""
    service = get_link_health_service(db)
    deleted_checks = await service.cleanup_old_checks(days=days)
    deleted_summaries = await service.remove_stale_summaries()

    return {
        "deleted_checks": deleted_checks,
        "deleted_summaries": deleted_summaries,
    }

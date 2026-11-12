# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Collection Alerts API Endpoints

Provides endpoints for staff to view and manage collection management alerts:
- Alerts for last available copy checkouts
- Alerts for high-demand items
- Alerts for non-circulating items
- Alerts for long hold queues
- Low inventory alerts by branch
"""
from datetime import datetime
from typing import List, Optional
import json
from app.core.logging import get_logger

logger = get_logger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.catalog import CatalogItem
from ....models.collection_alert import (
    CollectionAlert, AlertType, CollectionAlertStatus, CollectionAlertSeverity
)
from ....models.user import User
from ....services.collection_alert_service import (
    dismiss_alert, resolve_alert, get_all_active_alerts,
    get_alert_count_by_type, check_non_circulating_alert
)
from ..auth import get_current_user
from ..dependencies import require_staff

router = APIRouter(prefix="/staff", tags=["staff-collection-alerts"])


class AlertContextInfo(BaseModel):
    available_copies: Optional[int] = None
    total_copies: Optional[int] = None
    pending_holds: Optional[int] = None
    last_checkout_date: Optional[str] = None
    months_since_checkout: Optional[int] = None
    branch: Optional[str] = None
    checked_at: Optional[str] = None


class CollectionAlertResponse(BaseModel):
    id: int
    catalog_item_id: int
    item_title: Optional[str] = None
    item_author: Optional[str] = None
    alert_type: AlertType
    severity: CollectionAlertSeverity
    status: CollectionAlertStatus
    location: Optional[str] = None
    context: Optional[AlertContextInfo] = None
    created_at: datetime
    dismissed_at: Optional[datetime] = None


class CollectionAlertsSummary(BaseModel):
    total_active: int
    critical_count: int
    warning_count: int
    info_count: int
    by_type: dict[str, int]


class CollectionAlertsResponse(BaseModel):
    alerts: List[CollectionAlertResponse]
    total: int
    page: int
    per_page: int
    pages: int
    summary: CollectionAlertsSummary


@router.get("/collection-alerts", response_model=CollectionAlertsResponse)
async def get_collection_alerts(
    alert_type: Optional[AlertType] = Query(None, description="Filter by alert type"),
    severity: Optional[CollectionAlertSeverity] = Query(None, description="Filter by severity"),
    location: Optional[str] = Query(None, description="Filter by branch location"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated list of collection management alerts for staff"""
    offset = (page - 1) * per_page

    # Build base query
    query = select(CollectionAlert, CatalogItem).join(
        CatalogItem, CollectionAlert.catalog_item_id == CatalogItem.id
    ).where(
        CollectionAlert.status == CollectionAlertStatus.ACTIVE
    )

    # Apply filters
    if alert_type:
        query = query.where(CollectionAlert.alert_type == alert_type)

    if severity:
        query = query.where(CollectionAlert.severity == severity)

    if location:
        query = query.where(CollectionAlert.location == location)

    # Get total count
    count_query = select(func.count(CollectionAlert.id)).where(
        CollectionAlert.status == CollectionAlertStatus.ACTIVE
    )
    if alert_type:
        count_query = count_query.where(CollectionAlert.alert_type == alert_type)
    if severity:
        count_query = count_query.where(CollectionAlert.severity == severity)
    if location:
        count_query = count_query.where(CollectionAlert.location == location)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Execute paginated query
    query = query.order_by(
        CollectionAlert.severity.desc(),
        CollectionAlert.created_at.desc()
    ).offset(offset).limit(per_page)

    result = await db.execute(query)
    rows = result.all()

    # Get summary counts
    summary_counts = await get_alert_count_by_type(db)

    # Calculate severity counts
    severity_count_query = select(
        CollectionAlert.severity,
        func.count(CollectionAlert.id).label("count")
    ).where(
        CollectionAlert.status == CollectionAlertStatus.ACTIVE
    ).group_by(CollectionAlert.severity)

    severity_result = await db.execute(severity_count_query)
    severity_counts = {row[0]: row[1] for row in severity_result.all()}

    alerts = []
    for alert, item in rows:
        context = None
        if alert.context_data:
            try:
                context_dict = json.loads(alert.context_data)
                context = AlertContextInfo(**context_dict)
            except (json.JSONDecodeError, ValueError):
                pass

        alerts.append(
            CollectionAlertResponse(
                id=alert.id,
                catalog_item_id=alert.catalog_item_id,
                item_title=item.title,
                item_author=item.author,
                alert_type=alert.alert_type,
                severity=alert.severity,
                status=alert.status,
                location=alert.location,
                context=context,
                created_at=alert.created_at,
                dismissed_at=alert.dismissed_at,
            )
        )

    pages = (total + per_page - 1) // per_page
    summary = CollectionAlertsSummary(
        total_active=total,
        critical_count=severity_counts.get(CollectionAlertSeverity.CRITICAL, 0),
        warning_count=severity_counts.get(CollectionAlertSeverity.WARNING, 0),
        info_count=severity_counts.get(CollectionAlertSeverity.INFO, 0),
        by_type=summary_counts,
    )

    return CollectionAlertsResponse(
        alerts=alerts,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        summary=summary,
    )


@router.get("/collection-alerts/{alert_id}", response_model=CollectionAlertResponse)
async def get_collection_alert(
    alert_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific collection alert"""
    result = await db.execute(
        select(CollectionAlert, CatalogItem).join(
            CatalogItem, CollectionAlert.catalog_item_id == CatalogItem.id
        ).where(CollectionAlert.id == alert_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert, item = row
    context = None
    if alert.context_data:
        try:
            context_dict = json.loads(alert.context_data)
            context = AlertContextInfo(**context_dict)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse alert context_data for alert %s", alert.id)

    return CollectionAlertResponse(
        id=alert.id,
        catalog_item_id=alert.catalog_item_id,
        item_title=item.title,
        item_author=item.author,
        alert_type=alert.alert_type,
        severity=alert.severity,
        status=alert.status,
        location=alert.location,
        context=context,
        created_at=alert.created_at,
        dismissed_at=alert.dismissed_at,
    )


@router.post("/collection-alerts/{alert_id}/dismiss", response_model=CollectionAlertResponse)
async def dismiss_collection_alert(
    alert_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss a collection alert (mark as acknowledged by staff)"""
    alert = await dismiss_alert(db, alert_id, staff_user.id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.commit()
    await db.refresh(alert)

    # Get item for response
    item_result = await db.execute(
        select(CatalogItem).where(CatalogItem.id == alert.catalog_item_id)
    )
    item = item_result.scalar_one_or_none()

    context = None
    if alert.context_data:
        try:
            context_dict = json.loads(alert.context_data)
            context = AlertContextInfo(**context_dict)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse alert context_data for alert %s", alert.id)

    return CollectionAlertResponse(
        id=alert.id,
        catalog_item_id=alert.catalog_item_id,
        item_title=item.title if item else None,
        item_author=item.author if item else None,
        alert_type=alert.alert_type,
        severity=alert.severity,
        status=alert.status,
        location=alert.location,
        context=context,
        created_at=alert.created_at,
        dismissed_at=alert.dismissed_at,
    )


@router.post("/collection-alerts/{alert_id}/resolve", response_model=CollectionAlertResponse)
async def resolve_collection_alert(
    alert_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a collection alert (condition has been addressed)"""
    alert = await resolve_alert(db, alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.commit()
    await db.refresh(alert)

    # Get item for response
    item_result = await db.execute(
        select(CatalogItem).where(CatalogItem.id == alert.catalog_item_id)
    )
    item = item_result.scalar_one_or_none()

    context = None
    if alert.context_data:
        try:
            context_dict = json.loads(alert.context_data)
            context = AlertContextInfo(**context_dict)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse alert context_data for alert %s", alert.id)

    return CollectionAlertResponse(
        id=alert.id,
        catalog_item_id=alert.catalog_item_id,
        item_title=item.title if item else None,
        item_author=item.author if item else None,
        alert_type=alert.alert_type,
        severity=alert.severity,
        status=alert.status,
        location=alert.location,
        context=context,
        created_at=alert.created_at,
        dismissed_at=alert.dismissed_at,
    )


@router.get("/collection-alerts/summary", response_model=CollectionAlertsSummary)
async def get_collection_alerts_summary(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get summary counts of collection alerts"""
    # Total count
    total_result = await db.execute(
        select(func.count(CollectionAlert.id)).where(
            CollectionAlert.status == CollectionAlertStatus.ACTIVE
        )
    )
    total = total_result.scalar() or 0

    # Severity counts
    severity_result = await db.execute(
        select(
            CollectionAlert.severity,
            func.count(CollectionAlert.id).label("count")
        ).where(
            CollectionAlert.status == CollectionAlertStatus.ACTIVE
        ).group_by(CollectionAlert.severity)
    )
    severity_counts = {row[0]: row[1] for row in severity_result.all()}

    # Type counts
    type_counts = await get_alert_count_by_type(db)

    return CollectionAlertsSummary(
        total_active=total,
        critical_count=severity_counts.get(CollectionAlertSeverity.CRITICAL, 0),
        warning_count=severity_counts.get(CollectionAlertSeverity.WARNING, 0),
        info_count=severity_counts.get(CollectionAlertSeverity.INFO, 0),
        by_type=type_counts,
    )

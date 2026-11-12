# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Legal Reporting API - Reporting and Alerts Endpoints

Provides endpoints for:
- Compliance dashboard metrics
- Alert management
- Regulatory change tracking
- Reporting and analytics
"""
from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ....core.database import get_db
from ....models.legal_compliance import (
    ComplianceDashboardMetric, ComplianceAlert, RegulatoryChange,
    PolicyEnforcementTracking, LegalAlertSeverity, AlertStatus, LegalChangeType,
    LegalDocument, LegalComplianceRequirement, DocumentReviewCycle,
    LegalDocumentStatus, ComplianceStatus, ReviewStatus
)
from ....models.user import User
from ..dependencies import require_staff

router = APIRouter(prefix="/legal/reporting", tags=["legal-reporting"])


@router.get("/dashboard")
async def get_dashboard_metrics(
    metric_date: Optional[date] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get current dashboard metrics."""
    target_date = metric_date or date.today()

    # Try to get existing metrics for the date
    query = select(ComplianceDashboardMetric).where(
        and_(
            ComplianceDashboardMetric.metric_date == target_date,
            ComplianceDashboardMetric.metric_type == "daily"
        )
    )
    result = await db.execute(query)
    metric = result.scalar_one_or_none()

    if not metric:
        # Calculate fresh metrics
        from ....services.legal_compliance_service import LegalComplianceService
        metrics_data = await LegalComplianceService.calculate_dashboard_metrics(db, target_date)

        metric = ComplianceDashboardMetric(
            metric_date=target_date,
            metric_type="daily",
            **metrics_data
        )
        db.add(metric)
        await db.commit()
        await db.refresh(metric)

    return {
        "metric_date": metric.metric_date.isoformat(),
        "documents": {
            "total": metric.total_documents,
            "active": metric.active_documents,
            "pending_review": metric.documents_pending_review,
            "overdue_review": metric.documents_overdue_review,
            "expiring_soon": metric.documents_expiring_soon
        },
        "compliance": {
            "total_requirements": metric.total_requirements,
            "compliant": metric.compliant_requirements,
            "non_compliant": metric.non_compliant_requirements,
            "pending": metric.pending_requirements,
            "compliance_rate": metric.compliance_rate
        },
        "reviews": {
            "scheduled": metric.scheduled_reviews,
            "completed": metric.completed_reviews,
            "overdue": metric.overdue_reviews
        },
        "alerts": {
            "active": metric.active_alerts,
            "critical": metric.critical_alerts
        },
        "trend_data": metric.trend_data,
        "updated_at": metric.updated_at.isoformat() if metric.updated_at else None
    }


@router.get("/alerts")
async def list_alerts(
    severity: Optional[LegalAlertSeverity] = None,
    status: Optional[AlertStatus] = None,
    alert_type: Optional[str] = None,
    assigned_to_me: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List compliance alerts."""
    query = select(ComplianceAlert).options(
        joinedload(ComplianceAlert.document),
        joinedload(ComplianceAlert.requirement),
        joinedload(ComplianceAlert.assigned_to)
    )

    filters = []
    if severity:
        filters.append(ComplianceAlert.severity == severity)
    if status:
        filters.append(ComplianceAlert.status == status)
    if alert_type:
        filters.append(ComplianceAlert.alert_type == alert_type)
    if assigned_to_me:
        filters.append(ComplianceAlert.assigned_to_id == staff_user.id)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(
        ComplianceAlert.severity.desc(),
        ComplianceAlert.id.desc()
    )
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    alerts = result.scalars().all()

    return {
        "alerts": [
            {
                "id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "severity": str(alert.severity),
                "status": str(alert.status),
                "alert_type": alert.alert_type,
                "due_date": alert.due_date.isoformat() if alert.due_date else None,
                "document": {
                    "id": alert.document.id,
                    "title": alert.document.title
                } if alert.document else None,
                "requirement": {
                    "id": alert.requirement.id,
                    "title": alert.requirement.title
                } if alert.requirement else None,
                "assigned_to": {
                    "id": alert.assigned_to.id,
                    "name": f"{alert.assigned_to.first_name} {alert.assigned_to.last_name}"
                } if alert.assigned_to else None,
                "action_required": alert.action_required,
                "created_at": alert.created_at.isoformat()
            }
            for alert in alerts
        ],
        "total": len(alerts),
        "limit": limit,
        "offset": offset
    }


@router.post("/alerts")
async def create_alert(
    title: str,
    message: str,
    severity: LegalAlertSeverity,
    alert_type: str,
    document_id: Optional[int] = None,
    requirement_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    due_date: Optional[date] = None,
    action_required: Optional[str] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a compliance alert."""
    alert = ComplianceAlert(
        title=title,
        message=message,
        severity=severity,
        alert_type=alert_type,
        document_id=document_id,
        requirement_id=requirement_id,
        assigned_to_id=assigned_to_id,
        due_date=due_date,
        action_required=action_required
    )

    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    return {
        "id": alert.id,
        "title": alert.title,
        "severity": str(alert.severity),
        "status": str(alert.status),
        "created_at": alert.created_at.isoformat()
    }


@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge an alert."""
    query = select(ComplianceAlert).where(ComplianceAlert.id == alert_id)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = AlertStatus.acknowledged
    alert.acknowledged_by_id = staff_user.id
    alert.acknowledged_at = datetime.now()

    await db.commit()
    await db.refresh(alert)

    return {
        "id": alert.id,
        "status": str(alert.status),
        "acknowledged_at": alert.acknowledged_at.isoformat()
    }


@router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    resolution_notes: str,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Resolve an alert."""
    query = select(ComplianceAlert).where(ComplianceAlert.id == alert_id)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = AlertStatus.resolved
    alert.resolved_by_id = staff_user.id
    alert.resolved_at = datetime.now()
    alert.resolution_notes = resolution_notes

    await db.commit()
    await db.refresh(alert)

    return {
        "id": alert.id,
        "status": str(alert.status),
        "resolved_at": alert.resolved_at.isoformat(),
        "resolution_notes": alert.resolution_notes
    }


@router.get("/regulatory-changes")
async def list_regulatory_changes(
    change_type: Optional[LegalChangeType] = None,
    jurisdiction: Optional[str] = None,
    impact_level: Optional[str] = None,
    is_reviewed: Optional[bool] = None,
    upcoming_deadline_days: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List regulatory changes."""
    query = select(RegulatoryChange).options(
        joinedload(RegulatoryChange.reviewed_by),
        joinedload(RegulatoryChange.created_by)
    )

    filters = []
    if change_type:
        filters.append(RegulatoryChange.change_type == change_type)
    if jurisdiction:
        filters.append(RegulatoryChange.jurisdiction == jurisdiction)
    if impact_level:
        filters.append(RegulatoryChange.impact_level == impact_level)
    if is_reviewed is not None:
        filters.append(RegulatoryChange.is_reviewed == is_reviewed)
    if upcoming_deadline_days:
        target_date = date.today() + timedelta(days=upcoming_deadline_days)
        filters.append(
            and_(
                RegulatoryChange.compliance_deadline.isnot(None),
                RegulatoryChange.compliance_deadline <= target_date,
                RegulatoryChange.compliance_deadline >= date.today()
            )
        )

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(RegulatoryChange.announcement_date.desc())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    changes = result.scalars().all()

    return {
        "regulatory_changes": [
            {
                "id": change.id,
                "title": change.title,
                "change_type": str(change.change_type),
                "jurisdiction": change.jurisdiction,
                "issuing_authority": change.issuing_authority,
                "announcement_date": change.announcement_date.isoformat(),
                "effective_date": change.effective_date.isoformat() if change.effective_date else None,
                "compliance_deadline": change.compliance_deadline.isoformat() if change.compliance_deadline else None,
                "impact_level": change.impact_level,
                "is_reviewed": change.is_reviewed,
                "implementation_status": change.implementation_status,
                "created_at": change.created_at.isoformat()
            }
            for change in changes
        ],
        "total": len(changes),
        "limit": limit,
        "offset": offset
    }


@router.post("/regulatory-changes")
async def create_regulatory_change(
    title: str,
    change_type: LegalChangeType,
    description: str,
    announcement_date: date,
    jurisdiction: Optional[str] = None,
    issuing_authority: Optional[str] = None,
    effective_date: Optional[date] = None,
    compliance_deadline: Optional[date] = None,
    impact_level: Optional[str] = None,
    legal_citation: Optional[str] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a regulatory change record."""
    change = RegulatoryChange(
        title=title,
        change_type=change_type,
        description=description,
        announcement_date=announcement_date,
        jurisdiction=jurisdiction,
        issuing_authority=issuing_authority,
        effective_date=effective_date,
        compliance_deadline=compliance_deadline,
        impact_level=impact_level,
        legal_citation=legal_citation,
        created_by_id=staff_user.id
    )

    db.add(change)
    await db.commit()
    await db.refresh(change)

    return {
        "id": change.id,
        "title": change.title,
        "change_type": str(change.change_type),
        "created_at": change.created_at.isoformat()
    }


@router.get("/enforcement-tracking")
async def list_enforcement_tracking(
    document_id: Optional[int] = None,
    is_resolved: Optional[bool] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List policy enforcement tracking records."""
    query = select(PolicyEnforcementTracking).options(
        joinedload(PolicyEnforcementTracking.document),
        joinedload(PolicyEnforcementTracking.staff_member)
    )

    filters = []
    if document_id:
        filters.append(PolicyEnforcementTracking.document_id == document_id)
    if is_resolved is not None:
        filters.append(PolicyEnforcementTracking.is_resolved == is_resolved)
    if start_date:
        filters.append(PolicyEnforcementTracking.incident_date >= start_date)
    if end_date:
        filters.append(PolicyEnforcementTracking.incident_date <= end_date)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(PolicyEnforcementTracking.incident_date.desc())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "enforcement_records": [
            {
                "id": record.id,
                "document": {
                    "id": record.document.id,
                    "title": record.document.title
                } if record.document else None,
                "incident_date": record.incident_date.isoformat(),
                "policy_section_violated": record.policy_section_violated,
                "action_taken": str(record.action_taken),
                "action_date": record.action_date.isoformat(),
                "is_resolved": record.is_resolved,
                "resolution_date": record.resolution_date.isoformat() if record.resolution_date else None,
                "follow_up_required": record.follow_up_required,
                "created_at": record.created_at.isoformat()
            }
            for record in records
        ],
        "total": len(records),
        "limit": limit,
        "offset": offset
    }


@router.get("/compliance-summary")
async def get_compliance_summary(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a summary of compliance status."""
    # Get requirement counts by status
    req_counts = await db.execute(
        select(
            LegalComplianceRequirement.compliance_status,
            func.count(LegalComplianceRequirement.id)
        ).group_by(LegalComplianceRequirement.compliance_status)
    )
    requirement_status = {status.value: count for status, count in req_counts}

    # Get document counts by status
    doc_counts = await db.execute(
        select(
            LegalDocument.status,
            func.count(LegalDocument.id)
        ).group_by(LegalDocument.status)
    )
    document_status = {status.value: count for status, count in doc_counts}

    # Get overdue reviews
    overdue_reviews = await db.execute(
        select(func.count(DocumentReviewCycle.id)).where(
            and_(
                DocumentReviewCycle.due_date < date.today(),
                DocumentReviewCycle.status.in_([ReviewStatus.pending, ReviewStatus.in_progress])
            )
        )
    )
    overdue_count = overdue_reviews.scalar() or 0

    # Get active alerts by severity
    alert_counts = await db.execute(
        select(
            ComplianceAlert.severity,
            func.count(ComplianceAlert.id)
        ).where(
            ComplianceAlert.status == AlertStatus.active
        ).group_by(ComplianceAlert.severity)
    )
    alerts_by_severity = {severity.value: count for severity, count in alert_counts}

    return {
        "requirements": {
            "by_status": requirement_status,
            "total": sum(requirement_status.values())
        },
        "documents": {
            "by_status": document_status,
            "total": sum(document_status.values())
        },
        "reviews": {
            "overdue": overdue_count
        },
        "alerts": {
            "by_severity": alerts_by_severity,
            "total": sum(alerts_by_severity.values())
        },
        "generated_at": datetime.now().isoformat()
    }

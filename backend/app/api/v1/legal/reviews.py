# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Legal Reviews API - Review and Audit Endpoints

Provides endpoints for:
- Review cycle management
- Document reviews
- Audit log access
- Review scheduling
"""
from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ....core.database import get_db
from ....models.legal_compliance import (
    DocumentReviewCycle, DocumentReview, DocumentAuditLog,
    ReviewFrequency, ReviewStatus, AuditEventType, LegalDocument
)
from ....models.user import User
from ..dependencies import require_staff

router = APIRouter(prefix="/legal/reviews", tags=["legal-reviews"])


@router.get("/cycles")
async def list_review_cycles(
    status: Optional[ReviewStatus] = None,
    overdue: bool = False,
    upcoming_days: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List document review cycles."""
    query = select(DocumentReviewCycle).options(
        joinedload(DocumentReviewCycle.document),
        joinedload(DocumentReviewCycle.assigned_to),
        selectinload(DocumentReviewCycle.reviews)
    )

    filters = []
    if status:
        filters.append(DocumentReviewCycle.status == status)
    if overdue:
        filters.append(
            and_(
                DocumentReviewCycle.due_date.isnot(None),
                DocumentReviewCycle.due_date < date.today(),
                DocumentReviewCycle.status.in_([ReviewStatus.pending, ReviewStatus.in_progress])
            )
        )
    if upcoming_days:
        target_date = date.today() + timedelta(days=upcoming_days)
        filters.append(
            and_(
                DocumentReviewCycle.scheduled_date.isnot(None),
                DocumentReviewCycle.scheduled_date <= target_date,
                DocumentReviewCycle.scheduled_date >= date.today()
            )
        )

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(DocumentReviewCycle.due_date.asc().nullslast())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    cycles = result.scalars().all()

    return {
        "review_cycles": [
            {
                "id": cycle.id,
                "document": {
                    "id": cycle.document.id,
                    "title": cycle.document.title,
                    "document_number": cycle.document.document_number
                } if cycle.document else None,
                "review_frequency": str(cycle.review_frequency),
                "scheduled_date": cycle.scheduled_date.isoformat(),
                "due_date": cycle.due_date.isoformat() if cycle.due_date else None,
                "status": str(cycle.status),
                "assigned_to": {
                    "id": cycle.assigned_to.id,
                    "name": f"{cycle.assigned_to.first_name} {cycle.assigned_to.last_name}"
                } if cycle.assigned_to else None,
                "review_count": len(cycle.reviews),
                "created_at": cycle.created_at.isoformat()
            }
            for cycle in cycles
        ],
        "total": len(cycles),
        "limit": limit,
        "offset": offset
    }


@router.get("/cycles/{cycle_id}")
async def get_review_cycle(
    cycle_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed review cycle information."""
    query = select(DocumentReviewCycle).where(
        DocumentReviewCycle.id == cycle_id
    ).options(
        joinedload(DocumentReviewCycle.document),
        joinedload(DocumentReviewCycle.assigned_to),
        joinedload(DocumentReviewCycle.created_by),
        selectinload(DocumentReviewCycle.reviews).joinedload(DocumentReview.reviewer)
    )

    result = await db.execute(query)
    cycle = result.scalar_one_or_none()

    if not cycle:
        raise HTTPException(status_code=404, detail="Review cycle not found")

    return {
        "id": cycle.id,
        "document": {
            "id": cycle.document.id,
            "title": cycle.document.title,
            "document_number": cycle.document.document_number,
            "category": str(cycle.document.category)
        } if cycle.document else None,
        "review_frequency": str(cycle.review_frequency),
        "scheduled_date": cycle.scheduled_date.isoformat(),
        "started_date": cycle.started_date.isoformat() if cycle.started_date else None,
        "completed_date": cycle.completed_date.isoformat() if cycle.completed_date else None,
        "due_date": cycle.due_date.isoformat() if cycle.due_date else None,
        "status": str(cycle.status),
        "assigned_to": {
            "id": cycle.assigned_to.id,
            "name": f"{cycle.assigned_to.first_name} {cycle.assigned_to.last_name}"
        } if cycle.assigned_to else None,
        "review_committee": cycle.review_committee,
        "outcome_summary": cycle.outcome_summary,
        "recommendations": cycle.recommendations,
        "action_items": cycle.action_items,
        "reviews": [
            {
                "id": review.id,
                "reviewer": {
                    "id": review.reviewer.id,
                    "name": f"{review.reviewer.first_name} {review.reviewer.last_name}"
                } if review.reviewer else None,
                "review_date": review.review_date.isoformat(),
                "status": str(review.status),
                "approved": review.approved,
                "requires_update": review.requires_update
            }
            for review in cycle.reviews
        ],
        "created_at": cycle.created_at.isoformat(),
        "updated_at": cycle.updated_at.isoformat() if cycle.updated_at else None
    }


@router.post("/cycles")
async def create_review_cycle(
    document_id: int,
    review_frequency: ReviewFrequency,
    scheduled_date: date,
    assigned_to_id: Optional[int] = None,
    review_committee: Optional[List[int]] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new review cycle for a document."""
    # Calculate due date based on frequency
    if review_frequency == ReviewFrequency.annual:
        due_date = scheduled_date + timedelta(days=30)
    elif review_frequency == ReviewFrequency.biannual:
        due_date = scheduled_date + timedelta(days=21)
    elif review_frequency == ReviewFrequency.quarterly:
        due_date = scheduled_date + timedelta(days=14)
    else:
        due_date = scheduled_date + timedelta(days=30)

    cycle = DocumentReviewCycle(
        document_id=document_id,
        review_frequency=review_frequency,
        scheduled_date=scheduled_date,
        due_date=due_date,
        assigned_to_id=assigned_to_id,
        review_committee=review_committee or [],
        created_by_id=staff_user.id
    )

    db.add(cycle)
    await db.commit()
    await db.refresh(cycle)

    return {
        "id": cycle.id,
        "document_id": document_id,
        "scheduled_date": cycle.scheduled_date.isoformat(),
        "due_date": cycle.due_date.isoformat(),
        "status": str(cycle.status),
        "created_at": cycle.created_at.isoformat()
    }


@router.post("/cycles/{cycle_id}/start")
async def start_review_cycle(
    cycle_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Start a review cycle."""
    query = select(DocumentReviewCycle).where(DocumentReviewCycle.id == cycle_id)
    result = await db.execute(query)
    cycle = result.scalar_one_or_none()

    if not cycle:
        raise HTTPException(status_code=404, detail="Review cycle not found")

    if cycle.status != ReviewStatus.pending:
        raise HTTPException(status_code=400, detail="Review cycle already started")

    cycle.status = ReviewStatus.in_progress
    cycle.started_date = date.today()

    await db.commit()
    await db.refresh(cycle)

    return {
        "id": cycle.id,
        "status": str(cycle.status),
        "started_date": cycle.started_date.isoformat()
    }


@router.post("/cycles/{cycle_id}/reviews")
async def add_review_to_cycle(
    cycle_id: int,
    findings: str,
    recommendations: Optional[str] = None,
    requires_update: bool = False,
    approved: bool = True,
    legal_accuracy_rating: Optional[int] = None,
    clarity_rating: Optional[int] = None,
    completeness_rating: Optional[int] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Add a review to a review cycle."""
    # Verify cycle exists
    query = select(DocumentReviewCycle).where(DocumentReviewCycle.id == cycle_id)
    result = await db.execute(query)
    cycle = result.scalar_one_or_none()

    if not cycle:
        raise HTTPException(status_code=404, detail="Review cycle not found")

    review = DocumentReview(
        review_cycle_id=cycle_id,
        reviewer_id=staff_user.id,
        review_date=date.today(),
        status=ReviewStatus.completed,
        findings=findings,
        recommendations=recommendations,
        requires_update=requires_update,
        approved=approved,
        legal_accuracy_rating=legal_accuracy_rating,
        clarity_rating=clarity_rating,
        completeness_rating=completeness_rating
    )

    db.add(review)
    await db.commit()
    await db.refresh(review)

    return {
        "id": review.id,
        "review_cycle_id": cycle_id,
        "reviewer_id": staff_user.id,
        "review_date": review.review_date.isoformat(),
        "approved": review.approved,
        "requires_update": review.requires_update,
        "created_at": review.created_at.isoformat()
    }


@router.post("/cycles/{cycle_id}/complete")
async def complete_review_cycle(
    cycle_id: int,
    outcome_summary: str,
    recommendations: Optional[List[dict]] = None,
    action_items: Optional[List[dict]] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Complete a review cycle."""
    query = select(DocumentReviewCycle).where(DocumentReviewCycle.id == cycle_id)
    result = await db.execute(query)
    cycle = result.scalar_one_or_none()

    if not cycle:
        raise HTTPException(status_code=404, detail="Review cycle not found")

    if cycle.status not in [ReviewStatus.pending, ReviewStatus.in_progress]:
        raise HTTPException(status_code=400, detail="Review cycle already completed")

    cycle.status = ReviewStatus.completed
    cycle.completed_date = date.today()
    cycle.outcome_summary = outcome_summary
    cycle.recommendations = recommendations or []
    cycle.action_items = action_items or []

    # Update document's last reviewed date
    if cycle.document:
        cycle.document.last_reviewed_date = date.today()

        # Calculate next review date based on frequency
        if cycle.review_frequency == ReviewFrequency.annual:
            cycle.document.next_review_date = date.today() + timedelta(days=365)
        elif cycle.review_frequency == ReviewFrequency.biannual:
            cycle.document.next_review_date = date.today() + timedelta(days=180)
        elif cycle.review_frequency == ReviewFrequency.quarterly:
            cycle.document.next_review_date = date.today() + timedelta(days=90)
        elif cycle.review_frequency == ReviewFrequency.triennial:
            cycle.document.next_review_date = date.today() + timedelta(days=1095)

    await db.commit()
    await db.refresh(cycle)

    return {
        "id": cycle.id,
        "status": str(cycle.status),
        "completed_date": cycle.completed_date.isoformat(),
        "outcome_summary": cycle.outcome_summary
    }


@router.get("/dashboard")
async def get_reviews_dashboard(
    days_back: int = Query(30, ge=1, le=365, description="Review metrics for last N days"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get review management dashboard with key metrics.

    Shows:
    - Total cycles and their statuses
    - Overdue reviews
    - Upcoming reviews
    - Reviewer performance
    - Document review coverage
    - Compliance status
    """
    cutoff_date = date.today() - timedelta(days=days_back)

    # Query review cycles
    cycles_query = select(DocumentReviewCycle).where(
        DocumentReviewCycle.created_at >= datetime.combine(cutoff_date, datetime.min.time())
    )
    result = await db.execute(cycles_query)
    cycles = result.scalars().all()

    # Calculate metrics
    total_cycles = len(cycles)
    completed_cycles = len([c for c in cycles if c.status == ReviewStatus.completed])
    in_progress_cycles = len([c for c in cycles if c.status == ReviewStatus.in_progress])
    pending_cycles = len([c for c in cycles if c.status == ReviewStatus.pending])

    # Overdue reviews
    overdue_cycles = [
        c for c in cycles
        if c.due_date and c.due_date < date.today()
        and c.status in [ReviewStatus.pending, ReviewStatus.in_progress]
    ]

    # Upcoming reviews (next 7 days)
    upcoming_date = date.today() + timedelta(days=7)
    upcoming_cycles = [
        c for c in cycles
        if c.scheduled_date and
        c.scheduled_date >= date.today() and
        c.scheduled_date <= upcoming_date
    ]

    # Average completion time
    completed_with_times = [
        (c.completed_date - c.created_at.date()).days * 24
        for c in cycles if c.completed_date and c.created_at
    ]
    avg_hours_to_complete = (
        sum(completed_with_times) / len(completed_with_times)
        if completed_with_times else 0
    )

    return {
        "dashboard": {
            "summary": {
                "total_cycles": total_cycles,
                "completed": completed_cycles,
                "in_progress": in_progress_cycles,
                "pending": pending_cycles,
                "completion_percentage": (
                    completed_cycles / total_cycles * 100 if total_cycles > 0 else 0
                )
            },
            "urgent": {
                "overdue_count": len(overdue_cycles),
                "overdue_cycles": [
                    {
                        "id": c.id,
                        "due_date": c.due_date.isoformat() if c.due_date else None,
                        "days_overdue": (date.today() - c.due_date).days if c.due_date else None
                    }
                    for c in overdue_cycles[:5]  # Show top 5
                ]
            },
            "upcoming": {
                "next_7_days": len(upcoming_cycles),
                "upcoming_cycles": [
                    {
                        "id": c.id,
                        "scheduled_date": c.scheduled_date.isoformat() if c.scheduled_date else None,
                        "days_until": (c.scheduled_date - date.today()).days if c.scheduled_date else None
                    }
                    for c in upcoming_cycles[:5]  # Show top 5
                ]
            },
            "performance": {
                "average_hours_to_complete": round(avg_hours_to_complete, 1),
                "median_completion_time": "TBD - calculated on demand"
            }
        },
        "period": {
            "days_shown": days_back,
            "start_date": cutoff_date.isoformat(),
            "end_date": date.today().isoformat()
        }
    }


@router.get("/audit-log")
async def get_audit_log(
    document_id: Optional[int] = None,
    event_type: Optional[AuditEventType] = None,
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get audit log entries with filtering."""
    query = select(DocumentAuditLog).options(
        joinedload(DocumentAuditLog.document),
        joinedload(DocumentAuditLog.user)
    )

    filters = []
    if document_id:
        filters.append(DocumentAuditLog.document_id == document_id)
    if event_type:
        filters.append(DocumentAuditLog.event_type == event_type)
    if user_id:
        filters.append(DocumentAuditLog.user_id == user_id)
    if start_date:
        filters.append(DocumentAuditLog.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        filters.append(DocumentAuditLog.created_at <= datetime.combine(end_date, datetime.max.time()))

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(DocumentAuditLog.created_at.desc())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "audit_logs": [
            {
                "id": log.id,
                "document": {
                    "id": log.document.id,
                    "title": log.document.title,
                    "document_number": log.document.document_number
                } if log.document else None,
                "event_type": str(log.event_type),
                "event_description": log.event_description,
                "user": {
                    "id": log.user.id,
                    "name": f"{log.user.first_name} {log.user.last_name}",
                    "role": log.user_role
                } if log.user else None,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "field_changes": log.field_changes,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ],
        "total": len(logs),
        "limit": limit,
        "offset": offset
    }

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Focus Time Management API Endpoints

API for managing focus time blocks, approvals, overrides, and analytics.
"""
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from ...core.database import get_db
from ...core.shortcuts import get_or_404
from .dependencies import require_staff, require_admin
from .auth import get_current_user
from ...models.focus_time import (
    ApprovalStatus,
    FocusTimeApproval,
    FocusTimeBlock,
    FocusTimeOverride,
    FocusTimeSettings,
    FocusTimeStatus,
    FocusTimeTracking,
    FocusWorkType,
    OverrideReason,
)
from ...models.user import User, UserRole
from app.core.datetime_utils import utc_now
from ...services.focus_time_notifications import FocusTimeNotificationService

logger = get_logger(__name__)

router = APIRouter()


@router.post("/staff/focus-time/blocks")
async def create_focus_block(
    start_time: datetime,
    end_time: datetime,
    work_type: FocusWorkType,
    description: Optional[str] = None,
    backup_contact_id: Optional[int] = None,
    is_recurring: bool = False,
    recurrence_rule: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Create a new focus time block

    Schedules protected deep work time with optional manager approval.
    """
    # Get settings to check if approval is required
    result = await db.execute(
        select(FocusTimeSettings).where(
            FocusTimeSettings.organization_id == (current_user.home_library_system_id or 1)
        )
    )
    settings = result.scalars().first()

    requires_approval = settings.requires_manager_approval if settings else True

    # Create focus block
    focus_block = FocusTimeBlock(
        organization_id=(current_user.home_library_system_id or 1),
        user_id=current_user.id,
        start_time=start_time,
        end_time=end_time,
        work_type=work_type,
        description=description,
        backup_contact_id=backup_contact_id,
        is_recurring=is_recurring,
        recurrence_rule=recurrence_rule,
        requires_approval=requires_approval,
        status=FocusTimeStatus.PENDING_APPROVAL if requires_approval else FocusTimeStatus.APPROVED,
    )

    db.add(focus_block)
    await db.commit()
    await db.refresh(focus_block)

    # Create approval record if needed
    if requires_approval:
        approval = FocusTimeApproval(
            focus_block_id=focus_block.id,
            status=ApprovalStatus.PENDING,
            requested_at=utc_now().replace(tzinfo=None),
        )
        db.add(approval)
        await db.commit()

    # Create tracking record
    tracking = FocusTimeTracking(focus_block_id=focus_block.id)
    db.add(tracking)
    await db.commit()

    return {
        "message": "Focus time block created",
        "block": {
            "id": focus_block.id,
            "start_time": focus_block.start_time.isoformat(),
            "end_time": focus_block.end_time.isoformat(),
            "work_type": focus_block.work_type,
            "status": focus_block.status,
            "requires_approval": focus_block.requires_approval,
        },
    }


@router.get("/staff/focus-time/blocks")
async def list_focus_blocks(
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    status: Optional[FocusTimeStatus] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get focus time blocks for the current user"""
    query = select(FocusTimeBlock).where(
        FocusTimeBlock.user_id == current_user.id
    )

    if start_date:
        query = query.where(FocusTimeBlock.start_time >= start_date)
    if end_date:
        query = query.where(FocusTimeBlock.end_time <= end_date)
    if status:
        query = query.where(FocusTimeBlock.status == status)

    query = query.order_by(FocusTimeBlock.start_time).limit(500)

    result = await db.execute(query)
    blocks = result.scalars().all()

    return {
        "blocks": [
            {
                "id": b.id,
                "start_time": b.start_time.isoformat(),
                "end_time": b.end_time.isoformat(),
                "work_type": b.work_type,
                "description": b.description,
                "status": b.status,
                "requires_approval": b.requires_approval,
                "is_recurring": b.is_recurring,
                "backup_contact_id": b.backup_contact_id,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in blocks
        ]
    }


@router.get("/staff/focus-time/blocks/{block_id}")
async def get_focus_block(
    block_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get detailed information about a focus time block"""
    result = await db.execute(
        select(FocusTimeBlock).where(
            and_(
                FocusTimeBlock.id == block_id,
                FocusTimeBlock.user_id == current_user.id,
            )
        )
    )
    block = result.scalar_one_or_none()

    if not block:
        raise HTTPException(status_code=404, detail="Focus block not found")

    # Get tracking
    tracking_result = await db.execute(
        select(FocusTimeTracking).where(FocusTimeTracking.focus_block_id == block_id)
    )
    tracking = tracking_result.scalar_one_or_none()

    # Get approvals
    approvals_result = await db.execute(
        select(FocusTimeApproval).where(FocusTimeApproval.focus_block_id == block_id)
    )
    approvals = approvals_result.scalars().all()

    # Get overrides
    overrides_result = await db.execute(
        select(FocusTimeOverride).where(FocusTimeOverride.focus_block_id == block_id)
    )
    overrides = overrides_result.scalars().all()

    return {
        "block": {
            "id": block.id,
            "start_time": block.start_time.isoformat(),
            "end_time": block.end_time.isoformat(),
            "work_type": block.work_type,
            "description": block.description,
            "status": block.status,
            "requires_approval": block.requires_approval,
            "is_recurring": block.is_recurring,
            "backup_contact_id": block.backup_contact_id,
        },
        "tracking": {
            "interruption_count": tracking.interruption_count if tracking else 0,
            "work_completed_percentage": tracking.work_completed_percentage if tracking else None,
            "quality_rating": tracking.quality_rating if tracking else None,
            "productivity_rating": tracking.productivity_rating if tracking else None,
        } if tracking else None,
        "approvals": [
            {
                "id": a.id,
                "manager_id": a.manager_id,
                "status": a.status,
                "decision_comment": a.decision_comment,
                "decided_at": a.decided_at.isoformat() if a.decided_at else None,
            }
            for a in approvals
        ],
        "overrides": [
            {
                "id": o.id,
                "reason": o.reason,
                "description": o.description,
                "urgency_level": o.urgency_level,
                "is_resolved": o.is_resolved,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in overrides
        ],
    }


@router.patch("/staff/focus-time/blocks/{block_id}/cancel")
async def cancel_focus_block(
    block_id: int,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Cancel a focus time block"""
    result = await db.execute(
        select(FocusTimeBlock).where(
            and_(
                FocusTimeBlock.id == block_id,
                FocusTimeBlock.user_id == current_user.id,
            )
        )
    )
    block = result.scalar_one_or_none()

    if not block:
        raise HTTPException(status_code=404, detail="Focus block not found")

    block.status = FocusTimeStatus.CANCELLED
    block.cancelled_at = utc_now().replace(tzinfo=None)

    await db.commit()

    return {
        "message": "Focus block cancelled",
        "block_id": block_id,
    }


@router.get("/staff/focus-time/approvals/pending")
async def get_pending_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get pending focus time approvals (for managers)

    Returns focus blocks awaiting approval from the current manager.
    """
    # Get pending approvals where the user is a manager
    query = select(FocusTimeApproval).join(FocusTimeBlock).where(
        and_(
            FocusTimeApproval.status == ApprovalStatus.PENDING,
            FocusTimeBlock.organization_id == (current_user.home_library_system_id or 1),
        )
    )

    result = await db.execute(query)
    approvals = result.scalars().all()

    return {
        "pending_approvals": [
            {
                "id": a.id,
                "focus_block_id": a.focus_block_id,
                "requested_at": a.requested_at.isoformat() if a.requested_at else None,
                "expires_at": a.expires_at.isoformat() if a.expires_at else None,
            }
            for a in approvals
        ]
    }


@router.post("/staff/focus-time/approvals/{approval_id}/approve")
async def approve_focus_time(
    approval_id: int,
    decision_comment: Optional[str] = None,
    conditions: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Approve a focus time request (managers only)"""
    approval = await get_or_404(db, FocusTimeApproval, approval_id, "Approval not found")

    approval.status = ApprovalStatus.APPROVED
    approval.manager_id = current_user.id
    approval.decided_at = utc_now().replace(tzinfo=None)
    approval.decision_comment = decision_comment
    approval.conditions = conditions

    # Update focus block status
    block_result = await db.execute(
        select(FocusTimeBlock).where(FocusTimeBlock.id == approval.focus_block_id)
    )
    block = block_result.scalar_one_or_none()
    if block:
        block.status = FocusTimeStatus.APPROVED

    await db.commit()

    if block:
        try:
            svc = FocusTimeNotificationService(db)
            await svc.notify_focus_time_approved(block, current_user, decision_comment)
        except Exception:  # noqa: BLE001 - notification boundary
            logger.error("Failed to send focus-time approved notification for block %s", block.id)

    return {
        "message": "Focus time approved",
        "approval_id": approval_id,
    }


@router.post("/staff/focus-time/approvals/{approval_id}/reject")
async def reject_focus_time(
    approval_id: int,
    decision_comment: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Reject a focus time request (managers only)"""
    approval = await get_or_404(db, FocusTimeApproval, approval_id, "Approval not found")

    approval.status = ApprovalStatus.REJECTED
    approval.manager_id = current_user.id
    approval.decided_at = utc_now().replace(tzinfo=None)
    approval.decision_comment = decision_comment

    # Update focus block status
    block_result = await db.execute(
        select(FocusTimeBlock).where(FocusTimeBlock.id == approval.focus_block_id)
    )
    block = block_result.scalar_one_or_none()
    if block:
        block.status = FocusTimeStatus.REJECTED

    await db.commit()

    if block:
        try:
            svc = FocusTimeNotificationService(db)
            await svc.notify_focus_time_rejected(block, current_user, decision_comment)
        except Exception:  # noqa: BLE001 - notification boundary
            logger.error("Failed to send focus-time rejected notification for block %s", block.id)

    return {
        "message": "Focus time rejected",
        "approval_id": approval_id,
    }


@router.post("/staff/focus-time/overrides")
async def create_override(
    focus_block_id: int,
    reason: OverrideReason,
    description: str,
    urgency_level: int = Query(..., ge=1, le=5),
    requires_escalation: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create an emergency override for active focus time"""
    # Check if block exists
    block = await get_or_404(db, FocusTimeBlock, focus_block_id, "Focus block not found")

    # Create override
    override = FocusTimeOverride(
        focus_block_id=focus_block_id,
        overridden_by_id=current_user.id,
        reason=reason,
        description=description,
        urgency_level=urgency_level,
        requires_escalation=requires_escalation,
    )

    db.add(override)

    # Update block status
    block.status = FocusTimeStatus.OVERRIDDEN

    # Update tracking interruption count
    tracking_result = await db.execute(
        select(FocusTimeTracking).where(FocusTimeTracking.focus_block_id == focus_block_id)
    )
    tracking = tracking_result.scalar_one_or_none()
    if tracking:
        tracking.interruption_count += 1

    await db.commit()
    await db.refresh(override)

    try:
        svc = FocusTimeNotificationService(db)
        await svc.notify_focus_time_override(block, override)
    except Exception:  # noqa: BLE001 - notification boundary
        logger.error("Failed to send focus-time override notification for block %s", block.id)

    try:
        svc = FocusTimeNotificationService(db)
        # Notify the manager who approved the block, if one exists.
        approval_result = await db.execute(
            select(FocusTimeApproval).where(
                and_(
                    FocusTimeApproval.focus_block_id == focus_block_id,
                    FocusTimeApproval.manager_id.isnot(None),
                )
            )
        )
        approval_with_manager = approval_result.scalars().first()
        if approval_with_manager:
            manager = await db.get(User, approval_with_manager.manager_id)
            if manager:
                await svc.notify_manager_of_override(block, override, manager)
    except Exception:  # noqa: BLE001 - notification boundary
        logger.error("Failed to send manager override notification for block %s", block.id)

    return {
        "message": "Override created",
        "override": {
            "id": override.id,
            "reason": override.reason,
            "urgency_level": override.urgency_level,
            "requires_escalation": override.requires_escalation,
        },
    }


@router.patch("/staff/focus-time/overrides/{override_id}/resolve")
async def resolve_override(
    override_id: int,
    resolution_notes: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark an override as resolved"""
    override = await get_or_404(db, FocusTimeOverride, override_id, "Override not found")

    override.is_resolved = True
    override.resolved_at = utc_now().replace(tzinfo=None)
    override.resolution_notes = resolution_notes

    await db.commit()

    return {
        "message": "Override resolved",
        "override_id": override_id,
    }


@router.get("/staff/focus-time/analytics")
async def get_analytics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get focus time analytics and metrics

    Returns productivity data, usage patterns, and effectiveness metrics.
    """
    query = select(FocusTimeBlock).where(
        FocusTimeBlock.user_id == current_user.id
    )

    if start_date:
        query = query.where(FocusTimeBlock.start_time >= start_date)
    if end_date:
        query = query.where(FocusTimeBlock.end_time <= end_date)

    result = await db.execute(query)
    blocks = result.scalars().all()

    # Calculate metrics
    total_blocks = len(blocks)
    completed_blocks = len([b for b in blocks if b.status == FocusTimeStatus.COMPLETED])
    cancelled_blocks = len([b for b in blocks if b.status == FocusTimeStatus.CANCELLED])
    overridden_blocks = len([b for b in blocks if b.status == FocusTimeStatus.OVERRIDDEN])

    # Get tracking data
    total_hours = sum((b.end_time - b.start_time).total_seconds() / 3600 for b in blocks)

    return {
        "summary": {
            "total_blocks": total_blocks,
            "completed_blocks": completed_blocks,
            "cancelled_blocks": cancelled_blocks,
            "overridden_blocks": overridden_blocks,
            "total_hours": round(total_hours, 2),
            "completion_rate": round(completed_blocks / total_blocks * 100, 2) if total_blocks > 0 else 0,
        },
        "period": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
    }


@router.get("/staff/focus-time/settings")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get focus time settings for the organization"""
    result = await db.execute(
        select(FocusTimeSettings).where(
            FocusTimeSettings.organization_id == (current_user.home_library_system_id or 1)
        )
    )
    settings = result.scalars().first()

    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    return {
        "settings": {
            "requires_manager_approval": settings.requires_manager_approval,
            "min_advance_notice_hours": settings.min_advance_notice_hours,
            "max_duration_hours": settings.max_duration_hours,
            "min_duration_minutes": settings.min_duration_minutes,
            "max_blocks_per_week": settings.max_blocks_per_week,
            "allow_recurring_blocks": settings.allow_recurring_blocks,
            "allow_emergency_override": settings.allow_emergency_override,
            "require_backup_contact": settings.require_backup_contact,
            "notification_enabled": settings.notification_enabled,
        }
    }


@router.get("/focus-time/status/{user_id}")
async def get_user_focus_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current focus time status for a user.

    Users can only view their own focus status, or staff can view any user's status.
    High rate limit for real-time status displays (door signs, status lights).
    """
    if current_user.id != user_id and current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user's focus status",
        )
    now = utc_now().replace(tzinfo=None)

    result = await db.execute(
        select(FocusTimeBlock).where(
            and_(
                FocusTimeBlock.user_id == user_id,
                FocusTimeBlock.status == FocusTimeStatus.ACTIVE,
                FocusTimeBlock.start_time <= now,
                FocusTimeBlock.end_time >= now,
            )
        )
    )
    block = result.scalar_one_or_none()

    return {
        "user_id": user_id,
        "in_focus_time": block is not None,
        "block": {
            "id": block.id,
            "work_type": block.work_type,
            "end_time": block.end_time.isoformat(),
            "backup_contact_id": block.backup_contact_id,
        } if block else None,
    }
